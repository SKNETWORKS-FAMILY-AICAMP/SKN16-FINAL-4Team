
from fastapi import APIRouter, HTTPException, Depends, status
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.orm import Session
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
from utils.shared import top_k_chunks, build_rag_index, analyze_conversation_for_color_tone

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

다음 JSON 형식으로만 응답해주세요 (다른 설명 없이):
{{
    "emotional_description": "감성적이고 긍정적인 한 문장 (예: 당신은 따뜻하고 생기 넘치는 {season} 타입입니다!)",
    "color_palette": ["{season} 타입에 어울리는 5개의 HEX 색상 코드"],
    "style_keywords": ["{season} 타입의 특성을 나타내는 5개 키워드"],
    "makeup_tips": ["실용적인 메이크업 팁 4개"],
    "detailed_analysis": "대화 내용을 반영한 개인화된 분석 (2-3문단, 구체적이고 실용적인 조언 포함)"
}}

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
        
        # 대화 분석을 통한 퍼스널 컬러 진단
        primary_tone, sub_tone = analyze_conversation_for_color_tone(
            conversation_text, ""  # 현재 질문은 빈 문자열로 처리 (전체 대화 기반 분석)
        )
        
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
- "오늘 너무 힘들었어요" → sad
- "정말 고마워요!" → happy
- "화가 나요" → angry
- "사랑해요" → love
- "무서워요" → fearful
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
        return "wink"

@router.post("/analyze", response_model=ChatbotHistoryResponse)
def analyze(
    request: ChatbotRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
            raise HTTPException(status_code=400, detail="이미 종료된 세션입니다.")
    user_msg = models.ChatMessage(history_id=chat_history.id, role="user", text=request.question)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    # 이전 대화 히스토리에서 사용자 정보 수집
    prev_messages = db.query(models.ChatMessage).filter_by(history_id=chat_history.id).order_by(models.ChatMessage.id.asc()).all()
    # 닉네임 사용: current_user.nickname이 있으면, 없으면 '사용자'
    user_display_name = getattr(current_user, "nickname", None)
    if not user_display_name:
        user_display_name = "사용자"
    conversation_history = ""
    user_characteristics = []
    if prev_messages:
        # 이전 대화에서 사용자 특성 파악
        for msg in prev_messages[-6:]:  # 최근 6개 메시지만 사용 (3턴 대화)
            if msg.role == "user":
                conversation_history += f"{user_display_name}: {msg.text}\n"
            else:
                try:
                    ai_data = json.loads(msg.text)
                    conversation_history += f"전문가: {ai_data.get('description', '')}\n"
                    if ai_data.get('primary_tone'):
                        user_characteristics.append(f"추정 톤: {ai_data.get('primary_tone')} {ai_data.get('sub_tone')}")
                except:
                    conversation_history += f"전문가: {msg.text}\n"
    
    # 사용자 질문 + 대화 히스토리 결합
    combined_query = f"현재 질문: {request.question}\n\n이전 대화 맥락:\n{conversation_history}"
    
    # RAG 검색
    fixed_chunks = top_k_chunks(combined_query, fixed_index, client, k=3)
    trend_chunks = top_k_chunks(combined_query, trend_index, client, k=3)
    # Fine-tuned 감정 모델용 시스템 프롬프트 (퍼스널컬러 전문가 버전)
        # 사용자 닉네임을 description에 반영하도록 프롬프트 수정
    prompt_system = f"""당신은 경험이 풍부한 퍼스널컬러 전문가입니다. 다음 가이드라인을 따라 상담해주세요:

🎨 전문성과 친근함의 조화:
- 퍼스널컬러 전문 지식을 바탕으로 정확한 분석 제공
- 어려운 전문 용어는 쉽게 풀어서 설명
- 고객({user_display_name})이 편안하게 질문할 수 있도록 친근하고 따뜻한 톤 유지

� 감정 공감 기반 상담:
- 고객({user_display_name})의 고민과 니즈를 세심하게 파악 ("색깔 때문에 고민이 많으셨겠어요")
- 자신감 부족이나 스타일 고민에 공감하며 위로
- 긍정적인 변화를 위한 격려와 응원 메시지

🌟 실용적이고 개인화된 조언:
- 고객({user_display_name})의 라이프스타일, 직업, 선호도를 종합적으로 고려
- 구체적이고 실행 가능한 컬러 추천
- 예산과 상황에 맞는 현실적인 조언

💬 자연스러운 대화 스타일:
- 상담실에서 직접 대화하는 듯한 자연스러움
- "어떠세요?", "~해보시는 건 어떨까요?" 같은 상담 톤
- 고객({user_display_name})이 궁금해할 점을 먼저 예상해서 설명

당신의 뛰어난 감정 이해 능력을 활용하여, 고객({user_display_name})이 컬러에 대한 자신감을 갖고 아름다워질 수 있도록 도와주세요."""
    prompt_user = f"""대화 맥락:\n{combined_query}\n\n퍼스널컬러 전문 지식:\n{chr(10).join(fixed_chunks)}\n\n최신 트렌드 정보:\n{chr(10).join(trend_chunks)}\n\n다음 가이드라인으로 상담해주세요:
1. 고객({user_display_name})의 질문에 대해 전문적이면서도 친근하게 응답
2. 필요시 퍼스널컬러 진단을 위한 추가 질문 (피부톤, 선호 스타일, 라이프스타일 등)
3. 대화 흐름에 맞는 자연스러운 컬러 추천
4. 실용적이고 구체적인 조언 제공

JSON 형식으로 응답해주세요:
{{
    "primary_tone": "웜" 또는 "쿨",
    "sub_tone": "봄" 또는 "여름" 또는 "가을" 또는 "겨울",
    "description": "상세한 설명 텍스트 (자연스러운 대화체, 고객({user_display_name})을 직접 호명하며 안내)",
    "recommendations": ["구체적인 추천사항1", "구체적인 추천사항2", "구체적인 추천사항3"]
}}

주의: recommendations는 반드시 문자열 배열이어야 합니다.
"""
    messages = [{"role": "system", "content": prompt_system}, {"role": "user", "content": prompt_user}]
    
    # 모델 선택 함수 사용
    print(f"🤖 Using model: {get_model_to_use()[:30]}***")  # 디버깅용 로그
    try:
        resp = client.chat.completions.create(
            model=get_model_to_use(),
            messages=messages,
            temperature=0.8,  # 감정 모델에서는 좀 더 자연스러운 응답을 위해 temperature 상향
            max_tokens=600
        )
    except Exception as e:
        print(f"❌ OpenAI API 호출 실패: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI 서비스 일시적 오류: {str(e)}")
    content = resp.choices[0].message.content
    start, end = content.find("{"), content.rfind("}")
    
    # 대화를 통한 퍼스널컬러 진단 (유틸리티 함수 사용)
    primary_tone, sub_tone = analyze_conversation_for_color_tone(conversation_history, request.question)
    
    # JSON 파싱 시도
    if start != -1 and end != -1:
        try:
            data = json.loads(content[start:end+1])
            # 대화 분석 결과로 톤 정보 설정
            data["primary_tone"] = primary_tone
            data["sub_tone"] = sub_tone
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 fallback
            data = {
                "primary_tone": primary_tone,
                "sub_tone": sub_tone,
                "description": content.strip(),
                "recommendations": ["더 자세한 정보를 위해 피부톤이나 선호하는 색깔에 대해 말씀해주세요.", "평소 어떤 스타일을 좋아하시는지 알려주시면 더 정확한 분석을 도와드릴게요.", "궁금한 컬러나 스타일에 대해 언제든 물어보세요!"]
            }
    else:
        # JSON 형식이 전혀 없는 경우 fallback
        data = {
            "primary_tone": primary_tone,
            "sub_tone": sub_tone, 
            "description": content.strip() if content.strip() else "안녕하세요! 퍼스널컬러 전문가입니다. 어떤 컬러나 스타일에 대해 궁금한 점이 있으신가요? 피부톤, 좋아하는 색깔, 평소 스타일 등 어떤 것이든 편하게 말씀해주세요!",
            "recommendations": ["피부톤이나 혈관 색깔에 대해 알려주세요.", "평소 어떤 색깔 옷을 즐겨 입으시는지 말씀해주세요.", "메이크업이나 헤어 컬러 관련해서도 도움드릴 수 있어요."]
        }
    # 감정 이모티콘 분석 및 추가
    user_emotion = detect_emotion(request.question)
    data["emotion"] = user_emotion
    
    # recommendations 필드 정리
    recommendations = data.get("recommendations", [])
    if isinstance(recommendations, dict):
        recommendations = list(recommendations.values())
    elif isinstance(recommendations, list):
        # 중첩된 리스트를 평평하게 만들기
        flattened_recommendations = []
        for item in recommendations:
            if isinstance(item, list):
                flattened_recommendations.extend(item)
            elif isinstance(item, str):
                flattened_recommendations.append(item)
        recommendations = flattened_recommendations
    else:
        recommendations = []
    
    data["recommendations"] = recommendations
    ai_msg = models.ChatMessage(history_id=chat_history.id, role="ai", text=json.dumps(data, ensure_ascii=False))
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
    for i in range(0,len(msgs)-1,2):
        if msgs[i].role=="user" and msgs[i+1].role=="ai":
            d = json.loads(msgs[i+1].text)
            # 기존 데이터의 recommendations 필드도 정리
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
            items.append(ChatItemModel(
                question_id=qid,
                question=msgs[i].text,
                answer=d.get("description",""),
                chat_res=ChatResModel.model_validate(d),
                emotion=d.get("emotion", "wink")
            ))
            qid += 1
    return {"history_id": chat_history.id, "items": items}


@router.post("/start")
def start_chat_session(
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
        # Lock the user row for this transaction
        db.query(models.User).filter(models.User.id == current_user.id).with_for_update().first()

        # Now check again for an existing open session while holding the lock
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
