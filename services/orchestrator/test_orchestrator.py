from fastapi.testclient import TestClient
import asyncio

from services.orchestrator.main import app
import services.api_emotion.main as api_emotion

client = TestClient(app)


async def _fake_generate_emotion(payload):
    # emulate the async route returning a Pydantic-like object
    class R:
        def dict(self):
            return {
                "primary_tone": "calm",
                "sub_tone": "warm",
                "description": "mocked",
                "recommendations": ["relax"]
            }
    return R()


def test_orchestrator_combines(monkeypatch):
    # Patch emotion and color analyze calls
    monkeypatch.setattr(api_emotion, "generate_emotion", lambda payload: asyncio.get_event_loop().run_until_complete(_fake_generate_emotion(payload)))

    payload = {
        "user_text": "I felt good wearing peach today.",
        "conversation_history": [{"text": "I like soft tones."}],
        "use_color": True,
        "use_emotion": True
    }

    resp = client.post("/api/orchestrator/analyze", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["emotion"]["primary_tone"] == "calm"
