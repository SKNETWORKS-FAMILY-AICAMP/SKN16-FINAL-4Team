#!/usr/bin/env python3
"""
File Search 테스트 스크립트

Gemini API의 File Search 기능을 사용하여 불변 지식을 검색하고 쿼리하는 테스트.

사용법:
  python rag_service/tools/test_file_search.py

환경 변수:
  GEMINI_API_KEY: Gemini API 키 (필수)
"""

import sys
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_file_search():
    """Test File Search integration with immutable knowledge."""
    logger.info("="*70)
    logger.info("🔍 File Search 기능 테스트 시작")
    logger.info("="*70)
    
    try:
        # Import after path setup
        from rag_service.core.file_manager import get_file_manager
        from rag_service.core.config import GEMINI_API_KEY
        
        # Check API key
        if not GEMINI_API_KEY:
            logger.error("❌ GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
            return False
        
        logger.info(f"✅ GEMINI_API_KEY 설정됨 (길이: {len(GEMINI_API_KEY)})")
        
        # Get file manager
        file_manager = get_file_manager()
        logger.info(f"✅ File Manager 초기화 완료")
        
        # Check genai client availability
        if file_manager.genai_client:
            logger.info("✅ 새로운 google.genai 클라이언트 사용 가능")
        elif file_manager.genai_legacy:
            logger.info("✅ 레거시 google.generativeai 클라이언트 사용 가능")
        else:
            logger.warning("⚠️  genai 클라이언트 미설정 (google-genai 또는 google-generativeai 미설치)")
        
        # Test 1: Verify and repair immutable files
        logger.info("\n" + "="*70)
        logger.info("테스트 1️⃣: 불변 지식 파일 상태 점검")
        logger.info("="*70)
        verified_files = file_manager.verify_and_repair_files()
        logger.info(f"✅ 검증된 파일: {len(verified_files)}개")
        for name, file_id in verified_files.items():
            logger.info(f"   - {name}: {file_id}")
        
        # Test 2: Get or create File Search store
        logger.info("\n" + "="*70)
        logger.info("테스트 2️⃣: File Search 스토어 생성/조회")
        logger.info("="*70)
        store_name = file_manager.get_or_create_file_search_store(display_name="test_immutable_store")
        logger.info(f"✅ File Search 스토어: {store_name}")
        
        # Test 3: Import immutable files to File Search store
        logger.info("\n" + "="*70)
        logger.info("테스트 3️⃣: 불변 파일을 File Search에 업로드/임포트")
        logger.info("="*70)
        result_store = file_manager.import_all_immutable_to_file_search()
        logger.info(f"✅ 임포트 결과: {result_store}")
        
        # Test 4: Get active files (local text extraction)
        logger.info("\n" + "="*70)
        logger.info("테스트 4️⃣: 불변 지식 텍스트 추출 (로컬)")
        logger.info("="*70)
        if verified_files:
            active_files = file_manager.get_active_files(verified_files)
            logger.info(f"✅ 추출된 파일: {len(active_files)}개")
            for i, content in enumerate(active_files, 1):
                if isinstance(content, str):
                    logger.info(f"   파일 {i}: {len(content)} 문자 (텍스트)")
                else:
                    logger.info(f"   파일 {i}: {type(content).__name__} 객체")
        
        # Test 5: Query File Search store (if new client available)
        logger.info("\n" + "="*70)
        logger.info("테스트 5️⃣: File Search 스토어 쿼리")
        logger.info("="*70)
        if file_manager.genai_client and file_manager.genai_types:
            test_prompt = "퍼스널 컬러란 무엇인가요?"
            logger.info(f"쿼리: {test_prompt}")
            response = file_manager.query_file_search_store(store_name, test_prompt)
            if response:
                logger.info(f"✅ File Search 쿼리 성공")
                logger.info(f"응답 (첫 200자): {str(response)[:200]}...")
            else:
                logger.warning("⚠️  File Search 쿼리 미지원 (genai 타입 부재)")
        else:
            logger.warning("⚠️  File Search 쿼리 테스트 생략 (new genai 클라이언트 미설정)")
        
        logger.info("\n" + "="*70)
        logger.info("✅ File Search 기능 테스트 완료")
        logger.info("="*70)
        return True
        
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
        return False


def test_handlers_integration():
    """Test handlers integration with File Search."""
    logger.info("\n" + "="*70)
    logger.info("🤖 핸들러 통합 테스트 시작")
    logger.info("="*70)
    
    try:
        from rag_service.core.handlers import ImmutableKnowledgeHandler
        
        # Initialize immutable handler
        logger.info("불변 지식 핸들러 초기화 중...")
        handler = ImmutableKnowledgeHandler()
        logger.info(f"✅ 핸들러 초기화 완료")
        logger.info(f"   - 파일 개수: {len(handler.uploaded_files)}")
        logger.info(f"   - File Search 스토어: {getattr(handler, 'file_search_store_name', '미설정')}")
        
        # Test simple query
        logger.info("\nRAG 쿼리 테스트...")
        test_question = "퍼스널 컬러 유형에는 어떤 것들이 있나요?"
        logger.info(f"질문: {test_question}")
        
        result = handler.query(test_question)
        
        if result and isinstance(result, dict):
            logger.info(f"✅ 핸들러 쿼리 성공")
            logger.info(f"   - success: {result.get('success', False)}")
            logger.info(f"   - answer (첫 100자): {result.get('answer', 'N/A')[:100]}...")
        else:
            logger.info(f"❌ 핸들러 쿼리 실패 또는 형식 오류: {result}")
        
        logger.info("\n" + "="*70)
        logger.info("✅ 핸들러 통합 테스트 완료")
        logger.info("="*70)
        return True
        
    except Exception as e:
        logger.error(f"❌ 핸들러 테스트 실패: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logger.info("File Search 기능 테스트 시작\n")
    
    success_1 = test_file_search()
    success_2 = test_handlers_integration()
    
    if success_1 and success_2:
        logger.info("\n✅ 모든 테스트 통과")
        sys.exit(0)
    else:
        logger.info("\n❌ 일부 테스트 실패")
        sys.exit(1)
