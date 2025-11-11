import apiClient from './client';
import type { SurveyResultDetail } from './survey';

/**
 * 챗봇 관련 API 타입 정의
 */

export interface ChatbotRequest {
  question: string;
  history_id?: number;
}

export interface ChatResModel {
  primary_tone: string;
  sub_tone: string;
  description: string;
  recommendations: string[];
}

export interface ChatItemModel {
  question_id: number;
  question: string;
  answer: string;
  chat_res: ChatResModel;
}

export interface ChatbotHistoryResponse {
  history_id: number;
  items: ChatItemModel[];
}

/**
 * 챗봇 API 클래스
 */
class ChatbotApi {
  /**
   * 챗봇에게 메시지 전송 및 분석
   */
  async analyze(request: ChatbotRequest): Promise<ChatbotHistoryResponse> {
    const response = await apiClient.post<ChatbotHistoryResponse>(
      '/chatbot/analyze',
      request,
      {
        timeout: 30000, // 30초 타임아웃
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    return response.data;
  }

  /**
   * 채팅 세션 종료
   */
  async endChatSession(
    historyId: number
  ): Promise<{ message: string; ended_at: string }> {
    const response = await apiClient.post<{
      message: string;
      ended_at: string;
    }>(
      `/chatbot/end/${historyId}`,
      {},
      {
        timeout: 10000,
      }
    );
    return response.data;
  }

  /**
   * 채팅 세션 분석하여 진단 결과 저장
   */
  async analyzeChatForDiagnosis(
    historyId: number
  ): Promise<SurveyResultDetail> {
    const response = await apiClient.post<SurveyResultDetail>(
      `/chatbot/analyze/${historyId}`,
      {},
      {
        timeout: 30000, // 분석에 시간이 걸릴 수 있음
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    return response.data;
  }
}

// API 인스턴스 생성
export const chatbotApi = new ChatbotApi();
