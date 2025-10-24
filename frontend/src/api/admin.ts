import apiClient from "./client";

// 관리자용 유저 리스트
export async function getAdminUserList() {
    const res = await apiClient.get("/users/list");
    if (Array.isArray(res.data)) return res.data;
    if (Array.isArray(res.data.users)) return res.data.users;
    return [];
}

// 관리자용 통합 챗히스토리 엔드포인트 (QA pairs + user_feedback + ai_feedback)
export async function getAdminChatHistoryList(page = 1, page_size = 100) {
    const res = await apiClient.get(`/admin/chat_histories?page=${page}&page_size=${page_size}`);
    // expect { page, page_size, total, items }
    if (res.data && Array.isArray(res.data.items)) return res.data.items;
    // backward compatibility fallbacks
    if (Array.isArray(res.data)) return res.data;
    if (Array.isArray(res.data.chat_histories)) return res.data.chat_histories;
    return [];
}

// 관리자용 AI 피드백 리스트 (원래 엔드포인트 유지)
export async function getAdminAIFeedbackList() {
    const res = await apiClient.get("/feedback/list/ai_feedbacks");
    if (Array.isArray(res.data.ai_feedbacks)) return res.data.ai_feedbacks;
    if (Array.isArray(res.data)) return res.data;
    return [];
}

// 관리자용 유저 권한 변경
export async function changeUserRole(userId: number, newRole: string) {
    const res = await apiClient.patch(`/users/${userId}/role`, { role: newRole });
    return res.data;
}
