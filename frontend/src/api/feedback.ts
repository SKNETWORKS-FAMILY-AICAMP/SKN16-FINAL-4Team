import apiClient from './client';

/**
 * 사용자 피드백 관련 API 타입 정의
 */

export interface UserFeedbackRequest {
  history_id: number;
  feedback: string; // "좋다" 또는 "싫다"
}

export interface UserFeedbackResponse {
  user_feedback_id: number;
  history_id: number;
  user_id: number;
  feedback: string;
}

/**
 * 사용자 피드백 API 클래스
 */
class UserFeedbackApi {
  /**
   * 사용자 피드백 제출 (채팅 세션 종료 후 "좋다"/"싫다" 평가)
   */
  async submitUserFeedback(request: UserFeedbackRequest): Promise<UserFeedbackResponse> {
    const response = await apiClient.post<UserFeedbackResponse>(
      '/feedback/user_feedback',
      request,
      {
        timeout: 10000,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    return response.data;
  }

  /**
   * 특정 채팅 세션의 사용자 피드백 조회
   */
  async getUserFeedback(historyId: number): Promise<UserFeedbackResponse> {
    const response = await apiClient.get<UserFeedbackResponse>(
      `/feedback/user_feedback/${historyId}`,
      {
        timeout: 10000,
      }
    );
    return response.data;
  }
}

// API 인스턴스 생성
export const userFeedbackApi = new UserFeedbackApi();