"""
주간 자동 크롤링 스케줄러
매주 월요일 04:00에 패션/뷰티 트렌드 기사를 자동으로 크롤링합니다.
"""

import schedule
import time
import logging
from datetime import datetime
from pathlib import Path
from scrape_mutable_data import VogueKoreaScraper

# ==============================================================================
# 로깅 설정
# ==============================================================================

log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'crawler_schedule.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ==============================================================================
# 크롤링 작업 함수
# ==============================================================================

def crawl_vogue_articles():
    """매주 월요일 04:00에 실행되는 크롤링 작업"""
    logger.info("="*80)
    logger.info("주간 자동 크롤링 시작")
    logger.info("="*80)
    
    try:
        categories = ["fashion", "beauty"]
        total_articles = 0
        
        for category in categories:
            logger.info(f"\n[{category.upper()}] 크롤링 시작...")
            
            try:
                scraper = VogueKoreaScraper(category=category)
                
                # skip_existing=True: 새로운 기사만 추가
                articles = scraper.run(
                    max_articles=20,
                    min_delay=1,
                    max_delay=3,
                    skip_existing=True
                )
                
                if articles:
                    total_articles += len(articles)
                    logger.info(f"[{category}] {len(articles)}개 기사 수집 완료")
                else:
                    logger.info(f"[{category}] 새로운 기사 없음")
                
            except Exception as e:
                logger.error(f"[{category}] 크롤링 실패: {e}", exc_info=True)
                continue
        
        logger.info(f"\n총 {total_articles}개의 기사를 수집했습니다.")
        logger.info("="*80)
        logger.info("주간 자동 크롤링 완료")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"크롤링 작업 실패: {e}", exc_info=True)

# ==============================================================================
# 스케줄 설정 및 실행
# ==============================================================================

def setup_schedule():
    """크롤링 스케줄 설정"""
    
    # 매주 월요일 04:00에 실행
    schedule.every().monday.at("04:00").do(crawl_vogue_articles)
    
    logger.info("스케줄 설정 완료")
    logger.info("- 매주 월요일 04:00에 자동 크롤링 실행")
    logger.info(f"- 로그 파일: {log_dir / 'crawler_schedule.log'}")
    
    return schedule

def run_scheduler():
    """스케줄러 실행 (무한 루프)"""
    logger.info("크롤링 스케줄러 시작")
    logger.info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    setup_schedule()
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 스케줄 확인
            
    except KeyboardInterrupt:
        logger.info("\n스케줄러 중단됨 (Ctrl+C)")
    except Exception as e:
        logger.error(f"스케줄러 오류: {e}", exc_info=True)

# ==============================================================================
# 테스트 모드 (즉시 실행)
# ==============================================================================

def test_crawler():
    """크롤링 테스트 (즉시 실행)"""
    logger.info("테스트 모드: 즉시 크롤링 시작")
    crawl_vogue_articles()

# ==============================================================================
# CLI 인터페이스
# ==============================================================================

if __name__ == "__main__":
    import sys
    logger.info("="*80)
    logger.info("Vogue Korea 자동 크롤링 스케줄러")
    logger.info("="*80)
    logger.info("사용법:")
    logger.info("  python scheduler.py schedule  : 스케줄러 실행 (매주 월요일 04:00)")
    logger.info("  python scheduler.py test      : 테스트 실행 (즉시 실행)")
    logger.info("  python scheduler.py status    : 스케줄 상태 확인")
    logger.info("예시:")
    logger.info("  python scheduler.py schedule")
    logger.info("="*80)

    if len(sys.argv) < 2:
        logger.error("명령어를 입력해주세요: schedule, test, status")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "schedule":
        logger.info("✓ 스케줄러 시작 (매주 월요일 04:00)")
        logger.info("✓ 종료하려면 Ctrl+C 누르세요")
        logger.info("")
        run_scheduler()

    elif command == "test":
        logger.info("✓ 테스트 크롤링 시작")
        test_crawler()

    elif command == "status":
        logger.info("현재 스케줄:")
        setup_schedule()
        for job in schedule.jobs:
            logger.info(f"  {job}")
        logger.info("스케줄러를 실행하려면: python scheduler.py schedule")

    else:
        logger.error(f"알 수 없는 명령어: {command}")
        logger.error("사용 가능한 명령어: schedule, test, status")
        sys.exit(1)
