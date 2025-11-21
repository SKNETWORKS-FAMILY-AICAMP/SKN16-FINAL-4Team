import asyncio
import json
from datetime import datetime
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.chatbot_router as chat_router


class FakeDB:
    def __init__(self):
        self._storage = {}
        self._id_counter = 1

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = self._id_counter
            self._id_counter += 1
        if not hasattr(obj, "created_at"):
            obj.created_at = datetime.utcnow()
        key = obj.__class__.__name__
        self._storage.setdefault(key, []).append(obj)

    def commit(self):
        return None

    def refresh(self, obj):
        return None

    def rollback(self):
        return None

    def query(self, model):
        return FakeQuery(self, model)


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self._filters = {}

    def filter_by(self, **kwargs):
        self._filters.update(kwargs)
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        key = self.model.__name__
        records = list(self.db._storage.get(key, []))
        if not self._filters:
            return records
        out = []
        for r in records:
            ok = True
            for k, v in self._filters.items():
                if getattr(r, k, None) != v:
                    ok = False
                    break
            if ok:
                out.append(r)
        return out


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(chat_router.router)

    # Override dependencies
    fake_user = types.SimpleNamespace(id=1, nickname="테스터")
    app.dependency_overrides[chat_router.get_current_user] = lambda: fake_user

    fake_db = FakeDB()
    app.dependency_overrides[chat_router.get_db] = lambda: fake_db

    return app


@pytest.mark.asyncio
async def test_chatbot_analyze_monkeypatched_orchestrator(app, monkeypatch):
    client = TestClient(app)

    # Prepare a deterministic orchestrator response
    emo = {
        "primary_tone": "웜",
        "sub_tone": "봄",
        "description": "당신은 따뜻하고 화사한 봄웜톤이에요.",
        "recommendations": ["코랄 블러셔 사용", "따뜻한 베이지 계열 추천"],
        "influencer_styled": {"influencer": "원준", "styled_text": "원준 스타일로는 코랄 블러셔가 좋아요.", "recommendations": ["원준 추천1"]}
    }
    color = {
        "detected_color_hints": {"primary_tone": "웜", "sub_tone": "봄"},
        "recommendations": ["파스텔 계열 활용 추천"]
    }

    async def fake_analyze(payload):
        return types.SimpleNamespace(emotion=emo, color=color)

    # Patch the orchestrator used by the router module
    # Provide a lightweight OrchestratorRequest factory so router can construct payload
    def fake_orch_request(**kwargs):
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(chat_router, "orchestrator_service", types.SimpleNamespace(analyze=fake_analyze, OrchestratorRequest=fake_orch_request))

    payload = {"question": "최근 얼굴이 칙칙해 보여서 고민이에요.", "history_id": None}
    resp = client.post("/api/chatbot/analyze", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "history_id" in body
    assert "items" in body
    assert isinstance(body["items"], list)
    # There should be one QA pair saved
    assert len(body["items"]) >= 1
    first = body["items"][0]
    # chat_res should contain description from influencer styled text
    chat_res = first.get("chat_res")
    assert chat_res is not None
    assert chat_res.get("description") in (emo["influencer_styled"]["styled_text"], emo["description"]) 
    # recommendations should include merged items
    recs = chat_res.get("recommendations") or []
    assert any("코랄" in r or "파스텔" in r or "원준" in r for r in recs)
