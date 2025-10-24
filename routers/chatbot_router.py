from fastapi import APIRouter, HTTPException, Depends, status
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import models
from routers.user_router import get_current_user
from database import SessionLocal
import os, json
from typing import List, Dict, Any
from math import sqrt


from schemas import ChatbotRequest, ChatbotHistoryResponse, ChatItemModel, ChatResModel
# AI 피드백 자동 평가 함수 임포트
from routers.feedback_router import generate_ai_feedbacks

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("환경변수 OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)
router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    if overlap >= chunk_size:
        raise ValueError("overlap은 chunk_size보다 작아야 합니다.")
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunks.append(text[start:end])
        if end == text_length:
            break
        start += (chunk_size - overlap)
    return [c.strip() for c in chunks if c.strip()]

def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sqrt(sum(x * x for x in a)) or 1e-8
    nb = sqrt(sum(x * x for x in b)) or 1e-8
    return dot / (na * nb)

def embed_texts(client: OpenAI, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    res = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in res.data]

def top_k_chunks(query: str, index: Dict[str, Any], client: OpenAI, k: int = 3) -> List[str]:
    q_emb = embed_texts(client, [query])[0]
    sims = [(cosine_similarity(q_emb, emb), i) for i, emb in enumerate(index["embeddings"])]
    sims.sort(reverse=True, key=lambda x: x[0])
    return [index["chunks"][i] for _, i in sims[:k]]

def build_rag_index(client: OpenAI, filepath: str) -> Dict[str, Any]:
    with open(filepath, encoding="utf-8") as f:
        text = f.read()
    chunks = chunk_text(text, chunk_size=800, overlap=100)
    embeddings = embed_texts(client, chunks)
    return {"chunks": chunks, "embeddings": embeddings}

fixed_index = build_rag_index(client, "data/RAG/personal_color_RAG.txt")
trend_index = build_rag_index(client, "data/RAG/beauty_trend_2025_autumn_RAG.txt")

@router.post("/analyze", response_model=ChatbotHistoryResponse)
def analyze(
    request: ChatbotRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 신규 세션 생성 또는 기존 세션 이어받기
    if not request.history_id:
        chat_history = models.ChatHistory(user_id=current_user.id)
        db.add(chat_history)
        db.commit()
        db.refresh(chat_history)
    else:
        chat_history = db.query(models.ChatHistory).filter_by(id=request.history_id, user_id=current_user.id).first()
        if not chat_history:
            raise HTTPException(status_code=404, detail="해당 history_id 세션 없음")
        if chat_history.ended_at:
            raise HTTPException(status_code=400, detail="이미 종료된 세션입니다.")
    prev_questions = db.query(models.ChatMessage).filter_by(history_id=chat_history.id, role="user").order_by(models.ChatMessage.id.asc()).all()
    question_id = len(prev_questions) + 1
    user_msg = models.ChatMessage(history_id=chat_history.id, role="user", text=request.question)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    survey_result = db.query(models.SurveyResult).filter(models.SurveyResult.user_id==current_user.id).order_by(models.SurveyResult.created_at.desc()).first()
    survey_context = ""
    if survey_result:
        survey_context = f"최신 설문 결과\n진단 tone: {survey_result.result_tone}\nconfidence: {survey_result.confidence}\ntotal_score: {survey_result.total_score}\n"
        survey_context += "\n".join(f"{ans.question_id}: {ans.option_label}" for ans in survey_result.answers)
    combined_query = f"{request.question}\n\n사용자 설문 결과\n{survey_context}" if survey_context else request.question
    fixed_chunks = top_k_chunks(combined_query, fixed_index, client, k=3)
    trend_chunks = top_k_chunks(combined_query, trend_index, client, k=3)
    prompt_system = (
        "당신은 퍼스널컬러 전문가이자 최신 패션 트렌드 컨설턴트입니다. 사용자의 최신 설문 진단 결과(result_tone, confidence, total_score 등)를 반드시 참고해서 퍼스널컬러 리포트와 추천을 작성해 주세요."
    )
    prompt_user = f"""사용자 데이터:\n{combined_query}\n\n불변 지식\n{chr(10).join(fixed_chunks)}\n\n가변 지식\n{chr(10).join(trend_chunks)}\n\n다음 JSON 형식으로만 응답해주세요:
{{
  "primary_tone": "웜" 또는 "쿨",
  "sub_tone": "봄" 또는 "여름" 또는 "가을" 또는 "겨울",
  "description": "상세한 설명 텍스트",
  "recommendations": ["추천사항1", "추천사항2", "추천사항3"]
}}

주의: recommendations는 반드시 문자열 배열이어야 합니다.
"""
    messages = [{"role": "system", "content": prompt_system}, {"role": "user", "content": prompt_user}]
    resp = client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.3, max_tokens=600)
    content = resp.choices[0].message.content
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="JSON 결과 없음")
    data = json.loads(content[start:end+1])
    
    # recommendations 필드 정리
    recommendations = data.get("recommendations", [])
    if isinstance(recommendations, dict):
        recommendations = list(recommendations.values())
    elif isinstance(recommendations, list):
        # 중첩된 리스트를 평평하게 만들기
        flattened_recommendations = []
        for item in recommendations:
            if isinstance(item, list):
                flattened_recommendations.extend(item)
            elif isinstance(item, str):
                flattened_recommendations.append(item)
        recommendations = flattened_recommendations
    else:
        recommendations = []
    
    data["recommendations"] = recommendations
    answer_string = data.get("description","")
    ai_msg = models.ChatMessage(history_id=chat_history.id, role="ai", text=json.dumps(data, ensure_ascii=False))
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)

    # AI 답변 저장 후, AI 피드백 자동 평가 실행 (채팅 종료 전에도 평가 가능하도록 예외 무시)
    try:
        generate_ai_feedbacks(history_id=chat_history.id, current_user=current_user, db=db)
    except Exception as e:
        # 예: 채팅 종료 전에는 평가 불가 등의 예외 발생 가능, 무시하고 진행
        pass
    msgs = db.query(models.ChatMessage).filter_by(history_id=chat_history.id).order_by(models.ChatMessage.id.asc()).all()
    items = []
    qid = 1
    for i in range(0,len(msgs)-1,2):
        if msgs[i].role=="user" and msgs[i+1].role=="ai":
            d = json.loads(msgs[i+1].text)
            
            # 기존 데이터의 recommendations 필드도 정리
            recommendations = d.get("recommendations", [])
            if isinstance(recommendations, dict):
                recommendations = list(recommendations.values())
            elif isinstance(recommendations, list):
                # 중첩된 리스트를 평평하게 만들기
                flattened_recommendations = []
                for item in recommendations:
                    if isinstance(item, list):
                        flattened_recommendations.extend(item)
                    elif isinstance(item, str):
                        flattened_recommendations.append(item)
                recommendations = flattened_recommendations
            else:
                recommendations = []
            
            d["recommendations"] = recommendations
            
            items.append(ChatItemModel(
                question_id=qid,
                question=msgs[i].text,
                answer=d.get("description",""),
                chat_res=ChatResModel.model_validate(d)
            ))
            qid += 1
    return {"history_id": chat_history.id, "items": items}

@router.post("/end/{history_id}")
def end_chat_session(
    history_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = db.query(models.ChatHistory).filter_by(id=history_id, user_id=current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="대화 세션 없음")
    if chat.ended_at:
        return {"message": "이미 종료됨", "ended_at": chat.ended_at}
    chat.ended_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "대화 종료", "ended_at": chat.ended_at}
