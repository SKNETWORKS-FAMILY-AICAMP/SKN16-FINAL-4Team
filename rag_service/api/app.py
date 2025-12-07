"""
통합 지식 RAG API 서버

기능:
1. OpenAI 기반 지능형 라우팅 (GPT-4o-mini)
2. 불변 지식 (퍼스널 컬러) + 가변 지식 (Vogue 트렌드) 통합
3. Context Caching 옵션화 (개발: OFF, 프로덕션: ON)
4. 단일 엔드포인트로 모든 지식 접근

라우팅:
1. RAG 불필요 (일반 대화)
2. 불변 지식만
3. 가변 지식만
4. 불변 + 가변 통합
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
import logging
# google.generativeai는 core 모듈에서 사용되므로 이곳에서는 불필요하여 제거

# ============================================================
# 설정 및 핸들러 import
# ============================================================

from ..core import (
    USE_CONTEXT_CACHING,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    get_router,
    get_immutable_handler,
    get_mutable_handler,
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# FastAPI 앱 설정
# ============================================================

app = FastAPI(
    title="통합 지식 RAG API",
    description="퍼스널 컬러 + 패션 트렌드 통합 지식 시스템",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Pydantic 모델 정의
# ============================================================

class UnifiedQueryRequest(BaseModel):
    """통합 지식 검색 요청"""
    query: str = Field(..., description="사용자 질문")
    temperature: Optional[float] = Field(DEFAULT_TEMPERATURE, description="생성 온도")
    max_tokens: Optional[int] = Field(DEFAULT_MAX_TOKENS, description="최대 토큰 수")
    force_route: Optional[int] = Field(None, description="강제 라우팅 (1-4, 테스트용)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "봄 웜톤에게 어울리는 2025년 트렌드 립스틱 추천해줘",
                "temperature": 0.7,
                "max_tokens": 2048
            }
        }


class UnifiedQueryResponse(BaseModel):
    """통합 지식 검색 응답"""
    success: bool
    answer: str
    query: str
    route: int = Field(..., description="라우팅 결과 (1-4)")
    route_description: str
    sources: list[str] = Field(default_factory=list)
    metadata: Dict
    timestamp: str


class HealthCheckResponse(BaseModel):
    """헬스 체크 응답"""
    status: str
    immutable_files: int
    mutable_files: int
    caching_enabled: bool
    router_model: str
    timestamp: str


# ============================================================
# 통합 지식 RAG 시스템
# ============================================================

class UnifiedKnowledgeRAG:
    """
    통합 지식 RAG 시스템
    
    라우팅 → 지식 처리 → 응답 생성
    """
    
    def __init__(self):
        # 각 컴포넌트 초기화
        self.router = get_router()
        self.immutable_handler = get_immutable_handler()
        self.mutable_handler = get_mutable_handler()
        
        logger.info("="*60)
        logger.info("🚀 통합 지식 RAG 시스템 초기화 완료")
        logger.info(f"   Context Caching: {'ON' if USE_CONTEXT_CACHING else 'OFF'}")
        logger.info(f"   불변 지식: {len(self.immutable_handler.uploaded_files)}개 파일")
        logger.info(f"   가변 지식: {len(self.mutable_handler.uploaded_files)}개 파일")
        logger.info("="*60 + "\n")
    
    def query(
        self,
        question: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        force_route: Optional[int] = None
    ) -> Dict:
        """
        통합 질문 처리
        
        흐름:
        1. 라우팅 판단 (OpenAI)
        2. 지식 소스 선택
        3. RAG 실행
        4. 응답 반환
        """
        try:
            logger.info("="*60)
            logger.info(f"📥 질문: {question}")
            logger.info("="*60)
            
            # 1. 라우팅 (강제 라우팅 또는 자동 판단)
            if force_route:
                route = force_route
                logger.info(f"⚡ 강제 라우팅: {route}")
            else:
                route = self.router.route(question)
            
            route_desc = self.router.get_route_description(route)
            
            # 2. 라우팅에 따라 처리
            if route == 1:
                # RAG 불필요 - 기본 응답
                answer = self._handle_general(question)
                sources = []
                metadata = {
                    "route": route,
                    "route_description": route_desc,
                    "rag_used": False
                }
            
            elif route == 2:
                # 불변 지식만 (원본 query() 사용, 안전 필터 우회 로직 포함)
                result = self.immutable_handler.query(question, temperature, max_tokens)
                
                # ✅ None 응답 처리
                if result is None:
                    logger.error(f"❌ 불변 지식 핸들러 쿼리 실패 (None 응답)")
                    raise RuntimeError("불변 지식 쿼리 실패: 유효한 응답 없음")
                
                answer = result['answer']
                # Use citations if available, otherwise generic
                citations = result['metadata'].get('citations', [])
                sources = citations if citations else ["Personal Color Analysis Guide"]
                metadata = {
                    "route": route,
                    "route_description": route_desc,
                    "rag_used": True,
                    **result['metadata']
                }
            
            elif route == 3:
                # 가변 지식만 (실패 시 불변 지식으로 폴백)
                try:
                    result = self.mutable_handler.query(question, temperature, max_tokens)
                    answer = result['answer']
                    # Use file_names if available
                    file_names = result['metadata'].get('file_names', [])
                    sources = file_names if file_names else ["Vogue Korea Fashion Trends"]
                    metadata = {
                        "route": route,
                        "route_description": route_desc,
                        "rag_used": True,
                        **result['metadata']
                    }
                except Exception as e:
                    logger.warning(f"⚠️  가변 지식 쿼리 실패: {e}. 불변 지식으로 폴백합니다.")
                    # 불변 지식으로 폴백
                    result = self.immutable_handler.query(question, temperature, max_tokens)
                    
                    # ✅ None 응답 체크
                    if result is None:
                        raise RuntimeError("가변 지식 실패 후 불변 지식 폴백도 실패했습니다.")
                    
                    answer = result['answer']
                    sources = ["immutable_knowledge (fallback)"]
                    metadata = {
                        "route": 2,  # 실제로는 2번 경로 사용
                        "route_description": "Fallback to immutable knowledge",
                        "rag_used": True,
                        "fallback_from_route": route,
                        **result['metadata']
                    }
            
            elif route == 4:
                # 불변 + 가변 통합 (실패 시 불변만 사용)
                try:
                    answer, sources, metadata = self._handle_combined(
                        question, temperature, max_tokens
                    )
                    metadata["route"] = route
                    metadata["route_description"] = route_desc
                except Exception as e:
                    logger.warning(f"⚠️  통합 쿼리 실패: {e}. 불변 지식만 사용합니다.")
                    # 불변 지식만으로 폴백
                    result = self.immutable_handler.query(question, temperature, max_tokens)
                    
                    # ✅ None 응답 체크
                    if result is None:
                        raise RuntimeError("통합 쿼리 실패 후 불변 지식 폴백도 실패했습니다.")
                    
                    answer = result['answer']
                    sources = ["immutable_knowledge (fallback)"]
                    metadata = {
                        "route": 2,
                        "route_description": "Fallback to immutable knowledge",
                        "rag_used": True,
                        "fallback_from_route": route,
                        **result['metadata']
                    }
            
            else:
                raise ValueError(f"잘못된 라우팅: {route}")
            
            logger.info(f"✅ 처리 완료: {route_desc}\n")
            
            return {
                "success": True,
                "answer": answer,
                "query": question,
                "route": route,
                "route_description": route_desc,
                "sources": sources,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ 통합 쿼리 실패: {e}")
            raise e
    
    def _handle_general(self, question: str) -> str:
        """
        일반 대화 처리 (RAG 없음)
        
        간단한 응답 생성
        """
        logger.info("💬 일반 대화 모드")
        
        # 간단한 기본 응답
        responses = {
            "안녕": "안녕하세요! 퍼스널 컬러와 패션 트렌드에 대해 궁금하신 것이 있으신가요?",
            "도움": "퍼스널 컬러 진단, 색상 추천, 최신 패션 트렌드 등에 대해 도움을 드릴 수 있습니다.",
        }
        
        for keyword, response in responses.items():
            if keyword in question.lower():
                return response
        
        return "무엇을 도와드릴까요? 퍼스널 컬러나 패션 트렌드에 대해 질문해주세요."
    
    
    def _handle_combined(
        self,
        question: str,
        temperature: float,
        max_tokens: int
    ) -> tuple[str, list, Dict]:
        """
        불변 + 가변 지식 통합 처리
        
        전략:
        1. 불변 지식: File Search (퍼스널 컬러 관점)
        2. 가변 지식: OpenAI (최신 트렌드 관점)
        3. 두 답변을 통합하여 최종 응답 생성
        """
        logger.info("🔀 불변 + 가변 지식 통합 모드")
        
        try:
            # 불변 지식 쿼리 (File Search)
            logger.info("  📚 불변 지식 조회 중...")
            immutable_result = self.immutable_handler.query(
                question, temperature, max_tokens
            )
            
            # ✅ None 응답 체크
            if immutable_result is None:
                logger.error("❌ 불변 지식 쿼리 실패 (None 응답)")
                raise RuntimeError("불변 지식 쿼리 실패")
            
            # 가변 지식 쿼리 (OpenAI)
            logger.info("  📰 가변 지식 조회 중...")
            mutable_result = self.mutable_handler.query(
                question, temperature, max_tokens
            )
            
            # ✅ None 응답 체크
            if mutable_result is None:
                logger.error("❌ 가변 지식 쿼리 실패 (None 응답)")
                raise RuntimeError("가변 지식 쿼리 실패")
            
            # 두 답변 통합
            combined_answer = f"""**퍼스널 컬러 관점:**
{immutable_result['answer']}

**최신 트렌드 관점:**
{mutable_result['answer']}

---
위 두 가지 관점을 종합하여 답변드렸습니다."""
            
            # Combine sources
            imm_citations = immutable_result.get('metadata', {}).get('citations', [])
            mut_snippets = mutable_result.get('metadata', {}).get('reference_snippets', [])
            
            sources = []
            if imm_citations:
                sources.extend(imm_citations)
            else:
                sources.append("Personal Color Analysis Guide")
                
            if mut_snippets:
                sources.extend(mut_snippets)
            else:
                # fallback to file names
                mut_files = mutable_result.get('metadata', {}).get('file_names', [])
                if mut_files:
                    sources.extend(mut_files)
                else:
                    sources.append("Vogue Korea Fashion Trends")
            
            # ✅ 메타데이터 일관성 처리 (files_used 키 존재 확인)
            immutable_files = immutable_result.get('metadata', {}).get('files_used', 1)
            mutable_files = mutable_result.get('metadata', {}).get('files_used', 0)
            
            metadata = {
                "rag_used": True,
                "immutable_files": immutable_files,
                "mutable_files": mutable_files,
                "combined": True,
                "immutable_retrieval": immutable_result.get('metadata', {}).get('retrieval_method', 'gemini_file_search'),
                "mutable_retrieval": mutable_result.get('metadata', {}).get('retrieval_method', 'openai_rag'),
                "immutable_model": immutable_result.get('metadata', {}).get('model', 'gemini-2.5-flash'),
                "mutable_model": mutable_result.get('metadata', {}).get('model', 'gpt-4o-mini')
            }
            
            logger.info(f"✅ 통합 처리 성공: 불변({immutable_files}파일) + 가변({mutable_files}파일)")
            
            return combined_answer, sources, metadata
            
        except Exception as e:
            logger.error(f"❌ 통합 처리 실패: {e}", exc_info=True)
            # 폴백: 불변 지식만 사용
            logger.warning("⚠️  폴백: 불변 지식만 사용")
            result = self.immutable_handler.query(question, temperature, max_tokens)
            
            # ✅ None 응답 체크
            if result is None:
                raise RuntimeError("폴백도 실패: 불변 지식 쿼리 실패")
            
            return result['answer'], ["immutable_knowledge"], result['metadata']


# ============================================================
# RAG 시스템 초기화
# ============================================================

rag_system = UnifiedKnowledgeRAG()


# ============================================================
# FastAPI 엔드포인트
# ============================================================

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "통합 지식 RAG API",
        "version": "2.0.0",
        "features": [
            "지능형 라우팅 (OpenAI GPT-4o-mini)",
            "불변 지식 (퍼스널 컬러)",
            "가변 지식 (Vogue 트렌드)",
            "통합 검색"
        ],
        "caching": USE_CONTEXT_CACHING,
        "endpoints": {
            "health": "GET /health",
            "query": "POST /query",
            "docs": "GET /docs"
        }
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """헬스 체크"""
    return HealthCheckResponse(
        status="healthy",
        immutable_files=len(rag_system.immutable_handler.uploaded_files),
        mutable_files=len(rag_system.mutable_handler.uploaded_files),
        caching_enabled=USE_CONTEXT_CACHING,
        router_model=rag_system.router.model,
        timestamp=datetime.now().isoformat()
    )


@app.post("/query", response_model=UnifiedQueryResponse)
async def unified_query(request: UnifiedQueryRequest):
    """
    통합 지식 검색
    
    자동 라우팅으로 최적의 지식 소스 선택
    """
    try:
        result = rag_system.query(
            question=request.query,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            force_route=request.force_route
        )
        
        return UnifiedQueryResponse(
            **result,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"쿼리 처리 중 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/mutable")
async def sync_mutable_knowledge():
    """가변 지식 동기화 (새 Vogue 기사 추가 시)"""
    try:
        rag_system.mutable_handler.resync()
        
        return {
            "success": True,
            "message": "가변 지식 동기화 완료",
            "files": len(rag_system.mutable_handler.uploaded_files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/routing/test")
async def test_routing(question: str):
    """
    라우팅 테스트 (개발용)
    
    질문이 어떻게 라우팅되는지 확인
    """
    route = rag_system.router.route(question)
    
    return {
        "question": question,
        "route": route,
        "description": rag_system.router.get_route_description(route),
        "routes": {
            "1": "RAG 불필요",
            "2": "불변 지식 (퍼스널 컬러)",
            "3": "가변 지식 (트렌드)",
            "4": "불변 + 가변"
        }
    }


# ============================================================
# 서버 직접 실행 (개발용)
# ============================================================

if __name__ == "__main__":
    import uvicorn
    logger.info("="*60)
    logger.info("🚀 통합 지식 RAG API 서버 시작")
    logger.info("="*60)
    logger.info(f"🧠 라우터: {rag_system.router.model}")
    logger.info(f"📚 불변 지식: {len(rag_system.immutable_handler.uploaded_files)}개 파일")
    logger.info(f"📰 가변 지식: {len(rag_system.mutable_handler.uploaded_files)}개 파일")
    logger.info(f"📦 Context Caching: {'ON' if USE_CONTEXT_CACHING else 'OFF'}")
    logger.info(f"🌐 서버: http://localhost:8000")
    logger.info(f"📖 API 문서: http://localhost:8000/docs")
    logger.info("="*60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
