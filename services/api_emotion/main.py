from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json
import re

import utils.shared as shared
from utils.emotion_lottie import to_canonical

app = FastAPI()


class EmotionRequest(BaseModel):
    user_text: str
    conversation_history: Optional[List[Dict[str, Any]]] = None
    # This service focuses on emotion only; personal-color fields removed to keep single responsibility


class EmotionResponse(BaseModel):
    primary_tone: str
    sub_tone: Optional[str]
    description: str
    recommendations: List[str]
    # 추가 메타 정보
    confidence: Optional[float] = None  # 0.0 - 1.0
    tone_tags: Optional[List[str]] = None
    raw: Optional[Dict[str, Any]] = None
    # canonical 6-class label (one of: happy, sad, angry, love, fearful, neutral)
    canonical_label: Optional[str] = None


def _get_model_to_use() -> str:
    # Prefer explicit env var for emotion model, fallback to a reasonable default
    return os.getenv("EMOTION_MODEL_ID") or os.getenv("DEFAULT_MODEL") or "gpt-4o-mini"


def _extract_json_from_text(text: str):
    # Try to find the first JSON object in the text and parse it
    # Look for {...}
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    s = m.group(0)
    try:
        return json.loads(s)
    except Exception:
        return None


def _detect_emotion_label(text: str) -> str:
    """
    모델에게 감정 라벨 하나만 반환하도록 요청하여
    `happy, sad, angry, love, fearful, neutral` 중 하나를 얻습니다.
    실패하면 'neutral'을 반환합니다.
    """
    if not text:
        return "neutral"

    valid_emotions = ["happy", "sad", "angry", "love", "fearful", "neutral"]
    prompt = f"""
다음 사용자 발화의 감정을 아래 목록 중 하나로만 분류하세요. 반드시 한 단어만 답하세요. 다른 단어, 설명 없이.
목록: happy, sad, angry, love, fearful, neutral
발화: "{text}"
감정 (목록 중 하나, 한 단어만):
"""
    try:
        resp = shared.client.chat.completions.create(
            model=_get_model_to_use(),
            messages=[
                {"role": "system", "content": "너는 감정 분석 전문가야. 반드시 목록 중 하나의 감정만 한 단어로 답해줘."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=6,
            temperature=0.0,
        )

        content = None
        if resp and getattr(resp, "choices", None):
            ch = resp.choices[0]
            if isinstance(ch, dict):
                content = ch.get("message", {}).get("content") or ch.get("text")
            else:
                content = getattr(ch.message, "content", None) or getattr(ch, "text", None)

        if not content:
            return "neutral"

        emotion = str(content).strip().lower()
        # 정확히 매칭
        for e in valid_emotions:
            if emotion == e:
                return e
        # 포함되어 있으면 첫 매칭 반환
        for e in valid_emotions:
            if e in emotion:
                return e
        return "neutral"
    except Exception:
        return "neutral"


def _query_for_canonical(text: str) -> str:
    """
    Ask the model in a very constrained way to return exactly one canonical label.
    Returns one of the valid labels or 'neutral' on failure.
    This is used as a single retry when the main JSON output lacks a valid canonical_label.
    """
    try:
        valid = ["happy", "sad", "angry", "love", "fearful", "neutral"]
        prompt = f"다음 발화의 감정을 정확히 한 단어로만 아래 목록 중에서 골라서 반환하세요(다른 텍스트 금지): {', '.join(valid)}\n발화: {text}\n라벨:"
        resp = shared.client.chat.completions.create(
            model=_get_model_to_use(),
            messages=[
                {"role": "system", "content": "응답은 반드시 목록 중 하나의 단어만 한 단어로 반환하세요."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=6,
        )
        content = None
        if resp and getattr(resp, "choices", None):
            ch = resp.choices[0]
            if isinstance(ch, dict):
                content = ch.get("message", {}).get("content") or ch.get("text")
            else:
                content = getattr(ch.message, "content", None) or getattr(ch, "text", None)
        if not content:
            return "neutral"
        lab = str(content).strip().lower()
        for v in valid:
            if lab == v or v in lab:
                return v
        return "neutral"
    except Exception:
        return "neutral"


@app.post("/api/emotion/generate", response_model=EmotionResponse)
async def generate_emotion(payload: EmotionRequest):
    if not payload or not payload.user_text:
        raise HTTPException(status_code=400, detail="user_text가 필요합니다")

    # Build conversation context from recent messages
    conv_text = payload.user_text
    if payload.conversation_history:
        conv_text = "\n".join([m.get("text") or m.get("message") or "" for m in payload.conversation_history[-10:]])

    # Build a system prompt optimized for emotion analysis.
    # When a fine-tuned/emotion model is used, apply a friend-like empathetic system prompt
    # inspired by chatbot_evaluation.py to get the best tone-aware output.
    fine_tuned_system_prompt = """
당신은 사용자의 가장 친한 친구입니다. 다음 가이드라인을 따라 대화하세요:

감정 공감 우선:
- 사용자의 감정을 먼저 정확히 파악하고 공감 표현
- 자신감 부족이나 고민에 공감하며 위로
- 긍정적인 변화를 위한 격려와 응원 메시지
- "정말 힘들겠다", "그런 마음 이해해" 같은 공감 언어 사용
- 감정을 무시하거나 성급히 해결책만 제시하지 말고 먼저 위로

자연스러운 친구 톤:
- 적절한 친구 표현 사용 ("그치", "맞아", "진짜")
- 친근하되 품격 유지
- 과도한 줄임말이나 지나친 캐주얼함은 피하기

진정성 있는 조언:
- 자신의 경험이나 생각을 자연스럽게 공유
- 실질적이면서도 따뜻한 해결책 제시
- 사용자가 혼자가 아님을 느끼게 하는 응원

당신은 감정을 깊이 이해하는 능력이 뛰어나므로, 이를 활용해 사용자와 진심어린 대화를 나누세요.
"""

    base_system_prompt = """당신은 친구처럼 편안하고 공감해주는 챗봇입니다. 
    사용자의 감정을 잘 이해하고 자연스럽게 대화해주세요.
    반말로 친구같이 편안하게 대화하되, 따뜻하고 진심어린 톤을 유지해주세요."""

    # Strict JSON enforcement instructions (always include this)
    json_instructions = (
        "\n\n중요: 설명 없이 단 하나의 유효한 JSON 객체만 반환하세요. "
        "JSON은 다음 키들을 반드시 포함해야 합니다: primary_tone (짧은 문자열), sub_tone (선택, 문자열 또는 null), description (한 단락으로 된 설명), "
        "recommendations (짧은 문자열들의 배열). 또한 반드시 하나의 `canonical_label` 필드를 포함하세요. 이 값은 정확히 하나의 단어여야 하며 다음 중 하나여야 합니다: [happy, sad, angry, love, fearful, neutral]. "
        "선택적으로 추가할 수 있는 메타 필드: confidence (0.0-1.0), tone_tags (감정 태그 배열). "
        "예시: {\"primary_tone\":\"calm\", \"sub_tone\": null, \"description\":\"사용자는 차분해 보입니다.\", \"recommendations\":[\"부드러운 색상 사용\"], \"confidence\":0.92, \"tone_tags\":[\"calm\"], \"canonical_label\": \"neutral\" }"
    )

    # Additional few-shot examples to bias the model towards the canonical 6 labels
    few_shot_examples = """
예시 매핑:
- "정말 고마워요, 덕분에 행복한 하루였어요." -> canonical_label: happy
- "요즘 우울해서 아무것도 하기 싫어요." -> canonical_label: sad
- "그 사람 태도 때문에 열이 받아요." -> canonical_label: angry
- "내 노력을 무시하는 태도에 분노가 치밀어요." -> canonical_label: angry
- "그와 함께 있으면 행복하고 사랑을 느껴." -> canonical_label: love
- "무서워서 혼자 있을 수가 없어요." -> canonical_label: fearful
- "별 감정이 없어요." -> canonical_label: neutral

규칙: canonical_label은 반드시 위 6개 중 하나여야 하며, 불확실하면 'neutral'을 사용하세요.
"""

    # Choose system prompt based on model selection
    model = _get_model_to_use()
    # Include few-shot examples to bias model outputs toward the canonical 6-label set
    if model and os.getenv("EMOTION_MODEL_ID") and model == os.getenv("EMOTION_MODEL_ID"):
        system = fine_tuned_system_prompt + "\n" + few_shot_examples + json_instructions
    else:
        system = base_system_prompt + "\n" + few_shot_examples + json_instructions

    user_msg = f"대화:\n{conv_text}\n\n사용자 메시지:\n{payload.user_text}"

    # Choose generation params tuned for structured emotion output
    # Prefer lower temperature for deterministic JSON, allow slightly higher for base models
    # Make generation more deterministic to encourage consistent canonical output
    temp = 0.0
    max_tokens = 480

    try:
        resp = shared.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=temp,
            max_tokens=max_tokens,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream model error: {e}")

    # Extract content
    try:
        content = None
        if resp and getattr(resp, "choices", None):
            # Support both dict-like and attr-like responses
            ch = resp.choices[0]
            if isinstance(ch, dict):
                content = ch.get("message", {}).get("content") or ch.get("text")
            else:
                content = getattr(ch.message, "content", None) or getattr(ch, "text", None)

        if content is None:
            raise ValueError("empty model response")

        parsed = _extract_json_from_text(content)
        if not parsed:
            # As fallback, attempt to interpret whole content as JSON
            try:
                parsed = json.loads(content)
            except Exception:
                # return a deterministic structure with the model text in description
                return EmotionResponse(
                    primary_tone="neutral",
                    sub_tone=None,
                    description=content.strip(),
                    recommendations=["No structured recommendations returned by model"],
                    raw={"model_output": content},
                )

        # Validate parsed structure minimally
        primary = parsed.get("primary_tone") or parsed.get("primary") or parsed.get("tone")
        sub = parsed.get("sub_tone") or parsed.get("sub")
        description = parsed.get("description") or parsed.get("summary") or ""
        recommendations = parsed.get("recommendations") or parsed.get("advice") or []

        if isinstance(recommendations, str):
            # split by sentence
            recommendations = [r.strip() for r in re.split(r"[\n\.;]\s*", recommendations) if r.strip()]

        # confidence: prefer model-provided value, otherwise simple heuristic
        confidence = parsed.get("confidence")
        if confidence is None:
            confidence = 0.9 if primary else 0.4

        # canonical label: prefer explicit canonical_label if provided by model
        canonical = parsed.get("canonical_label") or parsed.get("canonical") or None

        # If canonical is missing or invalid, attempt a deterministic derivation
        valid_emotions = ["happy", "sad", "angry", "love", "fearful", "neutral"]
        def derive_canonical(parsed, description_text):
            # 1) check tone_tags
            tags = parsed.get('tone_tags') or parsed.get('tags') or []
            if isinstance(tags, str):
                tags = [tags]
            if isinstance(tags, list):
                for t in tags:
                    try:
                        c = to_canonical(t)
                        if c and c in valid_emotions and c != 'neutral':
                            return c
                    except Exception:
                        pass
            ems = []
            if isinstance(ems, str):
                ems = [ems]
            if isinstance(ems, list):
                for e in ems:
                    try:
                        c = to_canonical(e)
                        if c and c in valid_emotions and c != 'neutral':
                            return c
                    except Exception:
                        pass
            # 3) scan description with stronger regexes for anger/fear
            if description_text and isinstance(description_text, str):
                txt = description_text.lower()
                # anger cues
                if re.search(r"\b(화가|분노|열받|짜증|불쾌|성냄|격분)\b", txt):
                    return 'angry'
                # fear/anxiety cues
                if re.search(r"\b(무서|두렵|공포|겁|불안|막막|숨이 막히)\b", txt):
                    return 'fearful'
                # sadness cues
                if re.search(r"\b(슬프|우울|눈물|상처|외롭)\b", txt):
                    return 'sad'
            # 4) fallback neutral
            return 'neutral'

        if not (isinstance(canonical, str) and canonical in valid_emotions):
            # derive from parsed content and description
            canonical = derive_canonical(parsed, description)
            # If derivation didn't yield a strong non-neutral label, do a single deterministic retry
            if not (isinstance(canonical, str) and canonical in valid_emotions and canonical != 'neutral'):
                retry = _query_for_canonical(payload.user_text)
                if retry and retry in valid_emotions:
                    canonical = retry

        # tone_tags: prefer model-provided, otherwise derive from canonical/primary/sub
        tone_tags = parsed.get("tone_tags")
        if not tone_tags:
            tone_tags = []
            if canonical:
                tone_tags.append(canonical)
            if primary and primary not in tone_tags:
                tone_tags.append(primary)
            if sub and sub not in tone_tags:
                tone_tags.append(sub)
            if not tone_tags:
                tone_tags = None

        return EmotionResponse(
            primary_tone=primary or (canonical if canonical else "neutral"),
            sub_tone=sub,
            description=description.strip(),
            recommendations=recommendations,
            confidence=confidence,
            tone_tags=tone_tags,
            raw={"model_output": parsed},
            canonical_label=canonical,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse model output: {e}")
