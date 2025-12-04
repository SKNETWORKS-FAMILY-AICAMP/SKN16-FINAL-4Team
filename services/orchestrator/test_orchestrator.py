from fastapi.testclient import TestClient
import asyncio

from services.orchestrator.main import app
import services.api_emotion.main as api_emotion

client = TestClient(app)


class FakeEmotionResponse:
    """감정 분석 응답 mock"""
    def __init__(self):
        self.primary_tone = "calm"
        self.sub_tone = "warm"
        self.description = "mocked"
        self.recommendations = ["relax"]
    
    def model_dump(self):
        return {
            "primary_tone": self.primary_tone,
            "sub_tone": self.sub_tone,
            "description": self.description,
            "recommendations": self.recommendations
        }
    
    def dict(self):
        return self.model_dump()


def test_orchestrator_combines(monkeypatch):
    """orchestrator가 여러 서비스 결과를 통합하는지 확인"""
    # 감정 분석 mock
    def fake_emotion(payload):
        return FakeEmotionResponse()
    
    monkeypatch.setattr(api_emotion, "generate_emotion", fake_emotion)

    payload = {
        "user_text": "I felt good wearing peach today.",
        "conversation_history": [{"text": "I like soft tones."}],
        "use_color": False,  # 색상은 mock 없으니 비활성화
        "use_emotion": True
    }

    resp = client.post("/api/orchestrator/analyze", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["emotion"]["primary_tone"] == "calm"
