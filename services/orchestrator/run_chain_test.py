import types, json, asyncio
import utils.shared as shared

# Create a fake client to avoid external API calls and to provide deterministic responses
class FakeClient:
    def __init__(self):
        import types
        self.chat = types.SimpleNamespace(completions=self)
        self.embeddings = types.SimpleNamespace(create=self._embeddings_create)

    def create(self, model, messages, temperature=0.2, max_tokens=500):
        # Determine intent by checking system or user content
        combined = "\n".join([m.get('content','') for m in messages])
        # Emotion detection flow
        if '감정' in combined or '감정 분석' in combined or 'primary_tone' in combined:
            content = json.dumps({
                "primary_tone":"calm",
                "sub_tone":"warm",
                "description":"사용자가 차분하고 따뜻한 분위기입니다.",
                "recommendations":["부드러운 색상 사용"],
                "confidence":0.95,
                "tone_tags":["calm","warm"],
                "emojis":["neutral"]
            }, ensure_ascii=False)
            return types.SimpleNamespace(choices=[{'message':{'content':content}}])
        # Influencer styling flow
        if '인플루언서' in combined or 'styled_text' in combined or '재작성' in combined:
            content = json.dumps({"styled_text":"안녕하세요 귀욤이님! 사용자는 차분하고 따뜻한 분위기예요. 부드러운 색상 추천드려요."}, ensure_ascii=False)
            return types.SimpleNamespace(choices=[{'message':{'content':content}}])
        # Color model flow
        content = json.dumps({
            "primary_tone":"웜",
            "sub_tone":"봄",
            "recommended_palette":["코랄","피치","아이보리"],
            "suggested_styles":["자연스러운 메이크업","따뜻한 톤 섀도우"],
            "reason":"대화 및 트렌드 참고",
            "confidence":0.88
        }, ensure_ascii=False)
        return types.SimpleNamespace(choices=[{'message':{'content':content}}])

    def _embeddings_create(self, model, input):
        # return dummy embeddings matching input length
        return types.SimpleNamespace(data=[types.SimpleNamespace(embedding=[0.01]*8) for _ in input])


# Patch shared.client
shared.client = FakeClient()

# Now call the orchestrator analyze function programmatically
from services.orchestrator import main as orch
from services.orchestrator.main import OrchestratorRequest

payload = OrchestratorRequest(user_text="최근 얼굴이 칙칙해 보여서 고민이에요.", use_color=True, use_emotion=True)
res = asyncio.run(orch.analyze(payload))
print(json.dumps(res.dict(), ensure_ascii=False, indent=2))
