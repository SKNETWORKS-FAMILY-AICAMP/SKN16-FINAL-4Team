"""
OpenAI 기반 지식 라우터

GPT-4o-mini를 사용하여 질문을 4가지 카테고리로 분류:
1. 지식 RAG 불필요 (일반 대화)
2. 불변 지식 RAG (퍼스널 컬러)
3. 가변 지식 RAG (패션 트렌드)
4. 불변 + 가변 RAG (둘 다)
"""

from openai import OpenAI
import logging
from typing import Literal
from functools import lru_cache

from .config import (
    OPENAI_API_KEY,
    OPENAI_ROUTER_MODEL,
    ROUTING_TIMEOUT_SECONDS,
    ENABLE_ROUTING_CACHE
)

logger = logging.getLogger(__name__)

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

# 라우팅 타입 정의
RouteType = Literal[1, 2, 3, 4]


class KnowledgeRouter:
    """지식 라우팅 시스템"""
    
    def __init__(self):
        self.model = OPENAI_ROUTER_MODEL
        
        # 시스템 프롬프트 (라우팅 규칙 정의)
        self.system_prompt = """당신은 질문을 분석하여 어떤 지식 베이스를 사용할지 판단하는 라우터입니다.

**지식 베이스:**
- 불변 지식: 퍼스널 컬러 진단, 봄/여름/가을/겨울 컬러 타입, 메이크업/헤어/스타일링 (기본 원리)
- 가변 지식: 최신 패션 트렌드, Vogue Korea 기사, 시즌별 유행 아이템, 브랜드/컬렉션 정보

**분류 규칙:**

1 = 지식 RAG 불필요
   - 단순 인사, 잡담
   - 퍼스널 컬러나 패션과 무관한 질문
   - 예: "안녕하세요", "날씨가 어때요?", "점심 뭐 먹을까?"

2 = 불변 지식 RAG (퍼스널 컬러 기본 원리)
   - 퍼스널 컬러 타입 설명 요청
   - 색상 진단, 웜톤/쿨톤 특징
   - 퍼스널 컬러별 기본 메이크업/헤어/스타일
   - 예: "봄 웜톤 특징은?", "겨울 쿨톤 메이크업 방법"

3 = 가변 지식 RAG (최신 패션 트렌드)
   - 최신/현재/올해/이번 시즌 트렌드
   - 유행하는 아이템, 컬러, 스타일
   - 특정 브랜드나 컬렉션 정보
   - 예: "2025년 봄 트렌드는?", "요즘 유행하는 가방"

4 = 불변 + 가변 RAG (둘 다 필요)
   - 퍼스널 컬러 + 최신 트렌드 조합
   - 특정 컬러 타입에 맞는 최신 트렌드
   - 예: "봄 웜톤에게 어울리는 2025년 트렌드 립스틱", "여름 쿨톤이 입기 좋은 올해 유행 색상"

**중요:** 반드시 숫자만 출력하세요. 1, 2, 3, 4 중 하나만 응답하세요."""
    
    def route(self, question: str) -> RouteType:
        """
        질문을 라우팅하여 사용할 지식 베이스 결정
        
        Args:
            question: 사용자 질문
            
        Returns:
            1, 2, 3, 4 중 하나
        """
        # 캐싱 활성화 시 동일 질문 재사용
        if ENABLE_ROUTING_CACHE:
            return self._route_cached(question)
        else:
            return self._route_direct(question)
    
    @lru_cache(maxsize=100)
    def _route_cached(self, question: str) -> RouteType:
        """캐시된 라우팅 (동일 질문 반복 시 OpenAI 호출 생략)"""
        return self._route_direct(question)
    
    def _route_direct(self, question: str) -> RouteType:
        """OpenAI API 호출하여 라우팅"""
        try:
            logger.info(f"🤔 라우팅 판단 중: {question[:50]}...")
            
            # OpenAI API 호출
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0,  # 결정론적 출력
                max_tokens=1,   # 숫자 하나만
                timeout=ROUTING_TIMEOUT_SECONDS
            )
            
            # 결과 추출
            result = response.choices[0].message.content.strip()
            
            # 숫자로 변환
            route = int(result)
            
            if route not in [1, 2, 3, 4]:
                raise ValueError(f"잘못된 라우팅 결과: {route}")
            
            # 라우팅 결과 로깅
            route_names = {
                1: "❌ RAG 불필요",
                2: "📚 불변 지식 (퍼스널 컬러)",
                3: "📰 가변 지식 (트렌드)",
                4: "🔀 불변 + 가변"
            }
            
            logger.info(f"✅ 라우팅 결과: {route} - {route_names[route]}")
            
            # 토큰 사용량 로깅
            if hasattr(response, 'usage'):
                logger.info(f"   토큰: 입력 {response.usage.prompt_tokens}, "
                          f"출력 {response.usage.completion_tokens}")
            
            return route
            
        except Exception as e:
            logger.error(f"❌ 라우팅 실패: {e}")
            # 실패 시 기본값: 불변 지식 사용
            logger.warning("⚠️  기본값으로 폴백: 불변 지식 사용")
            return 2
    
    def get_route_description(self, route: RouteType) -> str:
        """라우팅 결과 설명"""
        descriptions = {
            1: "일반 대화 (지식 RAG 미사용)",
            2: "퍼스널 컬러 지식 활용",
            3: "최신 패션 트렌드 지식 활용",
            4: "퍼스널 컬러 + 트렌드 지식 통합 활용"
        }
        return descriptions.get(route, "알 수 없음")


# 싱글톤 인스턴스
_router = None

def get_router() -> KnowledgeRouter:
    """라우터 싱글톤 인스턴스 반환"""
    global _router
    if _router is None:
        _router = KnowledgeRouter()
    return _router
