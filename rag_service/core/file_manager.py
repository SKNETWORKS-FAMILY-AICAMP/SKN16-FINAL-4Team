"""
통합 지식 파일 관리자

불변 지식: 퍼스널 컬러 PDF (상태 점검 & 자동 복구)
가변 지식: Vogue 트렌드 (로컬 스캔만 수행)
"""

import logging
import importlib
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Literal
from enum import Enum

from .config import (
    GEMINI_API_KEY,
    IMMUTABLE_KNOWLEDGE_FILES,
    IMMUTABLE_BACKUP_DIR,
    IMMUTABLE_UPLOADED_FILES_JSON,
    MUTABLE_DATA_DIR,
    MAX_MUTABLE_FILES,
    MAX_FILE_SIZE_MB,
    SUPPORTED_EXTENSIONS
)

logger = logging.getLogger(__name__)

# 지식 종류 정의
KnowledgeType = Literal["immutable", "mutable"]


class FileManager:
    """
    통합 지식 파일 관리자
    
    불변 지식: verify_and_repair_files() - 파일 상태 확인 & 자동 복구
    가변 지식: sync_files() - 로컬 스캔 & 동기화 & 변경 감지
    """
    
    def __init__(self, knowledge_type: KnowledgeType):
        """
        Args:
            knowledge_type: "immutable" 또는 "mutable"
        """
        self.knowledge_type = knowledge_type
        # Initialize google genai client and types
        self.genai_client = None
        self.genai_types = None
        
        # Try new google.genai (uses google.genai.Client + google.genai.types)
        try:
            genai_pkg = importlib.import_module('google.genai')
            Client = getattr(genai_pkg, 'Client', None)
            if Client:
                # Configure with API key
                self.genai_client = Client(api_key=GEMINI_API_KEY)
                # Load types for File Search (FileSearch, Tool, GenerateContentConfig)
                try:
                    self.genai_types = importlib.import_module('google.genai.types')
                except Exception:
                    pass
                logging.getLogger(__name__).info('✅ Using google.genai Client')
        except Exception as init_err:
            logging.getLogger(__name__).debug(f'google.genai initialization failed: {init_err}')
        
        # Fallback to legacy google.generativeai if google.genai not available
        if self.genai_client is None:
            try:
                legacy = importlib.import_module('google.generativeai')
                legacy.configure(api_key=GEMINI_API_KEY)
                self.genai_legacy = legacy
                # Load legacy types
                try:
                    self.genai_types = importlib.import_module('google.generativeai.types')
                except Exception:
                    pass
                logging.getLogger(__name__).info('✅ Using legacy google.generativeai')
            except Exception:
                logging.getLogger(__name__).warning('❌ genai 라이브러리 미설치')
        
        if knowledge_type == "immutable":
            self._init_immutable()
        else:
            self._init_mutable()
    
    def _init_immutable(self):
        """불변 지식 초기화"""
        self.files_config = IMMUTABLE_KNOWLEDGE_FILES.copy()
        self.backup_dir = IMMUTABLE_BACKUP_DIR
        self.config_file = IMMUTABLE_UPLOADED_FILES_JSON
        self.data_dir = None
        self.max_files = None
        logger.info("📚 불변 지식 파일 관리자 초기화")
    
    def _init_mutable(self):
        """가변 지식 초기화 (로컬 파일만 관리)"""
        self.files_config = None
        self.backup_dir = None
        self.config_file = None  # Gemini 파일 ID 관리 불필요
        self.data_dir = MUTABLE_DATA_DIR
        self.max_files = MAX_MUTABLE_FILES if MAX_MUTABLE_FILES is not None else float('inf')  # 제한 없음
        logger.info("📰 가변 지식 파일 관리자 초기화 (로컬 파일 전용)")
    
    # ============================================================
    # 공통 메서드
    # ============================================================
    
    def load_config(self) -> Dict:
        """저장된 파일 설정 로드"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"설정 파일 로드 실패: {e}")
        return {}
    
    def save_config(self, config: Dict = None):
        """파일 설정 저장"""
        if self.knowledge_type == "immutable" and config is None:
            return
        
        try:
            if self.knowledge_type == "mutable":
                config = self.uploaded_files_info
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ 설정 파일 저장: {self.config_file}")
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
    
    def upload_file(self, local_path: Path) -> Optional[str]:
        """
        로컬 파일을 Gemini API에 업로드 (불변 지식 전용)
        
        Args:
            local_path: 업로드할 로컬 파일 경로
            
        Returns:
            업로드된 파일의 Gemini file_id, 또는 None
        """
        if self.knowledge_type != "immutable":
            raise RuntimeError("upload_file()은 불변 지식에서만 사용 가능합니다.")
        
        if not local_path.exists():
            logger.error(f"❌ 파일 없음: {local_path}")
            return None
        
        try:
            logger.info(f"📤 파일 업로드 시작: {local_path.name}")

            if self.genai_client is not None:
                try:
                    cfg = {'name': local_path.name}
                    uploaded = self.genai_client.files.upload(file=str(local_path), config=cfg)
                    if uploaded and hasattr(uploaded, 'name'):
                        file_name = uploaded.name
                        logger.info(f"✅ 파일 업로드 성공: {file_name}")
                        return file_name
                except Exception as e:
                    logger.warning(f"파일 업로드 실패: {e}")

            logger.error("❌ 업로드 실패: genai 클라이언트가 없습니다.")
            return None

        except Exception as e:
            logger.error(f"❌ 파일 업로드 실패: {local_path.name} - {e}")
            return None
    
    def get_active_files(self, file_ids: Dict[str, str]) -> List:
        """
        파일 ID를 실제 파일 콘텐츠로 변환
        
        불변 지식: 로컬 백업에서 텍스트 추출 (File Search 폴백용)
        가변 지식: 로컬 텍스트 파일 읽기
        """
        active_files = []

        # 가변 지식: 로컬 텍스트 파일만 읽음 (이미지는 자동으로 제외됨)
        if self.knowledge_type == "mutable":
            for filename in file_ids.keys():
                # ✅ 이미지 파일은 건너뜀 (이미지 파일이 스캔되지 않도록 설정되었음)
                if any(filename.lower().endswith(img_ext) for img_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    logger.debug(f"ℹ️ 이미지 파일 제외: {filename}")
                    continue
                
                try:
                    local_path = self.data_dir / filename
                    if local_path.exists():
                        with open(local_path, 'r', encoding='utf-8') as f:
                            text = f.read()
                        active_files.append(text)
                        logger.info(f"✅ 로컬 텍스트 로드: {filename} ({len(text)} chars)")
                    else:
                        logger.debug(f"ℹ️ 로컬 파일 없음: {local_path}")
                except UnicodeDecodeError:
                    # ✅ 이진 파일(이미지 등)은 조용히 제외
                    logger.debug(f"ℹ️ 이진 파일 제외: {filename}")
                except Exception as e:
                    logger.debug(f"ℹ️ 파일 읽기 실패 (제외): {filename} - {type(e).__name__}")

            return active_files

        # 불변 지식: 로컬 백업에서 텍스트 추출 (File Search 폴백용)
        for display_name, file_id in file_ids.items():
            try:
                local_path = self.backup_dir / display_name
                if not local_path.exists():
                    logger.warning(f"⚠️  백업 파일 없음: {local_path}")
                    continue

                # 지원되는 텍스트 형식
                if local_path.suffix.lower() in ['.txt', '.md', '.json']:
                    with open(local_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    active_files.append(text)
                    logger.info(f"✅ 로컬 텍스트 로드 (불변): {display_name} ({len(text)} chars)")
                    continue

                # 기타 형식 (PDF, 이진 파일 등): 파일 정보만 표시
                try:
                    file_size_mb = local_path.stat().st_size / (1024 * 1024)
                    content = f"[파일: {display_name} ({file_size_mb:.2f}MB)]"
                except Exception:
                    content = f"[파일: {display_name}]"
                active_files.append(content)
                logger.info(f"ℹ️ 파일 정보 추가: {display_name}")

            except Exception as e:
                logger.error(f"❌ 불변 지식 파일 읽기 실패: {display_name} - {e}")

        return active_files
    
    # ============================================================
    # 불변 지식 메서드 (verify_and_repair_files)
    # ============================================================
    
    def verify_and_repair_files(self) -> Dict[str, str]:
        """
        불변 지식 파일 상태 확인 및 자동 복구
        
        간소화된 버전: 저장된 config를 사용하고, 없으면 재업로드
        File Search 사용으로 파일 ID 유효성 검사 필요 없음
        
        Returns:
            사용 가능한 파일 ID 딕셔너리
        """
        if self.knowledge_type != "immutable":
            raise RuntimeError("이 메서드는 불변 지식에서만 사용 가능합니다.")
        
        logger.info("="*60)
        logger.info("🔍 불변 지식 파일 상태 점검")
        logger.info("="*60)
        
        # 백업 디렉토리 확인
        if not self.backup_dir.exists():
            logger.error(f"❌ 백업 디렉토리 없음: {self.backup_dir}")
            return {}
        
        logger.info(f"📁 백업 디렉토리: {self.backup_dir}")
        
        # 저장된 설정 로드
        saved_config = self.load_config()
        verified_files = {}
        
        logger.info(f"💾 저장된 설정 확인 ({len(saved_config)}개 파일)")
        
        for display_name in self.files_config.keys():
            if display_name in saved_config:
                verified_files[display_name] = saved_config[display_name]
                logger.info(f"   ✅ {display_name}: {saved_config[display_name]}")
            else:
                logger.warning(f"   ⚠️  {display_name}: 저장된 ID 없음")
        
        # 없으면 재업로드
        if len(verified_files) < len(self.files_config):
            logger.info("\n🔄 일부 파일 재업로드 시작")
            new_config = {}
            for display_name in self.files_config.keys():
                if display_name in verified_files:
                    continue
                    
                local_path = self.backup_dir / display_name
                new_file_id = self.upload_file(local_path)
                
                if new_file_id:
                    verified_files[display_name] = new_file_id
                    new_config[display_name] = new_file_id
                    logger.info(f"   ✅ {display_name}: {new_file_id}")
                else:
                    logger.error(f"   ❌ {display_name} 업로드 실패")
            
            if new_config:
                self.save_config(new_config)
                logger.info(f"✅ {len(new_config)}개 파일 ID 저장됨")
        
        logger.info("="*60 + "\n")
        return verified_files

    # ============================================================
    # File Search helpers (Gemini File Search)
    # ============================================================
    # store metadata file
    FILE_SEARCH_STORE_JSON = Path(__file__).parent.parent / "file_search_store.json"

    def _load_file_search_store_info(self) -> Optional[Dict]:
        if self.FILE_SEARCH_STORE_JSON.exists():
            try:
                with open(self.FILE_SEARCH_STORE_JSON, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"파일서치 메타 로드 실패: {e}")
        return None

    def _save_file_search_store_info(self, info: Dict):
        try:
            with open(self.FILE_SEARCH_STORE_JSON, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ FileSearch 스토어 정보 저장: {self.FILE_SEARCH_STORE_JSON}")
        except Exception as e:
            logger.error(f"FileSearch 스토어 정보 저장 실패: {e}")

    def _validate_store_name_format(self, store_name: str) -> bool:
        """Validate if store name matches Google Gemini API format.
        
        Valid format: fileSearchStores/[alphanumeric_underscore_hyphen]
        """
        if not isinstance(store_name, str):
            return False
        if not store_name.startswith('fileSearchStores/'):
            return False
        # Check the part after 'fileSearchStores/'
        store_id = store_name.split('/', 1)[1] if '/' in store_name else ''
        # Should be alphanumeric with underscores/hyphens, not empty, not too long
        if not store_id or len(store_id) > 63:
            return False
        # Only lowercase alphanumeric, hyphens, underscores allowed
        import re
        if not re.match(r'^[a-z0-9_-]+$', store_id):
            return False
        return True

    def get_or_create_file_search_store(self, display_name: str = "immutable_knowledge_store") -> Optional[str]:
        """Get existing FileSearch store name or create a new one and save metadata.
        
        Validates store name format and regenerates if invalid.
        Requires google.genai client.
        """
        logger.info(f"⏳ File Search 스토어 메타 준비 중...")

        # Try to load saved info
        info = self._load_file_search_store_info()
        if info and info.get('store_name'):
            store_name = info['store_name']
            
            # ✅ 검증: 형식이 올바른지 확인
            if self._validate_store_name_format(store_name):
                logger.info(f"✅ 기존 File Search 스토어 메타 사용 (검증됨): {store_name}")
                return store_name
            else:
                logger.warning(f"⚠️  저장된 store name 형식 오류: {store_name}")
                logger.warning(f"   메타데이터 초기화하고 새로 생성합니다")
                # 메타데이터 파일 삭제하여 새로 생성하도록 강제
                try:
                    self.FILE_SEARCH_STORE_JSON.unlink()
                    logger.info(f"✅ 기존 메타데이터 파일 삭제: {self.FILE_SEARCH_STORE_JSON}")
                except Exception as e:
                    logger.warning(f"⚠️  메타데이터 삭제 실패: {e}")

        # If new genai client available, create a real store
        if self.genai_client is not None:
            try:
                logger.info(f"🆕 새로운 File Search 스토어 생성 중...")
                store = self.genai_client.file_search_stores.create(config={'display_name': display_name})
                store_name = getattr(store, 'name', None)
                
                if store_name and self._validate_store_name_format(store_name):
                    self._save_file_search_store_info({
                        'store_name': store_name, 
                        'display_name': display_name,
                        'created_at': str(__import__('datetime').datetime.now().isoformat())
                    })
                    logger.info(f"✅ File Search 스토어 생성 및 저장: {store_name}")
                    return store_name
                else:
                    logger.error(f"❌ 생성된 store name 형식 오류: {store_name}")
                    return None
                    
            except Exception as e:
                logger.warning(f"File Search 스토어 생성 실패: {e}")
                
                # Fallback: 기존 스토어 목록에서 찾기
                try:
                    logger.info(f"🔍 기존 File Search 스토어 목록 탐색 중...")
                    for s in self.genai_client.file_search_stores.list():
                        if getattr(s, 'display_name', '') == display_name:
                            store_name = getattr(s, 'name', None)
                            if store_name and self._validate_store_name_format(store_name):
                                self._save_file_search_store_info({
                                    'store_name': store_name, 
                                    'display_name': display_name,
                                    'created_at': str(__import__('datetime').datetime.now().isoformat())
                                })
                                logger.info(f"✅ 기존 File Search 스토어 발견 및 저장: {store_name}")
                                return store_name
                except Exception as list_err:
                    logger.warning(f"⚠️  스토어 목록 조회 실패: {list_err}")
        else:
            logger.error(f"❌ google.genai 클라이언트 없음: File Search 스토어 생성 불가")
        
        return None

        # Fallback placeholder behavior
        store_name = f"fileSearchStores/immutable_knowledge_{int(time.time())}"
        self._save_file_search_store_info({'store_name': store_name, 'display_name': display_name})
        logger.info(f"✅ File Search 스토어 메타 저장(플레이스홀더): {store_name}")
        return store_name

    def upload_and_import_to_file_search_store(self, local_path: Path, store_name: str) -> bool:
        """Upload local file and import into File Search store.
        
        Note: Requires google-genai library for actual upload.
        For now, this logs the intent (mocked operation for development).
        """
        if not local_path.exists():
            logger.error(f"❌ 업로드 파일 없음: {local_path}")
            return False

        try:
            logger.info(f"📤 File Search 업로드 예정: {local_path.name} -> {store_name}")

            if self.genai_client is not None:
                try:
                    # Try direct upload+import
                    op = self.genai_client.file_search_stores.upload_to_file_search_store(
                        file=str(local_path),
                        file_search_store_name=store_name,
                        config={'display_name': local_path.name}
                    )
                    # Poll operation until done
                    while not getattr(op, 'done', False):
                        time.sleep(2)
                        try:
                            op = self.genai_client.operations.get(op.name)
                        except Exception:
                            break
                    logger.info(f"✅ File Search 업로드+임포트 완료: {local_path.name}")
                    return True
                except Exception as e:
                    logger.warning(f"upload_to_file_search_store 실패, fallback 시도: {e}")
                    # fallback: upload via Files API then import
                    try:
                        uploaded = self.genai_client.files.upload(file=str(local_path), config={'name': local_path.name})
                        op = self.genai_client.file_search_stores.import_file(
                            file_search_store_name=store_name,
                            file_name=getattr(uploaded, 'name', None)
                        )
                        while not getattr(op, 'done', False):
                            time.sleep(2)
                            try:
                                op = self.genai_client.operations.get(op.name)
                            except Exception:
                                break
                        logger.info(f"✅ File Search 임포트 완료 (fallback): {local_path.name}")
                        return True
                    except Exception as e2:
                        logger.error(f"File Search 업로드/임포트 실패(fallback): {e2}")
                        return False

            # Fallback: log intent and return False to indicate it wasn't actually uploaded
            logger.info(f"   (실제 업로드 미지원: google-genai 미설치) - {local_path.name}")
            return False

        except Exception as e:
            logger.error(f"❌ File Search 업로드 실패: {local_path.name} - {e}")
            return False

    def query_file_search_store(self, store_name: str, prompt: str, model: str = "gemini-2.5-flash"):
        """Query the File Search store using google.genai Client API.
        
        Official Gemini API documentation pattern:
        https://ai.google.dev/gemini-api/docs/file-search
        
        Args:
            store_name: File Search store name (e.g., 'fileSearchStores/abc123')
            prompt: User query/question
            model: Gemini model to use (default: gemini-2.5-flash)
        
        Returns:
            Response object with .text attribute, or None if query fails
        """
        if self.genai_client is None or self.genai_types is None:
            logger.warning("❌ File Search 쿼리 불가: genai client 또는 types 미설정")
            return None

        try:
            # Extract required type classes from genai.types
            types = self.genai_types
            FileSearch = getattr(types, 'FileSearch', None)
            Tool = getattr(types, 'Tool', None)
            GenerateContentConfig = getattr(types, 'GenerateContentConfig', None)

            if not (FileSearch and Tool and GenerateContentConfig):
                logger.error('❌ File Search 관련 타입을 찾을 수 없습니다 (FileSearch, Tool, GenerateContentConfig)')
                return None

            logger.info(f"🔍 File Search 쿼리 시작: {prompt[:50]}...")
            
            # Build File Search tool configuration (following official docs)
            config = GenerateContentConfig(
                tools=[
                    Tool(
                        file_search=FileSearch(
                            file_search_store_names=[store_name]
                        )
                    )
                ]
            )

            # Query using google.genai client
            logger.info(f"📡 Gemini {model} 호출 중...")
            resp = self.genai_client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )
            
            logger.info(f"✅ File Search 응답 수신")
            return resp
            
        except Exception as e:
            logger.error(f"❌ File Search 쿼리 실패: {e}", exc_info=True)
            return None

    def import_all_immutable_to_file_search(self) -> Optional[str]:
        """Import immutable knowledge files into a File Search store and return store_name.
        
        Currently handles: 1 combined PDF (previously: 5 separate PDFs)
        """
        try:
            store_name = self.get_or_create_file_search_store()
            if not store_name:
                return None

            # iterate configured files (now: 1 combined file)
            count = 0
            for filepath in sorted(self.backup_dir.glob("*")):
                if not filepath.is_file():
                    continue
                # skip non-supported
                if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS and filepath.suffix.lower() not in ['.pdf', '.txt', '.md']:
                    logger.info(f"건너뜀(확장자): {filepath.name}")
                    continue

                self.upload_and_import_to_file_search_store(filepath, store_name)
                count += 1

            logger.info(f"✅ {count}개 파일 File Search 처리 완료")
            return store_name
        except Exception as e:
            logger.error(f"전체 임포트 실패: {e}")
            return None
    
    # ============================================================
    # 가변 지식 메서드 (scan_local_files)
    # ============================================================
    
    def scan_local_files(self) -> List[Path]:
        """로컬 디렉토리에서 파일 스캔"""
        if self.knowledge_type != "mutable":
            raise RuntimeError("이 메서드는 가변 지식에서만 사용 가능합니다.")
        
        if not self.data_dir.exists():
            logger.error(f"❌ 데이터 디렉토리 없음: {self.data_dir}")
            return []
        
        files = []
        # 하위 폴더 포함 재귀 검색 (rglob 사용)
        for ext in SUPPORTED_EXTENSIONS:
            for filepath in self.data_dir.rglob(f"*{ext}"):
                # 파일 여부 확인
                if not filepath.is_file():
                    continue

                # 파일 크기 확인
                try:
                    size_mb = filepath.stat().st_size / (1024 * 1024)
                except Exception:
                    logger.warning(f"⚠️  파일 접근 실패 (건너뜀): {filepath}")
                    continue

                if size_mb > MAX_FILE_SIZE_MB:
                    logger.warning(f"⚠️  파일 크기 초과 (건너뜀): {filepath.name} ({size_mb:.2f}MB)")
                    continue

                files.append(filepath)

                if self.max_files != float('inf') and len(files) >= self.max_files:
                    logger.warning(f"⚠️  최대 파일 수 도달 ({self.max_files}개)")
                    break

            if self.max_files != float('inf') and len(files) >= self.max_files:
                break
        
        logger.info(f"📁 스캔 완료: {len(files)}개 파일 발견")
        return sorted(files) if self.max_files == float('inf') else sorted(files)[:int(self.max_files)]
    
    def sync_files(self) -> Dict[str, str]:
        """
        가변 지식 파일 동기화 (로컬 스캔만 수행)
        
        OpenAI API 사용으로 인해 Gemini 파일 업로드 불필요
        로컬 텍스트 파일만 스캔하여 반환
        
        Returns:
            {filename: "local"} 딕셔너리 (실제 파일은 get_active_files에서 로드)
        """
        if self.knowledge_type != "mutable":
            raise RuntimeError("이 메서드는 가변 지식에서만 사용 가능합니다.")
        
        logger.info("="*60)
        logger.info("🔄 가변 지식 파일 동기화 시작 (로컬 스캔)")
        logger.info("="*60)
        
        # 로컬 파일 스캔만 수행 (Gemini 업로드 제거)
        local_files = self.scan_local_files()
        
        if not local_files:
            logger.warning("⚠️  로컬 파일이 없습니다.")
            return {}
        
        verified_files = {}
        
        # 각 로컬 파일을 검증 (로컬만, Gemini 업로드 없음)
        for filepath in local_files:
            try:
                # 저장 키로는 data_dir로부터의 상대 경로를 사용하여 중복 이름 충돌 방지
                rel_path = filepath.relative_to(self.data_dir).as_posix()
            except Exception:
                rel_path = filepath.name

            # 로컬 파일 존재 확인
            if filepath.exists() and filepath.stat().st_size > 0:
                verified_files[rel_path] = "local"  # Gemini 파일 ID 대신 "local" 표시
                logger.info(f"✓ 로컬 파일 확인: {rel_path}")
            else:
                logger.warning(f"⚠️  파일 없음 또는 비어있음: {rel_path}")
        
        # 결과 요약
        logger.info("\n" + "="*60)
        logger.info("📊 동기화 완료 (로컬 파일만)")
        logger.info("="*60)
        logger.info(f"📁 스캔된 파일: {len(verified_files)}개")
        logger.info("="*60 + "\n")
        
        return verified_files


# ============================================================
# 싱글톤 인스턴스
# ============================================================

_immutable_manager = None
_mutable_manager = None


def get_file_manager() -> FileManager:
    """불변 지식 파일 관리자 싱글톤"""
    global _immutable_manager
    if _immutable_manager is None:
        _immutable_manager = FileManager(knowledge_type="immutable")
    return _immutable_manager


def get_mutable_file_manager() -> FileManager:
    """가변 지식 파일 관리자 싱글톤"""
    global _mutable_manager
    if _mutable_manager is None:
        _mutable_manager = FileManager(knowledge_type="mutable")
    return _mutable_manager
