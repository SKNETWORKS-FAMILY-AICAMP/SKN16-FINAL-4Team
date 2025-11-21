import asyncio
import json
import sys
from pathlib import Path

# ensure repo root importable
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.orchestrator.main as orch
import utils.shared as shared

# Dummy response wrapper similar to earlier harnesses
class DummyResp:
    def __init__(self, content: str):
        self.choices = [{"message": {"content": content}}]


def fake_create(*args, **kwargs):
    """
    Single fake create function that inspects messages to determine which stage
    (emotion / influencer / color) is being requested and returns an appropriate JSON.
    """
    # Inspect messages from kwargs or positional
    messages = None
    if 'messages' in kwargs:
        messages = kwargs['messages']
    elif len(args) >= 1:
        # sometimes model id is first arg; messages in kwargs usually
        pass

    sys_msg = ''
    user_msg = ''
    if messages and isinstance(messages, list):
        for m in messages:
            role = m.get('role')
            content = m.get('content') or ''
            if role == 'system':
                sys_msg += content + '\n'
            else:
                user_msg += content + '\n'

    # Decide stage
    # Prefer influencer detection when system prompt mentions 인플루언서 (because emotion JSON may be included in the user content)
    # If user content includes an explicit salutation, prefer that
    if '호칭:' in user_msg or '(호칭:' in user_msg:
        import re
        # try to extract the salutation token after '호칭:' or '(호칭:'
        m = re.search(r"호칭[:\s]*([^)\n]+)", user_msg)
        name = None
        if m:
            name = m.group(1).strip()
        if not name:
            m2 = re.search(r"\(호칭[:\s]*([^)]+)\)", user_msg)
            if m2:
                name = m2.group(1).strip()
        if name:
            styled = {"styled_text": f"안녕하세요 {name}! 최근 얼굴이 칙칙하다고 느끼신다구요? 원준 스타일로는 이렇게 추천드릴게요: 부드러운 코랄 톤의 블러셔와 따뜻한 베이지 계열 파운데이션을 사용해 보세요. 도움 되셨나요?"}
            return DummyResp(json.dumps(styled, ensure_ascii=False))
        # fallback to generic influencer greeting if extraction fails
        styled = {"styled_text": "안녕하세요 귀욤이님! 최근 얼굴이 칙칙하다고 느끼신다구요? 원준 스타일로는 이렇게 추천드릴게요: 부드러운 코랄 톤의 블러셔와 따뜻한 베이지 계열 파운데이션을 사용해 보세요. 도움 되셨나요?"}
        return DummyResp(json.dumps(styled, ensure_ascii=False))

    # Emotion model: contains the phrase '중요: 설명 없이 단 하나의 유효한 JSON 객체만 반환하세요' and asks for primary_tone
    if '감정' in user_msg or 'primary_tone' in sys_msg or '중요: 설명 없이 단 하나의 유효한 JSON 객체만 반환하세요' in sys_msg + user_msg:
        fake_json = {
            "primary_tone": "calm",
            "sub_tone": "warm",
            "description": "사용자가 차분하고 수용적인 상태입니다. 얼굴이 칙칙하다고 느끼는 감정이 섞여 있음.",
            "recommendations": ["부드러운 색상 팔레트 사용", "피부 톤 보정을 위한 하이라이터 사용"],
            "confidence": 0.88,
            "tone_tags": ["calm", "concerned"],
            "emojis": ["neutral"]
        }
        return DummyResp(json.dumps(fake_json, ensure_ascii=False))

    # Influencer model: system prompt likely includes '인플루언서' or '위 내용을' rewrite
    if '인플루언서' in sys_msg or '위 내용을' in user_msg or '말투' in user_msg:
        styled = {"styled_text": "안녕하세요 귀욤이님! 최근 얼굴이 칙칙하다고 느끼신다구요? 원준 스타일로는 이렇게 추천드릴게요: 부드러운 코랄 톤의 블러셔와 따뜻한 베이지 계열 파운데이션을 사용해 보세요. 도움 되셨나요?"}
        return DummyResp(json.dumps(styled, ensure_ascii=False))

    # Color model: system prompt contains '퍼스널컬러/뷰티 트렌드 전문가' or mentions 'recommended_palette'
    if '퍼스널컬러' in sys_msg or 'recommended_palette' in sys_msg or '뷰티 트렌드' in sys_msg:
        color_json = {
            "primary_tone": "웜",
            "sub_tone": "봄",
            "recommended_palette": ["코랄", "피치", "아이보리"],
            "suggested_styles": ["코랄 블러셔", "소프트 글로우 파운데이션", "웜 브라운 섀도우"],
            "reason": "대화에서 따뜻하고 화사한 톤을 선호하는 키워드가 감지되었으며 트렌드 문단과 매칭됩니다.",
            "confidence": 0.78
        }
        return DummyResp(json.dumps(color_json, ensure_ascii=False))

    # Default fallback
    return DummyResp(json.dumps({"message": "unhandled"}, ensure_ascii=False))


def run_chain_test():
    # Monkeypatch shared client
    shared.client.chat.completions.create = fake_create

    payload = orch.OrchestratorRequest(
        user_text="최근 얼굴이 칙칙해 보여서 고민이에요.",
        conversation_history=[{"text": "얼굴이 칙칙해 보여서 화장해도 예쁘게 안 보이는 느낌이에요."}],
        user_nickname="수빈",
        use_color=True,
        use_emotion=True,
    )

    try:
        result = asyncio.get_event_loop().run_until_complete(orch.analyze(payload))
    except RuntimeError:
        result = asyncio.run(orch.analyze(payload))

    # Print nicely
    print('=== Orchestrator chain result ===')
    # result is a Pydantic model OrchestratorResponse, convert to dict
    out = result.model_dump() if hasattr(result, 'model_dump') else (result.dict() if hasattr(result, 'dict') else result)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    run_chain_test()
