"""
불변 지식 RAG API 서버 (Gemini File Search 기반)
Context Caching 적용 - 최종 완결판

주요 기능:
1. 5개 PDF 파일 자동 상태 점검 및 복구
2. Context Caching으로 토큰 90% 절감
3. 자동 캐시 갱신 및 관리
4. 상세한 토큰 사용량 로깅
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import google.generativeai as genai
from google.generativeai import caching
from datetime import datetime, timedelta, timezone
import logging

# ============================================================
# 설정 및 초기화
# ============================================================

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

# Gemini API 키 설정 및 검증
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

genai.configure(api_key=GEMINI_API_KEY)

# ============================================================
# FastAPI 앱 설정
# ============================================================

app = FastAPI(
    title="불변지식 RAG API (Context Caching)",
    description="퍼스널 컬러 지식 기반 RAG 시스템 - 토큰 최적화 버전",
    version="2.0.0"
)

# CORS 설정 (다른 도메인에서 API 호출 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# ============================================================
# Pydantic 모델 정의 (요청/응답 스키마)
# ============================================================

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
    cache_active: bool
    model: str
    timestamp: str


# ============================================================
# 불변 지식 RAG 시스템 클래스
# ============================================================

class ImmutableKnowledgeRAG:
    """
    불변 지식 RAG 시스템 (Context Caching 적용)
    
    주요 기능:
    - 5개 PDF 파일 자동 로드 및 상태 점검
    - Context Caching으로 토큰 사용량 90% 절감
    - 캐시 자동 갱신 및 만료 관리
    - 파일 삭제 시 자동 재업로드
    """
    
    def __init__(self):
        """RAG 시스템 초기화"""
        self.model_name = MODEL_NAME
        self.uploaded_files = []  # Gemini에 업로드된 파일 객체 리스트
        self.file_manager = get_file_manager()  # 파일 관리자 (상태 점검, 재업로드)
        self.cached_content = None  # Context Caching 객체
        
        # 파일 초기화 및 캐시 설정
        self._initialize_files()
        self._setup_cache()
    
    def _initialize_files(self):
        """
        파일 초기화 (상태 점검 및 자동 복구)
        
        동작:
        1. 5개 PDF 파일의 Gemini 서버 상태 확인
        2. 삭제되거나 접근 불가 파일 감지
        3. 문제 발견 시 로컬 백업에서 자동 재업로드
        4. 파일 객체 리스트 업데이트
        """
        logger.info("불변 지식 파일 초기화 중...")
        
        # 파일 상태 점검 및 복구 (file_manager.py에서 처리)
        verified_file_ids = self.file_manager.verify_and_repair_files()
        
        if not verified_file_ids:
            logger.error("❌ 사용 가능한 파일이 없습니다!")
            return
        
        # 검증된 파일 ID를 실제 파일 객체로 변환
        self.uploaded_files = self.file_manager.get_active_files(verified_file_ids)
        
        logger.info(f"\n✅ 총 {len(self.uploaded_files)}개 파일 로드 완료\n")
    
    def _setup_cache(self):
        """
        Context Caching 설정
        
        동작:
        1. 5개 PDF 파일을 Gemini 서버에 캐시로 생성
        2. 캐시 생성 시 system_instruction 포함
        3. TTL(Time To Live) 1시간 설정
        4. 캐시된 토큰 수 로깅
        
        효과:
        - 첫 요청: 캐시 생성 (약 179K 토큰 소비)
        - 이후 요청: 질문만 전송 (약 500 토큰만 소비)
        - 비용 절감: 약 90-99%
        """
        if not self.uploaded_files:
            logger.warning("⚠️  파일이 없어 캐싱을 건너뜁니다.")
            return
        
        try:
            logger.info("="*60)
            logger.info("📦 Context Caching 설정 중...")
            logger.info("="*60)
            
            # 기존 캐시가 있다면 삭제
            if self.cached_content:
                try:
                    self.cached_content.delete()
                    logger.info("🗑️  기존 캐시 삭제")
                except:
                    pass
            
            # 새 캐시 생성
            self.cached_content = caching.CachedContent.create(
                model=self.model_name,
                display_name="Personal_Color_Knowledge_Base",
                
                # 시스템 지시사항 (AI의 역할 정의)
                system_instruction=(
                    "당신은 퍼스널 컬러 전문가입니다. "
                    "제공된 5개의 PDF 문서(봄/여름/가을/겨울 퍼스널 컬러 가이드)를 기반으로 "
                    "정확하고 상세한 답변을 제공하세요. "
                    "답변 시 구체적인 색상 예시와 근거를 포함하세요."
                ),
                
                # 캐시할 내용 (5개 PDF 파일)
                contents=self.uploaded_files,
                
                # 캐시 유효 시간 (1시간)
                ttl=timedelta(hours=1),
            )
            
            # 캐시 생성 결과 로깅
            logger.info("✅ 캐시 생성 완료!")
            logger.info(f"   캐시 ID: {self.cached_content.name}")
            
            # 캐시된 토큰 수 출력
            if hasattr(self.cached_content, 'usage_metadata'):
                total_tokens = self.cached_content.usage_metadata.total_token_count
                logger.info(f"   📊 캐시된 토큰: {total_tokens:,}개")
                logger.info(f"   💰 절약 효과: 매 요청마다 ~{total_tokens:,} 토큰 절약!")
            
            # 캐시 만료 시간
            logger.info(f"   ⏰ 만료 시간: {self.cached_content.expire_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("="*60 + "\n")
            
        except Exception as e:
            logger.error(f"❌ 캐싱 실패 (일반 모드로 전환): {e}")
            logger.error(f"   오류 타입: {type(e).__name__}")
            self.cached_content = None
    
    def _refresh_cache_if_needed(self):
        """
        캐시 상태 확인 및 자동 갱신
        
        동작:
        1. 캐시 만료 시간 확인
        2. 만료되었으면 재생성
        3. 만료 5분 전이면 TTL 연장
        4. 캐시가 없으면 생성 시도
        
        호출 시점: 매 query() 요청마다
        """
        # 캐시가 없으면 생성 시도
        if not self.cached_content:
            logger.warning("⚠️  캐시가 없습니다. 재생성 시도...")
            self._setup_cache()
            return
        
        try:
            now = datetime.now(timezone.utc)
            
            # 만료까지 남은 시간 계산 (초)
            time_until_expiry = (self.cached_content.expire_time - now).total_seconds()
            
            if time_until_expiry <= 0:
                # 캐시 만료됨 - 재생성 필요
                logger.info("🔄 캐시 만료 - 재생성 중...")
                self._setup_cache()
                
            elif time_until_expiry < 300:  # 5분 미만 남음
                # 만료 임박 - TTL 연장 시도
                logger.info(f"⏰ 캐시 만료 임박 ({time_until_expiry/60:.1f}분 남음) - TTL 연장 중...")
                try:
                    self.cached_content.update(ttl=timedelta(hours=1))
                    logger.info("✅ 캐시 TTL 1시간 연장")
                except Exception as e:
                    logger.warning(f"TTL 연장 실패, 재생성: {e}")
                    self._setup_cache()
            else:
                # 캐시 정상 상태
                logger.debug(f"✅ 캐시 정상 ({time_until_expiry/60:.1f}분 남음)")
                
        except Exception as e:
            logger.error(f"캐시 상태 확인 실패: {e}")
            logger.info("캐시 재생성 시도...")
            self._setup_cache()
    
    def query(
        self, 
        question: str, 
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        include_sources: bool = True
    ) -> Dict:
        """
        불변 지식을 기반으로 질문에 답변 (Context Caching 사용)
        
        Args:
            question: 사용자 질문
            temperature: 생성 온도 (0.0~1.0, 낮을수록 일관성↑)
            max_tokens: 최대 출력 토큰 수
            include_sources: 출처 정보 포함 여부
            
        Returns:
            답변 및 메타데이터 딕셔너리
            
        동작 흐름:
        1. 파일 존재 여부 확인
        2. 캐시 상태 점검 및 갱신
        3. 캐시 사용 여부에 따라 모델 생성
           - 캐시 있음: 질문만 전송 (초고속, 초저비용)
           - 캐시 없음: 파일 + 질문 전송 (느림, 비용 높음)
        4. 응답 생성
        5. 토큰 사용량 로깅
        6. 출처 정보 추출 (선택)
        7. 결과 반환
        """
        try:
            # 1. 파일 존재 확인
            if not self.uploaded_files:
                raise Exception("사용 가능한 불변 지식 파일이 없습니다.")
            
            # 2. 캐시 상태 확인 및 자동 갱신
            self._refresh_cache_if_needed()
            
            # 3. 모델 생성 설정
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            
            # 4. 캐시 사용 여부에 따라 모델 생성 및 요청
            if self.cached_content:
                # ===== 캐시 사용 모드 (권장) =====
                logger.info(f"📦 캐시 사용 - 질문: {question[:50]}...")
                
                # 캐시된 컨텍스트로 모델 생성
                # 75MB PDF는 이미 캐시에 있으므로 질문만 전송!
                model = genai.GenerativeModel.from_cached_content(
                    cached_content=self.cached_content,
                    generation_config=generation_config
                )
                
                # 질문만 전송 (매우 빠르고 저렴)
                response = model.generate_content(question)
                
            else:
                # ===== 일반 모드 (캐시 없음) =====
                logger.warning("⚠️  캐시 미사용 - 일반 모드 (비효율적)")
                
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    generation_config=generation_config
                )
                
                # 모든 파일 + 질문을 함께 전송 (느리고 비쌈)
                content_parts = self.uploaded_files + [question]
                response = model.generate_content(content_parts)
            
            # 5. 토큰 사용량 상세 로깅
            cached_tokens = 0
            prompt_tokens = 0
            output_tokens = 0
            total_tokens = 0
            
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                prompt_tokens = usage.prompt_token_count
                output_tokens = usage.candidates_token_count
                total_tokens = usage.total_token_count
                
                # 캐시된 토큰 수 (Context Caching 사용 시)
                if hasattr(usage, 'cached_content_token_count'):
                    cached_tokens = usage.cached_content_token_count
                
                # 토큰 사용량 상세 출력
                logger.info("="*60)
                logger.info("📊 토큰 사용량 상세:")
                logger.info(f"   💾 캐시된 토큰: {cached_tokens:,} (90% 할인!)")
                logger.info(f"   📥 입력 토큰:   {prompt_tokens:,}")
                logger.info(f"   📤 출력 토큰:   {output_tokens:,}")
                logger.info(f"   📊 총 토큰:     {total_tokens:,}")
                
                if cached_tokens > 0:
                    savings = (cached_tokens / (cached_tokens + prompt_tokens)) * 100
                    logger.info(f"   💰 절약률:      {savings:.1f}%")
                
                logger.info("="*60)
            
            # 6. 응답 텍스트 추출
            answer = response.text
            
            # 7. 출처 정보 추출 (선택)
            sources = []
            if include_sources and hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'citation_metadata') and candidate.citation_metadata:
                    for citation in candidate.citation_metadata.citation_sources:
                        if hasattr(citation, 'uri'):
                            sources.append(citation.uri)
            
            # 8. 메타데이터 구성
            metadata = {
                "model": self.model_name,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "files_used": len(self.uploaded_files),
                "cache_active": self.cached_content is not None,
                "cached_tokens": cached_tokens,
                "prompt_tokens": prompt_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "token_savings_percent": round((cached_tokens / (cached_tokens + prompt_tokens)) * 100, 1) if cached_tokens > 0 else 0,
            }
            
            logger.info("✅ 답변 생성 완료\n")
            
            # 9. 결과 반환
            return {
                "success": True,
                "answer": answer,
                "query": question,
                "sources": sources if sources else None,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ 쿼리 처리 실패: {e}")
            raise e


# ============================================================
# RAG 시스템 초기화 (서버 시작 시 자동 실행)
# ============================================================

rag_system = ImmutableKnowledgeRAG()


# ============================================================
# FastAPI 엔드포인트 정의
# ============================================================

@app.get("/", response_model=Dict)
async def root():
    """
    루트 엔드포인트
    API 정보 및 사용 가능한 엔드포인트 목록 반환
    """
    return {
        "service": "불변지식 RAG API (Context Caching)",
        "version": "2.0.0",
        "status": "running",
        "cache_active": rag_system.cached_content is not None,
        "endpoints": {
            "health": "GET /health - 서버 상태 확인",
            "query": "POST /query - RAG 쿼리 (메인 기능)",
            "files": "GET /files - 파일 목록 조회",
            "cache": "GET /cache - 캐시 상태 확인",
            "refresh": "POST /refresh - 파일 및 캐시 갱신",
            "cache_recreate": "POST /cache/recreate - 캐시 강제 재생성",
            "docs": "GET /docs - API 문서 (Swagger UI)",
        }
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    헬스 체크 엔드포인트
    서버 상태, 로드된 파일 수, 캐시 활성 여부 확인
    """
    return HealthCheckResponse(
        status="healthy" if rag_system.uploaded_files else "degraded",
        files_loaded=len(rag_system.uploaded_files),
        cache_active=rag_system.cached_content is not None,
        model=rag_system.model_name,
        timestamp=datetime.now().isoformat()
    )


@app.post("/query", response_model=KnowledgeQueryResponse)
async def query_knowledge(request: KnowledgeQueryRequest):
    """
    불변 지식 기반 RAG 쿼리 (메인 기능)
    
    Context Caching 적용으로:
    - 첫 요청: ~179K 토큰 (캐시 생성)
    - 이후 요청: ~500 토큰 (질문만)
    - 비용 절감: 약 90-99%
    """
    try:
        # 파일 로드 확인
        if not rag_system.uploaded_files:
            raise HTTPException(
                status_code=503,
                detail="불변 지식 파일이 로드되지 않았습니다. 관리자에게 문의하세요."
            )
        
        # RAG 쿼리 실행
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
    """
    불변 지식 파일 목록 조회
    현재 로드된 5개 PDF 파일의 상세 정보 반환
    """
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


@app.get("/cache", response_model=Dict)
async def cache_info():
    """
    캐시 상태 정보 조회
    캐시 ID, 만료 시간, 캐시된 토큰 수 등 반환
    """
    if not rag_system.cached_content:
        return {
            "cache_active": False,
            "message": "캐시가 비활성화되어 있습니다."
        }
    
    cache = rag_system.cached_content
    now = datetime.now(timezone.utc)
    time_until_expiry = (cache.expire_time - now).total_seconds()
    
    info = {
        "cache_active": True,
        "cache_name": cache.name,
        "display_name": cache.display_name,
        "model": cache.model,
        "expire_time": cache.expire_time.isoformat(),
        "time_until_expiry_seconds": int(time_until_expiry),
        "time_until_expiry_minutes": round(time_until_expiry / 60, 1),
    }
    
    if hasattr(cache, 'usage_metadata'):
        info["cached_tokens"] = cache.usage_metadata.total_token_count
    
    return info


@app.post("/refresh", response_model=Dict)
async def refresh_files():
    """
    파일 갱신 및 재점검 + 캐시 재생성
    
    동작:
    1. 5개 PDF 파일 상태 점검
    2. 문제 발견 시 자동 재업로드
    3. 캐시 재생성
    
    호출 시기: 파일이 삭제되었거나 문제가 의심될 때
    """
    try:
        # 파일 재점검 및 복구
        rag_system._initialize_files()
        
        # 캐시 재생성
        rag_system._setup_cache()
        
        return {
            "success": True,
            "message": "파일 및 캐시 갱신 완료",
            "files_loaded": len(rag_system.uploaded_files),
            "cache_active": rag_system.cached_content is not None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"갱신 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cache/recreate", response_model=Dict)
async def recreate_cache():
    """
    캐시 강제 재생성
    
    사용 케이스:
    - 캐시 오류 발생 시
    - 파일 내용 업데이트 후
    - 시스템 지시사항 변경 후
    """
    try:
        logger.info("🔄 캐시 강제 재생성 요청")
        rag_system._setup_cache()
        
        return {
            "success": True,
            "message": "캐시 재생성 완료",
            "cache_active": rag_system.cached_content is not None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"캐시 재생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 서버 직접 실행 (개발용)
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    print("="*60)
    print("🚀 불변지식 RAG API 서버 시작 (Context Caching)")
    print("="*60)
    print(f"🤖 모델: {MODEL_NAME}")
    print(f"📦 Context Caching: 활성화")
    print(f"💰 예상 절약: 토큰 90-99% 절감")
    print(f"🌐 서버: http://localhost:8001")
    print(f"📖 API 문서: http://localhost:8001/docs")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")