from fastapi.testclient import TestClient
import utils.shared as shared
from services.api_color.main import app
import json

client = TestClient(app)


def test_color_analyze_returns_hints(monkeypatch):
    # Provide deterministic hint
    monkeypatch.setattr(shared, "analyze_conversation_for_color_tone", lambda text: {"primary": "warm", "notes": "mocked"})

    payload = {
        "user_text": "I wore peach and felt cheerful today.",
        "conversation_history": [{"text": "I like soft tones."}]
    }

    resp = client.post("/api/color/analyze", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["detected_color_hints"]["primary"] == "warm"
    assert data["notes"] == "성공"
