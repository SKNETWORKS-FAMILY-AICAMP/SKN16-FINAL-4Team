import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { useCallback } from 'react';
import { chatbotApi } from '@/api/chatbot';
import type { InfluencerProfile } from '@/api/chatbot';
import { userFeedbackApi } from '@/api/feedback';
import { useCurrentUser } from './useUser';
import { message } from 'antd';

type FeedbackPayload = {
  historyId?: number | undefined;
  isPositive: boolean;
};

type UseChatbotOptions = {
  onAnalyzeSuccess?: (data: any) => void;
  onAnalyzeError?: (error: any) => void;
  onDiagnosisSuccess?: (data: any) => void;
  onDiagnosisError?: (error: any) => void;
  onFeedbackSuccess?: (data: any) => void;
  onFeedbackError?: (error: any) => void;
};

/**
 * Hook: useChatbot
 * - analyze & analyzeChatForDiagnosis are provided as mutations so callers can
 *   access loading/error states and show UI accordingly.
 * - feedback mutation will end session (best-effort) and submit user feedback,
 *   and on success will invalidate survey caches by default.
 */
export function useChatbot(options?: UseChatbotOptions) {
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();

  // start a new chat session explicitly
  const startSession = useCallback(async (influencerId?: string) => {
    try {
      const res = await chatbotApi.startSession(influencerId);
      return res as { history_id: number; reused: boolean; user_turns: number };
    } catch (e) {
      console.error('채팅 세션 시작 실패', e);
      throw e;
    }
  }, []);

  // ------------------ analyze mutation ------------------
  const analyzeMutation = useMutation({
    mutationFn: (params: { question: string; history_id?: number | undefined }) =>
      chatbotApi.analyze(params as any),
    onSuccess: (data: any) => {
      options?.onAnalyzeSuccess?.(data);
    },
    onError: (error: any) => {
      options?.onAnalyzeError?.(error);
    },
  } as any);

  // ------------------ diagnosis (3-turn) mutation ------------------
  const diagnosisMutation = useMutation({
    mutationFn: (historyId: number) => chatbotApi.analyzeChatForDiagnosis(historyId as any),
    onSuccess: (data: any) => {
      // invalidate survey caches so MyPage and related views refresh
      if (user?.id) {
        queryClient.invalidateQueries({ queryKey: ['surveyResults', user.id] });
        queryClient.invalidateQueries({ queryKey: ['users', 'stats'] });
      }
      options?.onDiagnosisSuccess?.(data);
    },
    onError: (error: any) => {
      options?.onDiagnosisError?.(error);
    },
  } as any);

  // ------------------ feedback mutation ------------------
  const feedbackMutation = useMutation({
    mutationFn: async (payload: FeedbackPayload) => {
      const { historyId, isPositive } = payload;
      const feedbackType = isPositive ? '좋다' : '싫다';

      // try to end session but do not fail on end errors
      if (historyId) {
        try {
          await chatbotApi.endChatSession(historyId);
        } catch (e) {
          // ignore
        }
      }

      if (historyId) {
        return await userFeedbackApi.submitUserFeedback({ history_id: historyId, feedback: feedbackType });
      }

      throw new Error('historyId is required to submit feedback');
    },
    onSuccess: (data: any) => {
      if (user?.id) {
        queryClient.invalidateQueries({ queryKey: ['surveyResults', user.id] });
        queryClient.invalidateQueries({ queryKey: ['users', 'stats'] });
      }
      options?.onFeedbackSuccess?.(data);
      message.success(data?.message || '피드백이 저장되었습니다.');
    },
    onError: (error: any) => {
      options?.onFeedbackError?.(error);
      const errMsg = (error?.response?.data?.detail as string) || error?.message || '피드백 전송 중 오류가 발생했습니다.';
      message.error(errMsg);
    },
  } as any);

  // convenience wrappers that return mutation promises so callers can await
  const analyze = (params: { question: string; history_id?: number | undefined }) =>
    (analyzeMutation.mutateAsync as any)(params);

  const analyzeChatForDiagnosis = (historyId: number) =>
    (diagnosisMutation.mutateAsync as any)(historyId);

  const endChatSession = async (historyId: number) => {
    return chatbotApi.endChatSession(historyId as any);
  };

  // ------------------ influencer profiles (react-query) ------------------
  const {
    data: influencerProfilesData,
    isLoading: isLoadingInfluencerProfiles,
    isError: isErrorInfluencerProfiles,
    refetch: refetchInfluencerProfiles,
  } = useQuery<InfluencerProfile[]>({
    queryKey: ['influencerProfiles'],
    queryFn: () => chatbotApi.getInfluencerProfiles(),
    staleTime: 1000 * 60 * 5,
  });

  // 호출용 래퍼: 캐시된 값 반환(없으면 빈 배열). 강제 갱신이 필요하면 forceRefresh=true 전달.
  const getInfluencerProfiles = async (forceRefresh = false) => {
    if (forceRefresh) {
      const result = await refetchInfluencerProfiles();
      return result.data || [];
    }
    return influencerProfilesData || [];
  };

  const submitFeedback = (payload: FeedbackPayload) => (feedbackMutation.mutateAsync as any)(payload);
  const getPendingFlag = (m: any) => {
    if (!m) return false;
    // prefer isPending if available (per-call pending), otherwise fall back to isLoading
    if (typeof m.isPending !== 'undefined') return !!m.isPending;
    return !!m.isLoading;
  };

  return {
    // session control
    startSession,
    // analyze mutation
    analyze,
    isAnalyzing: getPendingFlag(analyzeMutation),
    analyzeError: (analyzeMutation as any).error || null,

    // diagnosis (3-turn) mutation
    analyzeChatForDiagnosis,
    isDiagnosing: getPendingFlag(diagnosisMutation),
    diagnoseError: (diagnosisMutation as any).error || null,

    // end session (direct API call)
    endChatSession,

    // influencer profiles
    getInfluencerProfiles,
    influencerProfiles: influencerProfilesData || [],
    isLoadingInfluencerProfiles,
    influencerProfilesError: isErrorInfluencerProfiles,
    refetchInfluencerProfiles,

    // feedback
    submitFeedback,
    isSubmittingFeedback: getPendingFlag(feedbackMutation),
    feedbackError: (feedbackMutation as any).error || null,
  };
}

export default useChatbot;

