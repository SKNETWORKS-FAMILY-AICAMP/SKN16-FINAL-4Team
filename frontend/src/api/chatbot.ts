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

export interface InfluencerProfile {
  id: string;
  name: string;
  greeting: string;
  emoji: string;
  color: string;
  subscriber_name: string[];
  closing: string;
  characteristics: string;
  expertise: string[];
  short_description: string;
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

export interface InfluencerHistoryItem {
  influencer_id?: string;
  influencer_name?: string;
  total_sessions?: number;
  total_messages?: number;
  last_activity?: string;
  profile?: InfluencerProfile;
}

export interface InfluencerMessageItem {
  id?: string | number;
  history_id?: number;
  role?: string;
  text?: string;
  created_at?: string;
  raw?: any;
}

/**
 * 챗봇 API 클래스
 */
class ChatbotApi {
  /**
   * 챗봇에게 메시지 전송 및 분석
   */
  async analyze(request: ChatbotRequest): Promise<ChatbotHistoryResponse> {
    try {
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
    } catch (err: any) {
      // Defensive retry: if backend reports that the requested session is already ended
      // (400 with detail '이미 종료된 세션입니다.'), attempt to start a fresh session and retry once.
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail || '';
      if (status === 400 && typeof detail === 'string' && detail.includes('이미 종료된 세션')) {
        try {
          const startResp = await this.startSession();
          const newHistoryId = (startResp as any)?.history_id;
          if (newHistoryId) {
            const retryReq: any = { ...request, history_id: newHistoryId };
            const retryResp = await apiClient.post<ChatbotHistoryResponse>('/chatbot/analyze', retryReq, {
              timeout: 30000,
              headers: { 'Content-Type': 'application/json' },
            });
            return retryResp.data;
          }
        } catch (retryErr) {
          // ignore and fall through to rethrow original error
          console.warn('analyze: retry after startSession failed', retryErr);
        }
      }
      throw err;
    }
  }

  /** Get existing history items for a given history id */
  async getHistory(historyId: number): Promise<ChatbotHistoryResponse> {
    const response = await apiClient.get<ChatbotHistoryResponse>(`/chatbot/history/${historyId}`);
    return response.data;
  }

  /**
   * 명시적으로 새 채팅 세션을 생성하고 history_id를 반환합니다.
   */
  async startSession(influencerId?: string): Promise<{ history_id: number; reused: boolean; user_turns: number }> {
    const body: any = {};
    if (influencerId) {
      // include both keys for backward compatibility: some backend checks influencer_name
      body.influencer_id = influencerId;
      body.influencer_name = influencerId;
    }
    const response = await apiClient.post(`/chatbot/start`, body);
    return response.data;
  }

  /** 서버가 생성한 환영 메시지 가져오기 */
  async getWelcome(influencer?: string): Promise<{ message: string; influencer?: string; has_previous: boolean; previous_summary?: string }>{
    // Deprecated: welcome is handled via analyze({ question: '' }) now.
    // Keep a thin compatibility layer that calls analyze if needed.
    const body: any = { question: '' };
    if (influencer) body.influencer_id = influencer;
    const response = await apiClient.post('/chatbot/analyze', body, {
      headers: { 'Content-Type': 'application/json' },
    });
    return { message: response.data.items?.[0]?.answer || '', influencer: response.data.items?.[0]?.chat_res?.influencer || null, has_previous: false };
  }

  /** 등록된 인플루언서 프로필 목록을 가져옵니다. 실패 시 빈 배열을 반환합니다. */

  /** Get influencer grouped histories (aggregated) */
  async getInfluencerHistories(): Promise<InfluencerHistoryItem[]> {
    try {
      // This endpoint may occasionally be slower; allow a longer timeout here
      const response = await apiClient.get<InfluencerHistoryItem[]>(`/chatbot/history/influencers`, {
        timeout: 60000,
      });
      return response.data;
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('Failed to fetch influencer histories', e);
      return [];
    }
  }

  /** Get all messages for a given influencer across histories */
  async getMessagesForInfluencer(influencerId: string): Promise<InfluencerMessageItem[]> {
    try {
      // Fetch messages for an influencer — allow extra time for aggregation queries
      const response = await apiClient.get<any>(`/chatbot/history/influencer/${encodeURIComponent(influencerId)}`, {
        timeout: 60000,
      });
      const payload = response.data;
      // backend may return { history_ids: [...], items: [...] } or directly an array
      const rawItems: any[] = Array.isArray(payload) ? payload : (payload?.items || payload?.items || payload?.data || []);

      const normalized = rawItems.map((m: any) => {
        const out: InfluencerMessageItem = {
          id: m.id || m.history_id || undefined,
          history_id: m.history_id,
          role: m.role,
          text: m.text,
          created_at: m.created_at,
          raw: m.raw,
        };

        // Normalize raw: if it's a JSON string, try to parse it
        try {
          if (typeof out.raw === 'string') {
            try {
              out.raw = JSON.parse(out.raw);
            } catch (e) {
              // keep as string if parsing fails
            }
          }
        } catch (e) {
          // ignore
        }

        // If raw wasn't present or parsing failed, try to parse the text (legacy records)
        if ((!out.raw || typeof out.raw !== 'object') && out.text && typeof out.text === 'string') {
          const t = out.text.trim();
          if ((t.startsWith('{') || t.startsWith('['))) {
            try {
              const parsed = JSON.parse(t);
              if (parsed && typeof parsed === 'object') {
                out.raw = parsed;
              }
            } catch (e) {
              // ignore
            }
          }
        }

        // Prefer influencer.styled_text -> raw.styled_text -> raw.description -> existing text
        try {
          let finalText = out.text || '';
          const rawObj = out.raw && typeof out.raw === 'object' ? out.raw : null;
          if (rawObj) {
            // influencer may be nested
            const infl = rawObj.influencer;
            if (infl && typeof infl === 'object') {
              const st = infl.styled_text || infl.description || infl?.model_output || null;
              if (typeof st === 'string' && st.trim()) finalText = st;
            }
            if ((!finalText || finalText.trim() === '') && typeof rawObj.styled_text === 'string' && rawObj.styled_text.trim()) {
              finalText = rawObj.styled_text;
            }
            if ((!finalText || finalText.trim() === '') && typeof rawObj.description === 'string' && rawObj.description.trim()) {
              finalText = rawObj.description;
            }
          }
          out.text = finalText;
        } catch (e) {
          // ignore
        }

        return out;
      });

      return normalized;
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('Failed to fetch messages for influencer', influencerId, e);
      return [];
    }
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
    // Report generation can involve heavier processing (OpenAI calls, aggregation).
    // Use an extended timeout for this specific request to avoid client-side aborts.
    const response = await apiClient.post(`/chatbot/report/save`, {
      history_id: historyId,
    }, {
      timeout: 60000,
    });
    return response.data;
  }
}

// API 인스턴스 생성
export const chatbotApi = new ChatbotApi();
