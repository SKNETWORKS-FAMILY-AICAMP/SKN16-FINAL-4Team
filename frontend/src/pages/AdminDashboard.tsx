import React, { useEffect, useState } from "react";
import { Tabs, Table, Spin, message, Card, Typography, Button, Drawer, Descriptions, Select, Tag } from "antd";
import type { TabsProps } from "antd";
import { getAdminUserList, getAdminChatHistoryList, changeUserRole } from "../api/admin";
import { formatKoreanDate } from '@/utils/dateUtils';

const { Title } = Typography;

const AdminDashboard: React.FC = () => {
    // Drawer Tabs 활성 탭 상태
    const [drawerActiveTabKey, setDrawerActiveTabKey] = useState<string>('0');
    // 유저 리스트 테이블 컬럼
    const userColumns = [
        { title: "ID", dataIndex: "id", key: "id" },
        { title: "닉네임", dataIndex: "nickname", key: "nickname" },
        { title: "이메일", dataIndex: "email", key: "email" },
        { title: "성별", dataIndex: "gender", key: "gender" },
        { title: "가입일", dataIndex: "create_date", key: "create_date", render: (text: string) => formatKoreanDate(text, true) },
        {
            title: "권한",
            dataIndex: "role",
            key: "role",
            render: (role: string) => <b>{role}</b>,
        },
        {
            title: "권한변경",
            key: "role_edit",
            width: 250,
            render: (_: any, record: any) => {
                const isEditing = roleEditUserId === record.id;
                return (
                    <>
                        {isEditing ? (
                            <span>
                                <Select
                                    value={roleEditValue || record.role}
                                    style={{ marginRight: 8, minWidth: 80 }}
                                    onChange={v => setRoleEditValue(v)}
                                    options={[{ value: "user", label: "user" }, { value: "admin", label: "admin" }]}
                                    disabled={roleEditLoading}
                                />
                                <Button
                                    type="primary"
                                    size="small"
                                    loading={roleEditLoading}
                                    onClick={() => handleRoleChange(record.id, roleEditValue || record.role)}
                                    disabled={roleEditValue === record.role}
                                >저장</Button>
                                <Button
                                    size="small"
                                    style={{ marginLeft: 4 }}
                                    onClick={() => { setRoleEditUserId(null); setRoleEditValue(""); }}
                                    disabled={roleEditLoading}
                                >취소</Button>
                            </span>
                        ) : (
                            <Button
                                type="link"
                                size="small"
                                style={{ padding: 0, height: 22 }}
                                onClick={() => { setRoleEditUserId(record.id); setRoleEditValue(record.role); }}
                            >권한변경</Button>
                        )}
                    </>
                );
            },
        },
    ];
    // 권한 변경 상태 관리
    const [roleEditUserId, setRoleEditUserId] = useState<number | null>(null);
    const [roleEditValue, setRoleEditValue] = useState<string>("");
    const [roleEditLoading, setRoleEditLoading] = useState(false);

    // 권한 변경 API 호출 함수
    const handleRoleChange = async (userId: number, newRole: string) => {
        setRoleEditLoading(true);
        try {
            const data = await changeUserRole(userId, newRole);
            if (data.success) {
                message.success(data.message || "권한 변경 완료");
                setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, role: newRole } : u));
            } else {
                message.error(data.message || "권한 변경 실패");
            }
        } catch (err) {
            message.error("권한 변경 중 오류 발생");
        } finally {
            setRoleEditUserId(null);
            setRoleEditLoading(false);
        }
    };
    const [loading, setLoading] = useState(false);
    const [users, setUsers] = useState<any[]>([]);
    const [chatHistories, setChatHistories] = useState<any[]>([]);
    const [aiFeedbacks, setAIFeedbacks] = useState<any[]>([]);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [drawerQAPairs, setDrawerQAPairs] = useState<any[]>([]);

    useEffect(() => {
        setLoading(true);
        Promise.all([
            getAdminUserList(),
            getAdminChatHistoryList(),
        ])
            .then(([userRes, chatRes]) => {
                setUsers(userRes);
                setChatHistories(chatRes);
                // derive aiFeedbacks flattened from chat histories
                const flattened: any[] = [];
                (chatRes || []).forEach((h: any) => {
                    (h.qa_pairs || []).forEach((qa: any) => {
                        if (qa.ai_feedback) {
                            flattened.push({
                                history_id: h.chat_history_id,
                                answer_id: qa.answer_id,
                                ...qa.ai_feedback,
                            });
                        }
                    });
                });
                setAIFeedbacks(flattened);
            })
            .catch(() => message.error("관리자 데이터 로드 실패"))
            .finally(() => setLoading(false));
    }, []);

    // qa_paris 답변 구조 표 렌더 함수
    // The backend now returns `answer` as an object (parsed JSON or wrapped { text }).
    // Render structured fields if present (primary_tone, sub_tone, recommendations),
    // otherwise fall back to description or text fields.
    const renderQaParisAnswerTable = (answerObj: any) => {
        if (!answerObj || typeof answerObj !== 'object') return null;
        const { primary_tone, sub_tone, description, recommendations, text } = answerObj as any;
        // prefer primary/sub tone layout if available
        if (primary_tone || sub_tone || recommendations) {
            return (
                <Descriptions bordered column={1} size="middle" style={{ marginBottom: 12 }}>
                    {primary_tone && <Descriptions.Item label="추천 톤">{primary_tone}</Descriptions.Item>}
                    {sub_tone && <Descriptions.Item label="서브 톤">{sub_tone}</Descriptions.Item>}
                    {description && <Descriptions.Item label="설명">{description}</Descriptions.Item>}
                    {recommendations && (
                        <Descriptions.Item label="추천">
                            <ul style={{ margin: 0 }}>
                                {Array.isArray(recommendations) && recommendations.map((rec: string, idx: number) => (
                                    <li key={idx}>- {rec}</li>
                                ))}
                            </ul>
                        </Descriptions.Item>
                    )}
                </Descriptions>
            );
        }
        // fallback: show description or text
        const body = description ?? text ?? null;
        if (body) {
            return (
                <Descriptions bordered column={1} size="middle">
                    <Descriptions.Item label="답변">
                        <span style={{ color: '#1769aa', fontWeight: 600, whiteSpace: 'pre-line' }}>{body}</span>
                    </Descriptions.Item>
                </Descriptions>
            );
        }
        return null;
    };
    // 탭 변경 시 Drawer와 관련 상태 초기화
    const handleTabChange = () => {
        setDrawerOpen(false);
        setDrawerQAPairs([]);
        setDrawerActiveTabKey('0');
    };
    const chatColumns = [
        { title: "히스토리ID", dataIndex: "chat_history_id", key: "chat_history_id" },
        { title: "유저ID", dataIndex: "user_id", key: "user_id" },
        { title: "시작", dataIndex: "created_at", key: "created_at", render: (text: string) => formatKoreanDate(text, true) },
        { title: "종료", dataIndex: "ended_at", key: "ended_at", render: (text: string) => formatKoreanDate(text, true) },
        {
            title: "피드백",
            dataIndex: ["user_feedback", "feedback"],
            key: "feedback",
            render: (_: any, record: any) => {
                const feedback = record.user_feedback?.feedback;
                if (!feedback) return <Tag color="default">없음</Tag>;
                if (feedback === "좋다") return <Tag color="green">좋다</Tag>;
                if (feedback === "싫다") return <Tag color="red">싫다</Tag>;
                return <Tag>{feedback}</Tag>;
            },
        },
        {
            title: "Q/A 요약",
            key: "qa_summary",
            render: (_: any, record: any) => {
                const qa = record.qa_pairs?.[0];
                if (!qa) return "-";
                const toText = (ans: any) => {
                    if (!ans && ans !== "") return "";
                    if (typeof ans === 'string') return ans;
                    if (typeof ans === 'object') return ans.description ?? ans.text ?? JSON.stringify(ans);
                    return String(ans);
                };
                const truncate = (text: string, len: number) => text && text.length > len ? text.slice(0, len) + "..." : text;
                const answerText = toText(qa.answer);
                return (
                    <span>
                        <b>Q:</b> {truncate(qa.question, 20)} <b>A:</b> {truncate(answerText, 20)}
                    </span>
                );
            },
        },
        {
            title: "상세보기",
            key: "qa_detail",
            render: (_: any, record: any) => (
                <Button
                    type="primary"
                    size="small"
                    disabled={!Array.isArray(record.qa_pairs) || record.qa_pairs.length === 0}
                    onClick={() => {
                        // 현재 챗봇 히스토리의 history_id에 해당하는 ai_feedback만 맵핑
                        const feedbacksForHistory = aiFeedbacks.filter((fb: any) => fb.history_id === record.chat_history_id);
                        const mergedQAPairs = record.qa_pairs.map((qa: any) => {
                            const feedback = feedbacksForHistory.find((fb: any) => fb.answer_id === qa.answer_id);
                            return { ...qa, ai_feedback: feedback || null };
                        });
                        setDrawerQAPairs(mergedQAPairs);
                        setDrawerOpen(true);
                        setDrawerActiveTabKey('0');
                    }}
                >상세보기</Button>
            ),
        },
    ];

    const renderAIFeedbackDetail = (fb: any) => (
        <div style={{ fontSize: 15, lineHeight: 1.7 }}>
            <div><span role="img" aria-label="정확도">🎯</span> <b>정확도:</b> {fb.accuracy ?? '-'}<br /><span style={{ color: '#888', fontSize: 13 }}>{fb.detail_accuracy || ''}</span></div>
            <div><span role="img" aria-label="일관성">🔄</span> <b>일관성:</b> {fb.consistency ?? '-'}<br /><span style={{ color: '#888', fontSize: 13 }}>{fb.detail_consistency || ''}</span></div>
            <div><span role="img" aria-label="신뢰도">🔒</span> <b>신뢰도:</b> {fb.reliability ?? '-'}<br /><span style={{ color: '#888', fontSize: 13 }}>{fb.detail_reliability || ''}</span></div>
            <div><span role="img" aria-label="개인화">🧑‍💼</span> <b>개인화:</b> {fb.personalization ?? '-'}<br /><span style={{ color: '#888', fontSize: 13 }}>{fb.detail_personalization || ''}</span></div>
            <div><span role="img" aria-label="실용성">🛠️</span> <b>실용성:</b> {fb.practicality ?? '-'}<br /><span style={{ color: '#888', fontSize: 13 }}>{fb.detail_practicality || ''}</span></div>
            <div><span role="img" aria-label="총점">🏅</span> <b>총점:</b> {typeof fb.total_score === 'number' ? `${fb.total_score}/100` : (fb.total_score ?? '-')}</div>
        </div>
    );


    const items: TabsProps["items"] = [
        {
            key: "users",
            label: "유저 리스트",
            children: <Table rowKey="id" columns={userColumns} dataSource={users} pagination={false} />,
        },
        {
            key: "chat",
            label: "챗봇 히스토리",
            children: (
                <>
                    <Table
                        rowKey="chat_history_id"
                        columns={chatColumns}
                        dataSource={chatHistories}
                        pagination={false}
                    />
                    <Drawer
                        title="질문/답변 상세내역"
                        open={drawerOpen}
                        onClose={() => {
                            setDrawerOpen(false);
                            setDrawerActiveTabKey('0');
                            setDrawerQAPairs([]);
                        }}
                        size={'large'}
                    >
                        {drawerQAPairs.length > 0 && (
                            <Tabs
                                tabPosition="top"
                                items={drawerQAPairs.map((item, idx) => ({
                                    key: String(idx),
                                    label: `Q. ${idx + 1}`,
                                    children: (
                                        <>
                                            <Title level={5}>{item.question}</Title>
                                            <Tabs
                                                tabPosition="top"
                                                items={[
                                                    {
                                                        key: 'answer',
                                                        label: '답변',
                                                        children: (
                                                            <Card style={{ marginBottom: 16, borderRadius: 10, boxShadow: '0 2px 8px #eee' }}>
                                                                {/* Backend now supplies answer as an object; render accordingly */}
                                                                {typeof item.answer === 'object' && item.answer !== null ? (
                                                                    renderQaParisAnswerTable(item.answer)
                                                                ) : (
                                                                    <Descriptions bordered column={1} size="middle">
                                                                        <Descriptions.Item label="답변">
                                                                            <span style={{ color: '#1769aa', fontWeight: 600, whiteSpace: 'pre-line' }}>{item.answer}</span>
                                                                        </Descriptions.Item>
                                                                    </Descriptions>
                                                                )}
                                                                <div style={{ fontSize: 12, color: '#bbb', marginTop: 6, marginBottom: 2 }}>
                                                                    질문ID: {item.question_id} / 답변ID: {item.answer_id}
                                                                </div>
                                                            </Card>
                                                        ),
                                                    },
                                                    {
                                                        key: 'feedback',
                                                        label: 'AI 평가',
                                                        children: (
                                                            <Card style={{ marginBottom: 16, borderRadius: 10, boxShadow: '0 2px 8px #eee' }}>
                                                                {item.ai_feedback ? (
                                                                    <Descriptions bordered column={1} size="middle">
                                                                        <Descriptions.Item label="AI 평가">
                                                                            {renderAIFeedbackDetail(item.ai_feedback)}
                                                                        </Descriptions.Item>
                                                                        <Descriptions.Item label="피드백ID">{item.ai_feedback.id ?? '-'}</Descriptions.Item>
                                                                        <Descriptions.Item label="평가 일시">{item.ai_feedback.created_at ? formatKoreanDate(item.ai_feedback.created_at, true) : '-'}</Descriptions.Item>
                                                                        <Descriptions.Item label="히스토리ID">{item.ai_feedback.history_id ?? '-'}</Descriptions.Item>
                                                                    </Descriptions>
                                                                ) : (
                                                                    <span style={{ color: '#aaa' }}>AI 평가 데이터 없음</span>
                                                                )}
                                                            </Card>
                                                        ),
                                                    },
                                                ]}
                                            />
                                        </>
                                    ),
                                }))}
                                activeKey={drawerActiveTabKey}
                                onChange={key => setDrawerActiveTabKey(key)}
                            />
                        )}
                    </Drawer>
                </>
            ),
        },
    ];
    return (
        <div className="max-w-6xl mx-auto py-8 px-4">
            <Card variant={'outlined'} className="shadow-md rounded-xl">
                <Title level={3} style={{ marginBottom: 24, textAlign: 'center', fontWeight: 700 }}>
                    관리자 대시보드
                </Title>
                {loading ? (
                    <div style={{ textAlign: 'center', padding: '48px 0' }}>
                        <Spin size="large" />
                    </div>
                ) : (
                    <Tabs
                        items={items}
                        tabBarStyle={{ marginBottom: 24 }}
                        type="card"
                        onChange={handleTabChange}
                    />
                )}
            </Card>
        </div>
    );
};

export default AdminDashboard;
