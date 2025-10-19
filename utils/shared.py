import os
from dotenv import load_dotenv
from openai import OpenAI
from database import SessionLocal

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("환경변수 OPENAI_API_KEY가 설정되지 않았습니다.")
client = OpenAI(api_key=OPENAI_API_KEY)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utility functions for text chunking and embedding
from typing import List

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)

def embed_texts(client: OpenAI, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    response = client.embeddings.create(input=texts, model=model)
    return [d.embedding for d in response.data]
