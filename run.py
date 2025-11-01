import os
import uvicorn
import logging
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# watchfiles DEBUG 로깅 비활성화
logging.getLogger("watchfiles").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

if __name__ == "__main__":
    logger.info("🚀 퍼스널컬러 진단 서버를 시작합니다...")
    
    # migrations/versions 폴더 확인 및 생성
    versions_dir = os.path.join(os.path.dirname(__file__), 'migrations', 'versions')
    if not os.path.exists(versions_dir):
        os.makedirs(versions_dir)
        logger.info(f"📁 생성된 마이그레이션 버전 폴더: {versions_dir}")
    
    # 데이터베이스 관리는 Alembic을 사용하세요
    logger.info("💡 데이터베이스 설정이 필요하면 'alembic upgrade head'를 실행하세요.")
    
    # 서버 실행
    logger.info(f"🌐 서버 실행: http://{HOST}:{PORT}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)