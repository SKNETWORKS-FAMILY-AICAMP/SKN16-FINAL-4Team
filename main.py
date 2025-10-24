from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from contextlib import asynccontextmanager

# routers 폴더의 user_router를 import
from routers import user_router
from routers import chatbot_router
from routers import survey_router
from routers import feedback_router
from routers import admin_router

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@app.get("/")
def read_root():
    return {"message": "퍼스널컬러 진단 AI 백엔드 서버"}

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

# user_router.py에 있는 API들을 앱에 포함
app.include_router(user_router.router)
app.include_router(chatbot_router.router)
app.include_router(survey_router.router)
app.include_router(feedback_router.router)
app.include_router(admin_router.router)