from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json
import re

app = FastAPI()

import utils.shared as shared


class InfluencerRequest(BaseModel):
    user_text: str
    influencer_name: Optional[str] = None
    user_nickname: Optional[str] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None
    emotion_meta: Optional[Dict[str, Any]] = None


class InfluencerListItem(BaseModel):
    name: str
    short_description: Optional[str] = None
    example_sentences: Optional[List[str]] = None


class InfluencerApplyResponse(BaseModel):
    influencer: str
    styled_text: str
    raw: Optional[Dict[str, Any]] = None


def _extract_json_from_text(text: str):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    s = m.group(0)
    try:
        return json.loads(s)
    except Exception:
        return None


def load_influencers_from_excel(path: str):
    # Try to load with pandas/openpyxl, gracefully fallback to built-ins
    try:
        import pandas as pd
        df = pd.read_excel(path)
        items = []
        for _, row in df.iterrows():
            name = str(row.get('name') or row.get('Name') or row.get('이름') or '')
            short = row.get('short_description') or row.get('short') or row.get('설명') or ''
            examples = row.get('example_sentences') or row.get('examples') or row.get('예시') or ''
            if isinstance(examples, str):
                examples_list = [s.strip() for s in re.split(r"[\n;]\s*", examples) if s.strip()]
            elif isinstance(examples, (list, tuple)):
                examples_list = list(examples)
            else:
                examples_list = []
            if name:
                items.append({
                    'name': name,
                    'short_description': str(short) if short else None,
                    'example_sentences': examples_list,
                })
        return items
    except Exception:
        # fallback static influencers
        return [
            {'name': '원준', 'short_description': '친근하면서도 솔직한 리뷰', 'example_sentences': ['안녕하세요 귀욤이님! 원준입니다!', '정말 이건 추천해요.']},
            {'name': '세현', 'short_description': '자연스러운 데일리 메이크업 전문', 'example_sentences': ['안녕하세요 포드래곤님! 세현이예요!', '살짝만 발라도 예뻐요.']},
            {'name': '종민', 'short_description': '가성비 중심의 실용적 리뷰', 'example_sentences': ['안녕하세요 트루드래곤님! 종민입니다!', '가성비 좋고 실용적이에요.']},
            {'name': '혜경', 'short_description': '종합 뷰티 가이드', 'example_sentences': ['안녕하세요 뷰티패밀리님! 혜경입니다!', '상황에 맞게 추천드려요.']},
        ]


# load influencers once
_INFLUENCERS_PATH = os.path.join(os.getcwd(), 'popular_youtubers.xlsx')
_INFLUENCERS = load_influencers_from_excel(_INFLUENCERS_PATH) if os.path.exists(_INFLUENCERS_PATH) else load_influencers_from_excel('')


@app.get('/api/influencer/list', response_model=List[InfluencerListItem])
def list_influencers():
    return _INFLUENCERS


@app.post('/api/influencer/apply', response_model=InfluencerApplyResponse)
def apply_influencer_style(payload: InfluencerRequest):
    if not payload or not payload.user_text:
        raise HTTPException(status_code=400, detail='user_text가 필요합니다')

    # choose influencer
    influencer = None
    if payload.influencer_name:
        for it in _INFLUENCERS:
            if it['name'].strip().lower() == payload.influencer_name.strip().lower():
                influencer = it
                break
    if not influencer:
        # simple fallback: pick first
        influencer = _INFLUENCERS[0] if _INFLUENCERS else {'name': 'unknown', 'short_description': None, 'example_sentences': []}

    # build system prompt with influencer persona
    persona = influencer.get('short_description') or ''
    examples = '\n'.join(influencer.get('example_sentences') or [])

    system_prompt = f"""
당신은 다음 인플루언서의 말투로 답변하는 역할을 합니다.
인플루언서: {influencer['name']}
설명: {persona}
예시 문장:
{examples}
"""

    # Build user content including emotion metadata if provided
    emotion_block = ''
    if payload.emotion_meta:
        emotion_block = json.dumps(payload.emotion_meta, ensure_ascii=False)

    # Determine salutation: use provided user_nickname (append '님'), otherwise use influencer subscriber default
    salutation = None
    try:
        profile = YOUTUBER_PROFILES.get(influencer['name'], {})
        subs = profile.get('subscriber_name') or []
        default_sub = subs[0] if isinstance(subs, (list, tuple)) and len(subs) > 0 else '여러분'
    except Exception:
        default_sub = '여러분'

    if getattr(payload, 'user_nickname', None):
        salutation = f"{payload.user_nickname}님"
    else:
        salutation = default_sub

    user_content = f"호칭: {salutation}\n사용자 요청: {payload.user_text}\n감정 메타: {emotion_block}\n대화 맥락:\n"
    if payload.conversation_history:
        user_content += '\n'.join([m.get('text') or m.get('message') or '' for m in payload.conversation_history[-10:]])

    # Ask model to return a single JSON with styled_text
    json_instructions = (
        "\n\n중요: 설명 없이 단 하나의 유효한 JSON 객체만 반환하세요. JSON의 키: styled_text (문자열)."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content + json_instructions},
    ]

    try:
        resp = shared.client.chat.completions.create(
            model=os.getenv('DEFAULT_MODEL') or 'gpt-4o-mini',
            messages=messages,
            temperature=0.6,
            max_tokens=400,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f'Upstream model error: {e}')

    # extract content
    content = None
    if resp and getattr(resp, 'choices', None):
        ch = resp.choices[0]
        if isinstance(ch, dict):
            content = ch.get('message', {}).get('content') or ch.get('text')
        else:
            content = getattr(ch.message, 'content', None) or getattr(ch, 'text', None)

    if not content:
        raise HTTPException(status_code=500, detail='Empty model response')

    parsed = _extract_json_from_text(content)
    if not parsed:
        # try whole content
        try:
            parsed = json.loads(content)
        except Exception:
            # fallback: treat entire text as styled_text
            return InfluencerApplyResponse(influencer=influencer['name'], styled_text=content.strip(), raw={'model_output': content})

    styled = parsed.get('styled_text') or parsed.get('text') or parsed.get('response') or ''
    return InfluencerApplyResponse(influencer=influencer['name'], styled_text=styled, raw={'model_output': parsed})


# --- 추가: 강화된 유튜버 프로필 및 시스템 프롬프트 (원준, 세현, 종민, 혜경) ---
YOUTUBER_PROFILES = {
    '원준': {
        'greeting': '안녕하세요 귀욤이님! 원준입니다!',
        'emoji': '🌟',
        'color': '#FFE4E6',
        'icon': '👑',
        'subscriber_name': ['뷰티러버', '귀욤이'],
        'signature_expressions': ['정말', '솔직히', '완전', '개인적으로', '진짜'],
        'closing': '도움이 되셨나요? 더 궁금한 게 있으시면 언제든 물어보세요!',
        'characteristics': '친근하면서도 솔직한 평가, 초보자도 이해하기 쉬운 전문 리뷰',
        'speaking_style': '친근하지만 전문적인 톤, 믿을 수 있는 언니 느낌',
        'expertise': ['초보자 친화적', '솔직한 제품 리뷰'],
        'strengths': ['friendliness', 'honesty', 'beginner_friendly']
    },
    '세현': {
        'greeting': '안녕하세요 포드래곤님! 세현이예요!',
        'emoji': '🌿',
        'color': '#E8F5E8',
        'icon': '🍃',
        'subscriber_name': ['포드래곤'],
        'signature_expressions': ['살짝', '자연스럽게', '완전', '너무', '좀'],
        'closing': '자연스러운 아름다움으로 더 빛나세요! 구독 좋아요!',
        'characteristics': '자연스럽고 친근한 설명, 피부와 데일리 메이크업 전문',
        'speaking_style': '차분하면서 친근한 톤, 자연스러운 언니 느낌',
        'expertise': ['자연스러운 메이크업', '초보자 가이드'],
        'strengths': ['naturalness', 'friendliness', 'skin_focus']
    },
    '종민': {
        'greeting': '안녕하세요 트루드래곤님! 종민입니다!',
        'emoji': '💰',
        'color': '#FFF2CC',
        'icon': '💎',
        'subscriber_name': ['트루드래곤', '가성비러버'],
        'signature_expressions': ['솔직히', '개인적으로', '살짝', '가성비', '추천'],
        'closing': '가성비 최고 제품들로 예뻐지세요! 트루드래곤님 감사해요!',
        'characteristics': '솔직한 제품 분석과 자연스러운 사용법, 가성비 중심 리뷰',
        'speaking_style': '솔직하면서 편안한 톤, 실용적인 조언',
        'expertise': ['가성비 제품 분석', '자연스러운 활용법'],
        'strengths': ['product_analysis', 'cost_effectiveness', 'naturalness']
    },
    '혜경': {
        'greeting': '안녕하세요 뷰티패밀리님! 혜경입니다!',
        'emoji': '🎨',
        'color': '#F0E6FF',
        'icon': '🎪',
        'subscriber_name': ['뷰티패밀리'],
        'signature_expressions': ['정말', '솔직히', '자연스럽게', '완전', '개인적으로'],
        'closing': '뷰티패밀리 모두 예뻐지세요! 구독 좋아요 감사합니다!',
        'characteristics': '친근하고 솔직하며 자연스러운 종합 뷰티 가이드',
        'speaking_style': '모든 매력을 조화롭게 섞은 완벽한 톤',
        'expertise': ['초보자 가이드', '제품 리뷰', '자연스러운 메이크업'],
        'strengths': ['friendliness', 'honesty', 'naturalness', 'comprehensive']
    }
}


@app.get('/api/influencer/profiles')
def influencer_profiles():
    """Return enriched influencer profile objects for frontend consumption."""
    out = []
    for name, meta in YOUTUBER_PROFILES.items():
        # shallow copy to avoid accidental mutation
        obj = {'name': name, **(meta or {})}
        out.append(obj)
    return out

SYSTEM_PROMPTS = {
    '원준': """당신은 가상 인플루언서 '원준'의 메이크업 전문 어시스턴트입니다.
중요: 오직 메이크업, 뷰티, 스킨케어 관련 질문에만 답변하세요. 다른 주제는 절대 답변하지 마세요.
반드시 지켜야 할 규칙:
1. 인사말: 반드시 "안녕하세요 귀욤이님! 원준입니다!"로 시작하세요
2. 친근함(정말, 완전)과 솔직함(솔직히, 개인적으로)을 조화롭게 사용하세요
3. 초보자도 이해하기 쉬운 단계별 설명을 제공하세요
4. 마무리는 "도움이 되셨나요? 더 궁금한 게 있으시면 언제든 물어보세요!"로 끝내세요
""",
    '세현': """당신은 가상 인플루언서 '세현'의 메이크업 전문 어시스턴트입니다.
중요: 오직 메이크업, 뷰티, 스킨케어 관련 질문에만 답변하세요.
반드시 지켜야 할 규칙:
1. 인사말: 반드시 "안녕하세요 포드래곤님! 세현이예요!"로 시작하세요
2. 자연스럽고 차분한 톤 유지(살짝, 자연스럽게)
3. 데일리 메이크업과 피부 케어 중심으로 설명하세요
4. 마무리는 "자연스러운 아름다움으로 더 빛나세요!"로 끝내세요
""",
    '종민': """당신은 가상 인플루언서 '종민'의 메이크업 전문 어시스턴트입니다.
중요: 오직 메이크업, 뷰티, 스킨케어 관련 질문에만 답변하세요.
반드시 지켜야 할 규칙:
1. 인사말: 반드시 "안녕하세요 트루드래곤님! 종민입니다!"로 시작하세요
2. 솔직하고 실용적인 가성비 중심의 설명 제공
3. 제품의 장단점과 가격대별 추천 포함
4. 마무리는 "가성비 최고 제품들로 예뻐지세요! 트루드래곤님 감사해요!"로 끝내세요
""",
    '혜경': """당신은 가상 인플루언서 '혜경'의 메이크업 전문 어시스턴트입니다.
중요: 오직 메이크업, 뷰티, 스킨케어 관련 질문에만 답변하세요.
반드시 지켜야 할 규칙:
1. 인사말: 반드시 "안녕하세요 뷰티패밀리님! 혜경입니다!"로 시작하세요
2. 친근함과 솔직함, 자연스러움을 균형있게 사용하세요
3. 초보자 가이드 + 제품 리뷰 + 자연스러운 메이크업을 포함하세요
4. 마무리는 "뷰티패밀리 모두 예뻐지세요! 감사합니다!"로 끝내세요
""",
}


# Endpoint: api_emotion의 출력(JSON)을 받아 해당 인플루언서 말투로 재작성
class EmotionChainRequest(BaseModel):
    emotion_result: Dict[str, Any]
    # allow passing color_result so influencer can weave color recommendations
    color_result: Optional[Dict[str, Any]] = None
    influencer_name: Optional[str] = None
    user_nickname: Optional[str] = None


class EmotionChainResponse(BaseModel):
    influencer: str
    styled_text: str
    raw: Optional[Dict[str, Any]] = None


@app.post('/api/influencer/style_emotion', response_model=EmotionChainResponse)
def style_emotion_chain(payload: EmotionChainRequest):
    # pick influencer (default: first allowed)
    allowed = ['원준', '세현', '종민', '혜경']
    influencer = payload.influencer_name if payload.influencer_name in allowed else None
    if not influencer:
        influencer = allowed[0]

    system_prompt = SYSTEM_PROMPTS.get(influencer, '')

    # Build user content: include the emotion JSON, optional color JSON, and a request to rewrite in influencer tone
    emotion_json = json.dumps(payload.emotion_result, ensure_ascii=False)
    color_json = json.dumps(payload.color_result, ensure_ascii=False) if payload.color_result else ''

    user_content = f"다음은 감정 분석 결과입니다:\n{emotion_json}\n"
    if color_json:
        user_content += f"\n참고 퍼스널컬러 결과:\n{color_json}\n"
    # Determine salutation for emotion chain: prefer provided nickname, otherwise influencer subscriber default
    salutation = None
    try:
        subs = YOUTUBER_PROFILES.get(influencer, {}).get('subscriber_name') or []
        default_sub = subs[0] if isinstance(subs, (list, tuple)) and len(subs) > 0 else '여러분'
    except Exception:
        default_sub = '여러분'

    if getattr(payload, 'user_nickname', None):
        salutation = f"{payload.user_nickname}님"
    else:
        salutation = default_sub

    user_content += f"\n(호칭: {salutation})\n위 내용을 {influencer}의 말투로 자연스럽게 요약·재작성해주세요. 출력은 설명 없이 단 하나의 JSON 객체로, 키는 'styled_text'로 하세요."

    try:
        resp = shared.client.chat.completions.create(
            model=os.getenv('DEFAULT_MODEL') or 'gpt-4o-mini',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.6,
            max_tokens=400,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f'Upstream model error: {e}')

    content = None
    if resp and getattr(resp, 'choices', None):
        ch = resp.choices[0]
        if isinstance(ch, dict):
            content = ch.get('message', {}).get('content') or ch.get('text')
        else:
            content = getattr(ch.message, 'content', None) or getattr(ch, 'text', None)

    if not content:
        raise HTTPException(status_code=500, detail='Empty model response')

    parsed = _extract_json_from_text(content)
    if not parsed:
        try:
            parsed = json.loads(content)
        except Exception:
            return EmotionChainResponse(influencer=influencer, styled_text=content.strip(), raw={'model_output': content})

    styled = parsed.get('styled_text') or parsed.get('text') or parsed.get('response') or ''
    return EmotionChainResponse(influencer=influencer, styled_text=styled, raw={'model_output': parsed})
