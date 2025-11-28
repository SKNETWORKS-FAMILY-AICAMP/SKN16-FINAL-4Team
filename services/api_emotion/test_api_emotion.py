from fastapi.testclient import TestClient
import json
import types

import utils.shared as shared
from services.api_emotion.main import app


client = TestClient(app)


class DummyResp:
    def __init__(self, content: str):
        # emulate dict-like response with choices -> message -> content
        self.choices = [{"message": {"content": content}}]


def test_generate_emotion_returns_strict_json(monkeypatch):
    # Prepare a fake structured JSON the model would return
    fake_json = {
        "primary_tone": "calm",
        "sub_tone": "warm",
        "description": "The user appears calm and receptive.",
        "recommendations": ["Use soft colors", "Avoid harsh contrasts"]
    }
    content = json.dumps(fake_json, ensure_ascii=False)

    def fake_create(*args, **kwargs):
        return DummyResp(content)

    # Patch the project's shared client to avoid real OpenAI calls
    monkeypatch.setattr(shared.client.chat.completions, "create", fake_create)

    payload = {
        "user_text": "I tried new colors today and felt comfortable.",
        "conversation_history": [{"text": "I like soft tones."}]
    }

    resp = client.post("/api/emotion/generate", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["primary_tone"] == "calm"
    assert data["sub_tone"] == "warm"
    assert "description" in data and isinstance(data["description"], str)
    assert isinstance(data["recommendations"], list)
