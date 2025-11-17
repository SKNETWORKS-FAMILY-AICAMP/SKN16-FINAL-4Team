import apiClient from './client';

/**
 * 챗봇 관련 API 타입 정의
 */

export interface ChatbotRequest {
  question: string;
  history_id?: number;
}

export type EmotionType = 'happy' | 'sad' | 'angry' | 'love' | 'fearful' | 'neutral';

export interface ChatResModel {
  primary_tone: string;
  sub_tone: string;
  description: string;
  recommendations: string[];
  emotion: EmotionType;
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
   * 명시적으로 새 채팅 세션을 생성하고 history_id를 반환합니다.
   */
  async startSession(): Promise<{ history_id: number; reused: boolean; user_turns: number }> {
    const response = await apiClient.post(`/chatbot/start`, {});
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
   * 챗봇 대화 내용을 기반으로 진단 저장 (프론트 3턴 후 호출용)
   * 내부적으로 서버의 `/chatbot/report/save` 엔드포인트를 호출합니다.
   */
  async analyzeChatForDiagnosis(
    historyId: number
  ): Promise<{
    survey_result_id?: number;
    message?: string;
    created_at?: string;
    result_tone?: string;
    result_name?: string;
    detailed_analysis?: string;
    color_palette?: string[];
    style_keywords?: string[];
    makeup_tips?: string[];
    report_data?: any;
  }>
  {
    const response = await apiClient.post(`/chatbot/report/save`, {
      history_id: historyId,
    });
    return response.data;
  }
}

// API 인스턴스 생성
export const chatbotApi = new ChatbotApi();
