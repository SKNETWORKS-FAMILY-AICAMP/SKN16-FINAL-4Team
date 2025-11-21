from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from services.api_emotion import main as api_emotion
from services.api_color import main as api_color
from services.api_influencer import main as api_influencer
import asyncio

app = FastAPI()


class OrchestratorRequest(BaseModel):
    user_text: str
    conversation_history: Optional[List[Dict[str, Any]]] = None
    personal_color: Optional[str] = None
    user_nickname: Optional[str] = None
    use_color: Optional[bool] = False
    use_emotion: Optional[bool] = True


class OrchestratorResponse(BaseModel):
    emotion: Optional[Dict[str, Any]] = None
    color: Optional[Dict[str, Any]] = None


@app.post("/api/orchestrator/analyze", response_model=OrchestratorResponse)
async def analyze(payload: OrchestratorRequest):
    if not payload or not payload.user_text:
        raise HTTPException(status_code=400, detail="user_text가 필요합니다")

    results = {"emotion": None, "color": None}

    # Recommended pattern: run color and emotion in parallel (they are independent), then pass both results to influencer
    emo_result = None
    color_result = None

    async def _call_emotion():
        try:
            emo_payload = api_emotion.EmotionRequest(
                user_text=payload.user_text,
                conversation_history=payload.conversation_history,
            )
            emo_resp = await api_emotion.generate_emotion(emo_payload)
            return emo_resp
        except Exception as e:
            return {"error": str(e)}

    async def _call_color():
        try:
            color_payload = api_color.ColorRequest(
                user_text=payload.user_text,
                conversation_history=payload.conversation_history,
            )
            color_resp = await api_color.analyze_color(color_payload)
            return color_resp
        except Exception as e:
            return {"error": str(e)}

    # Run both concurrently
    tasks = []
    if payload.use_emotion:
        tasks.append(_call_emotion())
    else:
        tasks.append(asyncio.sleep(0, result=None))

    if payload.use_color:
        tasks.append(_call_color())
    else:
        tasks.append(asyncio.sleep(0, result=None))

    done = await asyncio.gather(*tasks)

    # Map results
    emo_res_raw = done[0]
    color_res_raw = done[1]

    if emo_res_raw is not None:
        emo_result = emo_res_raw.dict() if hasattr(emo_res_raw, "dict") else emo_res_raw
        results["emotion"] = emo_result

    if color_res_raw is not None:
        color_result = color_res_raw.dict() if hasattr(color_res_raw, "dict") else color_res_raw
        results["color"] = color_result

    # Now run influencer styling using both results (influencer should be last)
    influencer_result = None
    try:
        chain_payload = api_influencer.EmotionChainRequest(
            emotion_result=emo_result or {},
            color_result=color_result or {},
            user_nickname=payload.user_nickname,
        )
        chain_resp = api_influencer.style_emotion_chain(chain_payload)
        influencer_result = chain_resp.dict() if hasattr(chain_resp, "dict") else chain_resp
    except Exception as e:
        influencer_result = {"error": str(e)}

    # Attach influencer result to the final response under emotion (or separate if you prefer)
    if results.get("emotion") is None:
        results["emotion"] = {}
    results["emotion"]["influencer_styled"] = influencer_result

    return OrchestratorResponse(emotion=results["emotion"], color=results["color"])
