"""
RAG 서비스 설정
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Gemini API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 불변 지식 파일 설정
IMMUTABLE_KNOWLEDGE_FILES = {
    "personal_color_part_1.pdf": "files/j4r8jf2yjjaa",
    "personal_color_part_2.pdf": "files/kpp313mixp3j",
    "personal_color_part_3.pdf": "files/z76b8sstg07g",
    "personal_color_part_4.pdf": "files/7sd980yonlmt",
    "personal_color_part_5.pdf": "files/e53bnpf4xhzq",
}

# 로컬 백업 파일 경로
BACKUP_DIR = Path(__file__).parent.parent / "data" / "RAG" / "immutable"

# 모델 설정
MODEL_NAME = "models/gemini-2.5-pro"

# RAG 설정
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 512