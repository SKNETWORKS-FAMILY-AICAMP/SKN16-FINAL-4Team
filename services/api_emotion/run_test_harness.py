import asyncio
import json

import sys
from pathlib import Path

# Ensure repository root is in sys.path so imports like `services` and `utils` work
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.api_emotion.main as emo
import utils.shared as shared


class DummyResp:
    def __init__(self, content: str):
        self.choices = [{"message": {"content": content}}]


def fake_create(*args, **kwargs):
    # 모델이 반환할 고정된 JSON 응답 (테스트용)
    fake_json = {
        "primary_tone": "calm",
        "sub_tone": "warm",
        "description": "사용자가 차분하고 수용적인 상태로 보입니다.",
        "recommendations": ["부드러운 색상 팔레트 사용", "볼륨을 낮게 유지"]
    }
    return DummyResp(json.dumps(fake_json, ensure_ascii=False))


def run_harness():
    # Monkeypatch shared client (avoid real OpenAI calls)
    shared.client.chat.completions.create = fake_create

    payload = emo.EmotionRequest(
        user_text="I tried new colors today and felt comfortable.",
        conversation_history=[{"text": "I like soft tones."}],
    )

    try:
        result = asyncio.get_event_loop().run_until_complete(emo.generate_emotion(payload))
    except RuntimeError:
        # If no running loop, use asyncio.run
        result = asyncio.run(emo.generate_emotion(payload))

    print("=== generate_emotion 결과 ===")
    print(json.dumps(result.dict() if hasattr(result, 'dict') else result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    run_harness()
