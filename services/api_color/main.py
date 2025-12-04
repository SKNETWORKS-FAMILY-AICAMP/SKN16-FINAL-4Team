"""
API Color - 퍼스널 컬러 분석 서비스

RAG Service를 직접 통합하여 다음 기능 제공:
1. 사용자 입력 + 대화 히스토리 + 감정/인플루언서 결과 통합
2. UnifiedKnowledgeRAG를 이용한 4-way 라우팅 (일반/불변/가변/통합)
3. 자연어 응답을 구조화된 퍼스널 컬러 정보로 변환

아키텍처:
- RAG Service: 중앙 지식 엔진 (라우팅 + 처리)
- API Color: 색상 분석 전문가 (입력 통합 + 응답 변환)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

# RAG Service 직접 import
try:
    from rag_service import UnifiedKnowledgeRAG
except ImportError as e:
    raise ImportError(f"RAG Service import 실패: {e}. rag_service 패키지가 필요합니다.")

app = FastAPI(
    title="API Color",
    description="RAG Service 통합 퍼스널 컬러 분석 API",
    version="3.0.0"
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== RAG 시스템 초기화 ====================
try:
    rag_system = UnifiedKnowledgeRAG()
    logger.info("✅ RAG 시스템 초기화 완료")
except Exception as e:
    logger.error(f"❌ RAG 시스템 초기화 실패: {e}")
    rag_system = None
# ==============================================================

class ColorRequest(BaseModel):
    """퍼스널 컬러 분석 요청"""
    user_text: Optional[str] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None
    emotion_result: Optional[Dict[str, Any]] = None
    influencer_result: Optional[Dict[str, Any]] = None


class ColorResponse(BaseModel):
    """퍼스널 컬러 분석 응답"""
    detected_color_hints: Optional[Dict[str, Any]]
    notes: Optional[str] = None


def _compose_query_from_payload(payload: ColorRequest) -> str:
    """페이로드에서 RAG 쿼리 구성"""
    parts = []
    
    if payload.user_text:
        parts.append(payload.user_text)
    
    if payload.conversation_history:
        history_text = "\n".join([
            m.get("text") or m.get("message") or "" 
            for m in payload.conversation_history[-10:]
        ])
        parts.append(history_text)
    
    if payload.emotion_result:
        # Use description + recommendations if available
        desc = payload.emotion_result.get("description") or payload.emotion_result.get("summary") or ""
        parts.append(desc)
        recs = payload.emotion_result.get("recommendations")
        if isinstance(recs, list):
            parts.append(" ".join(recs))
    
    if payload.influencer_result:
        styled = payload.influencer_result.get("styled_text") or payload.influencer_result.get("text") or ""
        parts.append(styled)
    
    return "\n".join([p for p in parts if p])


def _parse_rag_answer_to_color_hints(answer: str, query: str) -> Dict[str, Any]:
    """
    RAG 서비스 응답을 ColorResponse 형식으로 변환
    
    RAG 응답에서 퍼스널 컬러 정보를 추출하여 구조화
    """
    # 기본 구조
    hints = {
        "primary_tone": None,
        "sub_tone": None,
        "result_name": None,
        "recommended_palette": [],
        "suggested_styles": [],
        "reason": answer,
        "confidence": 0.7,
        "top_types": [],
        "source": "rag_service"
    }
    
    # RAG 응답에서 퍼스널 컬러 키워드 추출 (간단한 휴리스틱)
    answer_lower = answer.lower()
    
    # 계절/톤 감지
    season_mapping = {
        "봄": ("웜", "봄"),
        "spring": ("웜", "봄"),
        "여름": ("쿨", "여름"),
        "summer": ("쿨", "여름"),
        "가을": ("웜", "가을"),
        "autumn": ("웜", "가을"),
        "fall": ("웜", "가을"),
        "겨울": ("쿨", "겨울"),
        "winter": ("쿨", "겨울")
    }
    
    detected_season = None
    for keyword, (primary, sub) in season_mapping.items():
        if keyword in answer_lower:
            hints["primary_tone"] = primary
            hints["sub_tone"] = sub
            detected_season = sub
            break
    
    # 웜/쿨톤 직접 감지
    if not hints["primary_tone"]:
        if "웜톤" in answer or "warm" in answer_lower:
            hints["primary_tone"] = "웜"
        elif "쿨톤" in answer or "cool" in answer_lower:
            hints["primary_tone"] = "쿨"
    
    # result_name 생성
    if hints["primary_tone"] and hints["sub_tone"]:
        hints["result_name"] = f"{hints['sub_tone']} {hints['primary_tone']}톤"
    
    # top_types 생성 (최소 하나)
    if hints["result_name"]:
        type_mapping = {
            ("웜", "봄"): "spring",
            ("웜", "가을"): "autumn",
            ("쿨", "여름"): "summer",
            ("쿨", "겨울"): "winter",
        }
        primary_type = type_mapping.get((hints["primary_tone"], hints["sub_tone"]), "")
        
        hints["top_types"].append({
            "name": hints["result_name"],
            "type": primary_type,
            "description": answer[:200],  # 앞부분만 사용
            "score": int(hints["confidence"] * 100)
        })
    
    # 색상 팔레트 추출 (간단한 패턴 매칭)
    color_keywords = [
        "코랄", "피치", "아이보리", "베이지", "살구", 
        "핑크", "로즈", "와인", "버건디", "네이비",
        "차콜", "그레이", "실버", "골드", "브라운"
    ]
    
    for color in color_keywords:
        if color in answer:
            hints["recommended_palette"].append(color)
    
    # 중복 제거
    hints["recommended_palette"] = list(set(hints["recommended_palette"]))[:5]
    
    return hints


@app.post("/api/color/analyze", response_model=ColorResponse)
async def analyze_color(payload: ColorRequest):
    """
    퍼스널 컬러 분석 (RAG Service 통합)
    
    요청 흐름:
    1. 입력 검증 (user_text 또는 연결된 입력 필요)
    2. 쿼리 구성 (user_text + history + emotion + influencer 통합)
    3. RAG 시스템에 쿼리 전송 (4-way 자동 라우팅)
    4. 응답 파싱 (자연어 → 구조화된 색상 정보)
    5. 메타데이터 추가
    
    응답:
    - detected_color_hints: 검출된 퍼스널 컬러 정보
    - notes: 분석 결과 설명
    """
    # 입력 검증
    if not payload or not any([
        payload.user_text, 
        payload.conversation_history, 
        payload.emotion_result, 
        payload.influencer_result
    ]):
        raise HTTPException(
            status_code=400, 
            detail="user_text or chaining inputs are required"
        )
    
    # RAG 시스템 확인
    if not rag_system:
        logger.error("[api_color] RAG 시스템 미초기화")
        raise HTTPException(
            status_code=500,
            detail="RAG 시스템이 초기화되지 않았습니다."
        )
    
    try:
        # 통합 쿼리 구성
        query_text = _compose_query_from_payload(payload)
        logger.info(f"[api_color] 쿼리 생성: {query_text[:100]}...")
        
        # RAG 시스템에 쿼리 전송 (동기 호출)
        rag_result = rag_system.query(
            question=query_text,
            temperature=0.2,  # 퍼스널 컬러는 일관성 중요
            max_tokens=500,
            force_route=None  # 자동 라우팅: 최적의 지식 소스 선택
        )
        
        # RAG 응답 처리
        if not rag_result.get("success"):
            logger.error(f"[api_color] RAG 쿼리 실패: {rag_result}")
            raise Exception(rag_result.get("answer", "RAG 처리 실패"))
        
        answer = rag_result.get("answer", "")
        logger.info(f"[api_color] RAG 응답 받음 (route: {rag_result.get('route')})")
        
        # 응답 파싱
        hints = _parse_rag_answer_to_color_hints(answer, query_text)
        
        # RAG 메타데이터 추가
        hints["rag_metadata"] = {
            "route": rag_result.get("route"),
            "route_description": rag_result.get("route_description"),
            "sources": rag_result.get("sources", []),
            "models": rag_result.get("metadata", {}).get("immutable_model"),
            "timestamp": datetime.now().isoformat()
        }
        
        return ColorResponse(
            detected_color_hints=hints, 
            notes="퍼스널 컬러 분석 완료"
        )
        
    except Exception as e:
        logger.error(f"[api_color] 분석 실패: {e}", exc_info=True)
        
        # 폴백: 기본 응답
        hints = {
            "primary_tone": "웜",
            "sub_tone": "봄",
            "result_name": "봄 웜톤",
            "recommended_palette": ["코랄", "피치"],
            "suggested_styles": ["내추럴 메이크업"],
            "reason": "시스템 오류로 기본 추천을 제공합니다.",
            "confidence": 0.3,
            "top_types": [{
                "name": "봄 웜톤",
                "type": "spring",
                "description": "기본 추천",
                "score": 30
            }],
            "source": "fallback",
            "error": str(e)
        }
        
        return ColorResponse(
            detected_color_hints=hints, 
            notes=f"오류 발생: {str(e)}"
        )


@app.get("/api/color/health")
async def health_check():
    """
    헬스 체크
    
    RAG 시스템과 불변/가변 지식 파일 상태 확인
    """
    if not rag_system:
        return {
            "status": "error",
            "service": "api_color",
            "rag_system": "not_initialized"
        }
    
    return {
        "status": "ok",
        "service": "api_color",
        "rag_system": "initialized",
        "immutable_files": len(rag_system.immutable_handler.uploaded_files),
        "mutable_files": len(rag_system.mutable_handler.uploaded_files),
        "router_model": "gpt-4o-mini",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """API 정보"""
    return {
        "name": "API Color",
        "version": "3.0.0",
        "description": "RAG Service 통합 퍼스널 컬러 분석 API",
        "endpoints": {
            "analyze": "POST /api/color/analyze",
            "health": "GET /api/color/health"
        }
    }

