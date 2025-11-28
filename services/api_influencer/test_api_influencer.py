from fastapi.testclient import TestClient
import services.api_influencer.main as emo
import utils.shared as shared


class DummyChoices:
    def __init__(self, content):
        self.message = {"content": content}


class DummyResp:
    def __init__(self, content):
        self.choices = [ {"message": {"content": content}} ]


def test_list_and_apply(monkeypatch):
    client = TestClient(emo.app)

    # ensure list endpoint returns a list
    r = client.get('/api/influencer/list')
    assert r.status_code == 200
    payload = r.json()
    assert isinstance(payload, list)

    # mock shared.client to avoid external API calls
    def fake_create(*args, **kwargs):
        # model returns a JSON with styled_text
        return DummyResp('{"styled_text":"안녕하세요, 저는 테스트 인플루언서 스타일입니다."}')

    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(*args, **kwargs):
                    return fake_create()

    monkeypatch.setattr(shared, 'client', FakeClient())

    # call apply endpoint
    req = {"user_text": "오늘 기분이 좋아요", "influencer_name": None}
    r = client.post('/api/influencer/apply', json=req)
    assert r.status_code == 200
    data = r.json()
    assert data.get('styled_text') is not None
