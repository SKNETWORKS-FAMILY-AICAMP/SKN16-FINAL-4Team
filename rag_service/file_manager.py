"""
불변 지식 파일 관리자
- 파일 상태 체크
- 자동 재업로드
- 설정 파일 업데이트
"""

import google.generativeai as genai
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional

from .config import IMMUTABLE_KNOWLEDGE_FILES, BACKUP_DIR, GEMINI_API_KEY

logger = logging.getLogger(__name__)

# 설정 파일 경로
CONFIG_FILE = Path(__file__).parent / "uploaded_files.json"


class FileManager:
    """불변 지식 파일 관리자"""
    
    def __init__(self):
        self.files_config = IMMUTABLE_KNOWLEDGE_FILES.copy()
        self.backup_dir = BACKUP_DIR
        genai.configure(api_key=GEMINI_API_KEY)
    
    def load_saved_config(self) -> Dict:
        """저장된 파일 설정 로드"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"설정 파일 로드 실패: {e}")
        return {}
    
    def save_config(self, config: Dict):
        """파일 설정 저장"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ 설정 파일 저장: {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
    
    def check_file_exists(self, file_id: str) -> bool:
        """Gemini에서 파일 존재 여부 확인"""
        try:
            file = genai.get_file(file_id)
            if file.state.name == "ACTIVE":
                logger.info(f"✅ 파일 확인: {file_id} (ACTIVE)")
                return True
            else:
                logger.warning(f"⚠️  파일 상태 이상: {file_id} - {file.state.name}")
                return False
        except Exception as e:
            logger.warning(f"❌ 파일 접근 실패: {file_id} - {e}")
            return False
    
    def upload_file(self, local_path: Path) -> Optional[str]:
        """로컬 파일을 Gemini에 업로드"""
        try:
            if not local_path.exists():
                logger.error(f"❌ 로컬 파일 없음: {local_path}")
                return None
            
            logger.info(f"📤 파일 업로드 중: {local_path.name}")
            uploaded_file = genai.upload_file(str(local_path))
            
            logger.info(f"✅ 업로드 성공: {uploaded_file.name}")
            logger.info(f"   URI: {uploaded_file.uri}")
            
            return uploaded_file.name
            
        except Exception as e:
            logger.error(f"❌ 업로드 실패: {local_path.name} - {e}")
            return None
    
    def verify_and_repair_files(self) -> Dict[str, str]:
        """
        파일 상태 확인 및 자동 복구
        
        Returns:
            사용 가능한 파일 ID 딕셔너리
        """
        logger.info("="*60)
        logger.info("🔍 불변 지식 파일 상태 점검 시작")
        logger.info("="*60)
        
        # 백업 디렉토리 확인
        if not self.backup_dir.exists():
            logger.error(f"❌ 백업 디렉토리 없음: {self.backup_dir}")
            logger.error("   파일 복구가 불가능합니다!")
            return {}
        
        logger.info(f"📁 백업 디렉토리: {self.backup_dir}")
        
        # 저장된 설정 로드 (이전에 성공적으로 업로드된 파일 ID)
        saved_config = self.load_saved_config()
        
        verified_files = {}
        files_to_upload = []
        
        # 각 파일 확인
        for display_name, file_id in self.files_config.items():
            logger.info(f"\n📄 점검 중: {display_name}")
            logger.info(f"   현재 파일 ID: {file_id}")
            
            # 1. 현재 파일 ID 확인
            if self.check_file_exists(file_id):
                verified_files[display_name] = file_id
                logger.info(f"   ✅ 정상")
            else:
                # 2. 저장된 설정에서 대체 ID 확인
                if display_name in saved_config:
                    alternative_id = saved_config[display_name]
                    logger.info(f"   🔄 대체 ID 시도: {alternative_id}")
                    
                    if self.check_file_exists(alternative_id):
                        verified_files[display_name] = alternative_id
                        logger.info(f"   ✅ 대체 ID 사용")
                        continue
                
                # 3. 재업로드 필요
                logger.warning(f"   ⚠️  파일 재업로드 필요")
                files_to_upload.append(display_name)
        
        # 재업로드 실행
        if files_to_upload:
            logger.info("\n" + "="*60)
            logger.info(f"🔄 {len(files_to_upload)}개 파일 재업로드 시작")
            logger.info("="*60)
            
            for display_name in files_to_upload:
                local_path = self.backup_dir / display_name
                
                new_file_id = self.upload_file(local_path)
                
                if new_file_id:
                    verified_files[display_name] = new_file_id
                    saved_config[display_name] = new_file_id
                else:
                    logger.error(f"❌ 복구 실패: {display_name}")
            
            # 업데이트된 설정 저장
            if saved_config:
                self.save_config(saved_config)
        
        # 결과 요약
        logger.info("\n" + "="*60)
        logger.info("📊 파일 상태 점검 완료")
        logger.info("="*60)
        logger.info(f"✅ 정상: {len(verified_files)}개")
        logger.info(f"🔄 재업로드: {len(files_to_upload)}개")
        
        if len(verified_files) < len(self.files_config):
            failed_count = len(self.files_config) - len(verified_files)
            logger.error(f"❌ 실패: {failed_count}개")
            logger.error("   일부 파일을 사용할 수 없습니다!")
        
        logger.info("="*60 + "\n")
        
        return verified_files
    
    def get_active_files(self, file_ids: Dict[str, str]) -> List:
        """파일 ID를 실제 파일 객체로 변환"""
        active_files = []
        
        for display_name, file_id in file_ids.items():
            try:
                file = genai.get_file(file_id)
                if file.state.name == "ACTIVE":
                    active_files.append(file)
                    logger.info(f"✅ 파일 로드: {display_name}")
                else:
                    logger.warning(f"⚠️  파일 상태 이상: {display_name}")
            except Exception as e:
                logger.error(f"❌ 파일 로드 실패: {display_name} - {e}")
        
        return active_files


# 싱글톤 인스턴스
_file_manager = None

def get_file_manager() -> FileManager:
    """파일 관리자 싱글톤 인스턴스 반환"""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager