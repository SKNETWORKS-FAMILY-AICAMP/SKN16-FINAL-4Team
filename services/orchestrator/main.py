from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import re
import asyncio
import os
import logging
import time

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
    start_time = time.time()
    """통합 분석 엔드포인트: 감정 + 색상 + 인플루언서 스타일링"""
    if not payload or not payload.user_text:
        raise HTTPException(status_code=400, detail="user_text가 필요합니다")

    # 0. Check for pre-analyzed JSON payload (e.g. from image analysis)
    pre_analyzed = None
    try:
        import json
        if payload.user_text.strip().startswith('{'):
            parsed = json.loads(payload.user_text)
            if isinstance(parsed, dict) and ('image_result' in parsed or 'orchestrator' in parsed):
                pre_analyzed = parsed
    except Exception:
        pass

    emo_res = None
    color_res = None
    
    # 🔥 이미지 분석 결과가 있어도 RAG 기반 추천을 위해 api_color 호출 필요
    should_call_color_api = payload.use_color and pre_analyzed and pre_analyzed.get('image_result')

    if pre_analyzed:
        logger.info("[orchestrator] Using pre-analyzed data from payload")
        orch_data = pre_analyzed.get('orchestrator') or {}
        emo_res = orch_data.get('emotion')
        
        # 🔥 이미지 결과가 있으면 일단 기본 color_res만 구성 (RAG는 아래에서 호출)
        if pre_analyzed.get('image_result'):
            img_res = pre_analyzed.get('image_result')
            best_type = img_res.get('best_type') or {}
            season = img_res.get('season') or best_type.get('season')
            
            # Map season to primary/sub if possible
            p_tone = None
            s_tone = None
            if season:
                if '봄' in season: s_tone = 'spring'
                elif '여름' in season: s_tone = 'summer'
                elif '가을' in season: s_tone = 'autumn'
                elif '겨울' in season: s_tone = 'winter'
                
                if '웜' in season: p_tone = 'warm'
                elif '쿨' in season: p_tone = 'cool'
            
            # Construct new color hints from image result
            new_color_hints = {
                "primary_tone": p_tone,
                "sub_tone": s_tone,
                "result_name": best_type.get('name') or season,
                "reason": f"이미지 분석 결과: {best_type.get('name') or season} ({best_type.get('description') or ''})",
                "confidence": best_type.get('probability', 0.0) / 100.0 if best_type.get('probability') else 0.8
            }
            
            # 임시 color_res 구성 (아래에서 RAG 호출로 업데이트됨)
            color_res = {"detected_color_hints": new_color_hints}
            
        # If emotion is missing, default to neutral or extract from image message
        if not emo_res:
            img_res = pre_analyzed.get('image_result', {})
            msg = img_res.get('message', '')
            status = img_res.get('status')
            best_name = img_res.get('best_type', {}).get('name')

            # If expert is required but we have a guess, guide the conversation
            if status == 'require_expert' and best_name:
                msg = "이미지에서 퍼스널 컬러 특징을 일부 확인했습니다. 더 정확한 분석을 위해 평소 즐겨 입으시는 옷 색상이나 선호하는 스타일을 알려주시겠어요?"
            elif best_name:
                msg = "이미지 분석이 완료되었습니다! 더 구체적인 스타일링 추천을 위해 평소 선호하시는 색상이나 분위기를 말씀해 주시겠어요?"
            elif not msg:
                msg = "이미지 분석이 완료되었습니다. 더 정확한 결과를 위해 평소 스타일을 알려주세요."

            emo_res = {
                "primary_tone": "neutral",
                "description": msg,
                "recommendations": [
                    "자주 입는 옷 색상 알려주기",
                    "어울리는 악세사리(골드/실버) 말하기",
                    "피부톤 특징 이야기하기"
                ],
                "_meta": {
                    "suppress_type_mention": True
                }
            }

    else:
        # 1. 감정 및 색상 분석 병렬 처리 (Original Logic)
        async def _call_emotion():
            t0 = time.time()
            try:
                emo_payload = api_emotion.EmotionRequest(
                    user_text=payload.user_text,
                    conversation_history=payload.conversation_history,
                )
                res = None
                if asyncio.iscoroutinefunction(api_emotion.generate_emotion):
                    res = await api_emotion.generate_emotion(emo_payload)
                else:
                    # 동기 함수 처리
                    result = api_emotion.generate_emotion(emo_payload)
                    # 코루틴이 반환되면 await
                    if asyncio.iscoroutine(result):
                        res = await result
                    else:
                        res = result
                print(f"✅ [Orchestrator] Emotion API Response: {res}")
                logger.info(f"[orchestrator] Emotion API took {time.time() - t0:.2f}s")
                return res
            except Exception as e:
                logger.error(f"[emotion] 실패: {e}")
                print(f"❌ [Orchestrator] Emotion API Error: {e}")
                return {"error": str(e)}

        async def _call_color():
            t0 = time.time()
            try:
                print(f"🎨 [Orchestrator] Color API 호출 시작...")
                print(f"   - user_text: {payload.user_text[:100] if payload.user_text else 'None'}...")
                print(f"   - conversation_history: {len(payload.conversation_history) if payload.conversation_history else 0} messages")
                
                color_payload = api_color.ColorRequest(
                    user_text=payload.user_text,
                    conversation_history=payload.conversation_history,
                )
                res = None
                if asyncio.iscoroutinefunction(api_color.analyze_color):
                    res = await api_color.analyze_color(color_payload)
                else:
                    # 동기 함수 처리
                    result = api_color.analyze_color(color_payload)
                    # 코루틴이 반환되면 await
                    if asyncio.iscoroutine(result):
                        res = await result
                    else:
                        res = result
                print(f"✅ [Orchestrator] Color API Response: {res}")
                logger.info(f"[orchestrator] Color API took {time.time() - t0:.2f}s")
                return res
            except Exception as e:
                logger.error(f"[color] 실패: {e}")
                print(f"❌ [Orchestrator] Color API Error: {e}")
                import traceback
                traceback.print_exc()
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
    
    # 🔥 이미지 분석 시에도 RAG 기반 추천을 위해 api_color 호출
    if should_call_color_api:
        print(f"🎨 [Orchestrator] 이미지 결과 있음 -> RAG 기반 추천 위해 api_color 호출")
        async def _call_color_for_image():
            t0 = time.time()
            try:
                # 이미지 결과를 user_text에 포함
                img_info = f"퍼스널 컬러: {color_res.get('detected_color_hints', {}).get('result_name', '')}"
                
                color_payload = api_color.ColorRequest(
                    user_text=img_info,
                    conversation_history=payload.conversation_history,
                )
                res = None
                if asyncio.iscoroutinefunction(api_color.analyze_color):
                    res = await api_color.analyze_color(color_payload)
                else:
                    result = api_color.analyze_color(color_payload)
                    if asyncio.iscoroutine(result):
                        res = await result
                    else:
                        res = result
                print(f"✅ [Orchestrator] RAG 기반 Color 응답: {res}")
                logger.info(f"[orchestrator] RAG Color API took {time.time() - t0:.2f}s")
                return res
            except Exception as e:
                logger.error(f"[color RAG] 실패: {e}")
                print(f"❌ [Orchestrator] RAG Color API Error: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        rag_color_res = await _call_color_for_image()
        if rag_color_res:
            # RAG 응답을 기존 color_res에 병합
            rag_dict = _to_dict(rag_color_res)
            if rag_dict and 'detected_color_hints' in rag_dict:
                # 기존 이미지 분석 결과는 유지하면서 RAG 추천만 추가
                if color_res and 'detected_color_hints' in color_res:
                    # RAG에서 받은 추천 정보만 병합
                    rag_hints = rag_dict['detected_color_hints']
                    if 'recommended_palette' in rag_hints:
                        color_res['detected_color_hints']['recommended_palette'] = rag_hints['recommended_palette']
                    if 'suggested_styles' in rag_hints:
                        color_res['detected_color_hints']['suggested_styles'] = rag_hints['suggested_styles']
                    if 'rag_metadata' in rag_hints:
                        color_res['detected_color_hints']['rag_metadata'] = rag_hints['rag_metadata']

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
        # Prepare color result for influencer (masking if needed)
        chain_color_res = color_result
        if emo_result and emo_result.get('_meta', {}).get('suppress_type_mention'):
            import copy
            chain_color_res = copy.deepcopy(color_result)
            if chain_color_res and 'detected_color_hints' in chain_color_res:
                hints = chain_color_res['detected_color_hints']
                # Mask explicit names but keep tones for styling context
                if 'result_name' in hints:
                    hints['result_name'] = "Analyzed Style"
                # Mask reason to prevent leaking the name
                if 'reason' in hints:
                     hints['reason'] = "이미지에서 감지된 퍼스널 컬러 특징"

        chain_payload = api_influencer.EmotionChainRequest(
            emotion_result=emo_result or {},
            color_result=chain_color_res or {},
            user_nickname=payload.user_nickname,
            influencer_name=payload.influencer_name,
        )
        
        # 웰컴 메시지 감지
        if isinstance(payload.user_text, str) and re.search(r"이미지|업로드|환영", payload.user_text):
            if isinstance(chain_payload.emotion_result, dict):
                chain_payload.emotion_result.setdefault("_meta", {})["is_welcome"] = True

        t0 = time.time()
        chain_resp = api_influencer.style_emotion_chain(chain_payload)
        logger.info(f"[orchestrator] Influencer API took {time.time() - t0:.2f}s")
        influencer_styled = _to_dict(chain_resp)
        print(f"✅ [Orchestrator] Influencer API Response: {influencer_styled}")
    except Exception as e:
        logger.error(f"[influencer] 실패: {e}")
        print(f"❌ [Orchestrator] Influencer API Error: {e}")
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

    end_time = time.time()
    logger.info(f"[orchestrator] Total execution time: {end_time - start_time:.2f}s")

    return OrchestratorResponse(**response)
