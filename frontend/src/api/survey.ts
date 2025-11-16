import apiClient from './client';
import type { PersonalColorType } from '../types/personalColor';

/**
 * 퍼스널 컬러 테스트 관련 API 타입 정의
 */

export interface SurveyAnswer {
  question_id: number;
  option_id: string;
  option_label: string;
}

export interface SurveySubmitRequest {
  answers: SurveyAnswer[];
}

export interface PersonalColorTypeData {
  type: PersonalColorType;
  name: string;
  description: string;
  color_palette: string[];
  style_keywords: string[];
  makeup_tips: string[];
  score: number;
}

export interface SurveySubmitResponse {
  message: string;
  survey_result_id: number;
  result_tone: PersonalColorType;
  confidence: number;
  total_score: number;
  detailed_analysis: string;
  top_types: PersonalColorTypeData[];
  name: string;
  description: string;
  color_palette: string[];
  style_keywords: string[];
  makeup_tips: string[];
  // OpenAI에서 생성된 동적 결과 데이터
  result_data?: {
    type: PersonalColorType;
    name: string;
    description: string;
    characteristics: string[];
    colors: string[];
    makeup_tips: string[];
    style_tips: string[];
  };
}

export interface SurveyResultDetail {
  id: number;
  user_id: number;
  created_at: string;
  result_tone: PersonalColorType;
  confidence: number;
  total_score: number;
  detailed_analysis?: string;
  result_name?: string;
  result_description?: string;
  color_palette?: string[];
  style_keywords?: string[];
  makeup_tips?: string[];
  top_types?: PersonalColorTypeData[];
  answers: SurveyAnswer[];
  // 챗봇 API 응답에서 필요한 추가 필드들
  message?: string;
  survey_result_id?: number;
}

/**
 * 설문 API 클래스
 */
class SurveyApi {
  /**
   * 퍼스널 컬러 테스트 결과 제출
   * PersonalColorTest 컴포넌트의 진단 결과를 백엔드로 전송
   */
  async submitSurvey(
    request: SurveySubmitRequest
  ): Promise<SurveySubmitResponse> {
    console.log('📤 [SurveyApi] submitSurvey 요청:', request);

    try {
      const response = await apiClient.post<SurveySubmitResponse>(
        '/survey/submit',
        request,
        {
          timeout: 60000, // 60초 타임아웃 (OpenAI 분석 시간 고려)
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      console.log('📥 [SurveyApi] submitSurvey 응답:', response.data);
      return response.data;
    } catch (error: any) {
      console.error('❌ [SurveyApi] submitSurvey 오류:', error);

      // 타임아웃 에러 처리
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        throw new Error(
          '분석 시간이 오래 걸리고 있습니다. 잠시 후 다시 시도해주세요.'
        );
      }

      // 네트워크 에러 처리
      if (error.message === 'Network Error') {
        throw new Error('네트워크 연결을 확인해주세요.');
      }

      // 서버 에러 처리
      if (error.response?.status >= 500) {
        throw new Error(
          '서버에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요.'
        );
      }

      // 400번대 에러 처리
      if (error.response?.status >= 400) {
        const errorMessage =
          error.response?.data?.detail || '요청 처리 중 오류가 발생했습니다.';
        throw new Error(errorMessage);
      }

      throw error;
    }
  }

  /**
   * 현재 사용자의 모든 설문 결과 조회 (최신순)
   */
  async getSurveyResults(): Promise<SurveyResultDetail[]> {
    const response = await apiClient.get<SurveyResultDetail[]>('/survey/list');
    return response.data;
  }

  /**
   * 특정 설문 결과 상세 조회
   */
  async getSurveyDetail(surveyId: number): Promise<SurveyResultDetail> {
    const response = await apiClient.get<SurveyResultDetail>(
      `/survey/${surveyId}`
    );
    return response.data;
  }

  /**
   * 설문 결과 삭제 (본인이 작성한 것만)
   */
  async deleteSurvey(surveyId: number): Promise<{ message: string }> {
    const response = await apiClient.delete<{ message: string }>(
      `/survey/${surveyId}`
    );
    return response.data;
  }
}

// API 인스턴스 생성
export const surveyApi = new SurveyApi();
