import apiClient from './client';

export interface ReportData {
  message: string;
  report_data: {
    user_info: {
      analysis_date: string;
      result_type: string;
      confidence: string;
    };
    color_analysis: {
      primary_tone: string;
      description: string;
      detailed_analysis: string;
      key_features: string[];
    };
    color_recommendations: {
      palette_image: string;
      color_codes: string[];
      style_keywords: string[];
      makeup_tips: string[];
    };
    styling_guide: {
      best_colors: string[];
      avoid_colors: string[];
      fashion_tips: string[];
    };
    shopping_tips: string[];
  };
  html_report: string;
  download_available: boolean;
}

export const reportApi = {
  /**
   * 퍼스널 컬러 진단 보고서 생성 요청
   */
  requestReport: async (historyId: number): Promise<{ message: string; status: string }> => {
    const response = await apiClient.post(`/chatbot/report/request`, {
      history_id: historyId
    });
    return response.data;
  },

  /**
   * 퍼스널 컬러 진단 보고서 조회
   */
  getReport: async (historyId: number): Promise<ReportData> => {
    const response = await apiClient.get(`/chatbot/report/${historyId}`);
    return response.data;
  }
};