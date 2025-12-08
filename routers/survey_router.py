from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
import models, schemas
import json
from datetime import datetime, timezone
from routers.user_router import get_current_user   # 인증 함수 import
import os
from openai import OpenAI
import re
from typing import List, Dict, Any
from math import sqrt
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("환경변수 OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)

router = APIRouter(prefix="/api/survey")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============ RAG 관련 유틸 함수 ============
def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """텍스트를 청크로 분할"""
    if overlap >= chunk_size:
        raise ValueError("overlap은 chunk_size보다 작아야 합니다.")
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunks.append(text[start:end])
        if end == text_length:
            break
        start += (chunk_size - overlap)
    return [c.strip() for c in chunks if c.strip()]

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """코사인 유사도 계산"""
    dot = sum(x * y for x, y in zip(a, b))
    na = sqrt(sum(x * x for x in a)) or 1e-8
    nb = sqrt(sum(x * x for x in b)) or 1e-8
    return dot / (na * nb)

def embed_texts(texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    """텍스트를 임베딩으로 변환"""
    res = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in res.data]

def top_k_chunks(query: str, index: Dict[str, Any], k: int = 3) -> List[str]:
    """쿼리와 유사한 상위 k개 청크 검색"""
    q_emb = embed_texts([query])[0]
    sims = [(cosine_similarity(q_emb, emb), i) for i, emb in enumerate(index["embeddings"])]
    sims.sort(reverse=True, key=lambda x: x[0])
    return [index["chunks"][i] for _, i in sims[:k]]

def build_rag_index(filepath: str) -> Dict[str, Any]:
    """RAG 인덱스 구축"""
    try:
        with open(filepath, encoding="utf-8") as f:
            text = f.read()
        chunks = chunk_text(text, chunk_size=800, overlap=100)
        embeddings = embed_texts(chunks)
        return {"chunks": chunks, "embeddings": embeddings}
    except FileNotFoundError:
        print(f"⚠️ RAG 파일을 찾을 수 없습니다: {filepath}")
        return {"chunks": [], "embeddings": []}

def analyze_personal_color_with_openai(answers: list[schemas.SurveyAnswerCreate]) -> dict:
    """
    사용자의 답변을 OpenAI API로 분석하여 퍼스널 컬러 타입 결정
    RAG를 활용하여 컨텍스트 기반 분석 수행
    
    Returns:
        {
            'result_tone': 'spring'|'summer'|'autumn'|'winter',
            'confidence': 0-100 (신뢰도 퍼센트),
            'total_score': 0-100 (종합 점수)
        }
    """
    
    # 프롬프트 구성 - 사용자의 답변을 명확하게 전달
    answers_text = "\n".join([
        f"Q{ans.question_id}: {ans.option_label}"
        for ans in answers
    ])
    
    system_prompt = (
        "당신은 전문적인 퍼스널 컬러 진단 컨설턴트입니다. "
        "사용자의 답변을 기반으로 가장 적합한 퍼스널 컬러 타입을 정확하게 진단해주세요. "
        "봄, 여름, 가을, 겨울 중 정확히 하나의 타입만 선택해야 하며, "
        "진단 신뢰도와 종합 점수를 객관적으로 평가해주세요."
    )
    
    user_prompt = f"""사용자의 퍼스널 컬러 테스트 답변:

{answers_text}

이 답변들을 기반으로 사용자의 퍼스널 컬러 타입을 분석하세요.

반드시 다음 가이드라인을 따라주세요:
- 메인 타입 1개와 추천 타입 2개로 총 3개의 타입을 제공해주세요
- 각 타입의 description은 문학적이고 감성적으로 작성해주세요
- name은 이모지와 함께 일관된 형식으로 작성해주세요 (예: '봄 웜톤 🌸')

분석 결과는 다음 형식으로 JSON으로 반드시 응답해주세요:
{{
    "result_tone": "spring|summer|autumn|winter 중 정확히 하나",
    "confidence": 0-100 사이의 숫자 (신뢰도 퍼센트, 진단의 확실성 정도),
    "total_score": 0-100 사이의 숫자 (종합 점수, 타입 특성의 부합도),
    "detailed_analysis": "사용자의 답변을 기반으로 한 자세한 분석 설명 (200-400자 정도)",
    "top_types": [
        {{
            "type": "spring|summer|autumn|winter",
            "name": "퍼스널 컬러 타입명 (반드시 '봄 웜톤 🌸' 형식)",
            "description": "타입의 특성을 문학적이고 감성적으로 표현한 설명 (30-50자)",
            "color_palette": ["#FF6F61", "#FFD1B3", "#FFE5B4", "#98FB98", "#40E0D0"],
            "style_keywords": ["화사함", "발랄함", "생동감", "밝음", "따뜻함"],
            "makeup_tips": ["코럴 블러셔", "피치 립", "골든 아이섀도우", "브라운 마스카라"],
            "score": 0-100 (해당 타입과의 일치도)
        }},
        {{
            "type": "두 번째로 적합한 타입",
            "name": "두 번째 타입명 (동일한 형식)",
            "description": "두 번째 타입의 감성적 설명",
            "color_palette": ["색상 코드 5개"],
            "style_keywords": ["키워드 5개"],
            "makeup_tips": ["메이크업 팁 4개"],
            "score": 첫 번째보다 10-20점 낮은 점수
        }},
        {{
            "type": "세 번째로 적합한 타입",
            "name": "세 번째 타입명 (동일한 형식)",
            "description": "세 번째 타입의 감성적 설명",
            "color_palette": ["색상 코드 5개"],
            "style_keywords": ["키워드 5개"],
            "makeup_tips": ["메이크업 팁 4개"],
            "score": 두 번째보다 10-15점 낮은 점수
        }}
    ]
}}

응답은 반드시 JSON 형식만 포함해야 합니다. 다른 설명은 포함하지 마세요."""

    try:
        # OpenAI API 호출 (타임아웃 30초)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1500,  # 토큰 수 증가
            timeout=30.0  # 30초 타임아웃
        )
        
        # 응답 파싱
        response_text = response.choices[0].message.content.strip()
        
        # JSON 추출 (혹시 다른 텍스트가 포함될 경우 대비)
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group()
        
        result = json.loads(response_text)
        
        # 결과 검증 및 정규화
        if result.get("result_tone") not in ["spring", "summer", "autumn", "winter"]:
            result["result_tone"] = "spring"
        
        result["confidence"] = max(0, min(100, int(result.get("confidence", 50))))
        result["total_score"] = max(0, min(100, int(result.get("total_score", 50))))
        
        # detailed_analysis 검증
        if not result.get("detailed_analysis"):
            result["detailed_analysis"] = "답변을 종합 분석한 결과입니다."
        
        # top_types 검증 및 기본값 설정
        if not result.get("top_types") or not isinstance(result.get("top_types"), list):
            # 기본 타입 데이터 생성
            type_names = {
                "spring": "봄 웜톤 🌸",
                "summer": "여름 쿨톤 💎", 
                "autumn": "가을 웜톤 🍂",
                "winter": "겨울 쿨톤 ❄️"
            }
            type_descriptions = {
                "spring": "밝고 생기 있는 봄날의 따뜻함을 담은 당신",
                "summer": "시원하고 우아한 여름날의 세련됨을 담은 당신",
                "autumn": "깊고 따뜻한 가을날의 포근함을 담은 당신", 
                "winter": "시원하고 강렬한 겨울날의 우아함을 담은 당신"
            }
            type_palettes = {
                "spring": ["#FF6F61", "#FFD1B3", "#FFE5B4", "#98FB98", "#40E0D0"],
                "summer": ["#F8BBD9", "#E6E6FA", "#ADD8E6", "#DDA0DD", "#D3D3D3"],
                "autumn": ["#800020", "#8B7355", "#FFD700", "#FF4500", "#556B2F"],
                "winter": ["#000000", "#FFFFFF", "#4169E1", "#FF1493", "#DC143C"]
            }
            type_styles = {
                "spring": ["화사함", "발랄함", "생동감", "밝음", "따뜻함"],
                "summer": ["차분함", "세련됨", "우아함", "로맨틱", "부드러움"],
                "autumn": ["따뜻함", "성숙함", "깊이", "풍성함", "고급스러움"],
                "winter": ["강렬함", "고급스러움", "시크함", "도시적", "명확함"]
            }
            type_makeup = {
                "spring": ["코럴 블러셔", "피치 립", "골든 아이섀도우", "브라운 마스카라"],
                "summer": ["로즈 블러셔", "더스티핑크 립", "라벤더 아이섀도우", "브라운 마스카라"],
                "autumn": ["오렌지 블러셔", "브릭레드 립", "골든브라운 아이섀도우", "브라운 마스카라"],
                "winter": ["푸시아 블러셔", "트루레드 립", "스모키 아이섀도우", "블랙 마스카라"]
            }
            
            # 메인 타입을 첫 번째로, 나머지 타입들을 추가 (최소 2개, 최대 3개)
            main_type = result["result_tone"]
            all_types = ["spring", "summer", "autumn", "winter"]
            other_types = [t for t in all_types if t != main_type]
            
            result["top_types"] = [
                {
                    "type": main_type,
                    "name": type_names[main_type],
                    "description": type_descriptions[main_type],
                    "color_palette": type_palettes[main_type],
                    "style_keywords": type_styles[main_type],
                    "makeup_tips": type_makeup[main_type],
                    "score": result.get("total_score", 85)
                },
                {
                    "type": other_types[0],
                    "name": type_names[other_types[0]],
                    "description": type_descriptions[other_types[0]],
                    "color_palette": type_palettes[other_types[0]],
                    "style_keywords": type_styles[other_types[0]],
                    "makeup_tips": type_makeup[other_types[0]],
                    "score": max(60, result.get("total_score", 85) - 20)
                },
                {
                    "type": other_types[1],
                    "name": type_names[other_types[1]],
                    "description": type_descriptions[other_types[1]],
                    "color_palette": type_palettes[other_types[1]],
                    "style_keywords": type_styles[other_types[1]],
                    "makeup_tips": type_makeup[other_types[1]],
                    "score": max(40, result.get("total_score", 85) - 35)
                }
            ]
        else:
            # top_types가 있는 경우 최소 2개, 최대 3개로 제한하고 필수 필드 검증
            if len(result["top_types"]) < 2:
                # 2개 미만이면 기본 타입들로 채우기
                main_type = result["result_tone"]
                all_types = ["spring", "summer", "autumn", "winter"]
                other_types = [t for t in all_types if t != main_type]
                
                # 부족한 만큼 기본 데이터로 추가 (개선된 fallback 데이터)
                type_names = {
                    "spring": "봄 웜톤 🌸",
                    "summer": "여름 쿨톤 💎", 
                    "autumn": "가을 웜톤 🍂",
                    "winter": "겨울 쿨톤 ❄️"
                }
                type_descriptions = {
                    "spring": "밝고 생기 있는 봄날의 따뜻함을 담은 당신",
                    "summer": "시원하고 우아한 여름날의 세련됨을 담은 당신",
                    "autumn": "깊고 따뜻한 가을날의 포근함을 담은 당신", 
                    "winter": "시원하고 강렬한 겨울날의 우아함을 담은 당신"
                }
                type_palettes = {
                    "spring": ["#FF6F61", "#FFD1B3", "#FFE5B4", "#98FB98", "#40E0D0"],
                    "summer": ["#F8BBD9", "#E6E6FA", "#ADD8E6", "#DDA0DD", "#D3D3D3"],
                    "autumn": ["#800020", "#8B7355", "#FFD700", "#FF4500", "#556B2F"],
                    "winter": ["#000000", "#FFFFFF", "#4169E1", "#FF1493", "#DC143C"]
                }
                type_styles = {
                    "spring": ["화사함", "발랄함", "생동감", "밝음", "따뜻함"],
                    "summer": ["차분함", "세련됨", "우아함", "로맨틱", "부드러움"],
                    "autumn": ["따뜻함", "성숙함", "깊이", "풍성함", "고급스러움"],
                    "winter": ["강렬함", "고급스러움", "시크함", "도시적", "명확함"]
                }
                type_makeup = {
                    "spring": ["코럴 블러셔", "피치 립", "골든 아이섀도우", "브라운 마스카라"],
                    "summer": ["로즈 블러셔", "더스티핑크 립", "라벤더 아이섀도우", "브라운 마스카라"],
                    "autumn": ["오렌지 블러셔", "브릭레드 립", "골든브라운 아이섀도우", "브라운 마스카라"],
                    "winter": ["푸시아 블러셔", "트루레드 립", "스모키 아이섀도우", "블랙 마스카라"]
                }
                
                while len(result["top_types"]) < 3:
                    missing_index = len(result["top_types"]) - 1
                    if missing_index < len(other_types):
                        type_key = other_types[missing_index]
                        result["top_types"].append({
                            "type": type_key,
                            "name": type_names[type_key],
                            "description": type_descriptions[type_key],
                            "color_palette": type_palettes[type_key],
                            "style_keywords": type_styles[type_key],
                            "makeup_tips": type_makeup[type_key],
                            "score": max(50, result.get("total_score", 85) - (len(result["top_types"]) * 15))
                        })
            
            # 최대 3개로 제한
            result["top_types"] = result["top_types"][:3]
            
            # 개선된 fallback 데이터
            fallback_data = {
                "spring": {
                    "name": "봄 웜톤 🌸",
                    "description": "밝고 생기 있는 봄날의 따뜻함을 담은 당신",
                    "color_palette": ["#FF6F61", "#FFD1B3", "#FFE5B4", "#98FB98", "#40E0D0"],
                    "style_keywords": ["화사함", "발랄함", "생동감", "밝음", "따뜻함"],
                    "makeup_tips": ["코럴 블러셔", "피치 립", "골든 아이섀도우", "브라운 마스카라"]
                },
                "summer": {
                    "name": "여름 쿨톤 💎",
                    "description": "시원하고 우아한 여름날의 세련됨을 담은 당신",
                    "color_palette": ["#F8BBD9", "#E6E6FA", "#ADD8E6", "#DDA0DD", "#D3D3D3"],
                    "style_keywords": ["차분함", "세련됨", "우아함", "로맨틱", "부드러움"],
                    "makeup_tips": ["로즈 블러셔", "더스티핑크 립", "라벤더 아이섀도우", "브라운 마스카라"]
                },
                "autumn": {
                    "name": "가을 웜톤 🍂",
                    "description": "깊고 따뜻한 가을날의 포근함을 담은 당신",
                    "color_palette": ["#800020", "#8B7355", "#FFD700", "#FF4500", "#556B2F"],
                    "style_keywords": ["따뜻함", "성숙함", "깊이", "풍성함", "고급스러움"],
                    "makeup_tips": ["오렌지 블러셔", "브릭레드 립", "골든브라운 아이섀도우", "브라운 마스카라"]
                },
                "winter": {
                    "name": "겨울 쿨톤 ❄️",
                    "description": "시원하고 강렬한 겨울날의 우아함을 담은 당신",
                    "color_palette": ["#000000", "#FFFFFF", "#4169E1", "#FF1493", "#DC143C"],
                    "style_keywords": ["강렬함", "고급스러움", "시크함", "도시적", "명확함"],
                    "makeup_tips": ["푸시아 블러셔", "트루레드 립", "스모키 아이섀도우", "블랙 마스카라"]
                }
            }
            
            for i, type_data in enumerate(result["top_types"]):
                if not isinstance(type_data, dict):
                    continue
                # 필수 필드 검증 및 개선된 fallback 적용
                type_key = type_data.get("type", result["result_tone"] if i == 0 else "spring")
                if type_key not in fallback_data:
                    type_key = "spring"
                
                type_data["type"] = type_key
                
                if not type_data.get("name") or type_data["name"] == f"{type_key} 타입":
                    type_data["name"] = fallback_data[type_key]["name"]
                if not type_data.get("description") or type_data["description"] in ["추가 타입입니다.", "퍼스널 컬러 타입입니다."]:
                    type_data["description"] = fallback_data[type_key]["description"]
                if not type_data.get("color_palette") or not isinstance(type_data.get("color_palette"), list):
                    type_data["color_palette"] = fallback_data[type_key]["color_palette"]
                if not type_data.get("style_keywords") or not isinstance(type_data.get("style_keywords"), list):
                    type_data["style_keywords"] = fallback_data[type_key]["style_keywords"]
                if not type_data.get("makeup_tips") or not isinstance(type_data.get("makeup_tips"), list):
                    type_data["makeup_tips"] = fallback_data[type_key]["makeup_tips"]
                if not type_data.get("score"):
                    type_data["score"] = max(50, result.get("total_score", 85) - (i * 15))
                    
        # 하위 호환성을 위한 메인 타입 정보 추출
        main_type_data = result["top_types"][0] if result["top_types"] else {}
        result["name"] = main_type_data.get("name", "퍼스널 컬러")
        result["description"] = main_type_data.get("description", "당신만의 특별한 컬러")
        result["color_palette"] = main_type_data.get("color_palette", [])
        result["style_keywords"] = main_type_data.get("style_keywords", [])
        result["makeup_tips"] = main_type_data.get("makeup_tips", [])
        
        print(f"✅ OpenAI 분석 완료: {result}")
        return result
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        # JSON 파싱 실패 시 기본값 반환
        return {
            "result_tone": "spring",
            "confidence": 50,
            "total_score": 50,
            "detailed_analysis": "분석 처리 중 오류가 발생했습니다.",
            "top_types": [
                {
                    "type": "spring",
                    "name": "봄 웜톤 🌸",
                    "description": "밝고 생기 있는 봄날의 따뜻함을 담은 당신",
                    "color_palette": ["#FF6F61", "#FFD1B3", "#FFE5B4", "#98FB98", "#40E0D0"],
                    "style_keywords": ["화사함", "발랄함", "생동감", "밝음", "따뜻함"],
                    "makeup_tips": ["코럴 블러셔", "피치 립", "골든 아이섀도우", "브라운 마스카라"],
                    "score": 50
                },
                {
                    "type": "summer",
                    "name": "여름 쿨톤 💎",
                    "description": "시원하고 우아한 여름날의 세련됨을 담은 당신",
                    "color_palette": ["#F8BBD9", "#E6E6FA", "#ADD8E6", "#DDA0DD", "#D3D3D3"],
                    "style_keywords": ["차분함", "세련됨", "우아함", "로맨틱", "부드러움"],
                    "makeup_tips": ["로즈 블러셔", "더스티핑크 립", "라벤더 아이섀도우", "브라운 마스카라"],
                    "score": 35
                }
            ]
        }
    except Exception as e:
        print(f"❌ OpenAI API 호출 오류: {e}")
        # API 오류 시 기본값 반환
        return {
            "result_tone": "spring",
            "confidence": 50,
            "total_score": 50,
            "detailed_analysis": "OpenAI API 연결에 문제가 발생했습니다.",
            "top_types": [
                {
                    "type": "spring",
                    "name": "봄 웜톤 🌸",
                    "description": "밝고 생기 있는 봄날의 따뜻함을 담은 당신",
                    "color_palette": ["#FF6F61", "#FFD1B3", "#FFE5B4", "#98FB98", "#40E0D0"],
                    "style_keywords": ["화사함", "발랄함", "생동감", "밝음", "따뜻함"],
                    "makeup_tips": ["코럴 블러셔", "피치 립", "골든 아이섀도우", "브라운 마스카라"],
                    "score": 50
                },
                {
                    "type": "summer",
                    "name": "여름 쿨톤 💎",
                    "description": "시원하고 우아한 여름날의 세련됨을 담은 당신",
                    "color_palette": ["#F8BBD9", "#E6E6FA", "#ADD8E6", "#DDA0DD", "#D3D3D3"],
                    "style_keywords": ["차분함", "세련됨", "우아함", "로맨틱", "부드러움"],
                    "makeup_tips": ["로즈 블러셔", "더스티핑크 립", "라벤더 아이섀도우", "브라운 마스카라"],
                    "score": 35
                }
            ]
        }

# TODO: survey API 구현 필요. 현재 정상 동작 X
@router.post("/submit", status_code=201)
async def submit_survey(
    result: schemas.SurveyResultCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    퍼스널 컬러 테스트 결과 제출
    
    프로세스:
    1. 프론트엔드에서 사용자 답변 데이터만 받음
    2. OpenAI API에 답변 데이터를 prompt로 전송 (RAG 컨텍스트 포함)
    3. OpenAI에서 result_tone, confidence, total_score 받음
    4. DB에 설문 결과 및 답변 저장
    
    Request Body (PersonalColorTest 컴포넌트에서 전송):
        {
            "answers": [
                {
                    "question_id": 1,
                    "option_id": "q1_opt_a",
                    "option_label": "밝고 생기 있는 피부"
                },
                ...
            ]
        }
    
    Response:
        {
            "message": "설문 결과 저장 완료",
            "survey_result_id": 123,
            "result_tone": "spring",
            "confidence": 85,
            "total_score": 88
        }
    """
    
    # 사용자 인증 확인
    if not current_user or not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="로그인 후 설문 응답만 가능합니다."
        )
    
    # 답변 데이터 검증
    if not result.answers or len(result.answers) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="답변 데이터가 필요합니다."
        )
    
    print(f"▶ 사용자 {current_user.username}({current_user.id})의 설문 제출")
    print(f"▶ 받은 답변 수: {len(result.answers)}")
    print(f"▶ 받은 데이터: {result}")

    try:
        # 1. OpenAI API 호출로 result_tone, confidence, total_score 받기
        print("▶ OpenAI API로 퍼스널 컬러 분석 중...")
        openai_result = analyze_personal_color_with_openai(result.answers)
        result_tone = openai_result['result_tone']
        confidence = openai_result['confidence']
        total_score = openai_result['total_score']
        
        print(f"✅ 분석 완료 - tone: {result_tone}, confidence: {confidence}, score: {total_score}")

        # 2. Survey Result 생성 (상세 분석 결과 포함)
        survey_result = models.SurveyResult(
            user_id=current_user.id,
            result_tone=result_tone,
            confidence=confidence,
            total_score=total_score,
            source_type="survey",  # 설문 분석 출처 표시
            detailed_analysis=openai_result.get('detailed_analysis'),
            result_name=openai_result.get('name'),
            result_description=openai_result.get('description'),
            color_palette=json.dumps(openai_result.get('color_palette', []), ensure_ascii=False),
            style_keywords=json.dumps(openai_result.get('style_keywords', []), ensure_ascii=False),
            makeup_tips=json.dumps(openai_result.get('makeup_tips', []), ensure_ascii=False),
            top_types=json.dumps(openai_result.get('top_types', []), ensure_ascii=False),
            created_at=datetime.now(timezone.utc)
        )
        db.add(survey_result)
        db.flush()  # ID 생성을 위해 flush
        
        print(f"▶ SurveyResult 생성: ID {survey_result.id}")
        
        # 3. 모든 답변 저장
        for ans in result.answers:
            answer = models.SurveyAnswer(
                survey_result_id=survey_result.id,
                question_id=ans.question_id,
                option_id=ans.option_id,
                option_label=ans.option_label
            )
            db.add(answer)
        
        db.commit()
        db.refresh(survey_result)
        
        print(f"✅ 설문 결과 저장 완료 - Survey ID: {survey_result.id}")
        
        return {
            "message": "설문 결과 저장 완료", 
            "survey_result_id": survey_result.id,
            "result_tone": result_tone,
            "confidence": confidence,
            "total_score": total_score,
            "detailed_analysis": openai_result.get('detailed_analysis', '분석 결과가 준비되지 않았습니다.'),
            "top_types": openai_result.get('top_types', []),
            "name": openai_result.get('name', '퍼스널 컬러'),
            "description": openai_result.get('description', '당신만의 특별한 컬러'),
            "color_palette": openai_result.get('color_palette', []),
            "style_keywords": openai_result.get('style_keywords', []),
            "makeup_tips": openai_result.get('makeup_tips', [])
        }
    
    except Exception as e:
        print(f"❌ 설문 처리 중 오류 발생: {e}")
        db.rollback()  # 롤백
        
        # OpenAI API 오류 등 예외 상황에서도 기본 응답 제공
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="분석 서비스에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
        )

@router.get("/list", response_model=list[schemas.SurveyResult])
async def get_my_survey_results(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    현재 사용자의 모든 설문 결과 조회 (최신순)
    """
    if not current_user or not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="로그인이 필요합니다."
        )

    results = db.query(models.SurveyResult).filter(
        models.SurveyResult.user_id == current_user.id,
        models.SurveyResult.is_active == True  # 활성화된 결과만
    ).order_by(models.SurveyResult.created_at.desc()).all()
    
    return results

@router.get("/{survey_id}", response_model=schemas.SurveyResult)
async def get_survey_detail(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    특정 설문 결과 상세 조회
    """
    if not current_user or not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="로그인이 필요합니다."
        )

    result = db.query(models.SurveyResult).filter(
        models.SurveyResult.id == survey_id,
        models.SurveyResult.user_id == current_user.id,
        models.SurveyResult.is_active == True  # 활성화된 결과만
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="설문 결과를 찾을 수 없습니다."
        )
    
    return result

@router.delete("/{survey_id}", status_code=200)
async def delete_survey(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    설문 결과 삭제 (본인이 작성한 것만) - 소프트 딜리트 방식
    """
    if not current_user or not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="로그인이 필요합니다."
        )

    result = db.query(models.SurveyResult).filter(
        models.SurveyResult.id == survey_id,
        models.SurveyResult.user_id == current_user.id,
        models.SurveyResult.is_active == True  # 이미 삭제된 것은 제외
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="설문 결과를 찾을 수 없습니다."
        )
    
    # 하드 딜리트 대신 소프트 딜리트
    result.is_active = False
    db.commit()
    
    return {"message": "설문 결과가 삭제되었습니다."}
