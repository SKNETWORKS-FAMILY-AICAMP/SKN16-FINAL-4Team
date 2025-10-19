import apiClient from './client';

/**
 * 챗봇 관련 API 타입 정의
 */

export interface ChatMessage {
  message: string;
}

export interface ChatResponse {
  response: string;
}

/**
 * 챗봇 API 클래스
 */
class ChatbotApi {
  /**
   * 챗봇에게 메시지 전송
   */
  async sendMessage(message: string): Promise<ChatResponse> {
    const response = await apiClient.post<ChatResponse>(
      '/chatbot/chat',
      { message },
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
   * 사용자의 퍼스널컬러 정보 기반 맞춤 질문
   */
  async getPersonalizedQuestion(): Promise<ChatResponse> {
    const response = await apiClient.get<ChatResponse>(
      '/chatbot/personalized-question',
      {
        timeout: 30000,
      }
    );
    return response.data;
  }
}

// API 인스턴스 생성
export const chatbotApi = new ChatbotApi();
