from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from contextlib import asynccontextmanager
import os
import httpx

# routers 폴더의 user_router를 import
from routers import user_router
from routers import chatbot_router
from routers import survey_router
from routers import feedback_router
from routers import admin_router
from routers import image_router

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== RAG 서비스 통합 헬퍼 ====================
class RAGServiceClient:
    """RAG 서비스 API 클라이언트"""
    
    def __init__(self, rag_api_url: str = None):
        """
        Args:
            rag_api_url: RAG API 베이스 URL (예: http://localhost:8001)
        """
        if rag_api_url is None:
            # 환경변수 또는 기본값 사용
            rag_host = os.getenv("RAG_HOST", "127.0.0.1")
            rag_port = os.getenv("RAG_PORT", "8001")
            rag_api_url = f"http://{rag_host}:{rag_port}"
        
        self.rag_api_url = rag_api_url
        self.logger = logging.getLogger(f"{__name__}.RAGServiceClient")
    
    async def query_rag(self, query: str, temperature: float = 0.7, max_tokens: int = 2048, force_route: int = None) -> dict:
        """
        RAG 서비스에 쿼리 전송
        
        Args:
            query: 사용자 질문
            temperature: 생성 온도 (0.0 - 1.0)
            max_tokens: 최대 토큰 수
            force_route: 강제 라우팅 (1-4, 테스트용)
        
        Returns:
            dict: RAG 서비스 응답 또는 에러
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.rag_api_url}/query",
                    json={
                        "query": query,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "force_route": force_route
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    self.logger.warning(f"RAG 서비스 에러 (상태: {response.status_code}): {response.text}")
                    return {
                        "success": False,
                        "error": f"RAG 서비스 에러: {response.status_code}",
                        "answer": None
                    }
        except Exception as e:
            self.logger.error(f"RAG 서비스 호출 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": None
            }
    
    async def get_health(self) -> dict:
        """RAG 서비스 헬스 체크"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.rag_api_url}/health")
                if response.status_code == 200:
                    return response.json()
                return {"status": "error", "message": f"상태 코드: {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# 전역 RAG 클라이언트 인스턴스
rag_client = RAGServiceClient()
# ==============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 lifespan 관리"""
    # 시작 시 실행되는 코드
    logger.info("🚀 퍼스널컬러 진단 서버가 시작됩니다...")
    logger.info("💡 데이터베이스 설정이 필요하면 'alembic upgrade head'를 실행하세요.")
    
    yield  # 여기서 애플리케이션이 실행됨
    
    # 종료 시 실행되는 코드 (필요한 경우)
    logger.info("🔚 퍼스널컬러 진단 서버가 종료됩니다...")

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173", # React 개발 서버 주소
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# @app.get("/")
# def read_root():
#     return {"message": "퍼스널컬러 진단 AI 백엔드 서버"}

# RequestValidationError 핸들러 추가 (422 에러 상세 정보)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"❌ 422 Validation Error from {request.url}")
    print(f"❌ Errors: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
        },
    )
  
# ==================== RAG 서비스 통합 엔드포인트 ====================

@app.get("/api/rag/health")
async def rag_health_check():
    """RAG 서비스 헬스 체크"""
    health = await rag_client.get_health()
    if health.get("status") == "error":
        return {"status": "unavailable", "details": health}
    return {"status": "available", "details": health}


@app.post("/api/rag/query")
async def query_rag_service(query: str, temperature: float = 0.7, max_tokens: int = 2048, force_route: int = None):
    """
    RAG 서비스에 쿼리 전송
    
    Args:
        query: 사용자 질문
        temperature: 생성 온도 (0.0 - 1.0)
        max_tokens: 최대 토큰 수
        force_route: 강제 라우팅 (1-4, 테스트용)
    """
    result = await rag_client.query_rag(query, temperature, max_tokens, force_route)
    return result

# user_router.py에 있는 API들을 앱에 포함
app.include_router(user_router.router)
app.include_router(chatbot_router.router)
app.include_router(survey_router.router)
app.include_router(feedback_router.router)
app.include_router(admin_router.router)
app.include_router(image_router.router)

