import os
import uvicorn
import logging
from dotenv import load_dotenv
from multiprocessing import Process

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
# watchfiles DEBUG 로깅 비활성화
logging.getLogger("watchfiles").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# 기본 호스트/포트
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# 🔄 기본값: 두 개의 앱을 동시에 실행 (RUN_BOTH=1)
# 단일 앱만 실행하려면 RUN_BOTH=0 환경변수 설정
RUN_BOTH = os.getenv("RUN_BOTH", "1")  # 기본값을 "1"로 변경하여 동시 실행
# 앱 경로와 포트 (필요시 환경변수로 오버라이드)
MAIN_APP_PATH = os.getenv("MAIN_APP_PATH", "main:app")
RAG_APP_PATH = os.getenv("RAG_APP_PATH", "rag_service.api:app")
MAIN_PORT = int(os.getenv("MAIN_PORT", str(PORT)))
RAG_PORT = int(os.getenv("RAG_PORT", str(PORT + 1)))


if __name__ == "__main__":
    logger.info("🚀 퍼스널컬러 진단 서버를 시작합니다...")

    # migrations/versions 폴더 확인 및 생성 (Alembic 사용 준비)
    versions_dir = os.path.join(os.path.dirname(__file__), "migrations", "versions")
    if not os.path.exists(versions_dir):
        try:
            os.makedirs(versions_dir, exist_ok=True)
            logger.info(f"📁 생성된 마이그레이션 버전 폴더: {versions_dir}")
        except Exception as e:
            logger.warning(f"폴더 생성 실패: {e}")

    logger.info("💡 데이터베이스 설정이 필요하면 'alembic upgrade head'를 실행하세요.")

    # 실행 정보 출력
    logger.info(f"🌐 호스트: {HOST}")
    logger.info(f"🔌 메인 앱 포트: {MAIN_PORT}, RAG 서비스 포트: {RAG_PORT}")
    logger.info(f"📖 메인 API 문서: http://{HOST}:{MAIN_PORT}/docs")
    logger.info(f"📖 RAG API 문서: http://{HOST}:{RAG_PORT}/docs")

    def _start_uvicorn(app_path: str, host: str, port: int, reload: bool = False):
        """uvicorn.run을 감싸는 헬퍼 (프로세스에서 호출됨)"""
        try:
            uvicorn.run(app_path, host=host, port=port, reload=reload)
        except Exception as e:
            logger.error(f"uvicorn 실행 실패({app_path}@{host}:{port}): {e}")

    if RUN_BOTH == "1":
        # 두 개 앱을 별도 프로세스로 실행 (개발: reload=False 권장)
        logger.info("⚖️ RUN_BOTH=1 - main 앱과 rag_service 앱을 동시에 실행합니다")
        logger.info(f"➡️ {MAIN_APP_PATH} -> http://{HOST}:{MAIN_PORT}")
        logger.info(f"➡️ {RAG_APP_PATH}  -> http://{HOST}:{RAG_PORT}")

        # reload는 개발환경에서만 True로 설정 가능하지만, 여러 프로세스에서 reload를 켜면 충돌이 발생할 수 있음
        p1 = Process(target=_start_uvicorn, args=(MAIN_APP_PATH, HOST, MAIN_PORT, False), daemon=False)
        p2 = Process(target=_start_uvicorn, args=(RAG_APP_PATH, HOST, RAG_PORT, False), daemon=False)

        p1.start()
        p2.start()

        try:
            p1.join()
            p2.join()
        except KeyboardInterrupt:
            logger.info("중단 신호 수신 - 자식 프로세스 종료 시도")
            p1.terminate()
            p2.terminate()
    else:
        # 단일 모드: 메인 앱만 실행 (RUN_BOTH=0 환경변수 설정 시)
        logger.info(f"⚠️ 단일 앱 모드: {MAIN_APP_PATH} 실행 (RAG 서비스 비활성화)")
        logger.info(f"✅ 메인 서비스 포트: http://{HOST}:{MAIN_PORT}")
        logger.info(f"💡 RAG 서비스를 함께 실행하려면: RUN_BOTH=1 python run.py")
        uvicorn.run(MAIN_APP_PATH, host=HOST, port=PORT, reload=True)