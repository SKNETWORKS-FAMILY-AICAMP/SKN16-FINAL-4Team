
from fastapi import APIRouter, HTTPException, Depends, Body, Query
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
import models
from routers.user_router import get_current_user
from database import SessionLocal
import os
import json

from schemas import (
    ChatbotRequest,
    ChatbotHistoryResponse,
    ChatItemModel,
    ChatResModel,
    ReportCreate,
    ReportResponse,
)
from routers.feedback_router import generate_ai_feedbacks
from utils.shared import build_rag_index, analyze_conversation_for_color_tone, normalize_personal_color
from utils.emotion_lottie import lottie_filename, to_canonical
import random
import asyncio

# Optional: load influencer personas from the influencer service if available
try:
    import services.api_influencer.main as influencer_service
except Exception:
    influencer_service = None
try:
    import services.api_color.main as api_color_service
except Exception:
    api_color_service = None
try:
    import services.orchestrator.main as orchestrator_service
except Exception:
    orchestrator_service = None
try:
    import services.api_emotion.main as api_emotion_service
except Exception:
    api_emotion_service = None

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("환경변수 OPENAI_API_KEY가 설정되지 않았습니다.")

# 모델 설정
EMOTION_MODEL_ID = os.getenv("EMOTION_MODEL_ID")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4.1-nano-2025-04-14")

client = OpenAI(api_key=OPENAI_API_KEY)
router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])


# 모델 선택 함수 (중복 제거)
def get_model_to_use():
    return EMOTION_MODEL_ID if EMOTION_MODEL_ID else DEFAULT_MODEL

# 모델 상태 출력
print(f"🚀 Chatbot Router 초기화")
print(f"   - 기본 모델: {DEFAULT_MODEL}")
if EMOTION_MODEL_ID:
    print(f"   - Fine-tuned 감정 모델: {EMOTION_MODEL_ID[:30]}***")
    print(f"   ✅ Fine-tuned 모델 사용 가능")
else:
    print(f"   ⚠️ Fine-tuned 모델 미설정, 기본 모델 사용")

def generate_complete_diagnosis_data(conversation_text: str, season: str) -> dict:
    """
    OpenAI API를 통해 완전한 진단 데이터 생성
    """
    try:
        # 대화 텍스트가 너무 길면 요약
        if len(conversation_text) > 1000:
            conversation_text = conversation_text[:1000] + "...(생략)"
        prompt = f"""
    사용자와 퍼스널 컬러 전문가의 대화:
    {conversation_text}

    위 대화를 바탕으로 {season} 타입 퍼스널 컬러 진단 결과를 생성해주세요.

    다음 유효한 JSON 객체 하나만, 다른 설명 없이 반환해주세요. JSON은 반드시 아래 키들을 포함해야 합니다:
    {{
        "result_name": "{season} {{primary_or_sub}} 형식의 한글 문자열 예: '가을 웜톤'",
        "primary_tone": "'웜' 또는 '쿨' (짧은 문자열)",
        "sub_tone": "'봄','여름','가을' 또는 '겨울' (짧은 문자열)",
        "emotional_description": "감성적이고 긍정적인 한 문장",
        "color_palette": ["{season} 타입에 어울리는 5개의 HEX 색상 코드"],
        "style_keywords": ["{season} 타입의 특성을 나타내는 5개 키워드"],
        "makeup_tips": ["실용적인 메이크업 팁 4개"],
        "detailed_analysis": "대화 내용을 반영한 개인화된 분석 (2-3문단, 구체적이고 실용적인 조언 포함)",
        "top_types": [
            {{"name": "{{계절}} {{웜/쿨}}톤", "type": "spring|summer|autumn|winter", "description": "간단 설명", "score": 0}}
        ]
    }}

    중요 요구사항:
    - `result_name`과 `top_types` 배열의 각 항목 `name`은 반드시 한국어로 "{{계절}} {{웜/쿨}}톤" 형식(예: "가을 웜톤", "겨울 쿨톤")이어야 합니다.
    - `top_types[0].name`은 `result_name`과 동일한 값이어야 합니다.
    - `primary_tone`은 반드시 '웜' 또는 '쿨'로 표기하고, `sub_tone`은 '봄/여름/가을/겨울' 중 하나로 표기하세요.
    - 숫자 값(score)은 0~100 사이의 정수로 표기하세요.
    - 출력은 오직 하나의 JSON 객체여야 하며, 추가 설명 텍스트는 포함하지 마세요.

    주의사항:
    - detailed_analysis는 반복적인 내용 없이 개인화된 분석으로 작성
    - 대화에서 언급된 개인적 특성을 반영
    - 실용적이고 구체적인 조언 포함
    - 한국어로 작성
    """
        # 모델 선택 함수 사용
        response = client.chat.completions.create(
            model=get_model_to_use(),
            messages=[{
                "role": "system",
                "content": "당신은 퍼스널 컬러 전문가입니다. 사용자의 대화를 분석하여 정확하고 개인화된 진단 결과를 제공합니다."
            }, {
                "role": "user", 
                "content": prompt
            }],
            max_tokens=1000,
            temperature=0.3
        )
        ai_response = response.choices[0].message.content.strip()
        try:
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                if not result.get("detailed_analysis") or len(result.get("detailed_analysis", "")) < 50:
                    print("⚠️ AI 분석 결과가 너무 짧음, 기본값 사용")
                    return get_default_diagnosis_data(season)
                return result
        except Exception as parse_error:
            print(f"❌ AI 응답 JSON 파싱 실패: {parse_error}")
            print(f"AI 응답: {ai_response[:200]}...")
        return get_default_diagnosis_data(season)
    except Exception as e:
        print(f"❌ OpenAI API 호출 실패: {e}")
        return get_default_diagnosis_data(season)

def get_default_diagnosis_data(season: str) -> dict:
    """
    API 실패 시 사용할 기본 진단 데이터
    """
    default_data = {
        "봄": {
            "emotional_description": "생기 넘치고 화사한 당신은 봄 웜톤 타입입니다! 밝고 따뜻한 색상이 자연스럽게 어울리는 매력적인 분이에요.",
            "color_palette": ["#FFB6C1", "#FFA07A", "#FFFF99", "#98FB98", "#87CEEB"],
            "style_keywords": ["밝은", "화사한", "생동감 있는", "따뜻한", "자연스러운"],
            "makeup_tips": ["코랄 계열 립스틱으로 생기 연출", "피치 블러셔로 자연스러운 홍조", "골드 아이섀도로 따뜻한 눈매", "브라운 마스카라로 부드러운 눈매"],
            "detailed_analysis": "봄 웜톤 타입인 당신은 따뜻하고 밝은 색상이 가장 잘 어울리는 타입입니다.\n\n평소 밝고 경쾌한 인상을 주는 당신에게는 코랄, 피치, 아이보리 계열의 색상이 피부톤을 더욱 생동감 있게 만들어 줍니다. 메이크업 시에는 너무 진하거나 쿨톤 계열보다는 자연스럽고 따뜻한 느낌의 색상을 선택하시면 더욱 매력적인 모습을 연출할 수 있어요.\n\n패션에서도 화이트, 크림, 코랄, 연두색 등을 활용하시면 활기찬 당신의 매력을 한층 더 돋보이게 할 수 있습니다."
        },
        "여름": {
            "emotional_description": "시원하고 우아한 당신은 여름 쿨톤 타입입니다! 부드럽고 세련된 색상이 당신의 우아함을 더욱 빛나게 해줍니다.",
            "color_palette": ["#E6E6FA", "#B0C4DE", "#FFC0CB", "#DDA0DD", "#F0F8FF"],
            "style_keywords": ["부드러운", "우아한", "세련된", "시원한", "파스텔"],
            "makeup_tips": ["로즈 핑크 립으로 상쾌한 인상", "라벤더 아이섀도로 몽환적 눈매", "실버 하이라이터로 투명한 윤기", "애쉬 브라운 아이브로우로 부드러운 인상"],
            "detailed_analysis": "여름 쿨톤 타입인 당신은 차가운 계열의 부드러운 색상이 가장 잘 어울리는 우아한 타입입니다.\n\n당신의 피부톤에는 로즈, 라벤더, 민트, 스카이블루 등의 파스텔 계열 색상이 완벽하게 조화를 이룹니다. 메이크업 시에는 너무 강렬하거나 따뜻한 톤보다는 쿨하고 부드러운 색상을 선택하시면 자연스럽게 세련된 분위기를 연출할 수 있어요.\n\n의상 선택 시에도 화이트, 실버, 네이비, 그레이 계열을 기본으로 하여 포인트 색상으로 파스텔 톤을 활용하시면 우아하면서도 현대적인 매력을 표현할 수 있습니다."
        },
        "가을": {
            "emotional_description": "깊이 있고 세련된 당신은 가을 웜톤 타입입니다! 진하고 따뜻한 색상이 당신의 성숙한 매력을 완벽하게 표현해줍니다.",
            "color_palette": ["#D2691E", "#CD853F", "#DEB887", "#BC8F8F", "#F4A460"],
            "style_keywords": ["깊은", "세련된", "따뜻한", "성숙한", "클래식"],
            "makeup_tips": ["브라운 계열 립으로 지적인 인상", "골드 브론즈 아이섀도로 깊은 눈매", "따뜻한 오렌지 블러셔", "다크 브라운 마스카라로 강조된 속눈썹"],
            "detailed_analysis": "가을 웜톤 타입인 당신은 깊이 있고 풍부한 색상이 가장 잘 어울리는 성숙하고 세련된 타입입니다.\n\n당신의 피부톤에는 머스타드, 브릭, 올리브, 버건디 등의 깊고 따뜻한 색상들이 자연스럽게 조화를 이룹니다. 메이크업에서는 베이지, 브라운, 골드 계열을 활용하여 자연스러우면서도 세련된 분위기를 연출할 수 있어요.\n\n패션에서는 카멜, 베이지, 브라운, 와인 컬러 등을 기본으로 하여 포인트 색상으로 머스타드나 올리브 그린을 활용하시면 클래식하면서도 트렌디한 스타일을 완성할 수 있습니다."
        },
        "겨울": {
            "emotional_description": "명확하고 강렬한 당신은 겨울 쿨톤 타입입니다! 선명하고 드라마틱한 색상이 당신의 카리스마를 한층 더 돋보이게 합니다.",
            "color_palette": ["#FF1493", "#4169E1", "#000000", "#FFFFFF", "#8A2BE2"],
            "style_keywords": ["명확한", "강렬한", "선명한", "드라마틱", "모던"],
            "makeup_tips": ["레드 립스틱으로 강렬한 포인트", "실버 아이섀도로 신비로운 눈매", "블랙 아이라이너로 또렷한 눈매", "볼드한 컨투어링으로 입체감"],
            "detailed_analysis": "겨울 쿨톤 타입인 당신은 선명하고 강렬한 색상이 가장 잘 어울리는 드라마틱하고 모던한 타입입니다.\n\n당신의 피부톤에는 퓨어 화이트, 블랙, 로얄 블루, 에메랄드 그린 등의 선명하고 차가운 색상들이 완벽하게 어울립니다. 메이크업에서는 명확한 컬러 대비를 활용하여 시크하고 세련된 이미지를 연출할 수 있어요.\n\n의상 선택 시에도 블랙, 화이트, 그레이를 베이스로 하여 포인트 색상으로 비비드한 컬러를 활용하시면 당신만의 독특하고 강인한 매력을 표현할 수 있습니다."
        }
    }
    
    return default_data.get(season, default_data["봄"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_welcome(db: Session, current_user: models.User, influencer_id: str | None = None):
    """
    Simple welcome endpoint used by frontend to provide a server-side welcome message
    and an optional influencer suggestion. This is intentionally lightweight so the
    frontend can fall back to local text if unavailable.
    """
    try:
        user_nick = getattr(current_user, 'nickname', None) or '사용자'
    except Exception:
        user_nick = '사용자'

    has_prev = False
    prev_summary = None
    try:
        if current_user and getattr(current_user, 'id', None):
            prev = (
                db.query(models.SurveyResult)
                .filter(models.SurveyResult.user_id == current_user.id, models.SurveyResult.is_active == True)
                .order_by(models.SurveyResult.created_at.desc())
                .first()
            )
            if prev:
                has_prev = True
                prev_summary = getattr(prev, 'result_name', None) or getattr(prev, 'result_tone', None)
    except Exception:
        # silently ignore DB failures here; frontend has a local fallback
        has_prev = False


    # Build a contextual welcome message using the LLM when possible.
    # If we have a previous diagnosis, ask the LLM to mention it; otherwise ask gentle diagnostic questions.
    try:
        infl_name = None
        infl_excerpt = None
        persona_notes = None

        # If caller provided an influencer id or slug, try to resolve it
        # to a full profile via the influencer service (or fallback list).
        if influencer_id:
            try:
                profiles = None
                if influencer_service and hasattr(influencer_service, 'influencer_profiles'):
                    res = influencer_service.influencer_profiles()
                    if isinstance(res, list):
                        outp = []
                        for it in res:
                            try:
                                if hasattr(it, 'dict'):
                                    outp.append(it.dict())
                                else:
                                    outp.append(it)
                            except Exception:
                                outp.append(it)
                        profiles = outp
                    else:
                        profiles = res
                if not profiles:
                    profiles = [
                        {'id': 'won_jun', 'name': '원준', 'short_description': '친근하면서도 솔직한 리뷰', 'example_sentences': ['안녕하세요 귀욤이님! 원준입니다!']},
                        {'id': 'se_hyun', 'name': '세현', 'short_description': '자연스러운 데일리 메이크업 전문', 'example_sentences': ['안녕하세요 포드래곤님! 세현이예요!']},
                        {'id': 'jong_min', 'name': '종민', 'short_description': '가성비 중심의 실용적 리뷰', 'example_sentences': ['안녕하세요 트루드래곤님! 종민입니다!']},
                        {'id': 'hye_kyung', 'name': '혜경', 'short_description': '종합 뷰티 가이드', 'example_sentences': ['안녕하세요 뷰티패밀리님! 혜경입니다!']},
                    ]

                # try match by id or name (case-insensitive)
                found = None
                for p in profiles:
                    try:
                        pid = str(p.get('id') or p.get('influencer_id') or '')
                        name = str(p.get('name') or p.get('short_name') or '')
                        if pid and pid == str(influencer_id):
                            found = p
                            break
                        if name and name.lower() == str(influencer_id).lower():
                            found = p
                            break
                    except Exception:
                        continue

                if found:
                    infl_name = found.get('name') or infl_name
                    infl_excerpt = found.get('short_description') or (found.get('example_sentences') and found.get('example_sentences')[0])
                    persona_notes = found.get('characteristics') or found.get('description') or None
            except Exception:
                pass

        # Build system + user prompt for the LLM
        system_prompt = "당신은 퍼스널컬러 분야의 친절한 상담자이며, 주어진 인플루언서 페르소나의 말투와 스타일을 모방하여 한국어로 자연스럽고 친근한 환영 인사를 작성합니다. 응답은 사용자에게 바로 표시할 텍스트 한 덩어리(문단)로만 출력하세요."

        user_prompt_lines = []
        if infl_name:
            user_prompt_lines.append(f"페르소나 이름: {infl_name}")
        if infl_excerpt:
            user_prompt_lines.append(f"간단 소개: {infl_excerpt}")
        if persona_notes:
            user_prompt_lines.append(f"말투 힌트: {persona_notes}")

        # Mandatory instruction: Request image upload
        user_prompt_lines.append("필수 포함 내용: 정확한 퍼스널컬러 진단을 위해 사용자의 얼굴이 잘 나온 사진(이미지)을 업로드해달라고 요청하는 문장을 반드시 포함하세요.")

        if has_prev and prev_summary:
            user_prompt_lines.append(f"이 사용자는 이전에 '{prev_summary}' 타입으로 진단된 기록이 있습니다. 환영 인사에서 '이전 진단 내역'이라는 단어를 포함하여 이를 언급하고, 이전 결과를 참고해 어떤 도움을 줄 수 있는지 알려주세요. 인플루언서의 말투로 작성하세요.")
        else:
            user_prompt_lines.append("이 사용자는 이전 진단 기록이 없습니다. 자연스럽게 퍼스널컬러 진단을 시작할 수 있도록 안내하고, 인플루언서의 말투로 작성하세요.")

        user_prompt_lines.append("응답은 2~4개의 짧은 문단(또는 문장들)으로 요약해주고, 추가 지시나 메타 정보는 출력하지 마세요. 오직 환영 텍스트만 출력하세요.")

        user_prompt = "\n".join(user_prompt_lines)

        # Call LLM
        try:
            resp = client.chat.completions.create(
                model=get_model_to_use(),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=250,
                temperature=0.7,
            )
            ai_message = resp.choices[0].message.content.strip()
            message = ai_message
        except Exception as e:
            # LLM failed — fall back to safe messages
            print(f"[welcome] LLM 호출 실패, 폴백 메시지 사용: {e}")
            if has_prev and prev_summary:
                if infl_name:
                    message = f"안녕하세요, {user_nick}! 이전 진단은 \"{prev_summary}\" 타입입니다. {infl_name}님 스타일을 참고해 이전 결과를 바탕으로 도와드릴게요. 원하시면 바로 추천을 시작할게요."
                else:
                    message = f"안녕하세요, {user_nick}! 이전 진단은 \"{prev_summary}\" 타입입니다. 이전 결과를 참고해 도움을 드릴게요. 무엇을 먼저 도와드릴까요?"
            else:
                if infl_name:
                    if infl_excerpt:
                        message = (
                            f"안녕하세요, {user_nick}! {infl_name}님 스타일로 퍼스널컬러를 도와드릴게요 — {infl_excerpt} 전문가입니다. "
                            "먼저 몇 가지 질문 드릴게요: 평소 자주 입는 옷 색상은 무엇인가요? 피부톤은 밝은 편인가요, 어두운 편인가요? 평소 선호하는 메이크업 스타일은 어떤가요?"
                        )
                    else:
                        message = (
                            f"안녕하세요, {user_nick}! {infl_name}님 스타일로 퍼스널컬러 진단을 도와드릴게요. "
                            "먼저 간단한 질문 몇 개만 드릴게요: 평소 자주 입는 색상은요? 피부톤은 밝은 편인가요, 어두운 편인가요? 메이크업이나 스타일 선호가 있으신가요?"
                        )
                else:
                    message = (
                        f"안녕하세요, {user_nick}! 😊 퍼스널컬러 전문 AI 컨설턴트입니다. "
                        "퍼스널컬러를 알아보려면 간단한 질문 몇 가지가 필요해요 — 평소 자주 입는 색상, 피부톤(밝음/어두움), 선호하는 메이크업 스타일을 알려주실래요?"
                    )
    except Exception as e:
        print(f"[welcome] 메시지 생성 중 오류: {e}")
        message = f"안녕하세요, {user_nick}! 😊 퍼스널컬러 전문 AI 컨설턴트입니다! 무엇을 도와드릴까요?"

    return {"message": message, "has_previous": has_prev, "previous_summary": prev_summary}


@router.get('/influencer/profiles')
def get_influencer_profiles(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Proxy endpoint: returns influencer profiles for the frontend.
    If the `services.api_influencer` module is available, call its `influencer_profiles()` function.
    Otherwise return a safe fallback list.
    """
    try:
        profiles = None
        if influencer_service and hasattr(influencer_service, 'influencer_profiles'):
            res = influencer_service.influencer_profiles()
            # convert pydantic models to dicts when necessary
            if isinstance(res, list):
                out = []
                for it in res:
                    try:
                        if hasattr(it, 'dict'):
                            out.append(it.dict())
                        else:
                            out.append(it)
                    except Exception:
                        out.append(it)
                profiles = out
            else:
                profiles = res
        # fallback safe list if service not available
        if not profiles:
            profiles = [
                {'name': '원준', 'short_description': '친근하면서도 솔직한 리뷰', 'example_sentences': ['안녕하세요 귀욤이님! 원준입니다!']},
                {'name': '세현', 'short_description': '자연스러운 데일리 메이크업 전문', 'example_sentences': ['안녕하세요 포드래곤님! 세현이예요!']},
                {'name': '종민', 'short_description': '가성비 중심의 실용적 리뷰', 'example_sentences': ['안녕하세요 트루드래곤님! 종민입니다!']},
                {'name': '혜경', 'short_description': '종합 뷰티 가이드', 'example_sentences': ['안녕하세요 뷰티패밀리님! 혜경입니다!']},
            ]

        # Ensure each profile has a stable unique id (slug) for client-side linking
        def make_id(name: str) -> str:
            try:
                s = name.strip().lower()
                s = s.replace(' ', '_')
                import re
                s = re.sub(r'[^a-z0-9_\-]', '', s)
                return s
            except Exception:
                return str(name)

        for p in profiles:
            try:
                if isinstance(p, dict) and not p.get('id'):
                    nm = p.get('name') or p.get('short_name') or p.get('short_description') or 'unknown'
                    p['id'] = make_id(str(nm))
            except Exception:
                p['id'] = p.get('name') or 'unknown'


        return profiles
    except Exception as e:
        print(f"[get_influencer_profiles] proxy call failed: {e}")
        return []

# RAG 인덱스 구축 (서버 시작 시 한 번만 실행)
fixed_index = build_rag_index(client, "data/RAG/personal_color_RAG.txt")
trend_index = build_rag_index(client, "data/RAG/beauty_trend_2025_autumn_RAG.txt")

def clean_analysis_text(text: str) -> str:
    """
    분석 텍스트를 정리하는 함수
    """
    if not text:
        return ""
    
    # 불필요한 공백 제거
    text = text.strip()
    
    # 연속된 줄바꿈을 하나로 정리
    import re
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    # 중복된 문장 제거 (간단한 중복 체크)
    sentences = text.split('. ')
    unique_sentences = []
    seen = set()
    
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and sentence not in seen and len(sentence) > 10:
            seen.add(sentence)
            unique_sentences.append(sentence)
    
    return '. '.join(unique_sentences) if unique_sentences else text

async def save_chatbot_analysis_result(
    user_id: int,
    chat_history_id: int,
    db: Session,
    force: bool = False,
):
    """
    🆕 새로운 퍼스널 컬러 진단 기록 생성 🆕
    
    ⚠️ 중요: 이 함수는 새로운 진단 기록(SurveyResult)을 생성합니다!
    - 챗봇 대화 분석을 통한 새로운 퍼스널 컬러 진단
    - 마이페이지 진단 기록에 새로운 항목이 추가됨
    - 대화 내용을 AI가 분석하여 새로운 진단 결과 도출
    
    호출 시점:
    1. 대화 세션 종료 시 (충분한 대화가 진행된 경우)
    """
    try:
        # 🔍 중복 방지: force=True이면 중복 체크를 무시하고 항상 새 레코드 생성
        if not force:
            existing_result = db.query(models.SurveyResult).filter(
                models.SurveyResult.user_id == user_id,
                models.SurveyResult.source_type == "chatbot",
                models.SurveyResult.is_active == True
            ).order_by(models.SurveyResult.created_at.desc()).first()

            # 최근 생성된 진단 결과가 5분 이내라면 중복으로 간주
            if existing_result:
                from datetime import timedelta
                # DB에 저장된 created_at이 tz-naive인 경우가 있어 subtraction 에러가 날 수 있음
                existing_created_at = existing_result.created_at
                if existing_created_at is None:
                    # 안전하게 넘어감
                    existing_created_at = datetime.now(timezone.utc)
                # if DB returned a naive datetime (no tzinfo), assume UTC
                if existing_created_at.tzinfo is None:
                    existing_created_at = existing_created_at.replace(tzinfo=timezone.utc)

                time_diff = datetime.now(timezone.utc) - existing_created_at
                if time_diff < timedelta(minutes=5):
                    print(f"🔄 중복 진단 방지: 최근 {time_diff.seconds}초 전에 생성된 결과 재사용")
                    print(f"   - 기존 결과 ID: {existing_result.id}")
                    print(f"   - 기존 결과 타입: {existing_result.result_tone}")
                    return existing_result
        print(f"🔍 새로운 진단 기록 생성 시작: user_id={user_id}, chat_history_id={chat_history_id}")
        
        # 대화 히스토리에서 메시지들 가져오기
        messages = db.query(models.ChatMessage).filter_by(
            history_id=chat_history_id
        ).order_by(models.ChatMessage.created_at.asc()).all()
        
        if not messages:
            print("❌ 대화 메시지가 없어서 진단 불가")
            return None
            
        print(f"📝 대화 메시지 {len(messages)}개 발견, 분석 시작...")
        
        # 대화 내용을 분석하여 퍼스널 컬러 결정
        conversation_text = ""
        for msg in messages:
            if msg.role == "user":
                conversation_text += f"User: {msg.text}\n"
            elif msg.role == "ai":
                try:
                    ai_data = json.loads(msg.text)
                    conversation_text += f"AI: {ai_data.get('description', msg.text)}\n"
                except:
                    conversation_text += f"AI: {msg.text}\n"
        
        # 먼저 color service를 호출해 퍼스널컬러 기반 톤을 얻어본다 (우선)
        primary_tone = None
        sub_tone = None
        try:
            if api_color_service:
                color_payload = api_color_service.ColorRequest(
                    user_text=conversation_text,
                    conversation_history=None,
                )
                color_resp = await api_color_service.analyze_color(color_payload)
                # color_resp may be a pydantic model
                hints = None
                if hasattr(color_resp, 'detected_color_hints'):
                    hints = color_resp.detected_color_hints
                elif isinstance(color_resp, dict):
                    hints = color_resp.get('detected_color_hints')
                if isinstance(hints, dict):
                    primary_tone = hints.get('primary_tone')
                    sub_tone = hints.get('sub_tone')
        except Exception as e:
            print(f"⚠️ color service call failed, falling back to heuristic: {e}")

        # 컬러 기반 톤이 없으면 기존 대화 기반 휴리스틱으로 보완
        if not primary_tone or not sub_tone:
            primary_tone, sub_tone = analyze_conversation_for_color_tone(
                conversation_text, ""  # 현재 질문은 빈 문자열로 처리 (전체 대화 기반 분석)
            )

        # Normalize tones into canonical values before proceeding
        try:
            primary_tone, sub_tone = normalize_personal_color(primary_tone, sub_tone)
        except Exception:
            pass

        print(f"🎨 AI 분석 결과: {primary_tone}톤 {sub_tone}")
        
        # 🆕 OpenAI를 통한 완전한 진단 데이터 생성
        print("🤖 OpenAI API를 통한 맞춤형 진단 데이터 생성 중...")
        ai_diagnosis_data = generate_complete_diagnosis_data(conversation_text, sub_tone)
        
        # 텍스트 정리
        cleaned_analysis = clean_analysis_text(ai_diagnosis_data["detailed_analysis"])
        
        # 기본 타입 정보에 AI 생성 데이터 적용
        type_info = {
            "name": f"{sub_tone} {primary_tone}톤",
            "description": ai_diagnosis_data["emotional_description"],
            "detailed_analysis": cleaned_analysis,
            "color_palette": ai_diagnosis_data["color_palette"],
            "style_keywords": ai_diagnosis_data["style_keywords"],
            "makeup_tips": ai_diagnosis_data["makeup_tips"]
        }
        
        # 결과 톤 및 신뢰도 설정  
        result_tone = f"{primary_tone}톤 {sub_tone}"
        confidence = 0.85  # 기본 신뢰도
        
        # primary_type 매핑
        type_mapping = {
            ("웜", "봄"): "spring",
            ("웜", "가을"): "autumn", 
            ("쿨", "여름"): "summer",
            ("쿨", "겨울"): "winter"
        }
        primary_type = type_mapping.get((primary_tone, sub_tone), "spring")
        
        # Top types 생성 (AI 생성 데이터 기반)
        top_types = [
            {
                "type": primary_type,
                "name": f"{sub_tone} {primary_tone}톤",
                "description": type_info["description"],
                "color_palette": type_info["color_palette"],
                "style_keywords": type_info["style_keywords"],
                "makeup_tips": type_info["makeup_tips"],
                "score": int(confidence * 100)
            }
        ]
        
        # SurveyResult로 새로운 진단 기록 저장
        print(f"💾 새로운 진단 기록 DB 저장 시작...")
        survey_result = models.SurveyResult(
            user_id=user_id,
            result_tone=primary_type,
            confidence=confidence,
            total_score=int(confidence * 100),
            source_type="chatbot",  # 챗봇 분석 출처 표시
            detailed_analysis=type_info["detailed_analysis"],
            result_name=type_info["name"],
            result_description=type_info["description"],
            color_palette=json.dumps(type_info["color_palette"], ensure_ascii=False),
            style_keywords=json.dumps(type_info["style_keywords"], ensure_ascii=False),
            makeup_tips=json.dumps(type_info["makeup_tips"], ensure_ascii=False),
            top_types=json.dumps(top_types, ensure_ascii=False)
        )
        
        db.add(survey_result)
        db.commit()
        db.refresh(survey_result)
        
        print(f"✅ 새로운 진단 기록 생성 완료: survey_result_id={survey_result.id}")
        print(f"   - 진단 타입: {survey_result.result_tone}")
        print(f"   - 신뢰도: {survey_result.confidence}")
        print(f"   ⚠️ 마이페이지 진단 기록에 새로운 항목 추가됨")
        
        return survey_result
        
    except Exception as e:
        print(f"❌ 챗봇 분석 결과 저장 중 오류: {e}")
        db.rollback()
        return None


@router.post("/report/save", response_model=ReportResponse)
async def save_report_now(
    request: ReportCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    프론트엔드에서 3턴마다 호출하는 엔드포인트입니다.
    force=True로 `save_chatbot_analysis_result`를 호출해 항상 새 진단 기록을 생성합니다.
    """
    if not request.history_id:
        raise HTTPException(status_code=400, detail="history_id가 필요합니다")

    survey_result = await save_chatbot_analysis_result(
        user_id=current_user.id,
        chat_history_id=request.history_id,
        db=db,
        force=request.force or True,  # 기본 동작은 강제 생성
    )

    if survey_result:
        # 생성된 survey_result의 요약/미리보기 데이터를 생성
        try:
            from utils.report_generator import PersonalColorReportGenerator

            report_generator = PersonalColorReportGenerator()

            # survey_result에 저장된 JSON 필드 파싱
            def parse_json_field(val):
                if not val:
                    return []
                if isinstance(val, str):
                    try:
                        return json.loads(val)
                    except:
                        return []
                return val

            survey_data = {
                "result_tone": survey_result.result_tone,
                "result_name": survey_result.result_name,
                "confidence": survey_result.confidence,
                "detailed_analysis": survey_result.detailed_analysis,
                "color_palette": parse_json_field(survey_result.color_palette),
                "style_keywords": parse_json_field(survey_result.style_keywords),
                "makeup_tips": parse_json_field(survey_result.makeup_tips),
            }

            # 대화 히스토리 조회
            chat_history = []
            try:
                messages = db.query(models.ChatMessage).filter_by(
                    history_id=request.history_id
                ).order_by(models.ChatMessage.created_at.asc()).all()
                chat_history = [
                    {"role": msg.role, "text": msg.text, "created_at": msg.created_at.isoformat()}
                    for msg in messages
                ]
            except Exception:
                chat_history = []

            report_data = report_generator.generate_report_data(survey_data, chat_history)

        except Exception as e:
            print(f"⚠️ 리포트 요약 생성 중 오류: {e}")
            report_data = None

        # 프론트가 즉시 표시하기 쉬운 미리보기 필드도 함께 반환
        return ReportResponse(
            survey_result_id=survey_result.id,
            message="진단 기록 생성 완료",
            created_at=survey_result.created_at,
            result_tone=survey_result.result_tone,
            result_name=survey_result.result_name,
            detailed_analysis=survey_result.detailed_analysis,
            color_palette=(json.loads(survey_result.color_palette) if survey_result.color_palette else []),
            style_keywords=(json.loads(survey_result.style_keywords) if survey_result.style_keywords else []),
            makeup_tips=(json.loads(survey_result.makeup_tips) if survey_result.makeup_tips else []),
            report_data=report_data,
        )
    else:
        raise HTTPException(status_code=500, detail="진단 기록 생성 실패")

def detect_emotion(text: str) -> str:
    """
    OpenAI 기반 감정 분석 (Lottie emotion string 반환)
    """
    prompt = f"""
다음 사용자 발화의 감정을 아래 목록 중 하나로만 분류하세요. 반드시 한 단어만 답하세요. 다른 단어, 설명 없이.
목록: happy, sad, angry, love, fearful, neutral
예시:
발화: "{text}"
감정 (목록 중 하나, 한 단어만):
"""
    prompt = f"""
다음 사용자 발화의 감정을 아래 목록 중 하나로만 분류하세요. 반드시 한 단어만 답하세요. 다른 단어, 설명 없이.
목록: happy, sad, angry, love, fearful, neutral
예시 (한국어 다양한 표현 포함):
- "오늘 너무 힘들었어요" → sad
- "정말 고마워요!" → happy
- "화가 나요" → angry
- "내 노력을 무시하는 태도에 분노가 치밀어요" → angry
- "그 사람 태도 때문에 열이 받아요" → angry
- "사랑해요" → love
- "그와 함께 있으면 행복하고 사랑을 느껴" → love
- "무서워서 혼자 있을 수가 없어요" → fearful
- "높은 곳에 서면 다리가 떨리고 무서워요" → fearful
- "별 감정이 없어요" → neutral
발화: "{text}"
감정 (목록 중 하나, 한 단어만):
"""
    try:
        response = client.chat.completions.create(
            model=get_model_to_use(),
            messages=[{"role": "system", "content": "너는 감정 분석 전문가야. 반드시 목록 중 하나의 감정만 한 단어로 답해줘."},
                      {"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0.0
        )
        emotion = response.choices[0].message.content.strip().lower()
        # 감정 단어만 추출 (정확히 일치하는 단어만 반환)
        valid_emotions = ["happy", "sad", "angry", "love", "fearful", "neutral"]
        for e in valid_emotions:
            if emotion == e:
                return e
        # 혹시 여러 단어가 섞여 있으면 첫 번째 유효 단어만 반환
        for e in valid_emotions:
            if e in emotion:
                return e
        return "neutral"
    except Exception as e:
        print(f"[detect_emotion] OpenAI 감정 분석 오류: {e}")
        return "neutral"


def _normalize_emotion_label(label: str) -> str:
    """Normalize arbitrary labels to the canonical set or return empty string."""
    if not label or not isinstance(label, str):
        return ""
    l = label.strip().lower()
    # emoji mapping: map common emoji characters to canonical labels
    emoji_map = {
        "😄": "happy",
        "😊": "happy",
        "🙂": "happy",
        "😁": "happy",
        "😂": "happy",
        "😭": "sad",
        "😢": "sad",
        "😞": "sad",
        "😠": "angry",
        "😡": "angry",
        "💔": "sad",
        "💖": "love",
        "❤️": "love",
        "😍": "love",
        "😨": "fearful",
        "😱": "fearful",
    }
    # if the label itself is an emoji or contains one, map it
    for emj, mapped in emoji_map.items():
        if emj == l or emj in label:
            return mapped
    # allowed canonical emotions
    valid = ["happy", "sad", "angry", "love", "fearful", "neutral"]
    # direct match
    if l in valid:
        return l
    # common synonyms mapping
    synonyms = {
        "joy": "happy",
        "happiness": "happy",
        "depressed": "sad",
        "anger": "angry",
        "fear": "fearful",
        "afraid": "fearful",
        "love": "love",
        "liked": "love",
    }
    if l in synonyms:
        return synonyms[l]
    # if label contains a valid token, pick first
    for v in valid:
        if v in l:
            return v
    return ""


def _precheck_strong_anger_fear(user_text: str, convo_text: str | None = None) -> str:
    """
    Lightweight pre-check for strong anger/fear lexical cues in Korean.
    Returns 'angry' or 'fearful' if a strong cue is found, otherwise empty string.
    """
    try:
        import re
        txt = (user_text or "") + "\n" + (convo_text or "")
        txt = txt.lower()
        # Anger cues (Korean stems)
        if re.search(r"(열이 받|열받|분노|화가 나|성냄|짜증|분개|격분|참을 수 없)", txt):
            return 'angry'
        # Fear/anxiety cues
        if re.search(r"(무서|두렵|공포|겁|불안|막막|숨이 막히|오싹)", txt):
            return 'fearful'
    except Exception:
        return ""
    return ""


async def _call_api_emotion_service(question: str, conversation_history: list | None = None):
    """Call the external api_emotion service if available and return the parsed response or None.

    Handles both coroutine and sync implementations by running sync calls in a thread executor.
    """
    if not api_emotion_service:
        return None
    try:
        # build payload if the service exposes the request model
        if hasattr(api_emotion_service, 'EmotionRequest'):
            payload = api_emotion_service.EmotionRequest(user_text=question, conversation_history=conversation_history)
        else:
            payload = {"user_text": question, "conversation_history": conversation_history}

        gen = getattr(api_emotion_service, 'generate_emotion', None)
        if gen is None:
            return None

        if asyncio.iscoroutinefunction(gen):
            resp = await gen(payload)
        else:
            # run sync function in executor to avoid blocking event loop
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(None, lambda: gen(payload))

        # convert pydantic model to dict if needed
        if hasattr(resp, 'dict'):
            return resp.dict()
        return resp if isinstance(resp, dict) else None
    except Exception as e:
        print(f"[analyze] api_emotion call failed: {e}")
        return None


def _extract_emotion_from_orchestrator(emotion_res: dict) -> str:
    """Try to extract a canonical emotion label from the orchestrator's parsed emotion dict."""
    if not emotion_res or not isinstance(emotion_res, dict):
        return ""
    # Prefer explicit canonical labels or primary tone fields returned by the model/orchestrator
    for key in ('canonical_label', 'canonical', 'primary_tone', 'primary', 'label', 'emotion'):
        val = emotion_res.get(key)
        if isinstance(val, str) and val:
            lab = _normalize_emotion_label(val)
            if lab:
                return lab

    # Next, prefer tone_tags (they often contain more descriptive tokens)
    tags = emotion_res.get('tone_tags') or emotion_res.get('tags')
    if tags and isinstance(tags, list):
        # Prefer explicit anger tokens if present (increase sensitivity)
        for t in tags:
            lab = _normalize_emotion_label(t)
            if lab == 'angry':
                return 'angry'
        for t in tags:
            lab = _normalize_emotion_label(t)
            if lab:
                return lab

    return ""


async def _resolve_emotion_tag(emotion_res: dict, conversation_history: list | None, question: str) -> str:
    """High-level resolver: orchestrator -> api_emotion -> local detector."""
    # 1) orchestrator
    try:
        val = _extract_emotion_from_orchestrator(emotion_res)
        if val:
            return val
    except Exception:
        pass

    # 2) external service
    try:
        api_resp = await _call_api_emotion_service(question, conversation_history)
        if isinstance(api_resp, dict):
            # Prefer explicit canonical_label from api_emotion if present
            canon_label = api_resp.get('canonical_label') or api_resp.get('canonical')
            if isinstance(canon_label, str) and canon_label:
                try:
                    return to_canonical(canon_label)
                except Exception:
                    return _normalize_emotion_label(canon_label) or ''
            # Prefer tone_tags (they often contain more specific tokens)
            tokens = api_resp.get('tone_tags') or api_resp.get('tags')
            if tokens:
                if isinstance(tokens, str):
                    tokens = [tokens]
                if isinstance(tokens, list):
                    # normalize all tokens then prefer 'angry' if any
                    canons = []
                    for t in tokens:
                        try:
                            canon = to_canonical(t)
                        except Exception:
                            canon = _normalize_emotion_label(t)
                        if canon:
                            canons.append(canon)
                    if 'angry' in canons:
                        return 'angry'
                    for canon in canons:
                        if canon and canon != 'neutral':
                            return canon

            # Try scanning description/summary for lexical cues (Korean stems included in SYNONYMS)
            desc = api_resp.get('description') or api_resp.get('summary') or ''
            if isinstance(desc, str) and desc:
                try:
                    desc_canon = to_canonical(desc)
                except Exception:
                    desc_canon = _normalize_emotion_label(desc)
                if desc_canon and desc_canon != 'neutral':
                    return desc_canon

            # Fallback to primary fields (canonicalize)
            for key in ('primary_tone', 'primary', 'label', 'tag', 'emotion'):
                v = api_resp.get(key)
                if isinstance(v, str):
                    try:
                        lab = to_canonical(v)
                    except Exception:
                        lab = _normalize_emotion_label(v)
                    if lab:
                        return lab
    except Exception:
        pass

    # 3) local fallback
    try:
        local = detect_emotion(question)
        local_norm = _normalize_emotion_label(local) or local
        if local_norm:
            return local_norm
    except Exception:
        pass

    return "neutral"

@router.post("/analyze", response_model=ChatbotHistoryResponse)
async def analyze(
    request: ChatbotRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Debug: log incoming request and user for tracing 400 errors
    try:
        print(f"[analyze] incoming request: history_id={request.history_id}, question={request.question}")
        print(f"[analyze] current_user.id={getattr(current_user,'id',None)}")
    except Exception:
        pass

    # 신규 세션 생성 또는 기존 세션 이어받기
    if not request.history_id:
        chat_history = models.ChatHistory(user_id=current_user.id)
        db.add(chat_history)
        db.commit()
        db.refresh(chat_history)
    else:
        chat_history = db.query(models.ChatHistory).filter_by(id=request.history_id, user_id=current_user.id).first()
        if not chat_history:
            raise HTTPException(status_code=404, detail="해당 history_id 세션 없음")
        if chat_history.ended_at:
            # Log ended session to help debugging
            print(f"[analyze] requested history_id {request.history_id} is already ended at {chat_history.ended_at}")
            raise HTTPException(status_code=400, detail="이미 종료된 세션입니다.")
    user_msg = models.ChatMessage(history_id=chat_history.id, role="user", text=request.question)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # If the incoming request has an empty question, treat this call as a "welcome" request
    # and return the same welcome message that `/welcome` provides so clients can use
    # a single endpoint for both welcome + normal analyze flows.
    if not request.question or (isinstance(request.question, str) and request.question.strip() == ""):
        try:
            # Reuse the existing welcome helper to build the message. Pass current db and user.
            infl_id = chat_history.influencer_id or chat_history.influencer_name
            welcome_resp = generate_welcome(db=db, current_user=current_user, influencer_id=infl_id)
            welcome_text = (welcome_resp or {}).get('message') or '안녕하세요! 퍼스널컬러 AI입니다.'
        except Exception as e:
            print(f"[analyze] welcome generation failed: {e}")
            welcome_text = '안녕하세요! 퍼스널컬러 AI입니다.'

        # persist AI welcome message
        ai_msg = models.ChatMessage(
            history_id=chat_history.id,
            role='ai',
            text=welcome_text,
            raw=json.dumps({'description': welcome_text}, ensure_ascii=False),
        )
        db.add(ai_msg)
        db.commit()
        db.refresh(ai_msg)

        # build items response compatible with frontend ChatbotHistoryResponse
        item = {
            'question_id': 0,
            'question': '',
            'answer': welcome_text,
            'chat_res': {
                'primary_tone': '',
                'sub_tone': '',
                'description': welcome_text,
                'recommendations': [],
                'emotion': 'neutral',
            }
        }
        # ensure top-level `emotion` exists to satisfy ChatItemModel response validation
        item['emotion'] = item['chat_res'].get('emotion', 'neutral')
        return {'history_id': chat_history.id, 'items': [item]}
    # 이전 대화 히스토리에서 사용자 정보 수집
    prev_messages = db.query(models.ChatMessage).filter_by(history_id=chat_history.id).order_by(models.ChatMessage.id.asc()).all()
    # 닉네임 사용: current_user.nickname이 있으면, 없으면 '사용자'
    user_display_name = getattr(current_user, "nickname", None)
    if not user_display_name:
        user_display_name = "사용자"
    # 최근 메시지는 later used to build `convo_list`; no separate summary needed here.
    
    # Use the local orchestrator service to run color+emotion -> influencer chain
    if not orchestrator_service:
        raise HTTPException(status_code=500, detail="Orchestrator service not available in this runtime")

    # Build a structured conversation history for the orchestrator
    convo_list = []
    for msg in prev_messages:
        try:
            if msg.role == 'user':
                convo_list.append({"role": "user", "text": msg.text})
            else:
                # ai messages may contain JSON with a description field
                try:
                    ai_data = json.loads(msg.text)
                    convo_list.append({"role": "ai", "text": ai_data.get("description", msg.text)})
                except Exception:
                    convo_list.append({"role": "ai", "text": msg.text})
        except Exception:
            continue

    try:
        # include any persona stored on the chat history so the orchestrator and influencer chain
        # can adapt responses to the selected persona
        persona_name = getattr(chat_history, 'influencer_name', None)
        orch_payload = orchestrator_service.OrchestratorRequest(
            user_text=request.question,
            conversation_history=convo_list,
            user_nickname=getattr(current_user, 'nickname', None),
            personal_color=None,
            use_color=True,
            use_emotion=True,
        )
        # attach influencer persona if available (some orchestrator implementations accept this)
        if persona_name and hasattr(orch_payload, 'dict'):
            # safest approach: set attribute when present
            try:
                setattr(orch_payload, 'influencer_name', persona_name)
            except Exception:
                pass
        orch_resp = await orchestrator_service.analyze(orch_payload)

        # Debug: print orchestrator full response for troubleshooting
        try:
            orch_serializable = None
            if hasattr(orch_resp, 'dict'):
                try:
                    orch_serializable = orch_resp.dict()
                except Exception:
                    # some pydantic models may require .dict(exclude_none=True)
                    try:
                        orch_serializable = orch_resp.dict(exclude_none=True)
                    except Exception:
                        orch_serializable = None
            elif isinstance(orch_resp, dict):
                orch_serializable = orch_resp

            if orch_serializable is not None:
                try:
                    print("[analyze] orch_resp:", json.dumps(orch_serializable, ensure_ascii=False)[:4000])
                except Exception:
                    print("[analyze] orch_resp (repr):", repr(orch_serializable)[:4000])
            else:
                print("[analyze] orch_resp (raw):", repr(orch_resp)[:4000])
        except Exception as e:
            print(f"[analyze] orch_resp logging failed: {e}")
    except Exception as e:
        print(f"❌ Orchestrator error: {e}")
        raise HTTPException(status_code=500, detail=f"Orchestrator failed: {str(e)}")
    # Extract results (orchestrator now returns namespaced structures)
    raw_emotion = orch_resp.emotion if getattr(orch_resp, 'emotion', None) is not None else (orch_resp.get('emotion') if isinstance(orch_resp, dict) else {})
    raw_color = orch_resp.color if getattr(orch_resp, 'color', None) is not None else (orch_resp.get('color') if isinstance(orch_resp, dict) else {})

    # unwrap parsed parts if present
    def _unwrap(parsed_like):
        if isinstance(parsed_like, dict) and parsed_like.get("parsed") is not None:
            return parsed_like.get("parsed"), parsed_like
        return (parsed_like if isinstance(parsed_like, dict) else {}, parsed_like)

    emotion_res, emotion_wrapped = _unwrap(raw_emotion)
    color_res, color_wrapped = _unwrap(raw_color)

    # Prefer influencer-styled text when available; it may be wrapped as well
    influencer_info = None
    if isinstance(raw_emotion, dict):
        inf = raw_emotion.get("influencer_styled") or raw_emotion.get("influencer")
        if isinstance(inf, dict) and inf.get("parsed") is not None:
            influencer_info = inf.get("parsed")
        else:
            influencer_info = inf

    # Defensive fixes: if influencer_info contains an error object, ignore it
    try:
        if isinstance(influencer_info, dict) and influencer_info.get('error'):
            influencer_info = None
    except Exception:
        influencer_info = influencer_info

    try:
        # if not found, check wrapped/raw payloads (various shapes)
        if isinstance(emotion_wrapped, dict):
            # common nested locations
            candidates = [emotion_wrapped.get('raw_model_output'), emotion_wrapped.get('raw'), emotion_wrapped.get('parsed')]
            for cand in candidates:
                try:
                    if isinstance(cand, dict):
                        mo = cand.get('model_output') or cand
                except Exception:
                    continue

        # also check orch_resp top-level dict forms if available
        if isinstance(orch_resp, dict):
            try:
                er = orch_resp.get('emotion') or {}
                if isinstance(er, dict):
                    rm = er.get('raw_model_output') or er.get('raw') or er.get('parsed')
                    if isinstance(rm, dict):
                        mo = rm.get('model_output') or rm
            except Exception:
                pass

    except Exception:
        pass

    # If influencer_info is missing or invalid, try a safe fallback: generate a short
    # influencer-styled message using the available color/emotion outputs via OpenAI.
    # This ensures the response follows the desired chain: color -> emotion -> influencer.
    try:
        if not influencer_info:
            # build a compact prompt summarizing color + emotion outputs
            try:
                color_summary = ''
                if isinstance(color_res, dict):
                    hints = color_res.get('detected_color_hints') or color_res.get('detected_color_hints') or {}
                    if isinstance(hints, dict):
                        color_summary = hints.get('result_name') or hints.get('reason') or ''
                emotion_summary = ''
                if isinstance(emotion_res, dict):
                    emotion_summary = emotion_res.get('description') or emotion_res.get('primary_tone') or ''

                system_msg = (
                    "당신은 한국어로 자연스럽고 친근한 인플루언서 말투를 모방하는 카피라이터입니다. "
                    "사용자에게 바로 보여줄 수 있는 2~3문장 분량의 응답을 생성하세요."
                )
                user_msg = (
                    f"사용자 상황: {emotion_summary}\n퍼스널 컬러 힌트: {color_summary}\n"
                    "위 정보를 바탕으로 친근하고 상담자다운 말투로 간단한 응답을 만들어주세요."
                )

                resp = client.chat.completions.create(
                    model=get_model_to_use(),
                    messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                    max_tokens=200,
                    temperature=0.7,
                )
                styled = ''
                try:
                    styled = resp.choices[0].message.content.strip()
                except Exception:
                    styled = str(resp)[:500]
                if styled:
                    influencer_info = {"styled_text": styled, "generated_by": "fallback_openai"}
            except Exception as e:
                # if OpenAI fallback fails, keep influencer_info as None
                print(f"[analyze] influencer fallback generation failed: {e}")
    except Exception:
        pass

    # Compose the data payload to store and return (keep structure compatible with frontend)
    data = {}
    # primary/sub tones: prefer personal-color hints from color service, fallback to emotion
    primary = None
    sub = None
    if isinstance(color_res, dict):
        detected = color_res.get("detected_color_hints") or {}
        primary = detected.get("primary_tone")
        sub = detected.get("sub_tone")
    if not primary and isinstance(emotion_res, dict):
        primary = emotion_res.get("primary_tone")
    if not sub and isinstance(emotion_res, dict):
        sub = emotion_res.get("sub_tone")

    # Normalize arbitrary model/free-text tones to canonical values
    try:
        norm_primary, norm_sub = normalize_personal_color(primary, sub)
        primary = norm_primary
        sub = norm_sub
    except Exception:
        # if normalization fails for any reason, fall back to raw values
        pass

    data["primary_tone"] = primary or ""
    data["sub_tone"] = sub or ""

    # description: influencer styled text (string) > influencer fields > emotion.description > color.description
    desc = None
    try:
        # influencer_info might be a string (already-styled text) or a dict with fields
        if isinstance(influencer_info, str) and influencer_info.strip():
            desc = influencer_info
        elif isinstance(influencer_info, dict):
            # prefer explicit styled_text, then description, then model_output.description
            desc = influencer_info.get('styled_text') or influencer_info.get('description')
            if not desc:
                mo = influencer_info.get('model_output') or influencer_info.get('raw') or None
                if isinstance(mo, dict):
                    desc = mo.get('description') or mo.get('styled_text')
    except Exception:
        desc = None

    if not desc:
        desc = (emotion_res.get("description") if isinstance(emotion_res, dict) else None) or (color_res.get("description") if isinstance(color_res, dict) else None)
    data["description"] = desc or "안녕하세요! 퍼스널컬러 전문가입니다. 어떤 부분이 고민이신가요?"

    # recommendations: merge lists from emotion, color, and influencer (if any)
    recs = []
    if isinstance(emotion_res, dict):
        recs.extend(emotion_res.get("recommendations", []) or [])
    if isinstance(color_res, dict):
        recs.extend(color_res.get("recommendations", []) or [])
    # influencer may include explicit recommendations
    if influencer_info and isinstance(influencer_info, dict):
        if influencer_info.get("recommendations"):
            recs.extend(influencer_info.get("recommendations"))

    # flatten and dedupe
    flat = []
    for item in recs:
        if isinstance(item, list):
            for subit in item:
                if isinstance(subit, str) and subit not in flat:
                    flat.append(subit)
        elif isinstance(item, str):
            if item not in flat:
                flat.append(item)
    if not flat:
        flat = ["더 자세한 정보를 위해 피부톤이나 선호 색을 알려주세요."]
    data["recommendations"] = flat

    # attach influencer metadata for frontend
    if influencer_info:
        data["influencer"] = influencer_info

    # Resolve emotion tag (orchestrator -> api_emotion -> local detector)
    # Fast pre-check: if the user's message or recent convo contains strong anger/fear cues,
    # short-circuit and use that label before calling external services.
    convo_text = "\n".join([c.get("text", "") for c in convo_list]) if convo_list else ""
    precheck_label = _precheck_strong_anger_fear(request.question, convo_text)
    if precheck_label:
        user_emotion = precheck_label
    else:
        # If this analyze call appears to be a welcome / image-upload prompt,
        # or the orchestrator explicitly marked it as a welcome, skip emotion
        # resolution and default to neutral to avoid UX confusion.
        try:
            # detect welcome flag coming from orchestrator (various shapes)
            is_welcome_meta = False
            try:
                meta = None
                if isinstance(orch_resp, dict):
                    meta = orch_resp.get('_meta') or orch_resp.get('meta')
                elif hasattr(orch_resp, 'dict'):
                    try:
                        orch_dict = orch_resp.dict()
                        meta = orch_dict.get('_meta') or orch_dict.get('meta')
                    except Exception:
                        meta = getattr(orch_resp, 'meta', None)
                if isinstance(meta, dict) and meta.get('is_welcome'):
                    is_welcome_meta = True
            except Exception:
                is_welcome_meta = False

            qtxt = request.question or ''
            if is_welcome_meta or (isinstance(qtxt, str) and re.search(r"이미지|업로드|환영|환영합니다|환영해", qtxt)):
                print('[analyze] welcome-like detected (meta or question); forcing emotion=neutral')
                user_emotion = 'neutral'
            else:
                user_emotion = await _resolve_emotion_tag(emotion_res, convo_list, request.question)
        except Exception:
            user_emotion = await _resolve_emotion_tag(emotion_res, convo_list, request.question)
    # canonicalize and attach emotion + lottie filename for frontend
    user_emotion = to_canonical(user_emotion)
    data["emotion"] = user_emotion
    # provide the frontend with the exact lottie filename it should load
    data["emotion_lottie"] = lottie_filename(user_emotion)
    # Store a human-readable message in the `text` field so the frontend
    # doesn't render a raw JSON blob. Prefer the `description` (influencer-styled
    # text) when available; fall back to the full JSON payload string.
    human_text = data.get("description") or json.dumps(data, ensure_ascii=False)
    # Store both human-friendly text and the structured payload as `raw`.
    ai_msg = models.ChatMessage(
        history_id=chat_history.id,
        role="ai",
        text=human_text,
        raw=json.dumps({
            "primary_tone": data.get("primary_tone"),
            "sub_tone": data.get("sub_tone"),
            "description": data.get("description"),
            "recommendations": data.get("recommendations"),
            "influencer": data.get("influencer"),
            "emotion": data.get("emotion"),
            "emotion_lottie": data.get("emotion_lottie"),
        }, ensure_ascii=False),
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)

    # AI 답변 저장 후, AI 피드백 자동 평가 실행 (채팅 종료 전에도 평가 가능하도록 예외 무시)
    try:
        generate_ai_feedbacks(history_id=chat_history.id, current_user=current_user, db=db)
    except Exception as e:
        # 예: 채팅 종료 전에는 평가 불가 등의 예외 발생 가능, 무시하고 진행
        pass
    msgs = db.query(models.ChatMessage).filter_by(history_id=chat_history.id).order_by(models.ChatMessage.id.asc()).all()
    items = []
    qid = 1
    i = 0
    # Robust pairing: for each user message, find the next AI message (if any)
    while i < len(msgs):
        try:
            if msgs[i].role == 'user':
                # find next ai message
                j = i + 1
                while j < len(msgs) and msgs[j].role != 'ai':
                    j += 1
                if j < len(msgs) and msgs[j].role == 'ai':
                    ai_msg = msgs[j]
                    raw_blob = getattr(ai_msg, 'raw', None) or (ai_msg.text or "")
                    d = None
                    try:
                        if isinstance(raw_blob, str):
                            d = json.loads(raw_blob)
                        elif isinstance(raw_blob, dict):
                            d = raw_blob
                        else:
                            d = {"description": str(raw_blob)}
                    except Exception:
                        try:
                            text_blob = ai_msg.text or ""
                            d = json.loads(text_blob)
                        except Exception:
                            d = {"description": ai_msg.text or ""}

                    # normalize nested description/json
                    if isinstance(d.get("description"), str):
                        desc_text = d.get("description", "").strip()
                        if desc_text.startswith("{") or desc_text.startswith("["):
                            try:
                                parsed_desc = json.loads(desc_text)
                                if isinstance(parsed_desc, dict):
                                    for k, v in parsed_desc.items():
                                        if k not in d or k == 'description':
                                            d[k] = v
                            except Exception:
                                pass

                    recommendations = d.get("recommendations", [])
                    if isinstance(recommendations, dict):
                        recommendations = list(recommendations.values())
                    elif isinstance(recommendations, list):
                        flattened_recommendations = []
                        for item in recommendations:
                            if isinstance(item, list):
                                flattened_recommendations.extend(item)
                            elif isinstance(item, str):
                                flattened_recommendations.append(item)
                        recommendations = flattened_recommendations
                    else:
                        recommendations = []
                    d["recommendations"] = recommendations
                    d.setdefault('primary_tone', '')
                    d.setdefault('sub_tone', '')
                    d.setdefault('emotion', d.get('emotion', 'neutral') or 'neutral')
                    d.setdefault('description', d.get('description') or '')

                    items.append(ChatItemModel(
                        question_id=qid,
                        question=msgs[i].text,
                        answer=d.get("description",""),
                        chat_res=ChatResModel.model_validate(d),
                        emotion=d.get("emotion", "neutral")
                    ))
                    qid += 1
                    # advance i to after this ai message
                    i = j + 1
                    continue
            i += 1
        except Exception:
            i += 1
    return {"history_id": chat_history.id, "items": items}


@router.post("/start")
def start_chat_session(
    payload: dict | None = Body(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    명시적으로 새 채팅 세션을 생성하고 history_id를 반환합니다.
    프론트엔드가 페이지 진입 시 이 엔드포인트를 호출하여
    기존 열린 세션과 관계없이 항상 새로운 세션을 시작하도록 합니다.
    """
    # DB-level concurrency handling:
    # Acquire a FOR UPDATE lock on the user row, then check for an open ChatHistory.
    # This prevents two concurrent requests from both observing "no open session" and
    # creating duplicate open sessions. Locking the user row is lightweight and
    # avoids requiring DB schema changes (partial unique indexes) here.
    try:
        # optional influencer_name from request body
        influencer_name = None
        try:
            if payload and isinstance(payload, dict):
                influencer_name = payload.get('influencer_name') or payload.get('influencer')
        except Exception:
            influencer_name = None

        # Lock the user row for this transaction
        db.query(models.User).filter(models.User.id == current_user.id).with_for_update().first()

        # Now check again for an existing open session while holding the lock
        # If an influencer_name was requested, prefer reusing an open session for that influencer
        existing = None
        if influencer_name:
            try:
                existing = db.query(models.ChatHistory).filter(
                    models.ChatHistory.user_id == current_user.id,
                    models.ChatHistory.ended_at == None,
                    models.ChatHistory.influencer_name == influencer_name,
                ).order_by(models.ChatHistory.created_at.desc()).first()
            except Exception:
                existing = None

        # fallback: any existing open session
        if not existing:
            existing = db.query(models.ChatHistory).filter(
                models.ChatHistory.user_id == current_user.id,
                models.ChatHistory.ended_at == None,
            ).order_by(models.ChatHistory.created_at.desc()).first()

        if existing:
            user_turns = db.query(models.ChatMessage).filter_by(history_id=existing.id, role='user').count()
            print(f"🔁 기존 열린 세션 재사용: user_id={current_user.id}, history_id={existing.id}, user_turns={user_turns}")
            return {"history_id": existing.id, "reused": True, "user_turns": user_turns}

        # No existing open session found while holding the lock: create one
        chat_history = models.ChatHistory(user_id=current_user.id)
        # persist both influencer id and name when available
        try:
            if influencer_name:
                # if influencer_name is actually an id (slug), store in influencer_id
                if isinstance(influencer_name, str) and '_' in influencer_name:
                    chat_history.influencer_id = influencer_name
                else:
                    chat_history.influencer_name = influencer_name
        except Exception:
            pass
        db.add(chat_history)
        db.commit()
        db.refresh(chat_history)
        print(f"➕ 새 채팅 세션 생성: user_id={current_user.id}, history_id={chat_history.id}")
        return {"history_id": chat_history.id, "reused": False, "user_turns": 0}
    except Exception as e:
        # Roll back on error and return a 500 so clients can retry safely
        print(f"❌ /start 오류 발생: {e}")
        try:
            db.rollback()
        except:
            pass
        raise HTTPException(status_code=500, detail="채팅 세션 생성 중 DB 오류가 발생했습니다")




@router.get('/history/influencers')
def get_influencer_histories(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return a list of influencer groups for the current user with simple summaries.

    Each item contains: `influencer_id`, `influencer_name`, `total_sessions`, `total_messages`, `last_activity`.
    """
    try:
        user_id = getattr(current_user, 'id', None)
        if not user_id:
            raise HTTPException(status_code=401, detail="로그인 필요")

        histories = db.query(models.ChatHistory).filter_by(user_id=user_id).order_by(models.ChatHistory.created_at.desc()).all()

        groups: dict = {}
        for h in histories:
            key = h.influencer_id or (h.influencer_name or 'unknown')
            name = h.influencer_name or h.influencer_id or 'unknown'
            if key not in groups:
                groups[key] = {
                    'influencer_id': key,
                    'influencer_name': name,
                    'histories': [],
                    'total_messages': 0,
                    'last_activity': h.created_at,
                }
            groups[key]['histories'].append(h.id)
            # count messages for this history
            try:
                cnt = db.query(models.ChatMessage).filter_by(history_id=h.id).count()
            except Exception:
                cnt = 0
            groups[key]['total_messages'] += cnt
            if h.created_at and (not groups[key]['last_activity'] or h.created_at > groups[key]['last_activity']):
                groups[key]['last_activity'] = h.created_at

        # Retrieve influencer profiles (prefer influencer service) to merge metadata
        profiles = None
        try:
            if influencer_service and hasattr(influencer_service, 'influencer_profiles'):
                res = influencer_service.influencer_profiles()
                if isinstance(res, list):
                    outp = []
                    for it in res:
                        try:
                            if hasattr(it, 'dict'):
                                outp.append(it.dict())
                            else:
                                outp.append(it)
                        except Exception:
                            outp.append(it)
                    profiles = outp
                else:
                    profiles = res
        except Exception:
            profiles = None

        # fallback safe list if service not available
        if not profiles:
            profiles = [
                {'id': 'won_jun', 'name': '원준', 'short_description': '친근하면서도 솔직한 리뷰', 'example_sentences': ['안녕하세요 귀욤이님! 원준입니다!']},
                {'id': 'se_hyun', 'name': '세현', 'short_description': '자연스러운 데일리 메이크업 전문', 'example_sentences': ['안녕하세요 포드래곤님! 세현이예요!']},
                {'id': 'jong_min', 'name': '종민', 'short_description': '가성비 중심의 실용적 리뷰', 'example_sentences': ['안녕하세요 트루드래곤님! 종민입니다!']},
                {'id': 'hye_kyung', 'name': '혜경', 'short_description': '종합 뷰티 가이드', 'example_sentences': ['안녕하세요 뷰티패밀리님! 혜경입니다!']},
            ]

        # Normalize profiles into a lookup by id and by name
        profile_map_by_id = {}
        profile_map_by_name = {}
        for p in profiles:
            try:
                if isinstance(p, dict):
                    pid = p.get('id') or p.get('influencer_id') or None
                    name = p.get('name') or p.get('short_name') or None
                    if pid:
                        profile_map_by_id[str(pid)] = p
                    if name:
                        profile_map_by_name[str(name).lower()] = p
            except Exception:
                continue

        # Ensure that every known profile appears in the groups map even if the user
        # has no chat histories with them. This lets the frontend depend on a
        # single endpoint for both the influencer list and per-influencer histories.
        def _slugify_name(n: str) -> str:
            try:
                s = str(n).strip().lower()
                s = s.replace(' ', '_')
                import re
                s = re.sub(r'[^a-z0-9_\-]', '', s)
                return s
            except Exception:
                return str(n)

        for p in profiles:
            try:
                if not isinstance(p, dict):
                    continue
                pid = p.get('id') or p.get('influencer_id')
                name = p.get('name') or p.get('short_name') or p.get('short_description')
                key = str(pid) if pid else _slugify_name(name or 'unknown')
                if key not in groups:
                    groups[key] = {
                        'influencer_id': key,
                        'influencer_name': name or key,
                        'histories': [],
                        'total_messages': 0,
                        'last_activity': None,
                    }
            except Exception:
                continue

        # Remove the generic 'unknown' group so the frontend receives only
        # meaningful influencer entries (profiles or named influencers).
        # This avoids showing an 'unknown' tile in the influencer list.
        filtered_groups = {k: v for k, v in groups.items() if str(k).lower() != 'unknown'}

        out = []
        for key, g in filtered_groups.items():
            recent_msg = None
            try:
                recent_msg = db.query(models.ChatMessage).join(models.ChatHistory).filter(models.ChatHistory.user_id==user_id, models.ChatHistory.id.in_(g['histories'])).order_by(models.ChatMessage.created_at.desc()).first()
            except Exception:
                recent_msg = None

            short = None
            if recent_msg:
                text = getattr(recent_msg, 'text', '') or ''
                short = text.replace('\n', ' ').strip()
                if len(short) > 120:
                    short = short[:117] + '...'

            # merge profile metadata if available
            profile_meta = None
            try:
                # prefer exact id match
                if g['influencer_id'] and profile_map_by_id.get(str(g['influencer_id'])):
                    profile_meta = profile_map_by_id.get(str(g['influencer_id']))
                else:
                    # try name match
                    nm = (g['influencer_name'] or '').lower()
                    if nm and profile_map_by_name.get(nm):
                        profile_meta = profile_map_by_name.get(nm)
            except Exception:
                profile_meta = None

            # prefer message-level timestamp for last_activity when available
            last_activity_val = g.get('last_activity')
            try:
                if recent_msg and getattr(recent_msg, 'created_at', None):
                    # if recent_msg is newer than the history-level last_activity, prefer it
                    if not last_activity_val or getattr(recent_msg, 'created_at') > last_activity_val:
                        last_activity_val = getattr(recent_msg, 'created_at')
            except Exception:
                pass

            item = {
                'influencer_id': g['influencer_id'],
                'influencer_name': g['influencer_name'],
                'total_sessions': len(g['histories']),
                'total_messages': g['total_messages'],
                'last_activity': last_activity_val,
            }

            # Aggregate numeric ratings for this influencer across its histories
            try:
                avg_cnt = db.query(
                    func.avg(models.UserFeedback.rating),
                    func.count(models.UserFeedback.id)
                ).filter(
                    models.UserFeedback.history_id.in_(g['histories']),
                    models.UserFeedback.rating != None
                ).one()
                avg_val, cnt_val = avg_cnt[0], avg_cnt[1]
                item['average_rating'] = float(avg_val) if avg_val is not None else None
                item['rating_count'] = int(cnt_val or 0)
            except Exception:
                item['average_rating'] = None
                item['rating_count'] = 0

            # Ensure profile object exists and attach short_description inside profile
            try:
                if profile_meta and isinstance(profile_meta, dict):
                    full_profile = dict(profile_meta)
                else:
                    # create a minimal profile object so frontend always finds `profile.short_description`
                    full_profile = {'id': g['influencer_id'] or g['influencer_name'], 'name': g['influencer_name']}

                # normalize aliases
                if not full_profile.get('id'):
                    full_profile['id'] = full_profile.get('influencer_id') or full_profile.get('name')

                # prefer recent message; otherwise keep existing profile short_description or description
                existing_short = full_profile.get('short_description') or full_profile.get('short_name') or full_profile.get('description') or ''
                full_profile['short_description'] = short or existing_short or ''

                item['profile'] = full_profile

            except Exception:
                # fallback: attach a minimal profile with empty short_description
                item['profile'] = {'id': g['influencer_id'] or g['influencer_name'], 'name': g['influencer_name'], 'short_description': short or ''}

            out.append(item)

        # sort by last_activity desc
        out.sort(key=lambda x: x.get('last_activity') or datetime.min, reverse=True)
        return out
    except HTTPException:
        raise
    except Exception as e:
        print(f"[get_influencer_histories] error: {e}")
        raise HTTPException(status_code=500, detail="인플루언서별 히스토리 조회 중 오류가 발생했습니다")


@router.get('/history/{history_id}')
def get_chat_history(history_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return existing chat history items for the current user.

    This endpoint is safe to call after `start` returns a history_id (including reused sessions)
    and will return the same `items` structure as `/analyze` produces so the frontend can
    rehydrate the chat UI without sending a new user message.
    """
    try:
        history = db.query(models.ChatHistory).filter_by(id=history_id, user_id=current_user.id).first()
        if not history:
            raise HTTPException(status_code=404, detail="해당 history_id 세션 없음")

        msgs = db.query(models.ChatMessage).filter_by(history_id=history.id).order_by(models.ChatMessage.id.asc()).all()
        items = []
        qid = 1
        # Robust pairing: for each user message, find the next AI/system/assistant message
        i = 0
        while i < len(msgs):
            try:
                if msgs[i].role == 'user':
                    j = i + 1
                    while j < len(msgs) and msgs[j].role not in ('ai', 'system', 'assistant'):
                        j += 1
                    if j < len(msgs):
                        ai_msg = msgs[j]
                        raw_blob = getattr(ai_msg, 'raw', None) or (ai_msg.text or "")
                        d = None
                        try:
                            if isinstance(raw_blob, str):
                                d = json.loads(raw_blob)
                            elif isinstance(raw_blob, dict):
                                d = raw_blob
                            else:
                                d = {"description": str(raw_blob)}
                        except Exception:
                            try:
                                text_blob = ai_msg.text or ""
                                d = json.loads(text_blob)
                            except Exception:
                                d = {"description": ai_msg.text or ""}

                        # normalize recommendations field
                        recommendations = d.get('recommendations', [])
                        if isinstance(recommendations, dict):
                            recommendations = list(recommendations.values())
                        elif isinstance(recommendations, list):
                            flattened_recommendations = []
                            for item in recommendations:
                                if isinstance(item, list):
                                    flattened_recommendations.extend(item)
                                elif isinstance(item, str):
                                    flattened_recommendations.append(item)
                            recommendations = flattened_recommendations
                        else:
                            recommendations = []
                        d['recommendations'] = recommendations
                        d.setdefault('primary_tone', '')
                        d.setdefault('sub_tone', '')
                        d.setdefault('emotion', d.get('emotion', 'neutral') or 'neutral')
                        d.setdefault('description', d.get('description') or '')

                        # create ChatItemModel-like structure
                        item = {
                            'question_id': qid,
                            'question': msgs[i].text,
                            'answer': d.get('description', ''),
                            'chat_res': d,
                            # include timestamps so clients can render original message times
                            'question_created_at': (msgs[i].created_at.isoformat() if getattr(msgs[i], 'created_at', None) else None),
                            'created_at': (msgs[j].created_at.isoformat() if getattr(msgs[j], 'created_at', None) else None),
                        }
                        items.append(item)
                        qid += 1
                        i = j + 1
                        continue
                i += 1
            except Exception:
                i += 1

        return {"history_id": history.id, "items": items}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[get_chat_history] error: {e}")
        raise HTTPException(status_code=500, detail="히스토리 조회 중 오류가 발생했습니다")


@router.get('/history/influencer/{influencer_id}')
def get_messages_for_influencer(influencer_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return all messages for the given influencer across the user's chat histories.

    The response contains `history_id` and `items` (list of messages ordered by created_at asc).
    """
    try:
        user_id = getattr(current_user, 'id', None)
        if not user_id:
            raise HTTPException(status_code=401, detail="로그인 필요")

        # find histories that match influencer_id (exact match on influencer_id OR name-like match)
        histories = db.query(models.ChatHistory).filter(models.ChatHistory.user_id==user_id).filter(
            (models.ChatHistory.influencer_id == influencer_id) | (models.ChatHistory.influencer_name.like(f"%{influencer_id}%"))
        ).order_by(models.ChatHistory.created_at.asc()).all()

        if not histories:
            return {'history_id': None, 'items': []}

        # collect messages across histories, preserving chronological order
        history_ids = [h.id for h in histories]
        msgs = db.query(models.ChatMessage).filter(models.ChatMessage.history_id.in_(history_ids)).order_by(models.ChatMessage.created_at.asc()).all()

        items = []
        for m in msgs:
            try:
                raw_val = getattr(m, 'raw', None)
                parsed = None
                # Try to obtain a parsed dict from raw (preferred)
                if raw_val:
                    if isinstance(raw_val, dict):
                        parsed = raw_val
                    elif isinstance(raw_val, str):
                        try:
                            parsed = json.loads(raw_val)
                        except Exception:
                            parsed = None
                # If we couldn't parse raw, try parsing the text (older records stored JSON in text)
                if parsed is None:
                    txt = getattr(m, 'text', '') or ''
                    if isinstance(txt, dict):
                        parsed = txt
                    elif isinstance(txt, str) and (txt.strip().startswith('{') or txt.strip().startswith('[')):
                        try:
                            parsed = json.loads(txt)
                        except Exception:
                            parsed = None

                # Normalize parsed into a dict-like structure for the frontend
                if not isinstance(parsed, dict):
                    # fallback: keep raw as-is inside a description
                    parsed = {'description': (getattr(m, 'text', '') or '')}

                # If the parsed payload contains nested JSON inside `description` or `styled_text`, try to unwrap
                if isinstance(parsed.get('description'), str):
                    desc_candidate = parsed.get('description').strip()
                    if desc_candidate.startswith('{') or desc_candidate.startswith('['):
                        try:
                            inner = json.loads(desc_candidate)
                            if isinstance(inner, dict):
                                # merge keys from parsed_desc into d without overwriting existing top-level fields
                                for k, v in inner.items():
                                    if k not in parsed or k == 'description':
                                        parsed[k] = v
                        except Exception:
                            pass

                # Prefer influencer.styled_text when available
                styled_text = None
                infl = parsed.get('influencer')
                if isinstance(infl, dict):
                    # some records embed another JSON string inside influencer.raw/raw.model_output
                    st = infl.get('styled_text') or infl.get('description') or None
                    if isinstance(st, str) and (st.strip().startswith('{') or st.strip().startswith('[')):
                        try:
                            stp = json.loads(st)
                            if isinstance(stp, dict) and stp.get('styled_text'):
                                styled_text = stp.get('styled_text')
                            else:
                                # If the nested value is actually a dict describing styled_text, try common keys
                                styled_text = stp.get('styled_text') or stp.get('description') or None
                        except Exception:
                            styled_text = st
                    else:
                        styled_text = st

                # fallback to top-level styled_text or description
                if not styled_text:
                    top_st = parsed.get('styled_text') or parsed.get('description') or None
                    if isinstance(top_st, str) and (top_st.strip().startswith('{') or top_st.strip().startswith('[')):
                        try:
                            inner_top = json.loads(top_st)
                            if isinstance(inner_top, dict):
                                styled_text = inner_top.get('styled_text') or inner_top.get('description') or None
                            else:
                                styled_text = str(top_st)
                        except Exception:
                            styled_text = str(top_st)
                    else:
                        styled_text = top_st

                # final_clean_text: ensure it's a simple string
                final_text = styled_text if isinstance(styled_text, str) and styled_text.strip() else (parsed.get('description') or (getattr(m, 'text', '') or ''))

                items.append({
                    'history_id': m.history_id,
                    'role': m.role,
                    'text': final_text,
                    'raw': parsed,
                    'created_at': m.created_at.isoformat() if getattr(m, 'created_at', None) else None,
                })
            except Exception:
                # fallback to original minimal representation on unexpected errors
                items.append({
                    'history_id': m.history_id,
                    'role': m.role,
                    'text': getattr(m, 'text', '') or '',
                    'raw': getattr(m, 'raw', None),
                    'created_at': m.created_at.isoformat() if getattr(m, 'created_at', None) else None,
                })

        return {'history_ids': history_ids, 'items': items}
    except Exception as e:
        print(f"[get_messages_for_influencer] error: {e}")
        raise HTTPException(status_code=500, detail="인플루언서별 메시지 조회 중 오류가 발생했습니다")
    

@router.post("/end/{history_id}")
async def end_chat_session(
    history_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = db.query(models.ChatHistory).filter_by(id=history_id, user_id=current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="대화 세션 없음")
    if chat.ended_at:
        return {"message": "이미 종료됨", "ended_at": chat.ended_at}
    
    # 대화 종료 시간 설정
    chat.ended_at = datetime.now(timezone.utc)
    db.commit()
    
    # 챗봇 대화 분석 결과를 SurveyResult로 저장
    try:
        survey_result = await save_chatbot_analysis_result(
            user_id=current_user.id,
            chat_history_id=history_id,
            db=db
        )
        
        if survey_result:
            return {
                "message": "대화 종료 및 분석 결과 저장 완료", 
                "ended_at": chat.ended_at,
                "survey_result_id": survey_result.id,
                "personal_color_type": survey_result.result_tone
            }
        else:
            return {
                "message": "대화 종료됨 (분석 결과 저장 실패)", 
                "ended_at": chat.ended_at
            }
            
    except Exception as e:
        print(f"❌ 분석 결과 저장 중 오류: {e}")
        return {
            "message": "대화 종료됨 (분석 결과 저장 중 오류 발생)", 
            "ended_at": chat.ended_at
        }


@router.post("/report/request")
async def request_personal_color_report(
    request_data: dict,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🔥 기존 퍼스널 컬러 진단 보고서 생성 요청 🔥
    
    ⚠️ 중요: 이 API는 새로운 진단 기록을 생성하지 않습니다!
    - 기존 진단 결과(SurveyResult)를 기반으로 리포트만 생성
    - 진단 기록(마이페이지)에 새로운 항목이 추가되지 않음
    - 단순히 기존 데이터를 시각화/포맷팅하여 리포트로 제공
    
    새로운 진단 기록은 오직 대화형 분석을 통해서만 생성됩니다.
    """
    survey_result_id = request_data.get("history_id")  # 실제로는 survey_result_id
    
    if not survey_result_id:
        raise HTTPException(status_code=400, detail="진단 결과 ID가 필요합니다")
    
    # 사용자의 기존 진단 결과 조회 (읽기 전용)
    survey_result = db.query(models.SurveyResult).filter_by(
        id=survey_result_id, 
        user_id=current_user.id, 
        is_active=True
    ).first()
    
    if not survey_result:
        raise HTTPException(status_code=404, detail="진단 결과를 찾을 수 없습니다")
    
    print(f"📊 기존 진단 결과 기반 리포트 생성: survey_result_id={survey_result_id}")
    print(f"   - 결과 타입: {survey_result.result_tone}")
    print(f"   - 생성일: {survey_result.created_at}")
    print(f"   ❗ 새로운 진단 기록을 생성하지 않음 (리포트만 생성)")
    
    try:
        from utils.report_generator import PersonalColorReportGenerator
        
        # 리포트 생성기 초기화
        report_generator = PersonalColorReportGenerator()
        
        # 기존 진단 결과를 리포트 데이터로 변환 (읽기 전용)
        survey_data = {
            "result_tone": survey_result.result_tone,
            "result_name": survey_result.result_name,
            "confidence": survey_result.confidence,
            "detailed_analysis": survey_result.detailed_analysis,
            "color_palette": survey_result.color_palette,
            "style_keywords": survey_result.style_keywords,
            "makeup_tips": survey_result.makeup_tips
        }
        
        # 대화 히스토리 조회 (리포트에 포함할 대화 내용, 읽기 전용)
        chat_history = []
        if hasattr(survey_result, 'chat_history_id') and survey_result.chat_history_id:
            messages = db.query(models.ChatMessage).filter_by(
                history_id=survey_result.chat_history_id
            ).order_by(models.ChatMessage.created_at.asc()).all()
            
            chat_history = [
                {
                    "role": msg.role,
                    "text": msg.text,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        
        # 리포트 데이터 생성 (기존 데이터 시각화만, DB 변경 없음)
        report_data = report_generator.generate_report_data(survey_data, chat_history)
        
        # ⚠️ 중요: 여기서 db.add(), db.commit() 등의 DB 변경 작업 절대 금지!
        print(f"✅ 리포트 생성 완료 (DB 변경 없음)")
        
        return {
            "status": "success",
            "message": f"{survey_result.result_name or survey_result.result_tone.upper()} 타입 분석 리포트가 생성되었습니다",
            "survey_result_id": survey_result_id,
            "report_data": report_data,
            "note": "기존 진단 데이터 기반 리포트 생성 (새로운 진단 기록 추가 없음)"
        }
        
    except Exception as e:
        print(f"❌ 리포트 생성 중 오류: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"리포트 생성 중 오류가 발생했습니다: {str(e)}")

@router.get("/report/{survey_result_id}")
async def get_personal_color_report(
    survey_result_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    생성된 퍼스널 컬러 진단 보고서 조회
    """
    survey_result = db.query(models.SurveyResult).filter_by(
        id=survey_result_id, 
        user_id=current_user.id, 
        is_active=True
    ).first()
    
    if not survey_result:
        raise HTTPException(status_code=404, detail="진단 결과를 찾을 수 없습니다")
    
    try:
        from utils.report_generator import PersonalColorReportGenerator
        
        report_generator = PersonalColorReportGenerator()
        
        # 진단 결과 데이터 준비
        survey_data = {
            "result_tone": survey_result.result_tone,
            "result_name": survey_result.result_name,
            "confidence": survey_result.confidence,
            "detailed_analysis": survey_result.detailed_analysis,
            "color_palette": survey_result.color_palette,
            "style_keywords": survey_result.style_keywords,
            "makeup_tips": survey_result.makeup_tips
        }
        
        # 대화 히스토리 조회
        chat_history = []
        
        # 리포트 데이터 생성
        report_data = report_generator.generate_report_data(survey_data, chat_history)
        
        # HTML 리포트도 생성
        html_report = report_generator.generate_html_report(report_data)
        
        return {
            "message": "리포트 조회 성공",
            "report_data": report_data,
            "html_report": html_report,
            "download_available": True
        }
        
    except Exception as e:
        print(f"❌ 리포트 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"리포트 조회 중 오류가 발생했습니다: {str(e)}")
