"""
test_api_color.py - API Color 테스트 스위트 (RAG Service 직접 통합)

테스트:
- 쿼리 구성 함수
- RAG 응답 파싱
- 엔드포인트 (analyze, health)
- 폴백 메커니즘
- 통합 테스트
"""

import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from main import (
    app,
    _compose_query_from_payload,
    _parse_rag_answer_to_color_hints,
    ColorRequest,
)


# ==================== Fixtures ====================

@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_rag_response_success():
    return {
        "success": True,
        "answer": "봄 웜톤은 밝고 따뜻한 색상이 잘 어울립니다. 코랄, 피치 계열의 립스틱을 추천드려요.",
        "route": 2,
        "route_description": "불변 지식 (퍼스널 컬러)",
        "sources": ["immutable_knowledge"],
        "metadata": {"model": "gemini-2.5-flash"}
    }


@pytest.fixture
def mock_rag_response_error():
    return {
        "success": False,
        "answer": "처리 실패",
        "error": "RAG 에러"
    }


# ==================== 쿼리 구성 테스트 ====================

class TestComposeQuery:
    def test_user_text_only(self):
        payload = ColorRequest(user_text="봄 웜톤 추천")
        query = _compose_query_from_payload(payload)
        assert "봄 웜톤" in query

    def test_with_history(self):
        payload = ColorRequest(
            user_text="색상 추천",
            conversation_history=[{"text": "칙칙해요"}]
        )
        query = _compose_query_from_payload(payload)
        assert "색상" in query
        assert "칙칙해요" in query

    def test_with_emotion(self):
        payload = ColorRequest(
            user_text="색상 추천",
            emotion_result={"description": "밝은 기분"}
        )
        query = _compose_query_from_payload(payload)
        assert "밝은 기분" in query

    def test_empty_payload(self):
        payload = ColorRequest()
        query = _compose_query_from_payload(payload)
        assert query == ""


# ==================== RAG 응답 파싱 테스트 ====================

class TestParseRAGAnswer:
    def test_parse_spring_warm(self):
        answer = "봄 웜톤은 밝고 따뜻해요. 코랄, 피치를 추천합니다."
        hints = _parse_rag_answer_to_color_hints(answer, "")
        
        assert hints["primary_tone"] == "웜"
        assert hints["sub_tone"] == "봄"
        assert hints["result_name"] == "봄 웜톤"
        assert "코랄" in hints["recommended_palette"]

    def test_parse_autumn_cool(self):
        answer = "가을 쿨톤의 특징입니다. 와인, 버건디 색상이 어울려요."
        hints = _parse_rag_answer_to_color_hints(answer, "")
        
        # "가을"은 웜톤으로 매핑됨
        assert hints["primary_tone"] == "웜"
        assert hints["sub_tone"] == "가을"

    def test_parse_colors(self):
        answer = "로즈, 베이지, 살구 색상을 추천합니다."
        hints = _parse_rag_answer_to_color_hints(answer, "")
        
        assert "로즈" in hints["recommended_palette"]
        assert "베이지" in hints["recommended_palette"]

    def test_confidence_score(self):
        answer = "웜톤입니다."
        hints = _parse_rag_answer_to_color_hints(answer, "")
        
        assert 0 <= hints["confidence"] <= 1


# ==================== 엔드포인트 테스트 ====================

class TestAnalyzeEndpoint:
    def test_basic_request(self, client, mock_rag_response_success):
        with patch('main.rag_system') as mock_rag:
            mock_rag.query.return_value = mock_rag_response_success
            
            response = client.post(
                "/api/color/analyze",
                json={"user_text": "봄 웜톤 추천"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "detected_color_hints" in data

    def test_with_conversation_history(self, client, mock_rag_response_success):
        with patch('main.rag_system') as mock_rag:
            mock_rag.query.return_value = mock_rag_response_success
            
            response = client.post(
                "/api/color/analyze",
                json={
                    "user_text": "색상 추천",
                    "conversation_history": [{"text": "칙칙해요"}]
                }
            )
            
            assert response.status_code == 200

    def test_missing_input(self, client):
        response = client.post(
            "/api/color/analyze",
            json={}
        )
        
        assert response.status_code == 400

    def test_rag_system_not_initialized(self, client):
        with patch('main.rag_system', None):
            response = client.post(
                "/api/color/analyze",
                json={"user_text": "색상 추천"}
            )
            
            assert response.status_code == 500

    def test_fallback_on_error(self, client, mock_rag_response_error):
        with patch('main.rag_system') as mock_rag:
            mock_rag.query.return_value = mock_rag_response_error
            
            response = client.post(
                "/api/color/analyze",
                json={"user_text": "색상 추천"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["detected_color_hints"]["source"] == "fallback"


class TestHealthEndpoint:
    def test_health_ok(self, client):
        with patch('main.rag_system') as mock_rag:
            mock_rag.immutable_handler.uploaded_files = [1]
            mock_rag.mutable_handler.uploaded_files = [1]
            
            response = client.get("/api/color/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    def test_health_error(self, client):
        with patch('main.rag_system', None):
            response = client.get("/api/color/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"


# ==================== 통합 테스트 ====================

class TestIntegration:
    def test_full_workflow(self, client, mock_rag_response_success):
        with patch('main.rag_system') as mock_rag:
            mock_rag.query.return_value = mock_rag_response_success
            mock_rag.immutable_handler.uploaded_files = [1]
            mock_rag.mutable_handler.uploaded_files = [1]
            
            # 1. 헬스 체크
            health = client.get("/api/color/health")
            assert health.status_code == 200
            
            # 2. 색상 분석
            response = client.post(
                "/api/color/analyze",
                json={
                    "user_text": "봄 웜톤 추천해줘",
                    "conversation_history": [{"text": "칙칙해요"}]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            hints = data["detected_color_hints"]
            
            assert hints["primary_tone"] == "웜"
            assert hints["sub_tone"] == "봄"
            assert "rag_metadata" in hints


# ==================== 엣지 케이스 ====================

class TestEdgeCases:
    def test_long_query(self, client, mock_rag_response_success):
        with patch('main.rag_system') as mock_rag:
            mock_rag.query.return_value = mock_rag_response_success
            
            long_text = "색상 " * 100
            response = client.post(
                "/api/color/analyze",
                json={"user_text": long_text}
            )
            
            assert response.status_code == 200

    def test_special_characters(self, client, mock_rag_response_success):
        with patch('main.rag_system') as mock_rag:
            mock_rag.query.return_value = mock_rag_response_success
            
            response = client.post(
                "/api/color/analyze",
                json={"user_text": "색상 & 추천! @#$%"}
            )
            
            assert response.status_code == 200

    def test_unicode(self, client, mock_rag_response_success):
        with patch('main.rag_system') as mock_rag:
            mock_rag.query.return_value = mock_rag_response_success
            
            response = client.post(
                "/api/color/analyze",
                json={"user_text": "색상 추천해줘 🎨👗"}
            )
            
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
