"""
통합 지식 RAG 설정 (불변 + 가변 지식)

불변 지식: 퍼스널 컬러 (5개 PDF)
가변 지식: Vogue Korea 트렌드 (텍스트 파일)
Context Caching 옵션화 (개발: OFF, 프로덕션: ON)
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# API 키 설정
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ============================================================
# Context Caching 설정
# ============================================================

USE_CONTEXT_CACHING = False  # 개발: False, 프로덕션: True

IMMUTABLE_CACHE_TTL_HOURS = 12  # 불변 데이터 (긴 TTL)
MUTABLE_CACHE_TTL_HOURS = 1     # 가변 데이터 (짧은 TTL)

# ============================================================
# 프로젝트 경로
# ============================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent

# ============================================================
# 불변 지식 설정 (퍼스널 컬러 PDF - 통합 문서)
# ============================================================

# 주의: 실제 파일 ID는 uploaded_files.json에서 관리
# 5개 부분 문서를 통합한 단일 PDF 파일 사용
IMMUTABLE_KNOWLEDGE_FILES = {
    "personal_color.pdf": None,
}

# 🔍 파일 ID 관리 전략:
# - uploaded_files.json에 실제 Gemini file ID 저장
# - 매번 시작할 때 saved config의 ID를 우선 사용
# - 유효하지 않으면 backup에서 재업로드

IMMUTABLE_BACKUP_DIR = PROJECT_ROOT / "data" / "RAG" / "immutable"
IMMUTABLE_UPLOADED_FILES_JSON = Path(__file__).parent.parent / "uploaded_files.json"

# ============================================================
# 가변 지식 설정 (Vogue 트렌드 - 로컬 파일만 관리)
# ============================================================

MUTABLE_DATA_DIR = PROJECT_ROOT / "data" / "RAG" / "mutable"

# ============================================================
# 파일 처리 설정
# ============================================================

MAX_MUTABLE_FILES = None  # 최대 파일 수 제한 없음 (모든 파일 로드)
MAX_FILE_SIZE_MB = 20
SUPPORTED_EXTENSIONS = ['.txt', '.json']  # 텍스트 형식만 지원 (이미지 제외)

# ============================================================
# 모델 설정
# ============================================================

# Gemini 모델 (RAG 응답 생성용)
GEMINI_MODEL = "models/gemini-2.5-flash"

# OpenAI 모델 (라우팅 판단용)
OPENAI_ROUTER_MODEL = "gpt-4o-mini"

# OpenAI 모델 (가변 지식 RAG 응답 생성용)
OPENAI_MUTABLE_MODEL = "gpt-4o-mini"

# ============================================================
# RAG 설정
# ============================================================

# 기본값 (불변 지식용)
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048

# 가변 지식용 (더 낮은 온도 = 더 정확한 답변)
MUTABLE_DEFAULT_TEMPERATURE = 0.3
MUTABLE_DEFAULT_MAX_TOKENS = 1024

# ============================================================
# 라우팅 설정
# ============================================================

ROUTING_TIMEOUT_SECONDS = 5
ENABLE_ROUTING_CACHE = True
ROUTING_CACHE_SIZE = 100
