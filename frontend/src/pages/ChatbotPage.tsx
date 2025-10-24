import React, { useState, useEffect, useRef } from 'react';
import { formatKoreanDate } from '@/utils/dateUtils';
import {
  Card,
  Input,
  Button,
  Typography,
  Spin,
  message,
  Avatar,
  Divider,
  Space,
  Empty,
  Alert,
  Modal,
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  ArrowLeftOutlined,
  BulbOutlined,
  LikeOutlined,
  DislikeOutlined,
} from '@ant-design/icons';
import { useNavigate, useBeforeUnload, useBlocker } from 'react-router-dom';
import { useCurrentUser } from '@/hooks/useUser';
import { useSurveyResultsLive } from '@/hooks/useSurvey';
import { chatbotApi, type ChatResModel } from '@/api/chatbot';
import { userFeedbackApi } from '@/api/feedback';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface ChatMessage {
  id: string;
  question?: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
  chatRes?: ChatResModel;
  questionId?: number;
}

/**
 * 챗봇 페이지 컴포넌트
 * 진단 내역이 있는 사용자만 접근 가능
 */
const ChatbotPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: user, isLoading: userLoading } = useCurrentUser();
  const { data: surveyResults, isLoading: surveyLoading } =
    useSurveyResultsLive();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState(false);
  const [isLeavingPage, setIsLeavingPage] = useState(false);
  const [currentHistoryId, setCurrentHistoryId] = useState<number | undefined>(
    undefined
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 대화가 있는지 확인하는 함수
  const hasConversation = () => messages.length > 1;

  // 페이지 벗어나기 차단 (브라우저 새로고침, 닫기 등)
  useBeforeUnload(
    React.useCallback(
      event => {
        if (hasConversation() && !isLeavingPage) {
          event.preventDefault();
        }
      },
      [messages.length, isLeavingPage]
    )
  );

  // React Router 네비게이션 차단
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      hasConversation() &&
      !isLeavingPage &&
      currentLocation.pathname !== nextLocation.pathname
  );

  // 메시지 스크롤 자동 이동
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // React Router 네비게이션 차단 시 피드백 모달 표시
  useEffect(() => {
    if (blocker.state === 'blocked') {
      setIsFeedbackModalOpen(true);
    }
  }, [blocker.state]);

  // 초기 환영 메시지 설정 및 업데이트
  useEffect(() => {
    if (surveyResults && surveyResults.length > 0) {
      const latestResult = surveyResults[0];
      const welcomeMessage: ChatMessage = {
        id: 'welcome',
        content: `안녕하세요! 🎨 퍼스널컬러 전문 AI 어시스턴트입니다.
        
최근 진단 결과가 "${latestResult.result_name || latestResult.result_tone.toUpperCase()
          } 타입"이시네요!

퍼스널컬러와 관련된 어떤 질문이든 자유롭게 물어보세요:
• 추천 색상 조합
• 메이크업 팁
• 스타일링 조언
• 계절별 코디 추천
• 브랜드별 제품 추천

어떤 도움이 필요하신가요?`,
        isUser: false,
        timestamp: new Date(),
      };

      // 메시지가 없거나, 첫 번째 메시지가 환영 메시지인 경우 업데이트
      setMessages(prevMessages => {
        if (prevMessages.length === 0) {
          return [welcomeMessage];
        } else if (prevMessages[0]?.id === 'welcome') {
          return [welcomeMessage, ...prevMessages.slice(1)];
        }
        return prevMessages;
      });
    }
  }, [surveyResults]);

  // 메시지 전송 처리
  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: inputMessage.trim(),
      isUser: true,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);

    try {
      const response = await chatbotApi.analyze({
        question: inputMessage.trim(),
        history_id: currentHistoryId,
      });

      // 히스토리 ID 업데이트
      setCurrentHistoryId(response.history_id);

      // 최신 아이템 가져오기 (방금 전송한 질문의 응답)
      const latestItem = response.items[response.items.length - 1];

      if (latestItem) {
        const botMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          content: latestItem.answer,
          isUser: false,
          timestamp: new Date(),
          chatRes: latestItem.chat_res,
          questionId: latestItem.question_id,
        };

        setMessages(prev => [...prev, botMessage]);
      }
    } catch (error: any) {
      console.error('챗봇 메시지 전송 오류:', error);

      let errorContent =
        '죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
      let errorTitle = '메시지 전송 실패';

      // 에러 타입별 메시지 분기
      if (error.response) {
        const status = error.response.status;
        console.error('API 응답 에러:', status, error.response.data);

        switch (status) {
          case 400:
            errorContent = '요청이 올바르지 않습니다. 다시 시도해주세요.';
            break;
          case 401:
            errorContent = '로그인이 필요합니다. 다시 로그인해주세요.';
            errorTitle = '인증 실패';
            break;
          case 404:
            errorContent = '채팅 세션을 찾을 수 없습니다. 새로 시작해주세요.';
            break;
          case 500:
            errorContent =
              '서버에 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
            break;
          default:
            errorContent = `서버 오류가 발생했습니다. (${status})`;
        }
      } else if (error.request) {
        console.error('네트워크 에러:', error.request);
        errorContent =
          '서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.';
        errorTitle = '네트워크 오류';
      }

      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: errorContent,
        isUser: false,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
      message.error(errorTitle);
    } finally {
      setIsTyping(false);
    }
  };

  // Enter 키 처리
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 샘플 질문 클릭 처리
  const handleSampleQuestion = (question: string) => {
    setInputMessage(question);
  };

  // 뒤로가기 클릭 시 피드백 모달 표시
  const handleGoBack = () => {
    // 대화가 있는 경우에만 피드백 요청
    if (hasConversation()) {
      setIsFeedbackModalOpen(true);
    } else {
      setIsLeavingPage(true);
      navigate('/');
    }
  };

  // 채팅 세션 종료 처리
  const handleEndChatSession = async () => {
    if (currentHistoryId) {
      try {
        await chatbotApi.endChatSession(currentHistoryId);
        console.log('채팅 세션이 종료되었습니다.');
      } catch (error) {
        console.error('채팅 세션 종료 중 오류:', error);
      }
    }
  };

  // 피드백 선택 처리
  const handleFeedback = async (isPositive: boolean) => {
    const feedbackType = isPositive ? '좋다' : '싫다';
    console.log(`챗봇 사용 피드백: ${feedbackType}`);

    try {
      // 채팅 세션 종료
      await handleEndChatSession();

      // 사용자 피드백 API 호출
      if (currentHistoryId) {
        await userFeedbackApi.submitUserFeedback({
          history_id: currentHistoryId,
          feedback: feedbackType,
        });
        console.log('사용자 피드백이 성공적으로 제출되었습니다.');
      }

      setIsFeedbackModalOpen(false);
      setIsLeavingPage(true);

      message.success(`피드백 감사합니다! (${feedbackType})`, 2);

      // blocker가 있으면 proceed, 없으면 일반 네비게이션
      if (blocker.state === 'blocked') {
        blocker.proceed();
      } else {
        setTimeout(() => {
          navigate('/');
        }, 500);
      }
    } catch (error) {
      console.error('피드백 제출 중 오류:', error);
      message.error('피드백 제출 중 오류가 발생했습니다.');

      // 오류가 발생해도 페이지는 나갈 수 있도록 처리
      setIsFeedbackModalOpen(false);
      setIsLeavingPage(true);

      if (blocker.state === 'blocked') {
        blocker.proceed();
      } else {
        setTimeout(() => {
          navigate('/');
        }, 500);
      }
    }
  };

  // 피드백 모달 닫기 (피드백 없이 나가기)
  const handleCloseFeedbackModal = async () => {
    // 채팅 세션 종료
    await handleEndChatSession();

    setIsFeedbackModalOpen(false);
    setIsLeavingPage(true);

    // blocker가 있으면 proceed, 없으면 일반 네비게이션
    if (blocker.state === 'blocked') {
      blocker.proceed();
    } else {
      navigate('/');
    }
  };

  // 로딩 상태
  if (userLoading || surveyLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 flex items-center justify-center pt-20">
        <Spin size="large" />
      </div>
    );
  }

  // 로그인하지 않은 경우
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 flex items-center justify-center pt-20">
        <Card
          className="shadow-xl border-0 max-w-md"
          style={{ borderRadius: '16px' }}
        >
          <div className="text-center p-8">
            <Title level={3}>로그인이 필요합니다</Title>
            <Text>챗봇을 사용하려면 로그인해주세요.</Text>
            <div className="mt-6">
              <Button type="primary" onClick={() => navigate('/login')}>
                로그인
              </Button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  // 진단 내역이 없는 경우
  if (!surveyResults || surveyResults.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 pt-8 pb-8">
        <div className="max-w-4xl mx-auto px-4">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center">
              <Button
                type="text"
                icon={<ArrowLeftOutlined />}
                onClick={handleGoBack}
                className="mr-4"
              />
              <div className="flex items-center gap-1">
                <Title level={2} className="!mb-0">
                  퍼스널컬러 AI 챗봇
                </Title>
                <Text className="!text-gray-500">
                  당신의 퍼스널컬러 전문 어시스턴트입니다
                </Text>
              </div>
            </div>
            <Button type="default" onClick={() => navigate('/mypage')}>
              진단 기록 보기
            </Button>
          </div>

          {/* 알림 메시지 */}
          <Alert
            message="진단이 필요합니다"
            description="퍼스널컬러 진단을 먼저 완료하시면 맞춤형 상담을 제공받을 수 있습니다."
            type="warning"
            showIcon
            className="mb-6"
          />

          <Card
            className="shadow-lg border-0"
            style={{ borderRadius: '16px', height: '600px' }}
          >
            <div className="h-full flex items-center justify-center">
              <div className="text-center py-12">
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <div>
                      <Title level={4} className="!text-gray-600">
                        진단 내역이 필요합니다
                      </Title>
                      <Text className="!text-gray-500 block mb-6">
                        퍼스널컬러 AI 챗봇을 사용하려면 먼저 퍼스널컬러 진단을
                        완료해주세요.
                        <br />
                        진단 결과를 바탕으로 더 정확하고 개인화된 조언을 제공할
                        수 있습니다.
                      </Text>
                    </div>
                  }
                />
                <Space size="large">
                  <Button
                    type="primary"
                    size="large"
                    onClick={() => navigate('/personal-color-test')}
                    icon={<BulbOutlined />}
                  >
                    퍼스널컬러 진단하기
                  </Button>
                  <Button size="large" onClick={handleGoBack}>
                    홈으로 가기
                  </Button>
                </Space>
              </div>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  // 챗봇 메인 화면
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 pt-8 pb-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* 헤더 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={handleGoBack}
              className="mr-4"
            />
            <div className="flex items-center gap-1">
              <Title level={2} className="!mb-0">
                퍼스널컬러 AI 챗봇
              </Title>
              <Text className="!text-gray-500">
                당신의 퍼스널컬러 전문 어시스턴트입니다
              </Text>
            </div>
          </div>
          <Button type="default" onClick={() => navigate('/mypage')}>
            진단 기록 보기
          </Button>
        </div>

        {/* 알림 메시지 */}
        <Alert
          message="맞춤형 조언 제공"
          description={`[${surveyResults[0].result_name ||
            surveyResults[0].result_tone.toUpperCase()
            }] 타입 기반으로 개인화된 상담을 제공합니다.`}
          type="info"
          showIcon
          className="mb-6"
        />

        {/* 채팅 영역 */}
        <Card
          className="shadow-lg border-0"
          style={{ borderRadius: '16px', height: '600px' }}
        >
          {/* 메시지 목록 */}
          <div className="h-96 overflow-y-auto mb-4 p-4 bg-gray-50 rounded-lg">
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`flex mb-4 ${msg.isUser ? 'justify-end' : 'justify-start'
                  }`}
              >
                <div
                  className={`flex max-w-xs lg:max-w-md items-start ${msg.isUser ? 'flex-row-reverse' : 'flex-row'
                    }`}
                >
                  <Avatar
                    icon={msg.isUser ? <UserOutlined /> : <RobotOutlined />}
                    style={{
                      backgroundColor: msg.isUser ? '#3b82f6' : '#8b5cf6',
                      flexShrink: 0,
                    }}
                    className={msg.isUser ? '!ml-2' : '!mr-2'}
                  />
                  <div
                    className={`px-4 py-2 rounded-lg ${msg.isUser
                        ? 'bg-blue-500 text-white'
                        : 'bg-white border border-gray-200'
                      }`}
                  >
                    <Text
                      className={`whitespace-pre-wrap ${msg.isUser ? '!text-white' : '!text-gray-800'
                        }`}
                    >
                      {msg.content}
                    </Text>

                    {/* AI 응답의 경우 추가 정보 표시 */}
                    {!msg.isUser && msg.chatRes && (
                      <div className="mt-3 pt-3 border-t border-gray-100">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-purple-600">
                              퍼스널 컬러:
                            </span>
                            <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full">
                              {msg.chatRes.primary_tone} -{' '}
                              {msg.chatRes.sub_tone}
                            </span>
                          </div>

                          {msg.chatRes.recommendations &&
                            msg.chatRes.recommendations.length > 0 && (
                              <div>
                                <div className="text-xs font-semibold text-gray-600 mb-1">
                                  🎨 추천사항:
                                </div>
                                <div className="space-y-1">
                                  {msg.chatRes.recommendations.map(
                                    (rec, index) => (
                                      <div
                                        key={index}
                                        className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded border-l-2 border-blue-300"
                                      >
                                        • {rec}
                                      </div>
                                    )
                                  )}
                                </div>
                              </div>
                            )}
                        </div>
                      </div>
                    )}

                    <div className="text-xs mt-1 opacity-70">
                      {formatKoreanDate(msg.timestamp, true)}
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {/* 타이핑 인디케이터 */}
            {isTyping && (
              <div className="flex justify-start mb-4">
                <div className="flex items-start">
                  <Avatar
                    icon={<RobotOutlined />}
                    style={{
                      backgroundColor: '#8b5cf6',
                      flexShrink: 0,
                    }}
                    className="!mr-2"
                  />
                  <div className="bg-white border border-gray-200 px-4 py-2 rounded-lg">
                    <Spin size="small" />
                    <Text className="ml-2 !text-gray-500">
                      답변을 생성하고 있습니다...
                    </Text>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <Divider />

          {/* 샘플 질문 */}
          <div className="mb-4">
            <Text strong className="!text-gray-700 block mb-2">
              💡 이런 질문은 어떠세요?
            </Text>
            <Space wrap>
              <Button
                size="small"
                onClick={() =>
                  handleSampleQuestion(
                    '내 퍼스널컬러에 어울리는 립스틱 색상을 추천해주세요'
                  )
                }
              >
                립스틱 색상 추천
              </Button>
              <Button
                size="small"
                onClick={() =>
                  handleSampleQuestion(
                    '지금 계절에 어울리는 옷 색깔 조합을 알려주세요'
                  )
                }
              >
                계절별 코디
              </Button>
              <Button
                size="small"
                onClick={() =>
                  handleSampleQuestion(
                    '내 퍼스널컬러 타입의 특징과 장점을 설명해주세요'
                  )
                }
              >
                타입 특징 설명
              </Button>
              <Button
                size="small"
                onClick={() =>
                  handleSampleQuestion(
                    '피해야 할 색상이나 메이크업 팁이 있나요?'
                  )
                }
              >
                주의사항
              </Button>
            </Space>
          </div>

          {/* 입력 영역 */}
          <div className="flex gap-2">
            <TextArea
              value={inputMessage}
              onChange={e => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="퍼스널컬러에 대해 궁금한 것을 물어보세요..."
              autoSize={{ minRows: 1, maxRows: 3 }}
              disabled={isTyping}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSendMessage}
              disabled={!inputMessage.trim() || isTyping}
              className="h-auto"
            >
              전송
            </Button>
          </div>
        </Card>

        {/* 피드백 모달 */}
        <Modal
          title="챗봇 사용 만족도"
          open={isFeedbackModalOpen}
          onCancel={handleCloseFeedbackModal}
          footer={null}
          centered
          width={400}
        >
          <div className="text-center py-4">
            <Title level={4} className="mb-4">
              챗봇 서비스는 어떠셨나요?
            </Title>
            <Text className="!text-gray-600 block mb-6">
              더 나은 서비스 제공을 위해 피드백을 남겨주세요.
            </Text>

            <Space size="large">
              <Button
                size="large"
                type="primary"
                icon={<LikeOutlined />}
                onClick={() => handleFeedback(true)}
                style={{
                  background:
                    'linear-gradient(135deg, #52c41a 0%, #389e0d 100%)',
                  border: 'none',
                  borderRadius: '10px',
                  minWidth: '120px',
                }}
              >
                좋음 👍
              </Button>
              <Button
                size="large"
                danger
                icon={<DislikeOutlined />}
                onClick={() => handleFeedback(false)}
                style={{
                  borderRadius: '10px',
                  minWidth: '120px',
                }}
              >
                나쁨 👎
              </Button>
            </Space>

            <div className="mt-4">
              <Button
                type="text"
                onClick={handleCloseFeedbackModal}
                className="!text-gray-500"
              >
                피드백 없이 나가기
              </Button>
            </div>
          </div>
        </Modal>
      </div>
    </div>
  );
};

export default ChatbotPage;
