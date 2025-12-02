import React, { useState, useEffect, useRef, useMemo } from 'react';
import { formatKoreanDate } from '@/utils/dateUtils';
import {
  Card,
  Input,
  Button,
  Typography,
  message,
  Avatar,
  Tag,
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { getAvatarRenderInfo } from '@/utils/genderUtils';
import { useNavigate, useBeforeUnload, useBlocker, useLocation } from 'react-router-dom';
import { useCurrentUser } from '@/hooks/useUser';
import { useSurveyResultsLive } from '@/hooks/useSurvey';
import useChatbot from '@/hooks/useChatbot';
import type { ChatResModel } from '@/api/chatbot';
import { chatbotApi } from '@/api/chatbot';
import localInfluencers from '@/data/influencers';
import { convertReportDataToSurveyDetail } from '@/utils/reportUtils';
import { normalizePersonalColor } from '@/utils/personalColorUtils';
import DiagnosisDetailModal from '@/components/DiagnosisDetailModal';
import FeedbackModal from '@/components/FeedbackModal';
import InfluencerProfileModal from '@/components/InfluencerProfileModal';
import type { SurveyResultDetail } from '@/api/survey';
import AnimatedEmoji from '@/components/AnimatedEmoji';
import { Loading } from '@/components';
import InfluencerImage from '@/components/InfluencerImage';

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
  const { data: surveyResults, isLoading: surveyLoading } =
    useSurveyResultsLive();
  const {
    submitFeedback,
    isSubmittingFeedback,
    analyze,
    analyzeChatForDiagnosis,
    endChatSession,
    isAnalyzing,
    isDiagnosing,
    analyzeError,
    diagnoseError,
    startSession,
    // from useChatbot: influencer histories
    influencerHistories,
    fetchMessagesForInfluencer,
  } = useChatbot();
  const sessionStartedRef = useRef(false);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  // description 버블 딜레이 표시용
  const [delayedDescriptions, setDelayedDescriptions] = useState<{ [id: string]: boolean }>({});
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const isBusy = isTyping || isAnalyzing || isDiagnosing;
  const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState(false);
  const [isLeavingPage, setIsLeavingPage] = useState(false);
  const [currentHistoryId, setCurrentHistoryId] = useState<number | undefined>(
    undefined
  );
  const [userTurnCount, setUserTurnCount] = useState(0); // 사용자 턴 카운트 추가
  const [hasAutoReportGenerated, setHasAutoReportGenerated] = useState(false); // 자동 리포트 생성 여부
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false); // 진단 상세보기 모달
  const [selectedResult, setSelectedResult] =
    useState<SurveyResultDetail | null>(null); // 선택된 진단 결과
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const [influencerModalOpen, setInfluencerModalOpen] = useState(false);
  const [activeInfluencerProfile, setActiveInfluencerProfile] = useState<any | null>(null);
  const autoCloseRef = useRef<number | null>(null);

  const location = useLocation();

  // 라우터 state로 전달된 인플루언서 프로필(예: MyPage에서 클릭으로 전달)을 수신
  useEffect(() => {
    try {
      const maybe = (location as any).state?.influencerProfile;
      if (maybe) {
        setActiveInfluencerProfile(maybe);
      }
    } catch (e) {
      // ignore
    }
  }, [location]);

  // When an influencer profile is active, load all previous messages for that influencer
  useEffect(() => {
    if (!activeInfluencerProfile) return;

    let mounted = true;
    (async () => {
      try {
        const inflId = activeInfluencerProfile.id || activeInfluencerProfile.name;
        if (!inflId) return;
        const resp = await fetchMessagesForInfluencer(inflId);
        // resp may be either an array of message items or an object { history_ids, items }
        let items: any[] = [];
        let historyIds: number[] = [];
        if (Array.isArray(resp)) {
          items = resp as any[];
        } else if (resp && typeof resp === 'object') {
          items = (resp as any).items || [];
          historyIds = (resp as any).history_ids || [];
        }

        const loaded: ChatMessage[] = items.map((m: any, idx: number) => {
          const isUser = (m.role || '').toString().toLowerCase() === 'user';
          let chatRes = undefined;
          try {
            if (m.raw) {
              const parsed = typeof m.raw === 'string' ? JSON.parse(m.raw) : m.raw;
              chatRes = parsed;
            }
          } catch (e) {
            chatRes = undefined;
          }
          return {
            id: `infl-${inflId}-${idx}-${m.history_id || ''}`,
            content: m.text || '',
            isUser,
            timestamp: m.created_at ? new Date(m.created_at) : new Date(),
            chatRes,
            questionId: undefined,
          } as ChatMessage;
        });

        if (!mounted) return;

        setMessages(prev => {
          // preserve welcome at index 0 if present
          if (prev.length > 0 && prev[0]?.id === 'welcome') return [prev[0], ...loaded];
          return loaded;
        });

        // if there's no currentHistoryId (no active session), restore the latest history id
        if (!currentHistoryId && Array.isArray(historyIds) && historyIds.length > 0) {
          setCurrentHistoryId(historyIds[historyIds.length - 1]);
        }
      } catch (e) {
        console.warn('인플루언서 메시지 불러오기 실패:', e);
      }
    })();

    return () => {
      mounted = false;
    };
    // only depend on influencer id to avoid re-running when function refs or profile objects change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeInfluencerProfile?.id]);

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


  // 메시지, 타이핑, 딜레이 상태 변경 시 스크롤 자동 이동
  useEffect(() => {
    if (!messagesEndRef.current || !messagesContainerRef.current) return;

    if (messages.length <= 2) return;

    const container = messagesContainerRef.current as HTMLDivElement;

    const isOverflowing = container.scrollHeight > container.clientHeight;

    console.debug('[chat-scroll] messages=', messages.length, 'isTyping=', isTyping, 'overflowing=', isOverflowing);

    if (!isOverflowing) return;

    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
  }, [messages, isTyping, delayedDescriptions]);

  useEffect(() => {
    if (analyzeError) {
      try {
        const errMsg = (analyzeError?.response?.data?.detail as string) || analyzeError?.message || '분석 중 오류가 발생했습니다.';
        message.error(errMsg);
      } catch (e) {
        message.error('분석 중 오류가 발생했습니다.');
      }
    }

    if (diagnoseError) {
      try {
        const errMsg = (diagnoseError?.response?.data?.detail as string) || diagnoseError?.message || '진단 저장 중 오류가 발생했습니다.';
        message.error(errMsg);
      } catch (e) {
        message.error('진단 저장 중 오류가 발생했습니다.');
      }
    }
  }, [analyzeError, diagnoseError]);

  // React Router 네비게이션 차단 시 피드백 모달 표시
  useEffect(() => {
    if (blocker.state === 'blocked') {
      setIsFeedbackModalOpen(true);
    }
  }, [blocker.state]);

  // legacy query/state influencer helpers removed (not used anymore)

  // influencer profiles: hook에서 제공하는 캐시 우선, 없으면 로컬 폴백
  const influencers = (Array.isArray(influencerHistories) && influencerHistories.length > 0)
    ? influencerHistories.map((h: any) => h.profile || { id: h.influencer_id, name: h.influencer_name })
    : localInfluencers;


  // 페이지 진입 시 명시적으로 새 채팅 세션을 시작합니다.
  // 이렇게 하면 이전 세션의 기록이 현재 세션에 섞이지 않고,
  // /end 호출 전까지는 이 세션의 히스토리만 참고하게 됩니다.
  useEffect(() => {
    if (sessionStartedRef.current) return;
    sessionStartedRef.current = true;

    let mounted = true;
    (async () => {
      try {
        const params = new URLSearchParams((location as any).search || window.location.search);
        const inflIdFromQuery = params.get('infl_id');
        const inflNameFromState = (location as any).state?.influencerProfile?.name || activeInfluencerProfile?.name;
        // prefer explicit query param infl_id (slug) if provided
        const startWith = inflIdFromQuery || inflNameFromState;
        const res = await startSession(startWith as any);
        if (mounted) {
          setCurrentHistoryId(res.history_id);
          // 복원 가능한 기존 열린 세션이면 이미 진행된 사용자 턴 수를 복원
          if (res.reused && typeof res.user_turns === 'number') {
            setUserTurnCount(res.user_turns);
            console.log('재사용 세션의 기존 사용자 턴 수 복원:', res.user_turns);
          }
          // If this session reuses existing history, fetch the previous messages
          if (res.reused) {
            try {
              const hist = await chatbotApi.getHistory(res.history_id);
              if (hist && Array.isArray(hist.items) && hist.items.length > 0) {
                // convert items to ChatMessage array (chronological)
                const loaded: ChatMessage[] = [];
                let baseTs = Date.now() - hist.items.length * 2000;
                for (const it of hist.items) {
                  const userMsg: ChatMessage = {
                    id: `h-${res.history_id}-${it.question_id}-u`,
                    content: it.question || '',
                    isUser: true,
                    timestamp: new Date(baseTs),
                  };
                  loaded.push(userMsg);
                  baseTs += 1000;
                  const botMsg: ChatMessage = {
                    id: `h-${res.history_id}-${it.question_id}-b`,
                    content: it.answer || '',
                    isUser: false,
                    timestamp: new Date(baseTs),
                    chatRes: it.chat_res,
                  };
                  loaded.push(botMsg);
                  baseTs += 1000;
                }
                // merge with existing welcome message if present
                setMessages(prev => {
                  // if prev already has welcome at index 0, keep it, otherwise prepend nothing
                  if (prev.length > 0 && prev[0]?.id === 'welcome') return [prev[0], ...loaded];
                  return loaded;
                });
              }
            } catch (e) {
              console.warn('히스토리 불러오기 실패:', e);
            }
          }
          // If this is a fresh session (not reused), request the welcome via analyze
          if (!res.reused) {
            try {
              const welcomeResp = await analyze({ question: '', history_id: res.history_id });
              const loaded: ChatMessage[] = [];
              if (welcomeResp && Array.isArray(welcomeResp.items) && welcomeResp.items.length > 0) {
                let baseTs = Date.now();
                for (const it of welcomeResp.items) {
                  const botMsg: ChatMessage = {
                    id: `w-${res.history_id}-${it.question_id || 0}-b`,
                    content: it.answer || (it.chat_res && it.chat_res.description) || '',
                    isUser: false,
                    timestamp: new Date(baseTs),
                    chatRes: it.chat_res,
                  };
                  loaded.push(botMsg);
                  baseTs += 1000;
                }
              } else {
                // Fallback: ensure a welcome message is shown even if backend returns empty
                const fallbackText = '안녕하세요! 퍼스널컬러 AI 컨설턴트입니다. 궁금한 점을 알려주시면 도와드릴게요.';
                loaded.push({
                  id: `w-${res.history_id}-0-b-fallback`,
                  content: fallbackText,
                  isUser: false,
                  timestamp: new Date(),
                  chatRes: { primary_tone: '', sub_tone: '', description: fallbackText, recommendations: [], emotion: 'neutral' } as any,
                });
              }

              setMessages(prev => (prev.length > 0 ? [...prev, ...loaded] : loaded));
            } catch (e) {
              console.warn('환영 메시지 로드 실패:', e);
              // On error, still show a local fallback welcome so the UI isn't blank
              const fallbackText = '안녕하세요! 퍼스널컬러 AI 컨설턴트입니다. 네트워크 문제로 환영 메시지를 불러오지 못했어요.';
              const fallbackMsg: ChatMessage = {
                id: `w-${res.history_id}-0-b-error`,
                content: fallbackText,
                isUser: false,
                timestamp: new Date(),
                chatRes: { primary_tone: '', sub_tone: '', description: fallbackText, recommendations: [], emotion: 'neutral' } as any,
              };
              setMessages(prev => (prev.length > 0 ? [...prev, fallbackMsg] : [fallbackMsg]));
            }
          }
        }
        console.log('새 채팅 세션 시작, history_id=', res.history_id, 'reused=', res.reused);
      } catch (e) {
        console.error('세션 시작 실패:', e);
        // 실패 시 재시도 가능하게 플래그 리셋
        sessionStartedRef.current = false;
      }
    })();

    return () => {
      mounted = false;
    };
  }, [startSession]);

  // 메시지에 리포트(진단) 상세보기 버튼을 보여야 하는지 판단
  const shouldShowReportButton = (msg: ChatMessage): boolean => {
    if (!msg || msg.isUser) return false;
    const content = (msg.content || '').toString();
    if (msg.diagnosisData) return true;
    if (content.includes('[상세보기]')) return true;
    if (/진단|리포트|분석/.test(content)) return true;
    return false;
  };


  // 진단 결과 상세보기 모달 열기
  const handleViewDiagnosisDetail = () => {
    if (selectedResult) {
      setIsDetailModalOpen(true);
      return;
    }

    const lastBotMessage = messages.filter(msg => !msg.isUser && msg.chatRes).pop();

    if (!lastBotMessage || !lastBotMessage.chatRes) {
      message.warning('진단 데이터를 찾을 수 없습니다.');
      return;
    }

    const cr = lastBotMessage.chatRes;

    const normalized = normalizePersonalColor(cr.primary_tone, cr.sub_tone);

    const tempResult: SurveyResultDetail = {
      id: Date.now(),
      result_tone: (cr.primary_tone || 'spring') as any,
      result_name: normalized.displayName,
      confidence: 0.85,
      total_score: 85,
      detailed_analysis: cr.description || '3턴 대화를 통한 분석 결과입니다.',
      color_palette: [],
      style_keywords: cr.recommendations || [],
      makeup_tips: [],
      answers: [],
      created_at: new Date().toISOString(),
      user_id: user?.id || 0,
      top_types: [
        {
          type: (cr.sub_tone?.toLowerCase() || 'spring') as any,
          name: normalized.displayName,
          description: cr.description || '3턴 대화 분석 결과',
          score: 0.85,
          color_palette: ['#FFB6C1', '#FFA07A', '#FFFF99', '#98FB98', '#87CEEB'],
          style_keywords: cr.recommendations?.slice(0, 3) || ['밝은', '화사한', '생동감'],
          makeup_tips: ['자연스러운 톤', '코랄 계열 립', '피치 블러셔'],
        },
      ],
    };

    setSelectedResult(tempResult);
    setIsDetailModalOpen(true);
  };

  // 진단 상세보기 모달 닫기
  const handleCloseDetailModal = () => {
    setIsDetailModalOpen(false);
    setSelectedResult(null);
  };

  // 메시지 전송 처리
  const handleSendMessage = async () => {
    // analyze 중복 호출 방지: 로딩 중이면 early return
    if (!inputMessage.trim() || isBusy) return;

    const userNickname = `${user?.nickname || '사용자'}님`;

    // 현재 상태 디버깅 로그
    console.log('🔍 현재 상태 확인:');
    console.log('  - currentHistoryId:', currentHistoryId);
    console.log('  - surveyResults:', surveyResults);
    console.log('  - surveyResults?.length:', surveyResults?.length);
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
      // 일반 챗봇 대화
      const response = await analyze({
        question: inputMessage.trim(),
        history_id: currentHistoryId,
      });

      console.log('💬 챗봇 응답:', response);
      console.log('🆔 새로운 history_id:', response.history_id);
      console.log('📝 Items 정보:', response.items);

      setCurrentHistoryId(response.history_id);
      const latestItem = response.items[response.items.length - 1];

      console.log('📋 Latest Item:', latestItem);

      if (latestItem) {
        // answer 필드 안전 처리 (더 견고한 JSON 감지/파싱)
        let botContent = latestItem.answer;

        console.log('🔤 원본 answer:', botContent);
        console.log('🎯 chat_res:', latestItem.chat_res);

        // Prefer chat_res.description when answer is empty
        if (!botContent || botContent.trim() === '') {
          botContent = latestItem.chat_res?.description || '답변을 준비 중입니다...';
          console.log('🔄 대체된 content (빈 answer 대체):', botContent);
        }

        // Attempt to parse JSON robustly: trim, then try JSON.parse regardless of surrounding whitespace/newlines
        try {
          const trimmed = (botContent || '').trim();
          if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
            const parsed = JSON.parse(trimmed);
            if (parsed && typeof parsed === 'object') {
              // Prefer explicit description field, then answer field
              botContent = parsed.description || parsed.answer || latestItem.chat_res?.description || '답변을 준비 중입니다...';
              console.log('📖 JSON 파싱 후:', botContent);
            }
          }
        } catch (e) {
          // JSON 파싱 실패 시 그대로 사용 (이미 handled by chat_res fallback)
          console.log('❌ JSON 파싱 실패, 원본 사용', e);
        }

        const botMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          content: botContent,
          isUser: false,
          timestamp: new Date(),
          chatRes: latestItem.chat_res,
          questionId: latestItem.question_id,
        };

        // 이모티콘 버블 먼저, description 버블은 딜레이 후 표시
        setMessages(prev => [...prev, botMessage]);
        if (botMessage.chatRes?.emotion && botMessage.content) {
          setDelayedDescriptions(prev => ({ ...prev, [botMessage.id]: false }));
          setTimeout(() => {
            setDelayedDescriptions(prev => ({ ...prev, [botMessage.id]: true }));
          }, 400); // 400ms 딜레이
        }

        // 사용자 턴 카운트 증가
        const newTurnCount = userTurnCount + 1;
        setUserTurnCount(newTurnCount);

        console.log(
          `📊 현재 대화 턴: ${newTurnCount}, 자동 리포트 생성 여부: ${hasAutoReportGenerated}`
        );

        // 3번 턴 후 자동 진단 결과 저장 (리포트는 별도 요청 시에만 생성)
        if (
          newTurnCount === 3 &&
          !hasAutoReportGenerated &&
          latestItem.chat_res
        ) {
          console.log('🎯 3번 턴 완료! 자동 진단 결과 저장 시작...');
          setHasAutoReportGenerated(true);

          try {
            // 진단 결과만 저장 (중복 생성 방지를 위해 리포트는 별도 처리하지 않음)
            console.log('💾 진단 결과 저장 중...');
            const diagnosisResult = await analyzeChatForDiagnosis(
              response.history_id
            );
            console.log('✅ 진단 결과 저장 성공:', diagnosisResult);
            console.log('📝 리포트 자동 생성 건너뜀 (중복 방지)');

            // 리포트(미리보기) 자동 표시: 백엔드가 반환한 요약 데이터를 모달로 열기
            // previewResultOuter을 상위 스코프에 선언해 버튼에서 직접 참조할 수 있게 합니다.
            let previewResultOuter: SurveyResultDetail | null = null;
            if (diagnosisResult && diagnosisResult.report_data) {
              try {
                const previewResult: SurveyResultDetail = (() => {
                  try {
                    // reportUtils expects an object with `report_data` at top-level
                    const wrapped = { report_data: diagnosisResult.report_data } as any;
                    return convertReportDataToSurveyDetail(
                      wrapped,
                      diagnosisResult.survey_result_id || Date.now()
                    );
                  } catch (e) {
                    console.warn('convertReportDataToSurveyDetail 실패, 폴백 사용', e);
                    return {
                      id: diagnosisResult.survey_result_id || Date.now(),
                      user_id: user?.id || 0,
                      created_at: diagnosisResult.created_at || new Date().toISOString(),
                      result_tone: (diagnosisResult.result_tone || 'spring') as any,
                      confidence: diagnosisResult?.message ? 0.85 : 0.85,
                      total_score: 85,
                      detailed_analysis: diagnosisResult.detailed_analysis || '',
                      result_name: diagnosisResult.result_name || '',
                      result_description: diagnosisResult.detailed_analysis || '',
                      color_palette: diagnosisResult.color_palette || [],
                      style_keywords: diagnosisResult.style_keywords || [],
                      makeup_tips: diagnosisResult.makeup_tips || [],
                      top_types: Array.isArray(diagnosisResult.report_data?.top_types)
                        ? diagnosisResult.report_data.top_types
                        : [],
                      answers: [],
                    } as SurveyResultDetail;
                  }
                })();
                previewResultOuter = previewResult;
                setSelectedResult(previewResultOuter);
                // 자동으로 모달을 열지 않고, 사용자에게 준비되었음을 알립니다.
                try {
                  message.success('진단이 완료되었습니다. 아래의 "🎨 진단 결과" 버튼을 눌러 확인하세요.');
                } catch (e) {
                  console.warn('토스트 알림 표시 실패', e);
                }
              } catch (e) {
                console.warn('미리보기 결과 생성 중 오류', e);
              }
            }

            // 요약 리포트 생성 완료 메시지
            const summaryMessage: ChatMessage = {
              id: `diagnosis-summary-${Date.now()}`,
              content: '',
              customContent: (
                <div style={{ padding: '16px' }}>
                  <div style={{ marginBottom: '20px' }}>
                    <div
                      style={{
                        fontSize: '16px',
                        fontWeight: 'bold',
                        marginBottom: '8px',
                        color: '#1a1a1a',
                      }}
                    >
                      🎉 {userNickname}과의 대화를 통해 퍼스널컬러 진단이
                      완료되었습니다!
                    </div>
                    <div
                      style={{
                        fontSize: '12px',
                        color: '#059669',
                        marginTop: '8px',
                        padding: '8px',
                        backgroundColor: '#f0fff4',
                        borderRadius: '6px',
                      }}
                    >
                      💬 계속 대화하시면 이전 진단 결과를 참고하여 더 자세한
                      상담을 받을 수 있어요!
                    </div>
                  </div>

                  {/* 퍼스널 타입 정보 - 동적 스타일 적용 */}
                  {(() => {
                    // 결과 타입에 따른 스타일 설정
                    const typeNames: Record<
                      string,
                      { name: string; emoji: string; color: string }
                    > = {
                      spring: {
                        name: '봄 웜톤',
                        emoji: '🌸',
                        color: '#fab1a0',
                      },
                      summer: {
                        name: '여름 쿨톤',
                        emoji: '💎',
                        color: '#a8e6cf',
                      },
                      autumn: {
                        name: '가을 웜톤',
                        emoji: '🍂',
                        color: '#d4a574',
                      },
                      winter: {
                        name: '겨울 쿨톤',
                        emoji: '❄️',
                        color: '#74b9ff',
                      },
                    };

                    // 현재 진단 결과에서 타입 추출
                    const resultTone =
                      diagnosisResult.result_tone ||
                      latestItem.chat_res.primary_tone ||
                      'spring';
                    const typeInfo = typeNames[resultTone] || typeNames.spring;

                    return (
                      <div
                        style={{
                          background: `linear-gradient(135deg, ${typeInfo.color}, ${typeInfo.color}aa)`,
                          color: '#000000',
                          padding: '16px',
                          borderRadius: '12px',
                          textAlign: 'center',
                          marginBottom: '16px',
                        }}
                      >
                        <div
                          style={{
                            fontSize: '18px',
                            fontWeight: 'bold',
                            margin: '0 0 4px 0',
                            color: '#000000',
                          }}
                        >
                          {typeInfo.emoji}{' '}
                          {diagnosisResult.result_name ||
                            `${latestItem.chat_res.sub_tone} ${latestItem.chat_res.primary_tone}톤`}
                        </div>
                        <div
                          style={{
                            fontSize: '13px',
                            margin: '0',
                            color: '#000000',
                          }}
                        >
                          {diagnosisResult.detailed_analysis?.split('.')[0] +
                            '.' ||
                            latestItem.chat_res.description ||
                            '당신만의 개성을 살릴 수 있는 퍼스널컬러를 찾았어요!'}
                        </div>
                      </div>
                    );
                  })()}

                  {/* 컬러 팔레트 */}
                  <div style={{ marginBottom: '16px' }}>
                    <div
                      style={{
                        fontSize: '14px',
                        fontWeight: 'bold',
                        marginBottom: '8px',
                        color: '#374151',
                      }}
                    >
                      🎨 당신만의 컬러 팔레트
                    </div>
                    <div
                      style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}
                    >
                      {(
                        diagnosisResult.color_palette || [
                          '#ff5722',
                          '#2196f3',
                          '#8bc34a',
                          '#ff9800',
                        ]
                      )
                        .slice(0, 4)
                        .map((color: string, index: number) => {
                          const isWhite = color.toLowerCase() === '#ffffff';
                          return (
                            <Tag
                              key={index}
                              style={
                                isWhite
                                  ? {
                                      backgroundColor: '#f5f5f5',
                                      color: '#333333',
                                      border: '1px solid #d9d9d9',
                                      borderRadius: '4px',
                                      padding: '4px 8px',
                                      fontSize: '12px',
                                      fontWeight: 'bold',
                                      margin: '0',
                                    }
                                  : {
                                      backgroundColor: color,
                                      color: '#ffffff',
                                      border: 'none',
                                      borderRadius: '4px',
                                      padding: '4px 8px',
                                      fontSize: '12px',
                                      fontWeight: 'bold',
                                      textShadow: '1px 1px 2px rgba(0,0,0,0.5)',
                                      margin: '0',
                                    }
                              }
                            >
                              {color}
                            </Tag>
                          );
                        })}
                    </div>
                  </div>

                  <div
                    style={{
                      fontSize: '14px',
                      color: '#6b7280',
                      textAlign: 'center',
                    }}
                  >
                    상세한 분석 결과를 확인해보세요!
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
                makeup_tips: diagnosisResult.makeup_tips || [],
              },
            };

            setTimeout(() => {
              setMessages(prev => [...prev, summaryMessage]);

              // 진단 완료 후 userTurnCount 초기화 (새로운 대화 사이클 시작)
              console.log('🔄 진단 완료! userTurnCount 초기화 (0으로 리셋)');
              setUserTurnCount(0);
              setHasAutoReportGenerated(false); // 새로운 대화를 위해 리포트 생성 플래그도 초기화
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

              // 에러 발생 시에도 userTurnCount 초기화 (새로운 대화 사이클 시작)
              console.log('🔄 진단 시도 완료! userTurnCount 초기화 (0으로 리셋)');
              setUserTurnCount(0);
              setHasAutoReportGenerated(false); // 새로운 대화를 위해 리포트 생성 플래그도 초기화
            }, 1000);
          }
        }
      }
    } catch (error: any) {
      console.error('챗봇 메시지 전송 오류:', error);
      let errorContent =
        '죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
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
            errorContent =
              '서버에 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
            break;
        }
      } else if (error.request) {
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
        await endChatSession(currentHistoryId);
        console.log('채팅 세션이 종료되었습니다.');
        // clear current session id so subsequent analyzes will start a new session
        setCurrentHistoryId(undefined);
      } catch (error) {
        console.error('채팅 세션 종료 중 오류:', error);
      }
    }
  };

  // 피드백 선택 처리
  const handleFeedback = async (isPositive: boolean) => {
    try {
      await submitFeedback({ historyId: currentHistoryId, isPositive });

      // 성공 시 UI 처리
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


// 진단 챗봇 버블 여부 판별 함수 (예시: description에 '진단', '분석', '추천', '퍼스널컬러', '톤', '결과' 등 포함 시)
// 진단 완료 요약 customContent가 있는 메시지(진단 완료 버블)만 true 반환
function isDiagnosisBubble(msg?: any): boolean {
  // 진단 요약 customContent가 있는 경우만 진단 버블로 간주
  if (msg && msg.customContent && typeof msg.customContent === 'object') {
    return true;
  }
  return false;
}

  // Helpers to group messages by date and format headers
  const isSameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

  const formatDateHeader = (d: Date) => {
    const today = new Date();
    if (isSameDay(d, today)) return '오늘';
    const weekdays = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일'];
    return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일 ${weekdays[d.getDay()]}`;
  };

  const groupMessagesByDate = (msgs: ChatMessage[]) => {
    const map = new Map<string, ChatMessage[]>();
    for (const m of msgs) {
      // normalize to YYYY-MM-DD key
      const d = new Date(m.timestamp);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
        d.getDate()
      ).padStart(2, '0')}`;
      if (!map.has(key)) {
        map.set(key, []);
      }
      map.get(key)!.push(m);
    }

    // sort keys (YYYY-MM-DD strings) ascending so oldest date comes first
    const keys = Array.from(map.keys()).sort((a, b) => a.localeCompare(b));

    return keys.map(k => {
      const items = (map.get(k) || []).slice().sort((x, y) => new Date(x.timestamp).getTime() - new Date(y.timestamp).getTime());
      const date = items.length > 0 ? new Date(items[0].timestamp) : new Date(k);
      return { key: k, items, date };
    });
  };

  // Memoized grouped sections so we don't recompute on every render
  const groupedSections = useMemo(() => groupMessagesByDate(messages), [messages]);

  // Small inline typing animation using SVG (no external CSS needed)
  const TypingAnimation: React.FC<{ size?: number; color?: string }> = ({ size = 10, color = '#9CA3AF' }) => (
    <svg width={size * 3 + 20} height={size} viewBox={`0 0 ${size * 3 + 20} ${size}`} xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <circle cx={size / 2} cy={size / 2} r={size / 2} fill={color}>
        <animate attributeName="opacity" values="0.2;1;0.2" dur="1s" repeatCount="indefinite" begin="0s" />
      </circle>
      <circle cx={size / 2 + size + 6} cy={size / 2} r={size / 2} fill={color}>
        <animate attributeName="opacity" values="0.2;1;0.2" dur="1s" repeatCount="indefinite" begin="0.15s" />
      </circle>
      <circle cx={size / 2 + (size + 6) * 2} cy={size / 2} r={size / 2} fill={color}>
        <animate attributeName="opacity" values="0.2;1;0.2" dur="1s" repeatCount="indefinite" begin="0.3s" />
      </circle>
    </svg>
  );

  const renderMessage = (msg: ChatMessage) => {
    const idx = messages.findIndex(m => m.id === msg.id);
    return (
      <div
        className={`flex mb-3 ${msg.isUser ? 'justify-end' : 'justify-start'}`}
      >
        <div
          className={`flex max-w-lg items-start ${msg.isUser ? 'flex-row-reverse' : 'flex-row'}`}
        >
          {msg.isUser ? (
            (() => {
              const avatarConfig = getAvatarRenderInfo(
                user?.gender,
                user?.id
              );
              return (
                <Avatar
                  className={`!ml-3 ${avatarConfig.className}`}
                  style={avatarConfig.style}
                >
                  {typeof avatarConfig.content === 'string' ? (
                    <span style={{ fontSize: '18px' }}>
                      {avatarConfig.content}
                    </span>
                  ) : (
                    avatarConfig.content
                  )}
                </Avatar>
              );
            })()
            ) : (
            (() => {
              // For bot messages, prefer the currently active influencer profile for avatar.
              // If none selected, fall back to influencer info embedded in the message, then robot icon.
              const inflKey = (msg as any).influencer || (msg as any).chatRes?.influencer || (msg as any).chatRes?.raw?.influencer || (msg as any).influencer_id || null;

              const getInfluencerAvatarInfo = (s: any) => {
                if (!s || typeof s !== 'string') return null;
                const key = s.trim().toLowerCase();

                if (Array.isArray(influencers) && influencers.length > 0) {
                  for (const p of influencers) {
                    const n = ((p as any).name || '').toString().toLowerCase();
                    if (!n) continue;
                    if (key === n || key.includes(n) || key.startsWith(n)) return p;
                  }
                }

                const map: Record<string, any> = {
                  '혜경': { name: '혜경', emoji: '🎨', color: '#F0E6FF', profile: '/profiles/혜경.png' },
                  '원준': { name: '원준', emoji: '🌟', color: '#FFE4E6', profile: '/profiles/원준.png' },
                  '종민': { name: '종민', emoji: '💰', color: '#FFF2CC', profile: '/profiles/종민.png' },
                  '세현': { name: '세현', emoji: '🌿', color: '#E8F5E8', profile: '/profiles/세현.png' },
                };
                for (const k of Object.keys(map)) {
                  if (key.includes(k) || key.startsWith(k.toLowerCase())) return map[k];
                }

                const prefix = key.split(/[_\s-]/)[0] || key;
                return { name: s, emoji: '🌟', color: '#e5e7eb', prefix };
              };

              const inflFromMsg = getInfluencerAvatarInfo(inflKey);
              const avatarProfile = activeInfluencerProfile || inflFromMsg;

              if (avatarProfile) {
                const inflName = (((avatarProfile as any)?.name || '') as string).toLowerCase();
                const activeName = typeof activeInfluencerProfile === 'string'
                  ? (activeInfluencerProfile as string).toLowerCase()
                  : (((activeInfluencerProfile as any)?.name || '') as string).toLowerCase();
                const activeId = (activeInfluencerProfile && (activeInfluencerProfile as any).id) ?? null;
                const inflId = (avatarProfile && (avatarProfile as any).id) ?? null;
                const isActive = (
                  activeId != null && inflId != null
                    ? String(activeId) === String(inflId)
                    : activeName && inflName && activeName === inflName
                );

                return (
                  <div
                    className={`influencer-avatar-clickable !mr-3 ${isActive ? 'influencer-avatar-active' : ''}`}
                    onClick={() => {
                      if (autoCloseRef.current) {
                        window.clearTimeout(autoCloseRef.current as any);
                        autoCloseRef.current = null;
                      }
                      setActiveInfluencerProfile(avatarProfile);
                      setInfluencerModalOpen(true);
                    }}
                    aria-label={`Open profile ${(avatarProfile as any).name}`}
                    role="button"
                    tabIndex={0}
                    style={{ display: 'inline-flex', alignItems: 'center' }}
                  >
                    <Avatar
                      size={50}
                      style={{ width: 50, height: 50, flexShrink: 0, padding: 0, overflow: 'hidden', background: '#fff' }}
                    >
                      <InfluencerImage profile={avatarProfile} name={(avatarProfile as any).name} emoji={(avatarProfile as any).emoji} />
                    </Avatar>
                  </div>
                );
              }

              return (
                <Avatar
                  icon={<RobotOutlined />}
                  style={{ backgroundColor: '#8b5cf6', flexShrink: 0 }}
                  className="!mr-3"
                />
              );
            })()
          )}
          <div className="flex flex-col gap-1">
            {!msg.isUser && (idx === 0 || (msg.chatRes?.emotion && !isDiagnosisBubble(msg))) && (
              <div
                className="relative px-4 py-2 rounded-lg bg-white border border-gray-200 mb-1 flex items-center chatbot-balloon"
                style={{ maxWidth: 'fit-content' }}
              >
                <span
                  className="absolute left-[-10px] top-4 w-0 h-0"
                  style={{
                    borderTop: '8px solid transparent',
                    borderBottom: '8px solid transparent',
                    borderRight: '10px solid #fff',
                    left: '-10px',
                    top: '16px',
                    zIndex: 1,
                  }}
                />
                <span
                  className="absolute left-[-12px] top-4 w-0 h-0"
                  style={{
                    borderTop: '9px solid transparent',
                    borderBottom: '9px solid transparent',
                    borderRight: '12px solid #e5e7eb',
                    left: '-12px',
                    top: '15px',
                    zIndex: 0,
                  }}
                />
                <AnimatedEmoji emotion={msg?.chatRes?.emotion ?? 'neutral'} size={40} />
              </div>
            )}
            {(msg.isUser || !msg.chatRes?.emotion || delayedDescriptions[msg.id] || typeof delayedDescriptions[msg.id] === 'undefined') && (
              <div
                className={`relative px-4 py-2 rounded-lg ${
                  msg.isUser
                    ? 'bg-blue-500 text-white user-balloon'
                    : 'bg-white chatbot-balloon'
                }`}
                style={{
                  marginLeft: msg.isUser ? 0 : '0',
                  marginRight: msg.isUser ? '0' : 0,
                  maxWidth: '100%',
                  border: msg.isUser ? undefined : '1.5px solid #e5e7eb',
                  boxShadow: msg.isUser ? undefined : '0 2px 8px rgba(0,0,0,0.04)',
                }}
              >
                {msg.isUser ? (
                  <>
                    <span
                      className="absolute right-[-10px] top-4 w-0 h-0"
                      style={{
                        borderTop: '8px solid transparent',
                        borderBottom: '8px solid transparent',
                        borderLeft: '10px solid #3b82f6',
                        right: '-10px',
                        top: '16px',
                        zIndex: 1,
                      }}
                    />
                    <span
                      className="absolute right-[-12px] top-4 w-0 h-0"
                      style={{
                        borderTop: '9px solid transparent',
                        borderBottom: '9px solid transparent',
                        borderLeft: '12px solid #2563eb',
                        right: '-12px',
                        top: '15px',
                        zIndex: 0,
                      }}
                    />
                  </>
                ) : (
                  <>
                    <span
                      className="absolute left-[-10px] top-4 w-0 h-0"
                      style={{
                        borderTop: '8px solid transparent',
                        borderBottom: '8px solid transparent',
                        borderRight: '10px solid #fff',
                        left: '-10px',
                        top: '16px',
                        zIndex: 1,
                      }}
                    />
                    <span
                      className="absolute left-[-12px] top-4 w-0 h-0"
                      style={{
                        borderTop: '9px solid transparent',
                        borderBottom: '9px solid transparent',
                        borderRight: '12px solid #e5e7eb',
                        left: '-12px',
                        top: '15px',
                        zIndex: 0,
                      }}
                    />
                  </>
                )}
                {msg.customContent ? (
                  msg.customContent
                ) : msg.content.includes('[상세보기]') ? (
                  <div>
                    {msg.content.includes('🌈 **추천 컬러 팔레트**') &&
                    msg.diagnosisData ? (
                      <div>
                        <Text
                          className={`whitespace-pre-wrap ${msg.isUser ? '!text-white' : '!text-gray-800'}`}
                        >
                          {msg.content.split('🌈 **추천 컬러 팔레트**')[0]}
                        </Text>

                        <div className="mt-3">
                          <Text
                            strong
                            className="block mb-2 !text-gray-700"
                          >
                            🌈 추천 컬러 팔레트
                          </Text>
                          <div className="flex flex-wrap gap-2 mb-3">
                            {msg.diagnosisData.color_palette &&
                            msg.diagnosisData.color_palette.length > 0 ? (
                              msg.diagnosisData.color_palette.map(
                                (color: string, index: number) => (
                                  <div
                                    key={index}
                                    className="flex items-center gap-1"
                                  >
                                    <div
                                      className="w-6 h-6 rounded-full border border-gray-300"
                                      style={{ backgroundColor: color }}
                                      title={color}
                                    />
                                    <Text className="text-xs text-gray-600">
                                      {color}
                                    </Text>
                                  </div>
                                )
                              )
                            ) : (
                              <>
                                <div className="flex items-center gap-1">
                                  <div
                                    className="w-6 h-6 rounded-full border border-gray-300"
                                    style={{ backgroundColor: '#FFB6C1' }}
                                  />
                                  <Text className="text-xs text-gray-600">
                                    #FFB6C1
                                  </Text>
                                </div>
                                <div className="flex items-center gap-1">
                                  <div
                                    className="w-6 h-6 rounded-full border border-gray-300"
                                    style={{ backgroundColor: '#FFA07A' }}
                                  />
                                  <Text className="text-xs text-gray-600">
                                    #FFA07A
                                  </Text>
                                </div>
                                <div className="flex items-center gap-1">
                                  <div
                                    className="w-6 h-6 rounded-full border border-gray-300"
                                    style={{ backgroundColor: '#FFFF99' }}
                                  />
                                  <Text className="text-xs text-gray-600">
                                    #FFFF99
                                  </Text>
                                </div>
                                <div className="flex items-center gap-1">
                                  <div
                                    className="w-6 h-6 rounded-full border border-gray-300"
                                    style={{ backgroundColor: '#98FB98' }}
                                  />
                                  <Text className="text-xs text-gray-600">
                                    #98FB98
                                  </Text>
                                </div>
                                <div className="flex items-center gap-1">
                                  <div
                                    className="w-6 h-6 rounded-full border border-gray-300"
                                    style={{ backgroundColor: '#87CEEB' }}
                                  />
                                  <Text className="text-xs text-gray-600">
                                    #87CEEB
                                  </Text>
                                </div>
                              </>
                            )}
                          </div>
                        </div>

                        <Text
                          className={`whitespace-pre-wrap ${msg.isUser ? '!text-white' : '!text-gray-800'}`}
                        >
                          {msg.content
                            .split('🌈 **추천 컬러 팔레트**')[1]
                            ?.replace(/🎨 #[A-Fa-f0-9]{6}/g, '')
                            .replace('[상세보기]', '')
                            .trim()}
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
                  {shouldShowReportButton(msg) && (
                    <Button
                      type="default"
                      size="small"
                      onClick={() => {
                        if (selectedResult) {
                          setIsDetailModalOpen(true);
                          return;
                        }
                        if (surveyResults && surveyResults.length > 0) {
                          setSelectedResult(surveyResults[0] as SurveyResultDetail);
                          setIsDetailModalOpen(true);
                          return;
                        }
                        handleViewDiagnosisDetail();
                      }}
                      className="border-purple-300 text-purple-600 hover:border-purple-500 hover:text-purple-700"
                    >
                      🎨 진단 결과
                    </Button>
                  )}
                  {formatKoreanDate(msg.timestamp, true)}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // 로딩 상태
  // `welcomeIsPending` used to be provided by a removed react-query welcome request; default to false.
  const welcomeIsPending = false;
  if (userLoading || surveyLoading || welcomeIsPending) {
    return (
      <Loading />
    );
  }

  // 로그인하지 않은 경우
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 flex items-center justify-center">
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

  // 샘플 질문 데이터 (진단 내역 유무에 따라 분기)
  const sampleQuestions =
    !surveyResults || surveyResults.length === 0
      ? [
          {
            label: '퍼스널컬러 진단받기',
            question: '안녕하세요! 저는 어떤 퍼스널컬러 타입일까요?',
          },
          {
            label: '색상 고민 상담',
            question:
              '평소에 밝은 색 옷을 많이 입는 편인데, 저한테 어울리나요?',
          },
          {
            label: '피부톤 고민',
            question: '피부톤에 대해 잘 모르겠어요. 어떻게 알 수 있을까요?',
          },
          {
            label: '색상 조화 고민',
            question: '제가 좋아하는 색깔과 잘 어울리는 색깔이 다른 것 같아요.',
          },
        ]
      : [
          {
            label: '립스틱 색상 추천',
            question: '내 퍼스널컬러에 어울리는 립스틱 색상을 추천해주세요.',
          },
          {
            label: '계절별 코디',
            question: '지금 계절에 어울리는 옷 색깔 조합을 알려주세요.',
          },
          {
            label: '새 진단 받기',
            question: '퍼스널컬러 타입 진단을 다시 받아보고 싶어요.',
          },
          {
            label: '타입 비교 분석',
            question: '내 타입의 특징과 다른 타입과의 차이점을 알려주세요.',
          },
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
                대화를 통해 AI가 당신의 퍼스널컬러를 분석해드립니다. 편하게
                대화해보세요!
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
          styles={{
            body: {
              padding: '16px',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
            },
          }}
        >
          {/* 메시지 목록 */}
          <div
            ref={messagesContainerRef}
            className="flex-1 overflow-y-auto mb-3 p-3 bg-gray-50 rounded-lg"
            style={{ minHeight: '400px', paddingTop: '30px', position: 'relative' }}
          >
            {groupedSections.map((sec) => (
              <div key={`sec-${sec.key}`} className="mb-3">
                <div className="flex items-center justify-center my-4">
                  <div className="flex-1 border-t border-gray-200" />
                  <span className="mx-4 px-4 py-1 bg-white text-sm text-gray-600 rounded-full shadow-sm">
                    {formatDateHeader(sec.date)}
                  </span>
                  <div className="flex-1 border-t border-gray-200" />
                </div>
                {sec.items.map((msg) => (
                  <div key={msg.id}>{renderMessage(msg)}</div>
                ))}
              </div>
            ))}

            {/* 타이핑 인디케이터 */}
            {isTyping && (
              <div className="flex justify-start mb-3">
                <div className="flex items-start">
                  {/* Avatar: prefer active influencer, else infer from last bot message, else robot */}
                  <div className={`chatbot-avatar-container !mr-2 ${isTyping ? 'chatbot-active' : ''}`}>
                    {
                      (() => {
                        // find last bot message to infer influencer if needed
                        const lastBot = [...messages].slice().reverse().find(m => !m.isUser);
                        const inflKey = (lastBot as any)?.influencer || (lastBot as any)?.chatRes?.influencer || (lastBot as any)?.chatRes?.raw?.influencer || (lastBot as any)?.influencer_id || null;

                        let found: any = null;
                        if (activeInfluencerProfile) {
                          found = activeInfluencerProfile;
                        } else if (inflKey && Array.isArray(influencers) && influencers.length > 0) {
                          const key = String(inflKey).toLowerCase();
                          for (const p of influencers) {
                            const n = ((p as any).name || '').toString().toLowerCase();
                            if (!n) continue;
                            if (key === n || key.includes(n) || key.startsWith(n)) {
                              found = p;
                              break;
                            }
                          }
                        }

                        if (found) {
                          return (
                            <div
                              className="influencer-avatar-clickable !mr-3 influencer-avatar-active"
                              role="button"
                              tabIndex={0}
                              onClick={() => {
                                if (autoCloseRef.current) {
                                  window.clearTimeout(autoCloseRef.current as any);
                                  autoCloseRef.current = null;
                                }
                                setActiveInfluencerProfile(found);
                                setInfluencerModalOpen(true);
                              }}
                            >
                              <Avatar
                                size={50}
                                style={{ width: 50, height: 50, flexShrink: 0, padding: 0, overflow: 'hidden', background: '#fff' }}
                              >
                                <InfluencerImage profile={found} name={(found as any).name} emoji={(found as any).emoji} />
                              </Avatar>
                            </div>
                          );
                        }

                        return (
                          <Avatar
                            icon={<RobotOutlined />}
                            style={{ backgroundColor: '#8b5cf6', flexShrink: 0 }}
                          />
                        );
                      })()
                    }
                  </div>

                  <div className="bg-white border border-gray-200 px-4 py-2 rounded-lg flex items-center">
                    <TypingAnimation size={8} color="#6b7280" />
                    <span className="sr-only">답변을 생성하고 있습니다</span>
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
              {!surveyResults || surveyResults.length === 0
                ? '💡 이런 대화로 시작해보세요!'
                : '💡 이런 질문은 어떠세요?'}
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
              onKeyDown={e => {
                // analyze 중복 호출 방지: 로딩 중이면 입력 무시
                if (isBusy) return;
                handleKeyDown(e);
              }}
              placeholder={
                !surveyResults || surveyResults.length === 0
                  ? '퍼스널컬러에 대해 궁금한 것을 자유롭게 말씀해주세요...'
                  : '퍼스널컬러에 대해 궁금한 것을 물어보세요...'
              }
              autoSize={{ minRows: 1, maxRows: 2 }}
              disabled={isBusy}
              style={{ fontSize: '14px' }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={() => {
                // analyze 중복 호출 방지: 로딩 중이면 클릭 무시
                if (isBusy) return;
                handleSendMessage();
              }}
              disabled={!inputMessage.trim() || isBusy}
              className="h-auto"
            >
              전송
            </Button>
          </div>
        </Card>

        {/* 피드백 모달 */}
        <FeedbackModal
          open={isFeedbackModalOpen}
          onCancel={handleCloseFeedbackModal}
          onFeedback={handleFeedback}
          isLoading={isSubmittingFeedback}
        />

        {/* 진단 결과 상세보기 모달 */}
        <DiagnosisDetailModal
          open={isDetailModalOpen}
          onClose={handleCloseDetailModal}
          selectedResult={selectedResult}
          showDeleteButton={false} // 챗봇에서는 삭제 버튼 숨김
          recentResults={(() => {
            // selectedResult (preview) first, then unique previous surveyResults
            const out: SurveyResultDetail[] = [];
            const seen = new Set<string>();
            const pushIfUnique = (r?: SurveyResultDetail | null) => {
              if (!r) return;
              const key = r.result_name || String(r.result_tone) || String(r.id);
              if (!seen.has(key)) {
                seen.add(key);
                out.push(r);
              }
            };

            pushIfUnique(selectedResult);
            if (surveyResults && surveyResults.length > 0) {
              for (const r of surveyResults) {
                pushIfUnique(r as SurveyResultDetail);
                if (out.length >= 3) break;
              }
            }
            return out;
          })()}
        />

        {/* Influencer profile modal */}
        <InfluencerProfileModal
          open={influencerModalOpen}
          onCancel={() => {
            setInfluencerModalOpen(false);
            if (autoCloseRef.current) {
              window.clearTimeout(autoCloseRef.current as any);
              autoCloseRef.current = null;
            }
          }}
          profile={activeInfluencerProfile}
        />
      </div>
    </div>
  );
};

export default ChatbotPage;
