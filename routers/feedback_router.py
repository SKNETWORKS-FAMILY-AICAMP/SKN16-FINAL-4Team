from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from routers.user_router import get_current_user
import models
import json
from schemas import UserFeedbackRequest, UserFeedbackResponse
from utils.shared import get_db, client

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])

@router.get("/list/ai_feedbacks")
def get_all_ai_feedbacks_admin(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자만 접근 가능합니다.")
    ai_feedbacks = db.query(models.AIFeedback).all()
    result = []
    for fb in ai_feedbacks:
        msg = db.query(models.ChatMessage).filter_by(id=fb.message_id).first()
        history = db.query(models.ChatHistory).filter_by(id=msg.history_id).first() if msg else None
        # 질문 메시지 찾기 (같은 history에서 msg.id보다 작은 user role)
        question_msg = None
        if history and msg:
            question_msg = db.query(models.ChatMessage).filter(
                models.ChatMessage.history_id == history.id,
                models.ChatMessage.role == "user",
                models.ChatMessage.id < msg.id
            ).order_by(models.ChatMessage.id.desc()).first()
        result.append({
            "history_id": history.id if history else None,
            "question": question_msg.text if question_msg else None,
            "answer": msg.text if msg else None,
            "ai_feedback": {
                "id": fb.id,
                "message_id": fb.message_id,
                "accuracy": fb.accuracy,
                "consistency": fb.consistency,
                "reliability": fb.reliability,
                "personalization": fb.personalization,
                "practicality": fb.practicality,
                "total_score": fb.total_score,
                "vector_db_quality": fb.vector_db_quality,
                "detail_accuracy": fb.detail_accuracy,
                "detail_consistency": fb.detail_consistency,
                "detail_reliability": fb.detail_reliability,
                "detail_personalization": fb.detail_personalization,
                "detail_practicality": fb.detail_practicality
            }
        })
    return {"ai_feedbacks": result}


def parse_chat_pair_items(history):
    msgs = sorted(history.messages, key=lambda m: m.id)
    items = []
    qid = 1
    for i in range(0, len(msgs)-1, 2):
        if msgs[i].role == "user" and msgs[i+1].role == "ai":
            items.append({
                "question_id": qid,
                "question": msgs[i].text,
                "ai_msg": msgs[i+1],
                "answer": json.loads(msgs[i+1].text).get("description", "")
            })
            qid += 1
    return items

# llm_auto_feedback 함수는 반드시 파일 상단에 분리되어야 함
def llm_auto_feedback(question, answer):
    llm_prompt = f"""너는 퍼스널컬러 AI 진단 결과를 평가하는 AI 평가자야.
아래 '질문'에 대해 '답변'이 얼마나 적절한지, 아래 항목에 따라 반드시 JSON 형태(아래 포맷)로 평가해줘.

질문: {question}
답변: {answer}

{{
    "accuracy": [0~100점],
    "detail_accuracy": "정확도 상세평가 근거(2문장 이상)",
    "consistency": [0~100점],
    "detail_consistency": "일관성 상세평가 근거(2문장 이상)",
    "reliability": [0~100점],
    "detail_reliability": "신뢰도 상세평가 근거(2문장 이상)",
    "personalization": [0~100점],
    "detail_personalization": "개인화 상세평가 근거(2문장 이상)",
    "practicality": [0~100점],
    "detail_practicality": "실용성 상세평가 근거(2문장 이상)",
    "total_score": [0~100점, 위 다섯 항목 종합점수],
    "vector_db_quality": [0~100점, DB 응답의 정보 정밀도 및 활용도 점수]
}}

절대로 JSON 객체만, 예시대로 아래에 반환해줘!!
"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "퍼스널컬러 평가 전문 AI"},{"role": "user", "content": llm_prompt}],
        temperature=0.3,max_tokens=1200
    )
    content = resp.choices[0].message.content
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1:
        raise Exception("JSON 결과를 찾을 수 없음: " + content)
    data = json.loads(content[start:end+1])
    return data

@router.get("/ai_feedbacks/{history_id}")
def get_all_ai_feedbacks(
    history_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    history = db.query(models.ChatHistory).filter_by(id=history_id, user_id=current_user.id).first()
    if not history:
        raise HTTPException(status_code=404, detail="채팅 이력 없음")
    items = parse_chat_pair_items(history)
    response = []
    for pair in items:
        ai_feedback_data = None
        ai_msg = pair["ai_msg"]
        if ai_msg.ai_feedback:
            fb = ai_msg.ai_feedback
            ai_feedback_data = {
                "accuracy": fb.accuracy,
                "consistency": fb.consistency,
                "reliability": fb.reliability,
                "personalization": fb.personalization,
                "practicality": fb.practicality,
                "total_score": fb.total_score,
                "vector_db_quality": fb.vector_db_quality,
                "detail_accuracy": fb.detail_accuracy,
                "detail_consistency": fb.detail_consistency,
                "detail_reliability": fb.detail_reliability,
                "detail_personalization": fb.detail_personalization,
                "detail_practicality": fb.detail_practicality
            }
        response.append({
            "question_id": pair["question_id"],
            "question": pair["question"],
            "answer": pair["answer"],
            "ai_feedback": ai_feedback_data
        })
    return {"history_id": history_id, "items": response}

@router.post("/ai_feedbacks/generate/{history_id}")
def generate_ai_feedbacks(
    history_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    history = db.query(models.ChatHistory).filter_by(id=history_id, user_id=current_user.id).first()
    if not history:
        raise HTTPException(status_code=404, detail="채팅 이력 없음")
    # 채팅 종료 여부와 상관없이 평가 가능하도록 변경
    items = parse_chat_pair_items(history)
    generated = 0
    for pair in items:
        ai_msg = pair["ai_msg"]
        if ai_msg.ai_feedback:
            continue
        # 실제 AI 평가 호출 (질문과 답변 모두 전달)
        data = llm_auto_feedback(pair["question"], ai_msg.text)
        ai_feedback = models.AIFeedback(
            message_id=ai_msg.id,
            accuracy=data["accuracy"],
            consistency=data["consistency"],
            reliability=data["reliability"],
            personalization=data["personalization"],
            practicality=data["practicality"],
            total_score=data["total_score"],
            vector_db_quality=data["vector_db_quality"],
            detail_accuracy=data["detail_accuracy"],
            detail_consistency=data["detail_consistency"],
            detail_reliability=data["detail_reliability"],
            detail_personalization=data["detail_personalization"],
            detail_practicality=data["detail_practicality"]
        )
        db.add(ai_feedback); generated += 1
    db.commit()
    return {"message": f"{generated}개의 AI피드백 저장 완료", "total": len(items)}

@router.post("/user_feedback", response_model=UserFeedbackResponse)
def submit_user_feedback(
    req: UserFeedbackRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    history = db.query(models.ChatHistory).filter_by(id=req.history_id, user_id=current_user.id).first()
    if not history:
        raise HTTPException(status_code=404, detail="채팅 이력 없음")
    if not history.ended_at:
        raise HTTPException(status_code=400, detail="아직 종료되지 않은 세션에는 피드백 불가")
    existing = db.query(models.UserFeedback).filter_by(history_id=req.history_id, user_id=current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 제출된 피드백입니다.")
    user_feedback = models.UserFeedback(
        history_id=req.history_id,
        user_id=current_user.id,
        feedback=req.feedback
    )
    db.add(user_feedback)
    db.commit()
    db.refresh(user_feedback)
    return UserFeedbackResponse(
        user_feedback_id=user_feedback.id,
        history_id=user_feedback.history_id,
        user_id=user_feedback.user_id,
        feedback=user_feedback.feedback
    )

@router.get("/user_feedback/{history_id}", response_model=UserFeedbackResponse)
def get_user_feedback(
    history_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_feedback = db.query(models.UserFeedback).filter_by(
        history_id=history_id, user_id=current_user.id
    ).first()
    if not user_feedback:
        raise HTTPException(status_code=404, detail="해당 history_id에 대한 유저 피드백 없음")
    return UserFeedbackResponse(
        user_feedback_id=user_feedback.id,
        history_id=user_feedback.history_id,
        user_id=user_feedback.user_id,
        feedback=user_feedback.feedback
    )
