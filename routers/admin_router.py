from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import models
import json
from routers.user_router import get_current_user
from utils.shared import get_db

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def parse_chat_pair_items(history):
    msgs = sorted(history.messages, key=lambda m: m.id)
    items = []
    qid = 1
    for i in range(0, len(msgs)-1, 2):
        if msgs[i].role == "user" and msgs[i+1].role == "ai":
            # ai message text may be a JSON string; standardize to always return an object
            try:
                parsed = json.loads(msgs[i+1].text)
                # if parsed is not an object, wrap it
                answer_obj = parsed if isinstance(parsed, dict) else {"text": parsed}
            except Exception:
                answer_obj = {"text": msgs[i+1].text}
            items.append({
                "question_id": qid,
                "question": msgs[i].text,
                "ai_msg": msgs[i+1],
                "answer": answer_obj,
            })
            qid += 1
    return items


@router.get("/chat_histories")
def get_admin_chat_histories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user_id: Optional[int] = None,
    include_ai_feedback: bool = True,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # admin 권한 체크
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자만 접근 가능합니다.")

    query = db.query(models.ChatHistory)
    if user_id:
        query = query.filter(models.ChatHistory.user_id == user_id)

    total = query.count()
    histories = query.order_by(models.ChatHistory.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for h in histories:
        # user feedback (if any)
        uf = db.query(models.UserFeedback).filter_by(history_id=h.id).first()
        user_feedback = None
        if uf:
            user_feedback = {
                "id": uf.id,
                "user_id": uf.user_id,
                "feedback": uf.feedback,
                "created_at": uf.created_at.isoformat() if hasattr(uf, 'created_at') and uf.created_at else None,
            }

        qa_items = []
        pairs = parse_chat_pair_items(h)
        for p in pairs:
            ai_msg = p["ai_msg"]
            ai_feedback_obj = None
            if include_ai_feedback:
                fb = db.query(models.AIFeedback).filter_by(message_id=ai_msg.id).first()
                if fb:
                    ai_feedback_obj = {
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
                        "detail_practicality": fb.detail_practicality,
                        "created_at": fb.created_at.isoformat() if hasattr(fb, 'created_at') and fb.created_at else None,
                    }

            qa_items.append({
                "question": p["question"],
                "question_id": p["question_id"],
                "answer": p["answer"],
                "answer_id": ai_msg.id,
                "ai_feedback": ai_feedback_obj,
            })

        items.append({
            "chat_history_id": h.id,
            "user_id": h.user_id,
            "created_at": h.created_at.isoformat() if hasattr(h, 'created_at') and h.created_at else None,
            "ended_at": h.ended_at.isoformat() if hasattr(h, 'ended_at') and h.ended_at else None,
            "user_feedback": user_feedback,
            "qa_pairs": qa_items,
        })

    return {"page": page, "page_size": page_size, "total": total, "items": items}
