import asyncio
import json
import sys
from pathlib import Path

# ensure repo root importable
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.api_emotion.main as emo
import services.api_influencer.main as infl
import utils.shared as shared
from fastapi.testclient import TestClient


class DummyResp:
    def __init__(self, content: str):
        self.choices = [{"message": {"content": content}}]


def fake_create_emotion(*args, **kwargs):
    fake_json = {
        "primary_tone": "calm",
        "sub_tone": "warm",
        "description": "사용자가 차분하고 수용적인 상태로 보입니다.",
        "recommendations": ["부드러운 색상 팔레트 사용", "볼륨을 낮게 유지"]
    }
    return DummyResp(json.dumps(fake_json, ensure_ascii=False))


def fake_create_influencer(*args, **kwargs):
    # return a JSON with styled_text
    styled = {"styled_text": "안녕하세요 귀욤이들! 사용자는 차분하고 따뜻한 분위기예요. 부드러운 색상 추천드려요. 도움 되셨나요?"}
    return DummyResp(json.dumps(styled, ensure_ascii=False))


def run_e2e():
    # 1) Monkeypatch emotion model
    shared.client.chat.completions.create = fake_create_emotion

    payload = emo.EmotionRequest(
        user_text="I tried new colors today and felt comfortable.",
        conversation_history=[{"text": "I like soft tones."}],
    )

    try:
        result = asyncio.get_event_loop().run_until_complete(emo.generate_emotion(payload))
    except RuntimeError:
        result = asyncio.run(emo.generate_emotion(payload))

    print("=== Emotion API result ===")
    print(json.dumps(result.model_dump() if hasattr(result, 'model_dump') else (result.dict() if hasattr(result, 'dict') else result), ensure_ascii=False, indent=2))

    # 2) Monkeypatch influencer model
    shared.client.chat.completions.create = fake_create_influencer

    client = TestClient(infl.app)
    post_payload = {
        "emotion_result": json.loads(json.dumps(result.model_dump() if hasattr(result, 'model_dump') else (result.dict() if hasattr(result, 'dict') else result))),
        "influencer_name": "원준"
    }

    r = client.post('/api/influencer/style_emotion', json=post_payload)
    print('\n=== Influencer API result ===')
    print(r.status_code)
    try:
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(r.text)


if __name__ == '__main__':
    run_e2e()
