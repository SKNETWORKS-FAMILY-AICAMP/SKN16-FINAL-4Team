import os
import uvicorn
import logging
from dotenv import load_dotenv
import multiprocessing
import time

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
RAG_PORT = int(os.getenv("RAG_PORT", "8001"))  # RAG API 포트


def run_main_server():
    """메인 뷰티 AI 에이전트 서버 실행"""
    logger.info(f"🎨 메인 서버 시작: http://{HOST}:{PORT}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)


def run_rag_server():
    """RAG API 서버 실행"""
    logger.info(f"📚 RAG 서버 시작: http://{HOST}:{RAG_PORT}")
    uvicorn.run(
        "rag_service.immutable_knowledge_rag_api:app", 
        host=HOST, 
        port=RAG_PORT, 
        reload=True
    )


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🚀 퍼스널컬러 진단 시스템을 시작합니다...")
    logger.info("="*60)
    
    # migrations/versions 폴더 확인 및 생성
    versions_dir = os.path.join(os.path.dirname(__file__), 'migrations', 'versions')
    if not os.path.exists(versions_dir):
        try:
            os.makedirs(versions_dir, exist_ok=True)
            logger.info(f"📁 생성된 마이그레이션 버전 폴더: {versions_dir}")
        except Exception as e:
            logger.warning(f"폴더 생성 실패: {e}")

    logger.info("💡 데이터베이스 설정이 필요하면 'alembic upgrade head'를 실행하세요.")
    
    # 두 개의 서버를 동시에 실행
    logger.info("\n📡 서버 구성:")
    logger.info(f"  🎨 메인 API: http://{HOST}:{PORT}")
    logger.info(f"  📚 RAG API:  http://{HOST}:{RAG_PORT}")
    logger.info(f"  📖 RAG 문서: http://{HOST}:{RAG_PORT}/docs")
    logger.info("="*60 + "\n")
    
    # 멀티프로세싱으로 두 서버 동시 실행
    main_process = multiprocessing.Process(target=run_main_server)
    rag_process = multiprocessing.Process(target=run_rag_server)
    
    try:
        # RAG 서버 먼저 시작 (의존성 때문에)
        rag_process.start()
        time.sleep(2)  # RAG 서버가 먼저 준비되도록 대기
        
        # 메인 서버 시작
        main_process.start()
        
        # 프로세스 대기
        main_process.join()
        rag_process.join()
        
    except KeyboardInterrupt:
        logger.info("\n\n👋 서버를 종료합니다...")
        main_process.terminate()
        rag_process.terminate()
        main_process.join()
        rag_process.join()
        logger.info("✅ 모든 서버가 정상 종료되었습니다.")