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
from typing import List, Dict, Any
from math import sqrt

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """
    텍스트를 겹치는 청크로 분할하는 함수
    
    Args:
        text: 분할할 텍스트
        chunk_size: 각 청크의 최대 크기
        overlap: 청크 간 겹치는 문자 수
        
    Returns:
        청크 문자열 리스트
    """
    if overlap >= chunk_size:
        raise ValueError("overlap은 chunk_size보다 작아야 합니다.")
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end].strip()
        if chunk:  # 빈 청크 제외
            chunks.append(chunk)
        
        if end == text_length:
            break
        start += (chunk_size - overlap)
    
    return chunks

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    두 벡터 간 코사인 유사도 계산
    
    Args:
        a: 첫 번째 벡터
        b: 두 번째 벡터
        
    Returns:
        코사인 유사도 (-1 ~ 1)
    """
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a)) or 1e-8  # 0으로 나누기 방지
    norm_b = sqrt(sum(y * y for y in b)) or 1e-8
    return dot_product / (norm_a * norm_b)

def embed_texts(client: OpenAI, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    """
    텍스트 리스트를 임베딩 벡터로 변환
    
    Args:
        client: OpenAI 클라이언트
        texts: 임베딩할 텍스트 리스트
        model: 사용할 임베딩 모델
        
    Returns:
        임베딩 벡터 리스트
    """
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]

def top_k_chunks(query: str, index: Dict[str, Any], client: OpenAI, k: int = 3) -> List[str]:
    """
    쿼리와 가장 유사한 상위 k개 청크 검색
    
    Args:
        query: 검색할 쿼리
        index: RAG 인덱스 (chunks, embeddings 포함)
        client: OpenAI 클라이언트
        k: 반환할 청크 개수
        
    Returns:
        상위 k개 유사한 청크 리스트
    """
    query_embedding = embed_texts(client, [query])[0]
    similarities = [
        (cosine_similarity(query_embedding, embedding), i)
        for i, embedding in enumerate(index["embeddings"])
    ]
    similarities.sort(reverse=True, key=lambda x: x[0])
    return [index["chunks"][i] for _, i in similarities[:k]]

def build_rag_index(client: OpenAI, filepath: str) -> Dict[str, Any]:
    """
    텍스트 파일로부터 RAG 인덱스 구축
    
    Args:
        client: OpenAI 클라이언트
        filepath: 텍스트 파일 경로
        
    Returns:
        RAG 인덱스 딕셔너리 (chunks, embeddings)
    """
    with open(filepath, encoding="utf-8") as f:
        text = f.read()
    
    chunks = chunk_text(text, chunk_size=800, overlap=100)
    embeddings = embed_texts(client, chunks)
    
    return {
        "chunks": chunks,
        "embeddings": embeddings
    }

def analyze_conversation_for_color_tone(conversation_history: str, current_question: str) -> tuple[str, str]:
    """
    대화 내용을 분석하여 퍼스널컬러 톤을 추정하는 순수 함수
    
    Args:
        conversation_history: 이전 대화 히스토리
        current_question: 현재 질문
        
    Returns:
        tuple[primary_tone, sub_tone]: ("웜"/"쿨", "봄"/"여름"/"가을"/"겨울")
    """
    # 기본값 설정
    default_tone = ("웜", "봄")
    
    # 대화에서 컬러 관련 키워드 추출
    text = (conversation_history + " " + current_question).lower()
    
    # 쿨톤 키워드 매칭
    cool_keywords = ["차가운", "시원한", "쿨톤", "블루베이스", "겨울", "여름", "파란", "보라", "실버"]
    warm_keywords = ["따뜻한", "웜톤", "옐로우베이스", "봄", "가을", "노란", "주황", "골드"]
    
    cool_score = sum(1 for keyword in cool_keywords if keyword in text)
    warm_score = sum(1 for keyword in warm_keywords if keyword in text)
    
    # 계절별 세부 키워드
    winter_keywords = ["진한", "강렬한", "선명한", "겨울", "블랙", "화이트", "비비드"]
    summer_keywords = ["부드러운", "파스텔", "여름", "라벤더", "그레이"]
    autumn_keywords = ["차분한", "깊은", "가을", "브라운", "카키", "베이지"]
    spring_keywords = ["밝은", "화사한", "봄", "코랄", "피치", "아이보리"]
    
    if cool_score > warm_score:
        winter_score = sum(1 for keyword in winter_keywords if keyword in text)
        summer_score = sum(1 for keyword in summer_keywords if keyword in text)
        return ("쿨", "겨울") if winter_score >= summer_score else ("쿨", "여름")
    elif warm_score > cool_score:
        autumn_score = sum(1 for keyword in autumn_keywords if keyword in text)
        spring_score = sum(1 for keyword in spring_keywords if keyword in text)
        return ("웜", "가을") if autumn_score >= spring_score else ("웜", "봄")
    
    return default_tone
