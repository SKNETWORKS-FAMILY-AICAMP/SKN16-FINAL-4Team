"""
RAG 서비스 - 통합 지식 관리 시스템

모듈 구조:
- core: 핵심 로직 (파일 관리, 핸들러, 라우터, 설정)
- api: FastAPI 애플리케이션
- tools: 유틸리티 도구 (웹 크롤러 등)

Backward Compatibility를 위해 주요 함수들을 root에서도 re-export합니다.
"""

from .core import (
    get_file_manager,
    get_mutable_file_manager,
    FileManager,
    get_immutable_handler,
    get_mutable_handler,
    ImmutableKnowledgeHandler,
    MutableKnowledgeHandler,
    KnowledgeHandler,
    get_router,
    KnowledgeRouter,
)

from .api import app
from .api.app import UnifiedKnowledgeRAG

__version__ = "2.0.0"

__all__ = [
    # Core
    "get_file_manager",
    "get_mutable_file_manager",
    "FileManager",
    "get_immutable_handler",
    "get_mutable_handler",
    "ImmutableKnowledgeHandler",
    "MutableKnowledgeHandler",
    "KnowledgeHandler",
    "get_router",
    "KnowledgeRouter",
    # API
    "app",
    "UnifiedKnowledgeRAG",
]