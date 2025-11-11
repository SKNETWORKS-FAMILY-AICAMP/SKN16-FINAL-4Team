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
  Space,
  Modal,
  Tag,
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  ArrowLeftOutlined,
  LikeOutlined,
  DislikeOutlined,
} from '@ant-design/icons';
import { useNavigate, useBeforeUnload, useBlocker } from 'react-router-dom';
import { useCurrentUser } from '@/hooks/useUser';
import { useSurveyResultsLive } from '@/hooks/useSurvey';
import { chatbotApi, type ChatResModel } from '@/api/chatbot';
import { reportApi } from '@/api/report';
import { userFeedbackApi } from '@/api/feedback';
import DiagnosisDetailModal from '@/components/DiagnosisDetailModal';
import type { SurveyResultDetail } from '@/api/survey';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface ChatMessage {
  id: string;
  question?: string;
  content: string;
  customContent?: React.ReactNode;
  isUser: boolean;
  timestamp: Date;
  chatRes?: ChatResModel;
  questionId?: number;
  diagnosisData?: {
    result_name: string;
    detailed_analysis: string;
    color_palette: string[];
    style_keywords: string[];
    makeup_tips: string[];
  };
}

/**
 * 챗봇 페이지 컴포넌트
 * 진단 내역과 관계없이 모든 사용자 접근 가능
 */
const ChatbotPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: user, isLoading: userLoading } = useCurrentUser();
  const { data: surveyResults, isLoading: surveyLoading } = useSurveyResultsLive();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState(false);
  const [isLeavingPage, setIsLeavingPage] = useState(false);
  const [currentHistoryId, setCurrentHistoryId] = useState<number | undefined>(undefined);
  const [userTurnCount, setUserTurnCount] = useState(0); // 사용자 턴 카운트 추가
  const [hasAutoReportGenerated, setHasAutoReportGenerated] = useState(false); // 자동 리포트 생성 여부
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false); // 진단 상세보기 모달
  const [selectedResult, setSelectedResult] = useState<SurveyResultDetail | null>(null); // 선택된 진단 결과
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
    // 초기 환영 메시지일 때는 스크롤하지 않음
    if (messages.length > 1) {
      scrollToBottom();
    }
  }, [messages]);

  // React Router 네비게이션 차단 시 피드백 모달 표시
  useEffect(() => {
    if (blocker.state === 'blocked') {
      setIsFeedbackModalOpen(true);
    }
  }, [blocker.state]);

  // 초기 환영 메시지 설정
  useEffect(() => {
    let welcomeMessage: ChatMessage;

    // 사용자 닉네임 추출 (친밀감 향상)
    const userNickname = `${user?.nickname ?? '사용자'}님`;
    
    if (surveyResults && surveyResults.length > 0) {
      // 과거 진단 내역이 있는 경우
      const latestResult = surveyResults[0];
      welcomeMessage = {
        id: 'welcome',
        content: `안녕하세요, ${userNickname}! 😊 퍼스널컬러 전문 AI 컨설턴트입니다!

이전 진단 결과를 확인해보니 "${latestResult.result_name || latestResult.result_tone.toUpperCase()} 타입"이시네요! 

${userNickname}의 이전 결과를 바탕으로 더 자세한 상담을 도와드릴 수도 있고, 
새롭게 대화를 통해 진단을 다시 받아보셔도 좋습니다! 

퍼스널컬러와 관련된 어떤 것이든 편하게 말씀해 주세요:
✨ 색상 고민이나 궁금한 점
💄 메이크업 팁이나 제품 추천  
👗 옷 색깔이나 스타일링 조언
🌈 새로운 퍼스널컬러 진단
📊 분석 리포트 요청 (리포트 생성해줘!)

어떤 이야기부터 시작해볼까요, ${userNickname}?`,
        isUser: false,
        timestamp: new Date(),
      };
    } else {
      // 진단 내역이 없는 경우 - 대화형 진단 안내
      welcomeMessage = {
        id: 'welcome',
        content: `안녕하세요, ${userNickname}! 😊 퍼스널컬러 전문 AI 컨설턴트입니다!

처음 방문해주셨네요! 반가워요 🎨

저와 자연스러운 대화를 통해 ${userNickname}만의 퍼스널컬러를 찾아보세요!
복잡한 설문지 없이도, 편안한 대화만으로 충분합니다.

이런 것들에 대해 얘기해보면 도움이 될 거예요:
✨ 평소 어떤 색깔 옷을 즐겨 입으시는지
💄 어떤 립스틱이나 블러셔가 잘 어울리는지  
👀 피부톤이나 혈관색에 대한 생각
🌟 좋아하는 스타일이나 색감 취향

어떤 이야기부터 시작해볼까요, ${userNickname}? 
편하게 말씀해 주세요! 😄`,
        isUser: false,
        timestamp: new Date(),
      };
    }

    setMessages(prevMessages => {
      if (prevMessages.length === 0) {
        return [welcomeMessage];
      } else if (prevMessages[0]?.id === 'welcome') {
        return [welcomeMessage, ...prevMessages.slice(1)];
      }
      return prevMessages;
    });
  }, [surveyResults]);

  // 리포트 키워드 확인 함수
  const checkReportKeywords = (message: string): boolean => {
    const reportKeywords = ["레포트", "리포트", "보고서", "결과", "분석", "진단서", "요약"];
    return reportKeywords.some(keyword => message.includes(keyword));
  };

  // 메시지에 리포트 버튼을 표시할지 확인하는 함수
  const shouldShowReportButton = (msg: ChatMessage): boolean => {
    return !msg.isUser && 
           (msg.content.includes("리포트") || msg.content.includes("레포트") || 
            msg.content.includes("분석") || msg.content.includes("요약")) &&
           !!(surveyResults && surveyResults.length > 0);
  };

  // 진단 결과 상세보기 모달 열기
  const handleViewDiagnosisDetail = () => {
    if (surveyResults && surveyResults.length > 0) {
      // 기존 진단 결과
      setSelectedResult(surveyResults[0] as SurveyResultDetail);
      setIsDetailModalOpen(true);
    } else if (userTurnCount >= 3 && messages.length > 0) {
      // 3턴 후 임시 진단 결과 생성
      const lastBotMessage = messages.filter(msg => !msg.isUser && msg.chatRes).pop();
      
      if (lastBotMessage?.chatRes) {
        const tempResult: SurveyResultDetail = {
          id: Date.now(),
          result_tone: (lastBotMessage.chatRes.primary_tone || 'spring') as any,
          result_name: `${lastBotMessage.chatRes.sub_tone || '봄'} ${lastBotMessage.chatRes.primary_tone || '웜'}톤`,
          confidence: 0.85,
          total_score: 85,
          detailed_analysis: lastBotMessage.chatRes.description || '3턴 대화를 통한 분석 결과입니다.',
          color_palette: [],
          style_keywords: lastBotMessage.chatRes.recommendations || [],
          makeup_tips: [],
          answers: [],
          created_at: new Date().toISOString(),
          user_id: user?.id || 0,
          top_types: [{
            type: (lastBotMessage.chatRes.sub_tone?.toLowerCase() || 'spring') as any,
            name: `${lastBotMessage.chatRes.sub_tone || '봄'} ${lastBotMessage.chatRes.primary_tone || '웜'}톤`,
            description: lastBotMessage.chatRes.description || '3턴 대화 분석 결과',
            score: 0.85,
            color_palette: ['#FFB6C1', '#FFA07A', '#FFFF99', '#98FB98', '#87CEEB'],
            style_keywords: lastBotMessage.chatRes.recommendations?.slice(0, 3) || ['밝은', '화사한', '생동감'],
            makeup_tips: ['자연스러운 톤', '코랄 계열 립', '피치 블러셔']
          }]
        };
        
        setSelectedResult(tempResult);
        setIsDetailModalOpen(true);
      } else {
        message.warning('진단 데이터를 찾을 수 없습니다.');
      }
    } else {
      message.warning('아직 충분한 진단 정보가 없습니다. 더 대화해보세요!');
    }
  };

  // 진단 상세보기 모달 닫기
  const handleCloseDetailModal = () => {
    setIsDetailModalOpen(false);
    setSelectedResult(null);
  };

  // 메시지 전송 처리
  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const isReportRequest = checkReportKeywords(inputMessage.trim());
    const userNickname = `${user?.nickname || '사용자'}님`;

    // 현재 상태 디버깅 로그
    console.log('🔍 현재 상태 확인:');
    console.log('  - currentHistoryId:', currentHistoryId);
    console.log('  - surveyResults:', surveyResults);
    console.log('  - surveyResults?.length:', surveyResults?.length);
    console.log('  - isReportRequest:', isReportRequest);
    console.log('  - user:', user);

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
      // 🔥 키워드 감지 시 리포트 요청
      if (isReportRequest) {
        // 3턴 이하인 경우 처리
        if (userTurnCount < 3) {
          // 이전 진단 데이터가 있는지 확인
          if (surveyResults && surveyResults.length > 0) {
            console.log('📊 리포트 키워드 감지, 이전 데이터 있음 - 상세 모달 버튼 노출');
            
            const existingDataMessage: ChatMessage = {
              id: (Date.now() + 1).toString(),
              content: `📊 ${userNickname}의 이전 퍼스널컬러 진단 결과를 찾았어요!

${surveyResults[0].result_name || surveyResults[0].result_tone.toUpperCase()} 타입으로 진단받으셨던 결과를 상세히 확인하실 수 있습니다.

[상세보기]`,
              isUser: false,
              timestamp: new Date(),
            };
            
            setMessages(prev => [...prev, existingDataMessage]);
            setIsTyping(false);
            return;
          } else {
            // 이전 데이터 없음
            console.log('📊 리포트 키워드 감지, 이전 데이터 없음 - 분석을 위해 정보가 더 필요');
            
            const needMoreDataMessage: ChatMessage = {
              id: (Date.now() + 1).toString(),
              content: `${userNickname}, 분석을 위해 정보가 더 필요해요! 📋

퍼스널컬러 진단을 위해 몇 가지 질문에 답변해 주시면, 그 결과로 상세한 분석 리포트를 만들어드릴 수 있어요!

어떤 색깔 옷을 좋아하시는지, 어떤 메이크업이 잘 어울리는지부터 편하게 이야기해보실래요? 🎨`,
              isUser: false,
              timestamp: new Date(),
            };
            
            setMessages(prev => [...prev, needMoreDataMessage]);
            setIsTyping(false);
            return;
          }
        }
        
        // 3턴 이상인 경우 기존 로직 유지
        if (surveyResults && surveyResults.length > 0) {
          console.log('📊 리포트 키워드 감지, 리포트 요청 중...');
          console.log('이전 진단 결과:', surveyResults[0]);
          
          try {
            // 진단 결과 ID 사용 (currentHistoryId가 아님)
            const latestSurveyId = surveyResults[0].id;
            const reportResponse = await reportApi.requestReport(latestSurveyId);
            console.log('✅ 리포트 요청 성공:', reportResponse);
            
            // 리포트 생성 알림 메시지
            const reportNotificationMessage: ChatMessage = {
              id: (Date.now() + 1).toString(),
              content: `📊 ${userNickname}의 ${surveyResults[0].result_name || surveyResults[0].result_tone.toUpperCase()} 타입 분석 리포트를 생성하고 있습니다! 

${reportResponse.message || '기존 진단 결과를 바탕으로 상세한 리포트를 만들고 있어요. 잠시만 기다려주세요...'}

생성이 완료되면 마이페이지에서 확인할 수 있습니다! 📋`,
              isUser: false,
              timestamp: new Date(),
            };
            
            setMessages(prev => [...prev, reportNotificationMessage]);
            setIsTyping(false);
            return; // 일반 챗봇 응답 대신 리포트 요청으로 대체
            
          } catch (reportError: any) {
            console.error('❌ 리포트 요청 실패:', reportError);
            
            // 리포트 생성 실패 메시지
            const reportErrorMessage: ChatMessage = {
              id: (Date.now() + 1).toString(),
              content: `${userNickname}, 리포트 생성 중 오류가 발생했어요 😅

다시 시도해보시거나, 먼저 저와 대화를 통해 새로운 퍼스널컬러 진단을 받아보시는 건 어떨까요? 

새로운 진단 결과가 나오면 더 정확한 리포트를 만들어드릴 수 있습니다! 🎨`,
              isUser: false,
              timestamp: new Date(),
            };
            
            setMessages(prev => [...prev, reportErrorMessage]);
            setIsTyping(false);
            return;
          }
        } else {
          // 3턴 이상이지만 진단 내역이 없어서 리포트 생성 불가
          const noHistoryMessage: ChatMessage = {
            id: (Date.now() + 1).toString(),
            content: `${userNickname}, 아직 저장된 퍼스널컬러 진단 내역이 없어서 리포트를 생성할 수 없어요 😅

방금 전 대화를 통해 분석한 결과가 있다면, 먼저 그 결과를 저장한 후 리포트를 요청해 주세요!

또는 새로운 진단을 진행하실 수도 있어요! 🎨`,
            isUser: false,
            timestamp: new Date(),
          };
          
          setMessages(prev => [...prev, noHistoryMessage]);
          setIsTyping(false);
          return;
        }
      }

      // 일반 챗봇 대화
      const response = await chatbotApi.analyze({
        question: inputMessage.trim(),
        history_id: currentHistoryId,
      });

      console.log('💬 챗봇 응답:', response);
      console.log('🆔 새로운 history_id:', response.history_id);

      setCurrentHistoryId(response.history_id);
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
        
        // 사용자 턴 카운트 증가
        const newTurnCount = userTurnCount + 1;
        setUserTurnCount(newTurnCount);
        
        // 3번 턴 후 자동 요약 레포트 생성
        if (newTurnCount === 3 && !hasAutoReportGenerated && latestItem.chat_res) {
          console.log('🎯 3번 턴 완료! 자동 진단 결과 저장 및 요약 생성 시작...');
          setHasAutoReportGenerated(true);
          
          try {
            // 1. 먼저 진단 결과를 저장하여 마이페이지에 기록 생성
            console.log('💾 진단 결과 저장 중...');
            const diagnosisResult = await chatbotApi.analyzeChatForDiagnosis(response.history_id);
            console.log('✅ 진단 결과 저장 성공:', diagnosisResult);
            
            // 2. 그 다음 리포트 생성 (선택사항)
            try {
              if (diagnosisResult.survey_result_id) {
                const reportResponse = await reportApi.requestReport(diagnosisResult.survey_result_id);
                console.log('✅ 리포트 생성 성공:', reportResponse);
              }
            } catch (reportError) {
              console.log('⚠️ 리포트 생성은 실패했지만 진단 결과는 저장됨:', reportError);
            }
            
            // 요약 리포트 생성 완료 메시지
            const summaryMessage: ChatMessage = {
              id: `diagnosis-summary-${Date.now()}`,
              content: '',
              customContent: (
                <div style={{ padding: '16px' }}>
                  <div style={{ marginBottom: '20px' }}>
                    <div style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '8px', color: '#1a1a1a' }}>
                      🎉 {userNickname}과의 대화를 통해 퍼스널컬러 진단이 완료되었습니다!
                    </div>
                  </div>

                  {/* 퍼스널 타입 정보 - 동적 스타일 적용 */}
                  {(() => {
                    // 결과 타입에 따른 스타일 설정
                    const typeNames: Record<string, { name: string; emoji: string; color: string }> = {
                      spring: { name: '봄 웜톤', emoji: '🌸', color: '#fab1a0' },
                      summer: { name: '여름 쿨톤', emoji: '💎', color: '#a8e6cf' },
                      autumn: { name: '가을 웜톤', emoji: '🍂', color: '#d4a574' },
                      winter: { name: '겨울 쿨톤', emoji: '❄️', color: '#74b9ff' },
                    };

                    // 현재 진단 결과에서 타입 추출
                    const resultTone = diagnosisResult.result_tone || latestItem.chat_res.primary_tone || 'spring';
                    const typeInfo = typeNames[resultTone] || typeNames.spring;

                    return (
                      <div style={{
                        background: `linear-gradient(135deg, ${typeInfo.color}, ${typeInfo.color}aa)`,
                        color: '#000000',
                        padding: '16px',
                        borderRadius: '12px',
                        textAlign: 'center',
                        marginBottom: '16px'
                      }}>
                        <div style={{ 
                          fontSize: '18px', 
                          fontWeight: 'bold', 
                          margin: '0 0 4px 0',
                          color: '#000000'
                        }}>
                          {typeInfo.emoji} {diagnosisResult.result_name || `${latestItem.chat_res.sub_tone} ${latestItem.chat_res.primary_tone}톤`}
                        </div>
                        <div style={{ 
                          fontSize: '13px', 
                          margin: '0',
                          color: '#000000'
                        }}>
                          {diagnosisResult.detailed_analysis?.split('.')[0] + '.' || latestItem.chat_res.description || '당신만의 개성을 살릴 수 있는 퍼스널컬러를 찾았어요!'}
                        </div>
                      </div>
                    );
                  })()}

                  {/* 컬러 팔레트 */}
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ 
                      fontSize: '14px', 
                      fontWeight: 'bold', 
                      marginBottom: '8px',
                      color: '#374151'
                    }}>
                      🎨 당신만의 컬러 팔레트
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {(diagnosisResult.color_palette || ['#ff5722', '#2196f3', '#8bc34a', '#ff9800']).slice(0, 4).map((color: string, index: number) => {
                        const isWhite = color.toLowerCase() === '#ffffff';
                        return (
                          <Tag
                            key={index}
                            style={isWhite ? {
                              backgroundColor: '#f5f5f5',
                              color: '#333333',
                              border: '1px solid #d9d9d9',
                              borderRadius: '4px',
                              padding: '4px 8px',
                              fontSize: '12px',
                              fontWeight: 'bold',
                              margin: '0'
                            } : {
                              backgroundColor: color,
                              color: '#ffffff',
                              border: 'none',
                              borderRadius: '4px',
                              padding: '4px 8px',
                              fontSize: '12px',
                              fontWeight: 'bold',
                              textShadow: '1px 1px 2px rgba(0,0,0,0.5)',
                              margin: '0'
                            }}
                          >
                            {color}
                          </Tag>
                        );
                      })}
                    </div>
                  </div>

                  <div style={{ fontSize: '14px', color: '#6b7280', textAlign: 'center' }}>
                    상세한 분석 결과를 확인해보세요!{' '}
                    <span 
                      style={{
                        color: '#3b82f6',
                        textDecoration: 'underline',
                        cursor: 'pointer',
                        fontWeight: 'bold'
                      }}
                      onClick={() => {
                        if (diagnosisResult) {
                          setSelectedResult(diagnosisResult);
                          setIsDetailModalOpen(true);
                        }
                      }}
                    >
                      [상세보기]
                    </span>
                  </div>
                </div>
              ),
              isUser: false,
              timestamp: new Date(),
              chatRes: latestItem.chat_res, // 진단 결과 데이터 포함
              // 추가 진단 데이터 포함
              diagnosisData: {
                result_name: diagnosisResult.result_name || '',
                detailed_analysis: diagnosisResult.detailed_analysis || '',
                color_palette: diagnosisResult.color_palette || [],
                style_keywords: diagnosisResult.style_keywords || [],
                makeup_tips: diagnosisResult.makeup_tips || []
              }
            };
            
            setTimeout(() => {
              setMessages(prev => [...prev, summaryMessage]);
            }, 1000); // 1초 딜레이로 자연스러운 흐름
            
          } catch (diagnosisError: any) {
            console.error('❌ 진단 결과 저장 실패:', diagnosisError);
            
            const summaryErrorMessage: ChatMessage = {
              id: (Date.now() + 2).toString(),
              content: `🎉 ${userNickname}과의 대화를 통해 퍼스널컬러 분석이 완료되었습니다!

📊 **퍼스널컬러 분석 요약**

🎨 **퍼스널 타입**: ${latestItem.chat_res.sub_tone ? `${latestItem.chat_res.sub_tone} 타입` : '퍼스널컬러 타입'}

� **타입 특성**: ${latestItem.chat_res.description || '당신만의 개성을 살릴 수 있는 퍼스널컬러를 찾았어요!'}

🌈 **추천 컬러 팔레트**: 
🎨 #FFB6C1 🎨 #FFA07A 🎨 #FFFF99 🎨 #98FB98 🎨 #87CEEB

상세한 분석 결과와 맞춤 추천을 확인해보세요!

[상세보기]`,
              isUser: false,
              timestamp: new Date(),
              chatRes: latestItem.chat_res, // 진단 결과 데이터 포함
            };
            
            setTimeout(() => {
              setMessages(prev => [...prev, summaryErrorMessage]);
            }, 1000);
          }
        }
      }
    } catch (error: any) {
      console.error('챗봇 메시지 전송 오류:', error);
      let errorContent = '죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
      let errorTitle = '메시지 전송 실패';

      if (error.response) {
        const status = error.response.status;
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
            errorContent = '서버에 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
            break;
        }
      } else if (error.request) {
        errorContent = '서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.';
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

    try {
      await handleEndChatSession();

      if (currentHistoryId) {
        await userFeedbackApi.submitUserFeedback({
          history_id: currentHistoryId,
          feedback: feedbackType,
        });
      }

      // 세션 종료 시 플래그 초기화
      
      setIsFeedbackModalOpen(false);
      setIsLeavingPage(true);
      message.success(`피드백 감사합니다!`, 2);

      if (blocker.state === 'blocked') {
        blocker.proceed();
      } else {
        setTimeout(() => navigate('/'), 500);
      }
    } catch (error) {
      console.error('피드백 제출 중 오류:', error);
      message.error('피드백 제출 중 오류가 발생했습니다.');
      
      // 오류 시에도 플래그 초기화
      
      setIsFeedbackModalOpen(false);
      setIsLeavingPage(true);

      if (blocker.state === 'blocked') {
        blocker.proceed();
      } else {
        setTimeout(() => navigate('/'), 500);
      }
    }
  };

  // 피드백 모달 닫기 (피드백 없이 나가기)
  const handleCloseFeedbackModal = async () => {
    await handleEndChatSession();
    
    // 세션 종료 시 플래그 초기화
    
    setIsFeedbackModalOpen(false);
    setIsLeavingPage(true);

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
        <Card className="shadow-xl border-0 max-w-md" style={{ borderRadius: '16px' }}>
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

  // 샘플 질문 데이터 (진단 내역 유무에 따라 분기)
  const sampleQuestions = (!surveyResults || surveyResults.length === 0) ? [
    { label: '퍼스널컬러 진단받기', question: '안녕하세요! 저는 어떤 퍼스널컬러 타입일까요?' },
    { label: '색상 고민 상담', question: '평소에 밝은 색 옷을 많이 입는 편인데, 저한테 어울리나요?' },
    { label: '피부톤 고민', question: '피부톤에 대해 잘 모르겠어요. 어떻게 알 수 있을까요?' },
    { label: '색상 조화 고민', question: '제가 좋아하는 색깔과 잘 어울리는 색깔이 다른 것 같아요.' }
  ] : [
    { label: '립스틱 색상 추천', question: '내 퍼스널컬러에 어울리는 립스틱 색상을 추천해주세요.' },
    { label: '계절별 코디', question: '지금 계절에 어울리는 옷 색깔 조합을 알려주세요.' },
    { label: '새 진단 받기', question: '퍼스널컬러 타입 진단을 다시 받아보고 싶어요.' },
    { label: '타입 비교 분석', question: '내 타입의 특징과 다른 타입과의 차이점을 알려주세요.' }
  ];

  // 메인 화면 렌더링
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 pt-4 pb-4">
      <div className="max-w-6xl mx-auto px-4 h-[90vh] flex flex-col">
        {/* 헤더 */}
        <div className="flex items-center justify-between mb-4 flex-shrink-0">
          <div className="flex items-center">
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={handleGoBack}
              className="mr-4"
            />
            <div className="flex flex-col gap-1">
              <Title level={3} className="!mb-0">
                퍼스널컬러 AI 챗봇
              </Title>
              <Text className="!text-gray-500 !text-sm">
                대화를 통해 AI가 당신의 퍼스널컬러를 분석해드립니다. 편하게 대화해보세요!
              </Text>
            </div>
          </div>
          <Button type="default" onClick={() => navigate('/mypage')}>
            진단 기록 보기
          </Button>
        </div>

        {/* 채팅 영역 */}
        <Card
          className="shadow-lg border-0 flex-1 flex flex-col"
          style={{ borderRadius: '16px', minHeight: 0 }}
          styles={{ body: {
            padding: '16px', height: '100%', display: 'flex', flexDirection: 'column'
          }}}
        >
          {/* 메시지 목록 */}
          <div className="flex-1 overflow-y-auto mb-3 p-3 bg-gray-50 rounded-lg" style={{ minHeight: '400px' }}>
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`flex mb-3 ${msg.isUser ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`flex max-w-lg items-start ${msg.isUser ? 'flex-row-reverse' : 'flex-row'}`}
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
                    {/* 메시지 내용 렌더링 - customContent 또는 일반 content */}
                    {msg.customContent ? (
                      msg.customContent
                    ) : msg.content.includes('[상세보기]') ? (
                      <div>
                        {/* 컬러 팔레트가 포함된 진단 결과 메시지인지 확인 */}
                        {msg.content.includes('🌈 **추천 컬러 팔레트**') && msg.diagnosisData ? (
                          <div>
                            {/* 메인 텍스트 (컬러 팔레트 부분 제외) */}
                            <Text
                              className={`whitespace-pre-wrap ${msg.isUser ? '!text-white' : '!text-gray-800'}`}
                            >
                              {msg.content.split('🌈 **추천 컬러 팔레트**')[0]}
                            </Text>
                            
                            {/* 컬러 팔레트 시각적 표시 */}
                            <div className="mt-3">
                              <Text strong className="block mb-2 !text-gray-700">
                                🌈 추천 컬러 팔레트
                              </Text>
                              <div className="flex flex-wrap gap-2 mb-3">
                                {msg.diagnosisData.color_palette && msg.diagnosisData.color_palette.length > 0 ? 
                                  msg.diagnosisData.color_palette.map((color: string, index: number) => (
                                    <div key={index} className="flex items-center gap-1">
                                      <div
                                        className="w-6 h-6 rounded-full border border-gray-300"
                                        style={{ backgroundColor: color }}
                                        title={color}
                                      />
                                      <Text className="text-xs text-gray-600">{color}</Text>
                                    </div>
                                  )) : (
                                    <>
                                      <div className="flex items-center gap-1">
                                        <div className="w-6 h-6 rounded-full border border-gray-300" style={{ backgroundColor: '#FFB6C1' }} />
                                        <Text className="text-xs text-gray-600">#FFB6C1</Text>
                                      </div>
                                      <div className="flex items-center gap-1">
                                        <div className="w-6 h-6 rounded-full border border-gray-300" style={{ backgroundColor: '#FFA07A' }} />
                                        <Text className="text-xs text-gray-600">#FFA07A</Text>
                                      </div>
                                      <div className="flex items-center gap-1">
                                        <div className="w-6 h-6 rounded-full border border-gray-300" style={{ backgroundColor: '#FFFF99' }} />
                                        <Text className="text-xs text-gray-600">#FFFF99</Text>
                                      </div>
                                      <div className="flex items-center gap-1">
                                        <div className="w-6 h-6 rounded-full border border-gray-300" style={{ backgroundColor: '#98FB98' }} />
                                        <Text className="text-xs text-gray-600">#98FB98</Text>
                                      </div>
                                      <div className="flex items-center gap-1">
                                        <div className="w-6 h-6 rounded-full border border-gray-300" style={{ backgroundColor: '#87CEEB' }} />
                                        <Text className="text-xs text-gray-600">#87CEEB</Text>
                                      </div>
                                    </>
                                  )
                                }
                              </div>
                            </div>
                            
                            {/* 나머지 텍스트 */}
                            <Text
                              className={`whitespace-pre-wrap ${msg.isUser ? '!text-white' : '!text-gray-800'}`}
                            >
                              {msg.content.split('🌈 **추천 컬러 팔레트**')[1]?.replace(/🎨 #[A-Fa-f0-9]{6}/g, '').replace('[상세보기]', '').trim()}
                            </Text>
                          </div>
                        ) : (
                          <Text
                            className={`whitespace-pre-wrap ${msg.isUser ? '!text-white' : '!text-gray-800'}`}
                          >
                            {msg.content.replace('[상세보기]', '')}
                          </Text>
                        )}
                        <div className="mt-3">
                          <Button
                            type="primary"
                            size="small"
                            onClick={handleViewDiagnosisDetail}
                            className="bg-purple-500 hover:bg-purple-600 border-purple-500 hover:border-purple-600"
                          >
                            📊 상세보기
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <Text
                        className={`whitespace-pre-wrap ${msg.isUser ? '!text-white' : '!text-gray-800'}`}
                      >
                        {msg.content}
                      </Text>
                    )}

                    <div className="text-xs mt-1 opacity-70 flex justify-between items-center">
                      {/* 리포트 관련 메시지에 리포트 상세보기 버튼 추가 */}
                      {shouldShowReportButton(msg) && (
                        <Button
                          type="default"
                          size="small"
                          onClick={handleViewDiagnosisDetail}
                          className="border-purple-300 text-purple-600 hover:border-purple-500 hover:text-purple-700"
                        >
                          🎨 진단 결과
                        </Button>
                    )}
                      {formatKoreanDate(msg.timestamp, true)}
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {/* 타이핑 인디케이터 */}
            {isTyping && (
              <div className="flex justify-start mb-3">
                <div className="flex items-start">
                  <Avatar
                    icon={<RobotOutlined />}
                    style={{ backgroundColor: '#8b5cf6', flexShrink: 0 }}
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

            {/* 스크롤 위치 참조점 - 항상 메시지 목록의 가장 아래에 위치 */}
            <div ref={messagesEndRef} />
          </div>

          {/* 샘플 질문 */}
          <div className="mb-2 flex-shrink-0">
            <Text strong className="!text-gray-700 block mb-1 text-xs">
              {(!surveyResults || surveyResults.length === 0) 
                ? '💡 이런 대화로 시작해보세요!' 
                : '💡 이런 질문은 어떠세요?'
              }
            </Text>
            <div className="flex flex-wrap gap-1">
              {sampleQuestions.map((item, index) => (
                <Button
                  key={index}
                  size="small"
                  onClick={() => handleSampleQuestion(item.question)}
                  className="text-xs h-6 px-2"
                  style={{ fontSize: '11px' }}
                >
                  {item.label}
                </Button>
              ))}
            </div>
          </div>

          {/* 입력 영역 */}
          <div className="flex gap-2 flex-shrink-0">
            <TextArea
              value={inputMessage}
              onChange={e => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={(!surveyResults || surveyResults.length === 0)
                ? '퍼스널컬러에 대해 궁금한 것을 자유롭게 말씀해주세요...'
                : '퍼스널컬러에 대해 궁금한 것을 물어보세요...'
              }
              autoSize={{ minRows: 1, maxRows: 2 }}
              disabled={isTyping}
              style={{ fontSize: '14px' }}
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
                  background: 'linear-gradient(135deg, #52c41a 0%, #389e0d 100%)',
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
                style={{ borderRadius: '10px', minWidth: '120px' }}
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

        {/* 진단 결과 상세보기 모달 */}
        <DiagnosisDetailModal
          open={isDetailModalOpen}
          onClose={handleCloseDetailModal}
          selectedResult={selectedResult}
          showDeleteButton={false} // 챗봇에서는 삭제 버튼 숨김
        />
      </div>
    </div>
  );
};

export default ChatbotPage;