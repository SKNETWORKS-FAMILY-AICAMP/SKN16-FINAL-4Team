import apiClient from './client';

// TODO: API 전달 후 타입 재정의 필요

/**
 * 사용자 관련 API 타입 정의
 */

export type GenderType = '남성' | '여성';

export interface User {
    id: number;
    username: string;
    nickname: string;
    email: string;
    create_date: string;
    is_active: boolean;
    gender?: GenderType;
}

export interface CreateUserRequest {
    nickname: string
    username: string;
    password: string;
    password_confirm: string;
    email: string;
    gender?: GenderType;
}

export interface LoginRequest {
    // TODO: nickname을 받고 있으나 FastAPI의 OAuth2PasswordRequestForm은 username 필드를 요구하여 username으로 맞춤
    username: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
    user: User;
}

export interface UserStats {
    total_surveys: number;      // 총 진단 기록 수
    saved_results: number;      // 저장된 결과 수
    chat_sessions: number;      // 채팅 세션 수
}

/**
 * 사용자 관련 API 함수들
 */
export const userApi = {
    // 모든 사용자 조회
    getUsers: async (): Promise<User[]> => {
        const response = await apiClient.get<User[]>('/users');
        return response.data;
    },

    // 사용자 생성
    createUser: async (userData: CreateUserRequest): Promise<User> => {
        const response = await apiClient.post<User>('/users/signup', userData);
        return response.data;
    },

    // 로그인
    login: async (credentials: LoginRequest): Promise<LoginResponse> => {
        // OAuth2PasswordRequestForm은 application/x-www-form-urlencoded 형식을 요구
        const formData = new URLSearchParams();
        formData.append('username', credentials.username);
        formData.append('password', credentials.password);

        const response = await apiClient.post<LoginResponse>('/users/login', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        });
        return response.data;
    },

    // 현재 사용자 정보 조회
    getCurrentUser: async (): Promise<User> => {
        const response = await apiClient.get<User>('/users/me');
        return response.data;
    },

    // 사용자 통계 정보 조회
    getUserStats: async (): Promise<UserStats> => {
        const response = await apiClient.get<UserStats>('/users/me/stats');
        return response.data;
    },

    // 현재 사용자 회원탈퇴
    deleteCurrentUser: async (password: string): Promise<{ message: string; detail: string }> => {
        // FormData를 사용하여 비밀번호 전송
        const formData = new URLSearchParams();
        formData.append('password', password);

        const response = await apiClient.delete<{ message: string; detail: string }>('/users/me', {
            data: formData,
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        });
        return response.data;
    },
};