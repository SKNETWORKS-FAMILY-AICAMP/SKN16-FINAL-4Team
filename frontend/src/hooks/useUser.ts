import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { userApi, type User, type CreateUserRequest, type LoginRequest, type UserStats } from '../api/user';
import { queryKeys } from '../lib/query-client';
import { message } from 'antd';
import { getErrorMessage } from '@/utils/handleApiError';

/**
 * 사용자 목록 조회 훅
 */
export const useUsers = () => {
    return useQuery({
        queryKey: queryKeys.users.lists(),
        queryFn: userApi.getUsers,
        // select: (users: User[]) => users.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    });
};

/**
 * 현재 사용자 정보 조회 훅
 * API 서버에서 현재 사용자 정보를 가져옵니다
 */
export const useCurrentUser = () => {
    return useQuery({
        queryKey: queryKeys.auth.currentUser(),
        queryFn: async () => {
            // API에서 현재 사용자 정보 조회 (localStorage fallback 제거)
            return await userApi.getCurrentUser();
        },
        // 토큰이 있을 때만 요청
        enabled: !!localStorage.getItem('access_token'),
        retry: 1, // API 호출 실패시 1번 재시도
        staleTime: 5 * 60 * 1000, // 5분간 fresh로 간주
    });
};

/**
 * 사용자 통계 정보 조회 훅
 * 진단 기록 수, 저장된 결과 수, 채팅 세션 수를 가져옵니다
 */
export const useUserStats = () => {
    return useQuery({
        queryKey: queryKeys.users.stats(),
        queryFn: userApi.getUserStats,
        // 토큰이 있을 때만 요청
        enabled: !!localStorage.getItem('access_token'),
        retry: 1,
        staleTime: 1 * 60 * 1000, // 1분간 fresh로 간주
    });
};

/**
 * 사용자 생성 뮤테이션 훅
 */
export const useCreateUser = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (userData: CreateUserRequest) => userApi.createUser(userData),
        onSuccess: (newUser: User) => {
            // 사용자 목록 쿼리 무효화 (자동 리페치)
            queryClient.invalidateQueries({ queryKey: queryKeys.users.lists() });

            // 새 사용자를 캐시에 직접 추가 (Optimistic Update)
            queryClient.setQueryData(queryKeys.users.detail(newUser.id), newUser);

            message.success('회원가입이 완료되었습니다.');
        },
        onError: (error: any) => {
            console.error('사용자 생성 실패:', error);

            // 서버에서 보낸 상세 에러 메시지 표시
            const errorMessage = getErrorMessage(error, '회원가입에 실패했습니다.');
            message.error(errorMessage);
        },
    });
};

/**
 * 현재 사용자 회원탈퇴 뮤테이션 훅
 */
export const useDeleteCurrentUser = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ password }: { password: string }) =>
            userApi.deleteCurrentUser(password),
        onSuccess: () => {
            // 로그아웃 처리
            localStorage.removeItem('access_token');

            // 모든 쿼리 캐시 클리어
            queryClient.clear();

            message.success('회원탈퇴가 완료되었습니다.');
        },
        onError: (error: any) => {
            console.error('회원탈퇴 실패:', error);

            // 서버에서 보낸 상세 에러 메시지 표시
            const errorMessage = getErrorMessage(error, '회원탈퇴에 실패했습니다.');
            message.error(errorMessage);
        },
    });
};

/**
 * 로그인 뮤테이션 훅
 */
export const useLogin = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (credentials: LoginRequest) => userApi.login(credentials),
        onSuccess: (response) => {
            // 토큰만 저장 (사용자 정보는 API로 조회)
            localStorage.setItem('access_token', response.access_token);

            // 현재 사용자 정보 캐시에 저장
            queryClient.setQueryData(queryKeys.auth.currentUser(), response.user);

            message.success('로그인 성공!');
        },
        onError: (error: any) => {
            console.error('로그인 실패:', error);

            // 서버에서 보낸 상세 에러 메시지 표시
            const errorMessage = getErrorMessage(error, '로그인에 실패했습니다. 닉네임과 비밀번호를 확인해주세요.');
            message.error(errorMessage);
        },
    });
};

/**
 * 로그아웃 함수
 */
export const useLogout = () => {
    const queryClient = useQueryClient();

    return () => {
        // 토큰 제거
        localStorage.removeItem('access_token');

        // 모든 쿼리 캐시 클리어
        queryClient.clear();

        message.success('로그아웃되었습니다.');
    };
};
