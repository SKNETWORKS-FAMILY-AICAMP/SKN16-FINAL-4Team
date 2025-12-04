from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import re

from services.api_emotion import main as api_emotion
from services.api_color import main as api_color
from services.api_influencer import main as api_influencer
import asyncio

import os
import logging

app = FastAPI()

# simple logger
logger = logging.getLogger("orchestrator")
logging.basicConfig(level=logging.INFO)
ENV = os.getenv("ENVIRONMENT") or os.getenv("ENV") or "production"


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
            # Support both coroutine functions and sync functions (tests may patch either)
            if asyncio.iscoroutinefunction(api_emotion.generate_emotion):
                emo_resp = await api_emotion.generate_emotion(emo_payload)
            else:
                # Try calling sync implementation directly first. If it fails due to "event loop is already running",
                # run it in a separate thread with its own event loop so sync helpers using run_until_complete work.
                try:
                    emo_resp = api_emotion.generate_emotion(emo_payload)
                except RuntimeError as e:
                    msg = str(e)
                    if "already running" in msg:
                        def _invoke_in_thread():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                return api_emotion.generate_emotion(emo_payload)
                            finally:
                                try:
                                    loop.close()
                                except Exception:
                                    pass
                        loop = asyncio.get_running_loop()
                        emo_resp = await loop.run_in_executor(None, _invoke_in_thread)
                    else:
                        raise
            return emo_resp
        except Exception as e:
            return {"error": str(e)}

    async def _call_color():
        try:
            color_payload = api_color.ColorRequest(
                user_text=payload.user_text,
                conversation_history=payload.conversation_history,
            )
            if asyncio.iscoroutinefunction(api_color.analyze_color):
                color_resp = await api_color.analyze_color(color_payload)
            else:
                try:
                    color_resp = api_color.analyze_color(color_payload)
                except RuntimeError as e:
                    msg = str(e)
                    if "already running" in msg:
                        def _invoke_in_thread_color():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                return api_color.analyze_color(color_payload)
                            finally:
                                try:
                                    loop.close()
                                except Exception:
                                    pass
                        loop = asyncio.get_running_loop()
                        color_resp = await loop.run_in_executor(None, _invoke_in_thread_color)
                    else:
                        raise
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
        # Wrap into namespaced structure: parsed + raw_model_output
        emo_wrapped = {
            "source": "api_emotion",
            "parsed": emo_result,
            "raw_model_output": (emo_result.get("raw") if isinstance(emo_result, dict) else None),
        }
        results["emotion"] = emo_wrapped

        # Promote parsed keys to top-level for backwards compatibility (tests expect primary_tone at top-level)
        try:
            if isinstance(emo_result, dict):
                # copy parsed keys into the top-level wrapper if not present
                for k, v in emo_result.items():
                    if k not in results["emotion"]:
                        results["emotion"][k] = v
        except Exception:
            pass

    if color_res_raw is not None:
        color_result = color_res_raw.dict() if hasattr(color_res_raw, "dict") else color_res_raw
        color_wrapped = {
            "source": "api_color",
            "parsed": color_result,
            "raw_model_output": color_result.get("raw_model_output") if isinstance(color_result, dict) else None,
        }
        results["color"] = color_wrapped

        # Promote parsed color hints to top-level for convenience
        try:
            if isinstance(color_result, dict):
                for k, v in color_result.items():
                    if k not in results["color"]:
                        results["color"][k] = v
        except Exception:
            pass

    # Normalize common key aliases for compatibility with tests / upstream callers
    try:
        if results.get("emotion"):
            e_wrapped = results["emotion"]
            e = e_wrapped.get("parsed") if isinstance(e_wrapped, dict) else e_wrapped
            # if the emotion response contains nested 'raw' or other formats, try to flatten minimal keys
            if isinstance(e, dict):
                # map 'primary' -> 'primary_tone' and vice versa
                if "primary" in e and "primary_tone" not in e:
                    e["primary_tone"] = e.get("primary")
                if "primary_tone" in e and "primary" not in e:
                    e["primary"] = e.get("primary_tone")
                if "sub" in e and "sub_tone" not in e:
                    e["sub_tone"] = e.get("sub")
                if "sub_tone" in e and "sub" not in e:
                    e["sub"] = e.get("sub_tone")

        if results.get("color"):
            c_wrapped = results["color"]
            c = c_wrapped.get("parsed") if isinstance(c_wrapped, dict) else c_wrapped
            # color_result might be a ColorResponse dict with detected_color_hints
            if isinstance(c, dict):
                hints = c.get("detected_color_hints") or c
                if isinstance(hints, dict):
                    if "primary" in hints and "primary_tone" not in hints:
                        hints["primary_tone"] = hints.get("primary")
                    if "primary_tone" in hints and "primary" not in hints:
                        hints["primary"] = hints.get("primary_tone")
                    if "sub" in hints and "sub_tone" not in hints:
                        hints["sub_tone"] = hints.get("sub")
                    if "sub_tone" in hints and "sub" not in hints:
                        hints["sub"] = hints.get("sub_tone")
                    # ensure detected_color_hints preserved
                    if c.get("detected_color_hints") is None:
                        c["detected_color_hints"] = hints
                    else:
                        c["detected_color_hints"] = hints
                    # write back parsed into wrapper
                    if isinstance(c_wrapped, dict):
                        c_wrapped["parsed"] = c
                        results["color"] = c_wrapped
                    else:
                        results["color"] = c
    except Exception:
        # best-effort normalization; don't fail the whole endpoint if normalization fails
        pass

    # Now run influencer styling using both results (influencer should be last)
    influencer_result = None
    try:
        chain_payload = api_influencer.EmotionChainRequest(
            emotion_result=emo_result or {},
            color_result=color_result or {},
            user_nickname=payload.user_nickname,
            influencer_name=payload.influencer_name if getattr(payload, 'influencer_name', None) else None,
        )
        # Detect if this analyze call is actually a welcome/message-seeding request
        # by looking for common welcome/upload keywords in the original user_text.
        try:
            is_welcome = False
            if isinstance(payload.user_text, str) and re.search(r"이미지|업로드|환영|환영해|환영합니다", payload.user_text):
                is_welcome = True
            if is_welcome:
                # attach a small meta flag so api_influencer can generate a welcome-style message
                try:
                    if isinstance(chain_payload.emotion_result, dict):
                        chain_payload.emotion_result.setdefault('_meta', {})
                        chain_payload.emotion_result['_meta'].update({'is_welcome': True, 'welcome_prompt': payload.user_text})
                    else:
                        chain_payload.emotion_result = {'_meta': {'is_welcome': True, 'welcome_prompt': payload.user_text}}
                except Exception:
                    pass
        except Exception:
            # non-fatal; continue without welcome flag
            pass
        chain_resp = api_influencer.style_emotion_chain(chain_payload)
        influencer_result = chain_resp.dict() if hasattr(chain_resp, "dict") else chain_resp
        # Wrap influencer result
        influencer_wrapped = {
            "source": "api_influencer",
            "parsed": influencer_result,
            "raw_model_output": influencer_result.get("raw") if isinstance(influencer_result, dict) else None,
        }
        # If influencer returned a styled text, set it as the emotion description
        try:
            # styled_text may be at top-level or under 'parsed'
            styled = None
            if isinstance(influencer_result, dict):
                # common places to look
                styled = (
                    influencer_result.get('styled_text')
                    or (influencer_result.get('parsed') or {}).get('styled_text')
                    or influencer_result.get('text')
                    or influencer_result.get('response')
                )

            if styled:
                # ensure emotion wrapper exists and has parsed dict
                if results.get('emotion') is None:
                    results['emotion'] = {}

                # if parsed dict exists, prefer placing description there
                try:
                    if isinstance(results['emotion'], dict) and isinstance(results['emotion'].get('parsed'), dict):
                        results['emotion']['parsed']['description'] = styled
                    else:
                        # fallback to a top-level description field
                        results['emotion']['description'] = styled
                except Exception:
                    # best-effort only; do not fail the request
                    results['emotion']['description'] = styled
        except Exception:
            pass
        # if ENV development, log service outputs for debugging
        if ENV and ENV.lower() == "development":
            try:
                logger.info("[orchestrator] emotion result: %s", emo_result)
                logger.info("[orchestrator] color result: %s", color_result)
                logger.info("[orchestrator] influencer result: %s", influencer_result)
            except Exception:
                pass
    except Exception as e:
        influencer_result = {"error": str(e)}

    # Attach influencer result to the final response under emotion (or separate if you prefer)
    # Attach influencer under a clear namespace; prefer the wrapped structure
    if results.get("emotion") is None:
        results["emotion"] = {}
    results["emotion"]["influencer_styled"] = influencer_wrapped if 'influencer_wrapped' in locals() else influencer_result

    # Return a structured response model (keep compatibility by keeping keys similar)
    return OrchestratorResponse(emotion=results["emotion"], color=results["color"])
