"""
통합 지식 처리기 (불변 & 가변)

Base 클래스: KnowledgeHandler
Subclass: ImmutableKnowledgeHandler, MutableKnowledgeHandler

✨ 주요 기능:
1. 불변 지식 (Gemini File Search) + 가변 지식 (OpenAI) 통합 처리
2. 간소화된 쿼리 전략
"""

import logging
import importlib
from typing import Dict, Literal, List
from abc import ABC, abstractmethod
import openai

from .config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    OPENAI_API_KEY,
    OPENAI_MUTABLE_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    MUTABLE_DEFAULT_TEMPERATURE,
    MUTABLE_DEFAULT_MAX_TOKENS,
    USE_CONTEXT_CACHING
)
from .file_manager import get_file_manager, get_mutable_file_manager

logger = logging.getLogger(__name__)


# ============================================================
# Base 클래스: KnowledgeHandler
# ============================================================

class KnowledgeHandler(ABC):
    """
    지식 처리 기본 클래스
    
    공통 기능:
    - 파일 관리자 초기화
    - RAG 쿼리 처리
    - 안전 필터 우회 (의문문 변환)
    - 응답 메타데이터 생성
    """
    
    def __init__(self, knowledge_type: Literal["immutable", "mutable"]):
        """
        Args:
            knowledge_type: "immutable" (불변 지식) 또는 "mutable" (가변 지식)
        """
        self.knowledge_type = knowledge_type
        self.model_name = GEMINI_MODEL
        self.uploaded_files = []
        
        # 파일 관리자 초기화
        if knowledge_type == "immutable":
            self.file_manager = get_file_manager()
            self._init_immutable()
        else:
            self.file_manager = get_mutable_file_manager()
            self._init_mutable()
        
        logger.info(f"🤖 {self._get_emoji()} {knowledge_type.upper()} 처리기 초기화 완료 (캐싱: {USE_CONTEXT_CACHING})")
    
    def _get_emoji(self) -> str:
        """지식 타입별 이모티콘"""
        return "📚" if self.knowledge_type == "immutable" else "📰"
    
    def _get_labels(self) -> Dict[str, str]:
        """지식 타입별 라벨 및 시스템 프롬프트"""
        if self.knowledge_type == "immutable":
            return {
                "init_msg": "불변 지식 파일 초기화 중...",
                "query_msg": "불변 지식 쿼리: ",
                "complete_msg": "불변 지식 답변 완료",
                "error_msg": "불변 지식 쿼리 실패",
                "system_instruction": (
                    "당신은 퍼스널 컬러 전문가입니다. "
                    "제공된 퍼스널 컬러 문서를 기반으로 "
                    "정확하고 상세한 답변을 제공하세요."
                ),
                "source": "immutable_knowledge",
                "no_files_error": "사용 가능한 불변 지식 파일이 없습니다."
            }
        else:
            return {
                "init_msg": "가변 지식 파일 동기화 중...",
                "query_msg": "가변 지식 쿼리: ",
                "complete_msg": "가변 지식 답변 완료",
                "error_msg": "가변 지식 쿼리 실패",
                "system_instruction": (
                    "당신은 패션 트렌드 전문가입니다. "
                    "Vogue Korea의 최신 패션 트렌드 기사를 기반으로 "
                    "현재 유행하는 스타일, 컬러, 아이템에 대한 정확한 정보를 제공하세요."
                ),
                "source": "mutable_knowledge",
                "no_files_error": "사용 가능한 트렌드 데이터가 없습니다."
            }
    
    @abstractmethod
    def _init_immutable(self):
        """불변 지식 초기화 (subclass 구현 필요)"""
        pass
    
    @abstractmethod
    def _init_mutable(self):
        """가변 지식 초기화 (subclass 구현 필요)"""
        pass
    
    def _load_files(self, method_name: str = None):
        """
        파일 로드 (공통 로직)
        
        불변 지식: verify_and_repair_files() 호출
        가변 지식: sync_files() 호출
        """
        labels = self._get_labels()
        logger.info(labels["init_msg"])
        
        if self.knowledge_type == "immutable":
            verified_file_ids = self.file_manager.verify_and_repair_files()
        else:
            verified_file_ids = self.file_manager.sync_files()
        
        if not verified_file_ids:
            if self.knowledge_type == "immutable":
                logger.error("❌ 사용 가능한 파일이 없습니다!")
            else:
                logger.warning("⚠️  사용 가능한 파일이 없습니다!")
            return
        
        self.uploaded_files = self.file_manager.get_active_files(verified_file_ids)
        logger.info(f"✅ {self.knowledge_type} 지식 파일 {len(self.uploaded_files)}개 로드 완료\n")
    
    # ============================================================
    # 핵심 기능: RAG 쿼리 처리
    # ============================================================
    
    def query(
        self, 
        question: str, 
        temperature: float = None,
        max_tokens: int = None
    ) -> Dict:
        """
        지식 기반 질문 답변 (공통 로직)
        
        전략:
        1. 원본 질문으로 Gemini 호출
        2. 안전 필터 실패 (finish_reason=2) 시:
           - 1차 정제: OpenAI로 의문문 변환 → Gemini 재호출
           - 2차 정제: 극단적 간소화 ("~은?") → Gemini 최종 시도
        
        Args:
            question: 사용자 질문
            temperature: 생성 온도 (None이면 기본값 사용)
            max_tokens: 최대 토큰 수 (None이면 기본값 사용)
            
        Returns:
            {
                "success": bool,
                "answer": str,
                "metadata": dict
            }
        """
        # 기본값 설정
        if temperature is None:
            temperature = (
                DEFAULT_TEMPERATURE 
                if self.knowledge_type == "immutable" 
                else MUTABLE_DEFAULT_TEMPERATURE
            )
        if max_tokens is None:
            max_tokens = (
                DEFAULT_MAX_TOKENS 
                if self.knowledge_type == "immutable" 
                else MUTABLE_DEFAULT_MAX_TOKENS
            )
        
        try:
            # 파일 존재 여부 확인
            if not self.uploaded_files:
                labels = self._get_labels()
                raise Exception(labels["no_files_error"])
            
            labels = self._get_labels()
            logger.info(f"{self._get_emoji()} {labels['query_msg']}{question[:50]}...")
            
            # 불변 지식: File Search 스토어 사용 (Gemini + google.genai Client)
            store_name = getattr(self, 'file_search_store_name', None)
            if store_name:
                logger.info(f"📂 File Search 스토어 사용: {store_name}")
                try:
                    response = self.file_manager.query_file_search_store(
                        store_name=store_name,
                        prompt=question,
                        model=self.model_name
                    )
                    
                    # ✅ None 응답 명시적 처리
                    if response is None:
                        logger.error(f"❌ File Search 쿼리 응답이 None입니다")
                        return None
                    
                    # ✅ 응답 검증
                    if hasattr(response, 'text') and response.text:
                        logger.info(f"✅ File Search 응답 성공")
                        answer = response.text
                        
                        # 인용 정보 추출 (grounding_metadata)
                        citations = None
                        if hasattr(response, 'candidates') and response.candidates:
                            candidate = response.candidates[0]
                            if hasattr(candidate, 'grounding_metadata'):
                                citations = candidate.grounding_metadata
                        
                        return {
                            "success": True,
                            "answer": answer,
                            "metadata": {
                                "source": "file_search",
                                "route": 2,
                                "model": self.model_name,
                                "citations": citations,
                                "files_used": len(self.uploaded_files),  # ✅ 추가: 통합 처리에서 메타데이터 일관성
                                "retrieval_method": "gemini_file_search"
                            }
                        }
                    else:
                        logger.error(f"❌ File Search 응답에 텍스트가 없습니다")
                        return None
                        
                except Exception as e:
                    logger.error(f"❌ File Search 쿼리 실패: {e}", exc_info=True)
                    return None
            else:
                logger.error(f"❌ File Search 스토어 이름이 없습니다")
                return None
            
        except Exception as e:
            labels = self._get_labels()
            logger.error(f"❌ {labels['error_msg']}: {e}", exc_info=True)
            raise e
    
    # ============================================================
    # 헬퍼 메서드들
    # ============================================================
    
    def _prepare_content_parts(self, question: str) -> List:
        """
        콘텐츠 파트 준비 (가변 지식용만 - 불변 지식은 File Search 사용)
        
        가변 지식(OpenAI): 최대 5개 문서, 20,000자 제한
        불변 지식(Gemini): File Search 사용하므로 여기서 처리 안 함
        """
        if self.knowledge_type == "mutable":
            # 가변 지식: 문서 개수/길이 제한 적용
            MAX_DOCS = 5
            MAX_TOTAL_CHARS = 20000
            
            docs = list(self.uploaded_files[-MAX_DOCS:])
            
            # 문자열 타입만 길이 계산
            string_total_chars = sum(len(d) for d in docs if isinstance(d, str))
            
            if string_total_chars > MAX_TOTAL_CHARS:
                ratio = MAX_TOTAL_CHARS / string_total_chars
                truncated = []
                for d in docs:
                    if isinstance(d, str):
                        keep = max(200, int(len(d) * ratio))
                        truncated.append(d[:keep])
                    else:
                        truncated.append(d)
                docs = truncated
            
            return docs + [question]
        else:
            # 불변 지식: File Search 사용하므로 질문만 반환
            return [question]
    
    def _call_gemini_with_retry(self, model, content_parts, max_retries: int = 3):
        """
        Gemini API 호출 (재시도 로직 포함)
        
        Args:
            model: Gemini 모델 객체
            content_parts: 콘텐츠 리스트
            max_retries: 최대 재시도 횟수
            
        Returns:
            Gemini response 객체
        """
        import time
        
        for attempt in range(1, max_retries + 1):
            try:
                response = model.generate_content(content_parts)
                return response
            except Exception as exc:
                msg = str(exc)
                if attempt < max_retries:
                    logger.warning(f"⚠️ 모델 호출 실패 (시도 {attempt}/{max_retries}): {msg} - 재시도 중")
                    time.sleep(0.5 * (2 ** (attempt - 1)))
                    continue
                else:
                    logger.error(f"❌ 재시도 실패: {exc}")
                    raise


# ============================================================
# Subclass 1: ImmutableKnowledgeHandler (불변 지식)
# ============================================================

class ImmutableKnowledgeHandler(KnowledgeHandler):
    """
    불변 지식 처리기 (퍼스널 컬러)
    
    특징:
    - Gemini API + File Search 사용
    - PDF 파일 (서버 측 파일 검색)
    """
    
    def __init__(self):
        super().__init__(knowledge_type="immutable")
        # attempt to ensure immutable knowledge is indexed in File Search
        try:
            store_name = self.file_manager.import_all_immutable_to_file_search()
            if store_name:
                self.file_search_store_name = store_name
                logger.info(f"📂 Immutable FileSearch store 준비됨: {store_name}")
            else:
                self.file_search_store_name = None
        except Exception:
            self.file_search_store_name = None
    
    def _init_immutable(self):
        """불변 지식 초기화"""
        # legacy: load files into memory for direct Gemini use
        self._load_files()
    
    def _init_mutable(self):
        """불변 지식에서는 미사용"""
        pass



# ============================================================
# Subclass 2: MutableKnowledgeHandler (가변 지식)
# ============================================================

class MutableKnowledgeHandler:
    """
    가변 지식 처리기 (Vogue 트렌드)
    
    특징:
    - OpenAI API 사용 (GPT-4o-mini)
    - 로컬 텍스트 파일 (최대 5개)
    - 안전 필터 우회 불필요 (OpenAI는 더 관대함)
    """
    
    def __init__(self):
        """OpenAI 기반 가변 지식 처리기 초기화"""
        self.knowledge_type = "mutable"
        self.file_manager = get_mutable_file_manager()
        self.uploaded_files = []
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.model_name = OPENAI_MUTABLE_MODEL
        
        logger.info(f"🤖 📰 OpenAI 기반 MUTABLE 처리기 초기화 중...")
        self._load_files()
        logger.info(f"🤖 📰 OpenAI 기반 MUTABLE 처리기 초기화 완료 (모델: {self.model_name})")
    
    def _load_files(self):
        """가변 지식 파일 로드"""
        logger.info("가변 지식 파일 동기화 중...")
        
        verified_file_ids = self.file_manager.sync_files()
        
        if not verified_file_ids:
            logger.warning("⚠️  사용 가능한 가변 지식 파일이 없습니다!")
            return
        
        # 가변 지식은 로컬 텍스트로 로드 (OpenAI 전송용)
        self.uploaded_files = self.file_manager.get_active_files(verified_file_ids)
        logger.info(f"✅ 가변 지식 파일 {len(self.uploaded_files)}개 로드 완료\n")
    
    def query(
        self,
        question: str,
        temperature: float = None,
        max_tokens: int = None
    ) -> Dict:
        """
        OpenAI API 기반 가변 지식 쿼리
        
        Args:
            question: 사용자 질문
            temperature: 생성 온도
            max_tokens: 최대 토큰 수
            
        Returns:
            {
                "success": bool,
                "answer": str,
                "metadata": dict
            }
        """
        # 기본값 설정
        if temperature is None:
            temperature = MUTABLE_DEFAULT_TEMPERATURE
        if max_tokens is None:
            max_tokens = MUTABLE_DEFAULT_MAX_TOKENS
        
        try:
            if not self.uploaded_files:
                raise Exception("사용 가능한 가변 지식 파일이 없습니다.")
            
            logger.info(f"📰 가변 지식 쿼리 (OpenAI): {question[:50]}...")
            
            # 가변 지식 문서 준비 (최대 5개, 30,000자)
            MAX_DOCS = 5
            MAX_TOTAL_CHARS = 30000
            
            # 최신 문서 우선 (리스트 끝이 최신이라고 가정)
            docs = []
            total_chars = 0
            
            for doc in reversed(self.uploaded_files):
                if isinstance(doc, str):
                    if len(docs) >= MAX_DOCS:
                        break
                    if total_chars + len(doc) > MAX_TOTAL_CHARS:
                        # 현재 문서를 부분적으로 추가
                        remaining = MAX_TOTAL_CHARS - total_chars
                        if remaining > 500:
                            docs.append(doc[:remaining])
                        break
                    docs.append(doc)
                    total_chars += len(doc)
            
            # 문서 역순 정렬 (최신순 유지)
            docs.reverse()
            
            # 시스템 프롬프트 준비
            doc_text = ""
            for i, doc in enumerate(docs):
                if len(doc) > 1000:
                    doc_text += f"### 자료 {i+1}\n{doc[:1000]}...\n\n"
                else:
                    doc_text += f"### 자료 {i+1}\n{doc}\n\n"
            
            system_prompt = f"""당신은 패션 트렌드 전문가입니다.
사용자의 질문에 대해 제공된 Vogue Korea 트렌드 자료를 기반으로 정확하고 상세한 답변을 제공하세요.

제공된 자료:
{doc_text}"""
            
            # OpenAI API 호출 (재시도 포함)
            max_retries = 3
            response = None
            for attempt in range(1, max_retries + 1):
                try:
                    response = self.openai_client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": question}
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    break
                except Exception as exc:
                    msg = str(exc)
                    if attempt < max_retries:
                        logger.warning(f"⚠️  OpenAI 호출 실패 (시도 {attempt}): {msg} - 재시도 중")
                        import time
                        time.sleep(0.5 * (2 ** (attempt - 1)))
                        continue
                    else:
                        logger.error(f"❌ 재시도 실패: {exc}")
                        raise
            
            answer = response.choices[0].message.content
            
            metadata = {
                "source": "mutable_knowledge",
                "model": self.model_name,
                "api": "openai",
                "files_used": len(docs),
                "total_chars": total_chars
            }
            
            logger.info(f"📰 가변 지식 답변 완료 (OpenAI)\n")
            
            return {
                "success": True,
                "answer": answer,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ 가변 지식 쿼리 실패: {e}")
            raise e
    
    def resync(self):
        """파일 재동기화"""
        self._load_files()


# ============================================================
# 싱글톤 인스턴스
# ============================================================

_immutable_handler = None
_mutable_handler = None


def get_immutable_handler() -> ImmutableKnowledgeHandler:
    """불변 지식 처리기 싱글톤"""
    global _immutable_handler
    if _immutable_handler is None:
        _immutable_handler = ImmutableKnowledgeHandler()
    return _immutable_handler


def get_mutable_handler() -> MutableKnowledgeHandler:
    """가변 지식 처리기 싱글톤"""
    global _mutable_handler
    if _mutable_handler is None:
        _mutable_handler = MutableKnowledgeHandler()
    return _mutable_handler
