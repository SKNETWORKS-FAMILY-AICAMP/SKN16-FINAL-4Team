from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import re
import asyncio
import os
import logging

from services.api_emotion import main as api_emotion
from services.api_color import main as api_color
from services.api_influencer import main as api_influencer

app = FastAPI()

logger = logging.getLogger("orchestrator")
logging.basicConfig(level=logging.INFO)
ENV = os.getenv("ENVIRONMENT") or os.getenv("ENV") or "production"


def _to_dict(obj: Any) -> Dict[str, Any]:
    """Pydantic v2 호환: model_dump() 또는 dict() 사용"""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    elif hasattr(obj, "dict"):
        return obj.dict()
    return obj if isinstance(obj, dict) else {}


class OrchestratorRequest(BaseModel):
    user_text: str
    conversation_history: Optional[List[Dict[str, Any]]] = None
    personal_color: Optional[str] = None
    user_nickname: Optional[str] = None
    influencer_name: Optional[str] = None
    use_color: Optional[bool] = False
    use_emotion: Optional[bool] = True


class OrchestratorResponse(BaseModel):
    emotion: Optional[Dict[str, Any]] = None
    color: Optional[Dict[str, Any]] = None


def _normalize_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """응답 구조 정규화: 필드명 일관성 확보"""
    if not result:
        return result
    
    # primary/sub 필드명 정규화
    if "primary" in result and "primary_tone" not in result:
        result["primary_tone"] = result.get("primary")
    if "sub" in result and "sub_tone" not in result:
        result["sub_tone"] = result.get("sub")
    
    return result


def _invoke_sync_service(service_func, payload):
    """동기 함수를 이벤트 루프 내에서 안전하게 호출"""
    try:
        return service_func(payload)
    except RuntimeError as e:
        if "already running" not in str(e) and "no current event loop" not in str(e):
            raise
        # 이미 실행 중인 루프가 있으면 별도 스레드에서 실행
        def _run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return service_func(payload)
            finally:
                try:
                    loop.close()
                except Exception:
                    pass
        
        # 동기 방식으로 실행 후 결과 반환
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_in_thread)
            return future.result()


@app.post("/api/orchestrator/analyze", response_model=OrchestratorResponse)
async def analyze(payload: OrchestratorRequest):
    """통합 분석 엔드포인트: 감정 + 색상 + 인플루언서 스타일링"""
    if not payload or not payload.user_text:
        raise HTTPException(status_code=400, detail="user_text가 필요합니다")

    # 1. 감정 및 색상 분석 병렬 처리
    async def _call_emotion():
        try:
            emo_payload = api_emotion.EmotionRequest(
                user_text=payload.user_text,
                conversation_history=payload.conversation_history,
            )
            if asyncio.iscoroutinefunction(api_emotion.generate_emotion):
                return await api_emotion.generate_emotion(emo_payload)
            else:
                # 동기 함수 처리
                result = api_emotion.generate_emotion(emo_payload)
                # 코루틴이 반환되면 await
                if asyncio.iscoroutine(result):
                    return await result
                return result
        except Exception as e:
            logger.error(f"[emotion] 실패: {e}")
            return {"error": str(e)}

    async def _call_color():
        try:
            color_payload = api_color.ColorRequest(
                user_text=payload.user_text,
                conversation_history=payload.conversation_history,
            )
            if asyncio.iscoroutinefunction(api_color.analyze_color):
                return await api_color.analyze_color(color_payload)
            else:
                # 동기 함수 처리
                result = api_color.analyze_color(color_payload)
                # 코루틴이 반환되면 await
                if asyncio.iscoroutine(result):
                    return await result
                return result
        except Exception as e:
            logger.error(f"[color] 실패: {e}")
            return {"error": str(e)}

    # 병렬 실행
    tasks = []
    if payload.use_emotion:
        tasks.append(_call_emotion())
    if payload.use_color:
        tasks.append(_call_color())

    if not tasks:
        return OrchestratorResponse(emotion=None, color=None)

    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    emo_res = results_list[0] if payload.use_emotion else None
    color_res = results_list[1] if (payload.use_emotion and payload.use_color) or (not payload.use_emotion and payload.use_color) else None

    # 2. 결과 변환 (Pydantic v2 호환)
    emo_result = _to_dict(emo_res) if emo_res else None
    color_result = _to_dict(color_res) if color_res else None

    # 정규화
    if emo_result:
        emo_result = _normalize_response(emo_result)
    if color_result:
        color_result = _normalize_response(color_result)

    # 3. 인플루언서 스타일링 (감정+색상 결과 활용)
    influencer_styled = None
    try:
        chain_payload = api_influencer.EmotionChainRequest(
            emotion_result=emo_result or {},
            color_result=color_result or {},
            user_nickname=payload.user_nickname,
            influencer_name=payload.influencer_name,
        )
        
        # 웰컴 메시지 감지
        if isinstance(payload.user_text, str) and re.search(r"이미지|업로드|환영", payload.user_text):
            if isinstance(chain_payload.emotion_result, dict):
                chain_payload.emotion_result.setdefault("_meta", {})["is_welcome"] = True

        chain_resp = api_influencer.style_emotion_chain(chain_payload)
        influencer_styled = _to_dict(chain_resp)
    except Exception as e:
        logger.error(f"[influencer] 실패: {e}")
        influencer_styled = {"error": str(e)}

    # 4. 최종 응답 구성
    response = {
        "emotion": emo_result or {},
        "color": color_result or {},
    }

    # 인플루언서 스타일 감정에 추가
    if influencer_styled and "styled_text" in influencer_styled:
        if response["emotion"]:
            response["emotion"]["styled_text"] = influencer_styled["styled_text"]

    if ENV and ENV.lower() == "development":
        logger.info(f"[orchestrator] emotion: {emo_result}")
        logger.info(f"[orchestrator] color: {color_result}")
        logger.info(f"[orchestrator] influencer: {influencer_styled}")

    return OrchestratorResponse(**response)
