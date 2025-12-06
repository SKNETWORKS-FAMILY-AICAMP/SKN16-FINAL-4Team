import axios, {
  type AxiosInstance,
  type AxiosResponse,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios';

/**
 * API 클라이언트 설정
 * - 기본 URL과 타임아웃 설정
 * - 요청/응답 인터셉터
 * - 에러 핸들링
 */

// 환경변수에서 API 설정 가져오기
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const API_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT) || 60000; // 60초로 증가

// Axios 인스턴스 생성
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 요청 전 로깅 (개발 환경에서만)
    if (import.meta.env.DEV) {
      console.log(
        `🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`
      );
    }

    // 토큰이 있다면 헤더에 추가
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error: AxiosError) => {
    console.error('❌ Request Error:', error);
    return Promise.reject(error);
  }
);

// 응답 인터셉터
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // 응답 성공 로깅 (개발 환경에서만)
    if (import.meta.env.DEV) {
      console.log(`✅ API Response: ${response.status} ${response.config.url}`);
    }
    return response;
  },
  (error: AxiosError) => {
    // 에러 응답 처리
    console.error('❌ Response Error:', error.response?.status, error.message);

    // 422 Validation Error 상세 정보 로깅
    if (error.response?.status === 422) {
      console.error('❌ Validation Error Details:', error.response?.data);
    }

    // 401 에러 시 토큰 제거 및 로그인 페이지로 리다이렉트
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      // 필요시 로그인 페이지로 리다이렉트
      // window.location.href = '/login';
    }

    return Promise.reject(error);
  }
);

export default apiClient;
