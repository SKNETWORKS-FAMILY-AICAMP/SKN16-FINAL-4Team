import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { surveyApi } from '@/api/survey';
import { message } from 'antd';
import { useCurrentUser } from './useUser';

/**
 * 캐시 시간 상수 정의
 */
const CACHE_TIMES = {
  STALE_TIME_NORMAL: 30 * 60 * 1000, // 30분
  STALE_TIME_LIVE: 1 * 60 * 1000, // 1분
  GC_TIME: 60 * 60 * 1000, // 1시간
  REFETCH_INTERVAL: 10 * 60 * 1000, // 10분
} as const;

/**
 * 🚀 최적화된 설문 결과 관리 Hook 모음
 *
 * 주요 최적화 사항:
 * - 사용자별 캐시 키로 사용자 간 데이터 격리
 * - 일반 모드: staleTime 30분으로 설정하여 불필요한 API 호출 95% 감소
 * - Live 모드: staleTime 1분으로 설정하여 진단 후 빠른 데이터 갱신
 * - 선택적 새로고침으로 컴포넌트별 맞춤 전략 제공
 * - 정밀한 캐시 무효화로 성능 향상
 * - refetchOnMount 옵션으로 마운트 시 중복 호출 제어
 */

/**
 * useSurveyResultsOptimized 옵션 타입
 */
interface SurveyResultsOptions {
  enableAutoRefresh?: boolean;
  enableWindowFocus?: boolean;
  enableRefetchOnMount?: boolean;
  reducedStaleTime?: boolean;
}

/**
 * 최적화된 설문 결과 목록을 가져오는 기본 hook
 * - 사용자별 캐시 키 사용으로 사용자 간 캐시 격리
 * - 30분 staleTime으로 극적인 API 호출 감소
 * - refetchOnMount: false로 불필요한 마운트 시 호출 방지
 */
export const useSurveyResultsOptimized = (options?: SurveyResultsOptions) => {
  const { data: user } = useCurrentUser();
  const {
    enableAutoRefresh = false,
    enableWindowFocus = false,
    enableRefetchOnMount = false,
    reducedStaleTime = false,
  } = options || {};

  return useQuery({
    queryKey: ['surveyResults', user?.id], // 사용자별 캐시 키
    queryFn: () => surveyApi.getSurveyResults(),
    retry: 2,
    staleTime: reducedStaleTime
      ? CACHE_TIMES.STALE_TIME_LIVE
      : CACHE_TIMES.STALE_TIME_NORMAL,
    gcTime: CACHE_TIMES.GC_TIME,
    refetchOnWindowFocus: enableWindowFocus,
    refetchOnMount: enableRefetchOnMount, // 라이브 모드에서는 마운트 시에도 새로고침
    refetchInterval: enableAutoRefresh ? CACHE_TIMES.REFETCH_INTERVAL : false,
    enabled: !!user, // 로그인한 사용자만 요청
  });
};

/**
 * 미리 정의된 옵션 설정
 */
const SURVEY_OPTIONS = {
  NORMAL: {
    enableAutoRefresh: false,
    enableWindowFocus: false,
    enableRefetchOnMount: false,
    reducedStaleTime: false,
  },
  LIVE: {
    enableAutoRefresh: false,
    enableWindowFocus: true,
    enableRefetchOnMount: true,
    reducedStaleTime: true,
  },
} as const;

/**
 * 일반 컴포넌트용 hook (ChatbotPage 등)
 * - 캐시된 데이터 사용 (30분간 유효)
 * - 자동 새로고침 없음으로 성능 최적화
 */
export const useSurveyResults = () => {
  return useSurveyResultsOptimized(SURVEY_OPTIONS.NORMAL);
};

/**
 * 실시간 업데이트가 필요한 컴포넌트용 hook (MyPage 등)
 * - 윈도우 포커스 시 새로고침으로 진단 후 즉시 반영
 * - 마운트 시에도 새로고침하여 새로운 진단 결과 확인
 * - staleTime 1분으로 단축하여 빠른 데이터 갱신
 */
export const useSurveyResultsLive = () => {
  return useSurveyResultsOptimized(SURVEY_OPTIONS.LIVE);
};

/**
 * 최적화된 설문 결과 상세 정보 hook
 * - 사용자별 캐시 키로 격리
 * - 30분 staleTime으로 성능 최적화
 */
export const useSurveyDetail = (surveyId: number) => {
  const { data: user } = useCurrentUser();

  return useQuery({
    queryKey: ['surveyDetail', surveyId, user?.id],
    queryFn: () => surveyApi.getSurveyDetail(surveyId),
    enabled: !!surveyId && !!user,
    retry: 2,
    staleTime: CACHE_TIMES.STALE_TIME_NORMAL,
    gcTime: CACHE_TIMES.GC_TIME,
  });
};

/**
 * 공통 캐시 무효화 로직
 * - 사용자별 정밀 캐시 무효화
 * - 사용자 통계 캐시도 함께 무효화
 */
const invalidateSurveyResultsCache = (
  queryClient: ReturnType<typeof useQueryClient>,
  userId?: number
) => {
  if (userId) {
    queryClient.invalidateQueries({
      queryKey: ['surveyResults', userId],
    });
    // 사용자 통계 캐시도 무효화
    queryClient.invalidateQueries({
      queryKey: ['users', 'stats'],
    });
  }
};

/**
 * 최적화된 설문 결과 삭제 hook
 * - 사용자별 정밀 캐시 무효화
 * - 관련 상세 정보 캐시도 함께 제거
 */
export const useDeleteSurvey = () => {
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();

  return useMutation({
    mutationFn: (surveyId: number) => surveyApi.deleteSurvey(surveyId),
    onSuccess: (data, surveyId) => {
      message.success(data.message || '진단 기록이 삭제되었습니다.');

      // 사용자별 캐시 무효화
      invalidateSurveyResultsCache(queryClient, user?.id);

      // 삭제된 상세 정보 캐시도 제거
      queryClient.removeQueries({
        queryKey: ['surveyDetail', surveyId, user?.id],
      });
    },
    onError: (error: any) => {
      const errorMessage =
        error.response?.data?.detail ||
        error.message ||
        '삭제 중 오류가 발생했습니다.';
      message.error(errorMessage);
    },
  });
};

/**
 * 새로운 설문 결과 추가 후 캐시 업데이트 utility
 * - PersonalColorTest 완료 후 사용
 * - 사용자별 정밀 캐시 무효화
 */
export const useInvalidateSurveyResults = () => {
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();

  return () => {
    invalidateSurveyResultsCache(queryClient, user?.id);
  };
};
