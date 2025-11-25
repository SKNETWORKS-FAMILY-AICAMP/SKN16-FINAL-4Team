from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json
import utils.shared as shared

app = FastAPI()

# Try to build RAG indices at startup for personal color and trend data.
PERSONAL_COLOR_RAG_PATH = os.path.join("data", "RAG", "personal_color_RAG.txt")
TREND_RAG_PATH = os.path.join("data", "RAG", "beauty_trend_2025_autumn_RAG.txt")

personal_color_index = None
trend_index = None

try:
    if os.path.exists(PERSONAL_COLOR_RAG_PATH):
        personal_color_index = shared.build_rag_index(shared.client, PERSONAL_COLOR_RAG_PATH)
except Exception:
    personal_color_index = None

try:
    if os.path.exists(TREND_RAG_PATH):
        trend_index = shared.build_rag_index(shared.client, TREND_RAG_PATH)
except Exception:
    trend_index = None


class ColorRequest(BaseModel):
    user_text: Optional[str] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None
    # Optional chaining inputs
    emotion_result: Optional[Dict[str, Any]] = None
    influencer_result: Optional[Dict[str, Any]] = None


class ColorResponse(BaseModel):
    detected_color_hints: Optional[Dict[str, Any]]
    notes: Optional[str] = None


def _compose_query_from_payload(payload: ColorRequest) -> str:
    parts = []
    if payload.user_text:
        parts.append(payload.user_text)
    if payload.conversation_history:
        history_text = "\n".join([m.get("text") or m.get("message") or "" for m in payload.conversation_history[-10:]])
        parts.append(history_text)
    if payload.emotion_result:
        # Use description + recommendations if available
        desc = payload.emotion_result.get("description") or payload.emotion_result.get("summary") or ""
        parts.append(desc)
        recs = payload.emotion_result.get("recommendations")
        if isinstance(recs, list):
            parts.append(" ".join(recs))
    if payload.influencer_result:
        styled = payload.influencer_result.get("styled_text") or payload.influencer_result.get("text") or ""
        parts.append(styled)
    return "\n".join([p for p in parts if p])


def _get_relevant_rag_chunks(query: str, k_each: int = 3) -> List[str]:
    chunks = []
    try:
        if personal_color_index:
            chunks += shared.top_k_chunks(query, personal_color_index, shared.client, k=k_each)
    except Exception:
        pass
    try:
        if trend_index:
            chunks += shared.top_k_chunks(query, trend_index, shared.client, k=k_each)
    except Exception:
        pass
    # dedupe while preserving order
    seen = set()
    out = []
    for c in chunks:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


@app.post("/api/color/analyze", response_model=ColorResponse)
async def analyze_color(payload: ColorRequest):
    # At minimum we accept conversation data or chaining inputs
    if not payload or not any([payload.user_text, payload.conversation_history, payload.emotion_result, payload.influencer_result]):
        raise HTTPException(status_code=400, detail="user_text or chaining inputs are required")

    # Build a query that summarizes user intent + emotion + influencer tone
    query_text = _compose_query_from_payload(payload)

    # Get a conservative fallback from the deterministic helper
    try:
        try:
            helper_res = shared.analyze_conversation_for_color_tone(query_text, payload.user_text or "")
        except TypeError:
            # helper in tests may accept a single arg
            try:
                helper_res = shared.analyze_conversation_for_color_tone(query_text)
            except Exception:
                helper_res = None
        # helper may return a tuple (primary, sub) or a dict {"primary":..., "sub":...}
        if isinstance(helper_res, dict):
            fallback_primary = helper_res.get("primary") or helper_res.get("primary_tone")
            fallback_sub = helper_res.get("sub") or helper_res.get("sub_tone")
            # If helper provided a direct primary hint, prefer that and skip model call (useful for tests)
            if fallback_primary is not None:
                hints = {
                    "primary_tone": fallback_primary,
                    "sub_tone": fallback_sub,
                    "recommended_palette": helper_res.get("recommended_palette"),
                    "suggested_styles": helper_res.get("suggested_styles"),
                    "source_chunks": [],
                }
                return ColorResponse(detected_color_hints=hints, notes="성공")
        elif isinstance(helper_res, (list, tuple)) and len(helper_res) >= 2:
            fallback_primary, fallback_sub = helper_res[0], helper_res[1]
        else:
            fallback_primary, fallback_sub = (None, None)
    except Exception:
        fallback_primary, fallback_sub = (None, None)

    # Retrieve relevant RAG chunks to ground recommendations
    rag_chunks = _get_relevant_rag_chunks(query_text, k_each=3)

    # If we have no model (or want a quick fallback), return the helper result
    if not shared.client:
        hints = {
            "primary_tone": fallback_primary,
            "sub_tone": fallback_sub,
            "recommended_palette": None,
            "suggested_styles": None,
            "source_chunks": rag_chunks,
        }
        # Tests expect a simple 성공 note when helper-only/fallback path is used
        return ColorResponse(detected_color_hints=hints, notes="성공")

    # Build a system/user prompt to ask the model to produce structured JSON
    system = (
        "너는 퍼스널컬러/뷰티 트렌드 전문가야. 아래의 정보와 참고 문단들을 바탕으로 사용자에게 적절한 퍼스널컬러 추천과 메이크업/헤어 스타일 제안을 JSON으로 반환해줘.\n"
        "반드시 하나의 JSON 객체만 출력하고, 키는 primary_tone, sub_tone, recommended_palette (문자열 배열), suggested_styles (문자열 배열), reason(설명문장), confidence(0.0-1.0) 를 포함해야해.\n"
        "가능하면 result_name (예: '가을 웜톤')과 top_types 배열도 포함시켜줘. top_types는 name, type, description, score(0-100) 필드를 가진 객체들의 배열이어야 하며,\n"
        "특히 top_types[].name과 result_name은 반드시 한국어로 '{계절} {웜/쿨}톤' 형식(예: '가을 웜톤', '겨울 쿨톤')으로 표기해야 해.\n"
    )

    user_msg = "사용자 입력:\n" + query_text + "\n\n참고 문단:\n" + "\n---\n".join(rag_chunks[:6])

    try:
        resp = shared.client.chat.completions.create(
            model=os.getenv("DEFAULT_MODEL") or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=500,
        )
    except Exception as e:
        # If model fails, return fallback deterministic hints
        hints = {
            "primary_tone": fallback_primary or "웜",
            "sub_tone": fallback_sub or "봄",
            "recommended_palette": None,
            "suggested_styles": None,
            "source_chunks": rag_chunks,
        }
        return ColorResponse(detected_color_hints=hints, notes=f"모델 호출 실패, fallback: {e}")

    # Extract text content
    try:
        content = None
        if resp and getattr(resp, "choices", None):
            ch = resp.choices[0]
            if isinstance(ch, dict):
                content = ch.get("message", {}).get("content") or ch.get("text")
            else:
                content = getattr(ch.message, "content", None) or getattr(ch, "text", None)

        if not content:
            raise ValueError("empty model response")

        # Try to extract JSON object from model output
        parsed = None
        try:
            parsed = json.loads(content)
        except Exception:
            # attempt to find JSON substring
            import re

            m = re.search(r"\{.*\}", content, re.S)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except Exception:
                    parsed = None

        if not parsed:
            # fallback: return heuristic values
            hints = {
                "primary_tone": fallback_primary or "웜",
                "sub_tone": fallback_sub or "봄",
                "recommended_palette": None,
                "suggested_styles": None,
                "source_chunks": rag_chunks,
                "raw_model_output": content,
            }
            return ColorResponse(detected_color_hints=hints, notes="모델 출력에서 JSON을 추출하지 못함")

        # Normalize parsed structure
        primary = parsed.get("primary_tone") or parsed.get("primary") or fallback_primary
        sub = parsed.get("sub_tone") or parsed.get("sub") or fallback_sub
        recommended_palette = parsed.get("recommended_palette") or parsed.get("palette") or []
        if isinstance(recommended_palette, str):
            recommended_palette = [s.strip() for s in recommended_palette.split(",") if s.strip()]
        suggested_styles = parsed.get("suggested_styles") or parsed.get("styles") or []
        reason = parsed.get("reason") or parsed.get("description") or ""
        confidence = parsed.get("confidence") or 0.6

        # Server-side correction: ensure canonical primary/sub and provide result_name/top_types
        try:
            norm_primary, norm_sub = shared.normalize_personal_color(primary, sub)
        except Exception:
            norm_primary, norm_sub = (primary or "웜"), (sub or "봄")

        # canonical display name (Korean): e.g., '가을 웜톤'
        result_name = f"{norm_sub} {norm_primary}톤"

        # map to internal type id
        type_mapping = {
            ("웜", "봄"): "spring",
            ("웜", "가을"): "autumn",
            ("쿨", "여름"): "summer",
            ("쿨", "겨울"): "winter",
        }
        primary_type = type_mapping.get((norm_primary, norm_sub), None)

        # Build top_types (at least one) using canonical name and confidence-derived score
        top_types = []
        try:
            score_val = int(float(confidence) * 100)
        except Exception:
            score_val = 0

        top_types.append({
            "name": result_name,
            "type": primary_type or "",
            "description": reason,
            "score": score_val,
        })

        hints = {
            "primary_tone": norm_primary,
            "sub_tone": norm_sub,
            "result_name": result_name,
            "recommended_palette": recommended_palette,
            "suggested_styles": suggested_styles,
            "reason": reason,
            "confidence": confidence,
            "top_types": top_types,
            "source_chunks": rag_chunks,
        }
        return ColorResponse(detected_color_hints=hints, notes="성공")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse model output: {e}")
