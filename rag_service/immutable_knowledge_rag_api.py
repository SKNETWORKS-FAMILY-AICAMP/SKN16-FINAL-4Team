"""
불변 지식 RAG API 서버 (Gemini File Search 기반)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import google.generativeai as genai
from datetime import datetime
import logging

# 설정 및 파일 관리자 import
from .config import (
    GEMINI_API_KEY,
    MODEL_NAME,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS
)
from .file_manager import get_file_manager

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API 키 설정
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

genai.configure(api_key=GEMINI_API_KEY)

# FastAPI 앱 생성
app = FastAPI(
    title="불변지식 RAG API",
    description="퍼스널 컬러 지식 기반 RAG 시스템",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모델 설정
MODEL_NAME = MODEL_NAME


class KnowledgeQueryRequest(BaseModel):
    """지식 검색 요청 모델"""
    query: str = Field(..., description="검색할 질문 또는 가공된 문구")
    temperature: Optional[float] = Field(DEFAULT_TEMPERATURE, description="생성 온도 (0.0-1.0)")
    max_tokens: Optional[int] = Field(DEFAULT_MAX_TOKENS, description="최대 토큰 수")
    include_sources: Optional[bool] = Field(True, description="출처 정보 포함 여부")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "봄 웜톤의 특징과 어울리는 메이크업을 설명해주세요",
                "temperature": 0.7,
                "max_tokens": 2048,
                "include_sources": True
            }
        }


class KnowledgeQueryResponse(BaseModel):
    """지식 검색 응답 모델"""
    success: bool = Field(..., description="성공 여부")
    answer: str = Field(..., description="RAG 기반 답변")
    query: str = Field(..., description="원본 질문")
    sources: Optional[List[str]] = Field(None, description="참조한 문서 목록")
    metadata: Dict = Field(default_factory=dict, description="메타데이터")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class HealthCheckResponse(BaseModel):
    """헬스 체크 응답 모델"""
    status: str
    files_loaded: int
    model: str
    timestamp: str


class ImmutableKnowledgeRAG:
    """불변 지식 RAG 시스템"""
    
    def __init__(self):
        self.model_name = MODEL_NAME
        self.uploaded_files = []
        self.file_manager = get_file_manager()
        self._initialize_files()
    
    def _initialize_files(self):
        """파일 초기화 (상태 점검 및 자동 복구)"""
        logger.info("불변 지식 파일 초기화 중...")
        
        # 파일 상태 점검 및 복구
        verified_file_ids = self.file_manager.verify_and_repair_files()
        
        if not verified_file_ids:
            logger.error("❌ 사용 가능한 파일이 없습니다!")
            return
        
        # 파일 객체 로드
        self.uploaded_files = self.file_manager.get_active_files(verified_file_ids)
        
        logger.info(f"\n✅ 총 {len(self.uploaded_files)}개 파일 로드 완료\n")
    
    def query(
        self, 
        question: str, 
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        include_sources: bool = True
    ) -> Dict:
        """
        불변 지식을 기반으로 질문에 답변
        
        Args:
            question: 사용자 질문
            temperature: 생성 온도
            max_tokens: 최대 토큰 수
            include_sources: 출처 포함 여부
            
        Returns:
            답변 및 메타데이터
        """
        try:
            # 파일이 없으면 에러
            if not self.uploaded_files:
                raise Exception("사용 가능한 불변 지식 파일이 없습니다.")
            
            # 모델 설정
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config
            )
            
            # 모든 파일 + 질문을 함께 전달
            content_parts = self.uploaded_files + [question]
            
            logger.info(f"질문 처리 중: {question[:50]}...")
            
            # 생성
            response = model.generate_content(content_parts)
            
            # 출처 정보 추출
            sources = []
            if include_sources and hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'citation_metadata') and candidate.citation_metadata:
                    for citation in candidate.citation_metadata.citation_sources:
                        if hasattr(citation, 'uri'):
                            sources.append(citation.uri)
            
            # 메타데이터
            metadata = {
                "model": self.model_name,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "files_used": len(self.uploaded_files),
                "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else None,
                "candidates_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else None,
            }
            
            logger.info("✅ 답변 생성 완료")
            
            return {
                "success": True,
                "answer": response.text,
                "query": question,
                "sources": sources if sources else None,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ 쿼리 처리 실패: {e}")
            raise e


# RAG 시스템 초기화 (서버 시작 시 자동 실행)
rag_system = ImmutableKnowledgeRAG()


# 나머지 엔드포인트는 동일...
@app.get("/", response_model=Dict)
async def root():
    """루트 엔드포인트"""
    return {
        "service": "불변지식 RAG API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "query": "/query (POST)",
            "docs": "/docs",
        }
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """헬스 체크"""
    return HealthCheckResponse(
        status="healthy" if rag_system.uploaded_files else "degraded",
        files_loaded=len(rag_system.uploaded_files),
        model=rag_system.model_name,
        timestamp=datetime.now().isoformat()
    )


@app.post("/query", response_model=KnowledgeQueryResponse)
async def query_knowledge(request: KnowledgeQueryRequest):
    """불변 지식 기반 RAG 쿼리"""
    try:
        if not rag_system.uploaded_files:
            raise HTTPException(
                status_code=503,
                detail="불변 지식 파일이 로드되지 않았습니다."
            )
        
        result = rag_system.query(
            question=request.query,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            include_sources=request.include_sources
        )
        
        return KnowledgeQueryResponse(**result)
        
    except Exception as e:
        logger.error(f"쿼리 처리 중 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files", response_model=Dict)
async def list_files():
    """불변 지식 파일 목록 조회"""
    files_info = []
    
    for file in rag_system.uploaded_files:
        files_info.append({
            "display_name": file.display_name,
            "file_id": file.name,
            "uri": file.uri,
            "state": file.state.name,
            "size_bytes": file.size_bytes if hasattr(file, 'size_bytes') else None
        })
    
    return {
        "total_files": len(files_info),
        "files": files_info
    }


@app.post("/refresh", response_model=Dict)
async def refresh_files():
    """파일 갱신 및 재점검"""
    try:
        rag_system._initialize_files()
        
        return {
            "success": True,
            "message": "파일 갱신 완료",
            "files_loaded": len(rag_system.uploaded_files),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    print("="*60)
    print("🚀 불변지식 RAG API 서버 시작")
    print("="*60)
    print(f"🤖 모델: {MODEL_NAME}")
    print(f"🌐 서버: http://localhost:8001")
    print(f"📖 문서: http://localhost:8001/docs")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")