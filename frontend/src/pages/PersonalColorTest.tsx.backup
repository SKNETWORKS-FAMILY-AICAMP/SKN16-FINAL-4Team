import React, { useEffect } from 'react';
import {
  Card,
  Button,
  Progress,
  Typography,
  Space,
  Tag,
  Alert,
  Tooltip,
  message,
  Row,
  Col,
  Badge,
} from 'antd';
import {
  ArrowLeftOutlined,
  ArrowRightOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { usePersonalColorTest } from '@/hooks/usePersonalColorTest';
import { useCurrentUser } from '@/hooks/useUser';
import { useInvalidateSurveyResults } from '@/hooks/useSurvey';
import RouterPaths from '@/routes/Router';
import type { PersonalColorType } from '@/types/personalColor';
import {
  surveyApi,
  type SurveyAnswer,
  type SurveySubmitResponse,
  type PersonalColorTypeData,
} from '../api/survey';

const { Title, Text } = Typography;

const PersonalColorTest: React.FC = () => {
  const navigate = useNavigate();
  const { data: user, isLoading: userLoading } = useCurrentUser();
  const invalidateSurveyResults = useInvalidateSurveyResults();
  const {
    currentQuestion,
    progress,
    result,
    selectAnswer,
    goToNextQuestion,
    goToPreviousQuestion,
    resetTest,
  } = usePersonalColorTest();

  const [selectedAnswer, setSelectedAnswer] = React.useState<string>('');
  const [expandedType, setExpandedType] = React.useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = React.useState(false);
  const [apiResult, setApiResult] = React.useState<SurveySubmitResponse | null>(
    null
  );

  // 질문이 변경될 때마다 화면을 최상단으로 스크롤
  useEffect(() => {
    if (currentQuestion) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [currentQuestion?.id]);

  // 결과가 나타날 때도 화면을 최상단으로 스크롤
  useEffect(() => {
    if (result) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [result]);

  // 답변 선택 핸들러
  const handleAnswerSelect = (optionId: string) => {
    setSelectedAnswer(optionId);
    selectAnswer(optionId);
  };

  // 다음 질문으로 이동
  const handleNext = async () => {
    if (!selectedAnswer) return;

    // 마지막 질문이면 API 호출하여 결과 분석
    if (progress.currentQuestion === progress.totalQuestions) {
      await handleGetResult();
    } else {
      goToNextQuestion();
      setSelectedAnswer(''); // 선택 초기화
    }
  };

  // 이전 질문으로 이동
  const handlePrevious = () => {
    goToPreviousQuestion();
    setSelectedAnswer(''); // 선택 초기화
  };

  // 결과 분석 및 가져오기
  const handleGetResult = async () => {
    console.log('▶ handleGetResult 시작');
    console.log('  progress:', progress);

    if (!progress.answers || progress.answers.length === 0) {
      message.error('답변 데이터가 없습니다.');
      console.error('❌ progress.answers가 비어있음');
      return;
    }

    setIsAnalyzing(true);
    try {
      // progress.answers를 survey API 형식으로 변환
      const answers: SurveyAnswer[] = progress.answers.map(answer => {
        console.log('  답변 변환 중:', answer);
        return {
          question_id: answer.questionId,
          option_id: answer.optionId,
          option_label: answer.optionLabel || '(라벨 없음)',
        };
      });

      console.log('📤 전송할 데이터:', { answers });

      // API 호출 - OpenAI 분석 결과 받기
      const response = await surveyApi.submitSurvey({ answers });

      console.log('✅ OpenAI 분석 완료:', response);

      // API 결과를 상태에 저장
      setApiResult(response);

      // 로컬 결과도 생성하여 화면 표시
      goToNextQuestion();
      setSelectedAnswer('');

      // 설문 결과 캐시 무효화 - 마이페이지에서 최신 데이터 표시를 위해
      invalidateSurveyResults();

      message.success('🎉 퍼스널 컬러 분석이 완료되었습니다!');
    } catch (error: any) {
      console.error('❌ 결과 분석 실패:', error);

      // 에러 메시지 처리
      let errorMessage = '분석에 실패했습니다. 다시 시도해주세요.';
      if (error.message && typeof error.message === 'string') {
        errorMessage = error.message;
      }

      message.error(errorMessage, 5); // 5초간 표시

      // 실패 시 로컬 결과라도 보여주기
      goToNextQuestion();
      setSelectedAnswer('');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // 테스트 다시 하기
  const handleRestart = () => {
    resetTest();
    setSelectedAnswer('');
    setExpandedType(null);
    setApiResult(null);
    // 화면을 최상단으로 스크롤
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // 챗봇 페이지로 이동
  const handleGoToChatbot = () => {
    // 챗봇 페이지 이동 전 캐시 무효화로 최신 데이터 보장
    invalidateSurveyResults();
    navigate(RouterPaths.Chatbot);
  };

  // 마이페이지로 이동
  const handleGoToMyPage = () => {
    // 마이페이지 이동 전 캐시 무효화로 최신 데이터 보장
    invalidateSurveyResults();
    navigate(RouterPaths.MyPage);
  };

  // 홈으로 이동 (결과는 이미 저장됨)
  const handleGoToHome = () => {
    navigate(RouterPaths.Home);
  };

  // 로그인 페이지로 이동
  const handleGoToLogin = () => {
    navigate(RouterPaths.Login);
  };

  // 로딩 중일 때
  if (userLoading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}
      >
        <div className="w-full max-w-md mx-auto p-4">
          <Card
            className="shadow-2xl border-0 text-center"
            style={{
              borderRadius: '20px',
              background: 'rgba(255, 255, 255, 0.95)',
              backdropFilter: 'blur(10px)',
            }}
          >
            <Alert
              message="로딩 중..."
              type="info"
              showIcon
              style={{
                background: 'transparent',
                border: 'none',
              }}
            />
          </Card>
        </div>
      </div>
    );
  }

  // 로그인하지 않은 경우
  if (!user) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}
      >
        <div className="w-full max-w-md mx-auto p-4">
          <Card
            className="shadow-2xl border-0"
            style={{
              borderRadius: '20px',
              background: 'rgba(255, 255, 255, 0.95)',
              backdropFilter: 'blur(10px)',
            }}
          >
            <div className="text-center p-6">
              <Title level={3} className="mb-4 text-gray-800">
                🔐 로그인이 필요합니다
              </Title>
              <Text className="text-gray-600 block mb-6">
                퍼스널 컬러 테스트를 이용하려면 로그인해주세요.
              </Text>
              <div className="flex gap-3 justify-center">
                <Button
                  onClick={handleGoToHome}
                  size="large"
                  style={{
                    borderColor: '#d1d5db',
                    color: '#6b7280',
                    borderRadius: '10px',
                  }}
                >
                  홈으로 가기
                </Button>
                <Button
                  type="primary"
                  onClick={handleGoToLogin}
                  size="large"
                  style={{
                    background:
                      'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    border: 'none',
                    borderRadius: '10px',
                  }}
                >
                  로그인하기
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  // 결과 화면
  if (result) {
    return (
      <div
        className="min-h-screen pt-4"
        style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}
      >
        <div className="max-w-2xl mx-auto p-4">
          <Card
            className="shadow-2xl border-0 mb-6"
            style={{
              borderRadius: '20px',
              background: 'rgba(255, 255, 255, 0.95)',
              backdropFilter: 'blur(10px)',
            }}
          >
            {/* 헤더 */}
            <div className="text-center mb-6">
              <div className="flex justify-center mb-3">
                <CheckCircleOutlined
                  className="text-4xl"
                  style={{ color: '#10b981' }}
                />
              </div>
              <Title level={3} className="mb-1 text-gray-800">
                🎉 진단 완료!
              </Title>
              <Text className="text-gray-600 text-base">
                당신만의 특별한 컬러를 찾았습니다
              </Text>
            </div>

            {/* 추천 타입 카드 - 항상 노출 */}
            <div className="mb-6">
              <Row gutter={[12, 12]} justify="center">
                {(() => {
                  // API 결과가 있으면 top_types 사용, 없으면 로컬 결과 사용
                  if (apiResult?.top_types && apiResult.top_types.length > 0) {
                    // API top_types는 최소 2개, 최대 3개 보장
                    return apiResult.top_types.slice(0, 3);
                  } else {
                    // 로컬 결과 사용 (최소 2개, 최대 3개)
                    const scores = result.scores || {};
                    let sortedTypes = Object.entries(scores)
                      .map(([type, score]) => ({
                        type,
                        score: score as number,
                      }))
                      .sort((a, b) => b.score - a.score);

                    // 최소 2개 보장
                    if (sortedTypes.length < 2) {
                      const allTypes = ['spring', 'summer', 'autumn', 'winter'];
                      const missingTypes = allTypes.filter(
                        type => !sortedTypes.some(st => st.type === type)
                      );
                      while (
                        sortedTypes.length < 2 &&
                        missingTypes.length > 0
                      ) {
                        sortedTypes.push({
                          type: missingTypes.shift()!,
                          score: 50,
                        });
                      }
                    }

                    return sortedTypes.slice(0, 3);
                  }
                })().map((typeData, index) => {
                  // API 데이터인지 로컬 데이터인지 구분
                  const isApiData = 'name' in typeData;
                  const type = isApiData
                    ? (typeData as PersonalColorTypeData).type
                    : typeData.type;

                  const typeNames: Record<
                    string,
                    { name: string; emoji: string; color: string }
                  > = {
                    spring: { name: '봄 웜톤', emoji: '🌸', color: '#fab1a0' },
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
                  const typeInfo = typeNames[type];
                  const isSelected = expandedType === type;
                  const isHighestScore = index === 0; // 가장 점수가 높은 타입

                  return (
                    <Col key={type} xs={12} sm={8} md={5}>
                      <Badge.Ribbon
                        text="추천"
                        color={isHighestScore ? typeInfo.color : 'transparent'}
                        style={{ display: isHighestScore ? 'block' : 'none' }}
                      >
                        <Card
                          hoverable
                          onClick={() =>
                            setExpandedType(isSelected ? null : type)
                          }
                          className={`transition-all cursor-pointer text-center h-[100px] flex flex-col justify-center p-4 scale-[1.02] ${
                            isHighestScore
                              ? '!border-2 !border-purple-200 !bg-gradient-to-br from-purple-50 to-purple-100 shadow-md'
                              : ''
                          }`}
                        >
                          {/* 카드 내용 */}
                          <div className="text-xl">{typeInfo.emoji}</div>
                          <Title
                            level={5}
                            className={`mb-0 text-xs transition-all ${
                              isHighestScore
                                ? '!text-purple-600 !font-semibold'
                                : '!text-gray-800 !font-normal'
                            }`}
                            style={{ marginTop: '2px', wordBreak: 'keep-all' }}
                          >
                            {typeInfo.name}
                          </Title>
                        </Card>
                      </Badge.Ribbon>
                    </Col>
                  );
                })}
              </Row>
            </div>

            {/* 결과 메인 카드 - 동적 콘텐츠 */}
            {(() => {
              // API 결과가 있으면 우선 사용, 없으면 로컬 결과 사용
              const mainType = apiResult?.result_tone || result.type;
              // expandedType이 null이면 메인 타입, 아니면 선택된 타입
              const displayType =
                expandedType && expandedType !== 'toggle'
                  ? expandedType
                  : mainType;

              // 선택된 타입에 해당하는 API 데이터 찾기
              let selectedTypeData = null;
              if (apiResult?.top_types) {
                selectedTypeData = apiResult.top_types.find(
                  t => t.type === displayType
                );
              }

              // API 결과가 있으면 해당 데이터 우선 사용
              let displayName, displayDescription;
              if (selectedTypeData) {
                displayName = selectedTypeData.name;
                displayDescription = selectedTypeData.description;
              } else if (apiResult && displayType === apiResult.result_tone) {
                // 메인 타입이면서 selectedTypeData가 없는 경우 메인 API 데이터 사용
                displayName = apiResult.name;
                displayDescription = apiResult.description;
              } else {
                // 로컬 데이터 사용
                const allResults = {
                  spring: {
                    name: '봄 웜톤 🌸',
                    description: '밝고 생기 있는 봄날의 따뜻함을 담은 당신',
                  },
                  summer: {
                    name: '여름 쿨톤 💎',
                    description: '시원하고 우아한 여름날의 세련됨을 담은 당신',
                  },
                  autumn: {
                    name: '가을 웜톤 🍂',
                    description: '깊고 따뜻한 가을날의 포근함을 담은 당신',
                  },
                  winter: {
                    name: '겨울 쿨톤 ❄️',
                    description: '시원하고 강렬한 겨울날의 우아함을 담은 당신',
                  },
                };
                const localResult =
                  allResults[displayType as PersonalColorType];
                displayName = localResult.name;
                displayDescription = localResult.description;
              }

              // 배경 스타일은 타입별로 고정
              const allBackgrounds = {
                spring: {
                  background:
                    'linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%)',
                  color: '#2d3436',
                },
                summer: {
                  background:
                    'linear-gradient(135deg, #a8e6cf 0%, #dcedc8 100%)',
                  color: '#2d3436',
                },
                autumn: {
                  background:
                    'linear-gradient(135deg, #d4a574 0%, #8b4513 100%)',
                  color: '#ffffff',
                },
                winter: {
                  background:
                    'linear-gradient(135deg, #74b9ff 0%, #0984e3 100%)',
                  color: '#ffffff',
                },
              };
              const displayStyle =
                allBackgrounds[displayType as PersonalColorType];

              return (
                <div
                  className="p-4 rounded-2xl mb-4 text-center transition-all duration-300"
                  style={{
                    background: displayStyle.background,
                    color: displayStyle.color,
                  }}
                >
                  <Title
                    level={3}
                    style={{ color: displayStyle.color, margin: 0 }}
                  >
                    {displayName}
                  </Title>
                  <Text
                    style={{
                      color: displayStyle.color,
                      fontSize: '14px',
                      display: 'block',
                      marginTop: '8px',
                    }}
                  >
                    {displayDescription}
                  </Text>
                </div>
              );
            })()}

            {/* AI 전문가 분석 결과 */}
            {apiResult && (
              <Card
                className="mb-4"
                style={{ borderColor: '#7c3aed', borderWidth: '2px' }}
              >
                <div className="text-center mb-3">
                  <Title level={4} className="mb-1 text-purple-600">
                    🤖 AI 전문가 분석
                  </Title>
                  <Text className="text-gray-600 text-sm">
                    OpenAI가 당신의 답변을 분석한 결과입니다
                  </Text>
                </div>

                {/* 상위 타입들 표시 */}
                {apiResult.top_types && apiResult.top_types.length >= 2 && (
                  <div className="mb-4">
                    <Text strong className="text-gray-700 block mb-2 text-sm">
                      🏆 일치도가 높은 타입 순위 (상위{' '}
                      {Math.min(apiResult.top_types.length, 3)}개)
                    </Text>
                    <div className="flex flex-wrap justify-center gap-2">
                      {apiResult.top_types
                        .slice(0, 3)
                        .map((typeData, index) => {
                          const isFirst = index === 0;

                          return (
                            <div key={typeData.type} className="text-center">
                              <Tag
                                className="px-4 py-2 text-sm border-0 rounded-full"
                                style={{
                                  background: isFirst
                                    ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                                    : 'linear-gradient(135deg, #e2e8f0 0%, #cbd5e0 100%)',
                                  color: isFirst ? 'white' : '#4a5568',
                                  fontWeight: isFirst ? 'bold' : 'normal',
                                }}
                              >
                                {typeData.name}
                              </Tag>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                )}

                <div className="bg-purple-50 p-4 rounded-lg">
                  <Text className="whitespace-pre-line text-gray-700 leading-relaxed">
                    {apiResult.detailed_analysis}
                  </Text>
                </div>
              </Card>
            )}

            {/* 컬러 팔레트 - 동적 콘텐츠 */}
            {(() => {
              const mainType = apiResult?.result_tone || result.type;
              const displayType =
                expandedType && expandedType !== 'toggle'
                  ? expandedType
                  : mainType;

              // 선택된 타입에 해당하는 API 데이터 찾기
              let selectedTypeData = null;
              if (apiResult?.top_types) {
                selectedTypeData = apiResult.top_types.find(
                  t => t.type === displayType
                );
              }

              // API 결과가 있으면 해당 데이터 우선 사용
              let colorData;
              if (selectedTypeData) {
                colorData = {
                  swatches: selectedTypeData.color_palette || [],
                  keyColors:
                    selectedTypeData.color_palette?.map(
                      (_, index) => `색상 ${index + 1}`
                    ) || [],
                };
              } else if (apiResult && displayType === apiResult.result_tone) {
                colorData = {
                  swatches: apiResult.color_palette || [],
                  keyColors:
                    apiResult.color_palette?.map(
                      (_, index) => `색상 ${index + 1}`
                    ) || [],
                };
              } else {
                // 로컬 데이터 사용
                const allTypeData = {
                  spring: {
                    swatches: [
                      '#FF6F61',
                      '#FFD1B3',
                      '#FFE5B4',
                      '#98FB98',
                      '#40E0D0',
                      '#E6E6FA',
                      '#FFFACD',
                    ],
                    keyColors: [
                      '코럴',
                      '피치',
                      '골든 옐로우',
                      '터콰이즈',
                      '라벤더',
                    ],
                  },
                  summer: {
                    swatches: [
                      '#F8BBD9',
                      '#E6E6FA',
                      '#ADD8E6',
                      '#DDA0DD',
                      '#D3D3D3',
                      '#FFB6C1',
                      '#B0E0E6',
                    ],
                    keyColors: [
                      '로즈',
                      '라벤더',
                      '소프트 블루',
                      '더스티핑크',
                      '라이트 그레이',
                    ],
                  },
                  autumn: {
                    swatches: [
                      '#800020',
                      '#8B7355',
                      '#FFD700',
                      '#FF4500',
                      '#556B2F',
                      '#A0522D',
                      '#CD853F',
                    ],
                    keyColors: [
                      '버건디',
                      '카키',
                      '골드',
                      '딥 오렌지',
                      '올리브 그린',
                    ],
                  },
                  winter: {
                    swatches: [
                      '#000000',
                      '#FFFFFF',
                      '#4169E1',
                      '#FF1493',
                      '#DC143C',
                      '#50C878',
                      '#191970',
                    ],
                    keyColors: [
                      '블랙',
                      '퓨어 화이트',
                      '로얄블루',
                      '푸시아',
                      '트루레드',
                    ],
                  },
                };
                colorData = allTypeData[displayType as PersonalColorType];
              }

              return (
                <div className="mb-4">
                  <Text strong className="text-gray-700 block mb-2 text-sm">
                    🎨 당신만의 컬러 팔레트
                  </Text>
                  <div className="flex flex-wrap justify-center gap-3 mb-3">
                    {colorData.swatches.slice(0, 5).map((color, index) => (
                      <Tooltip
                        key={index}
                        title={`${color} 복사`}
                        placement="top"
                      >
                        <div
                          className="cursor-pointer transition-transform hover:scale-110 active:scale-95 group"
                          onClick={() => {
                            navigator.clipboard.writeText(color);
                            message.success(`${color} 복사됨!`, 1.5);
                          }}
                        >
                          <div
                            className="w-12 h-12 rounded-full border-2 border-white shadow-md group-hover:shadow-lg transition-shadow"
                            style={{ backgroundColor: color }}
                            title={`${colorData.keyColors[index] || color}`}
                          />
                          <Text
                            className="text-center text-xs text-gray-600 block mt-1 font-mono"
                            style={{ fontSize: '10px' }}
                          >
                            {color}
                          </Text>
                        </div>
                      </Tooltip>
                    ))}
                  </div>
                </div>
              );
            })()}

            {/* 핵심 특징 - 동적 콘텐츠 */}
            {(() => {
              const mainType = apiResult?.result_tone || result.type;
              const displayType =
                expandedType && expandedType !== 'toggle'
                  ? expandedType
                  : mainType;

              // 선택된 타입에 해당하는 API 데이터 찾기
              let selectedTypeData = null;
              if (apiResult?.top_types) {
                selectedTypeData = apiResult.top_types.find(
                  t => t.type === displayType
                );
              }

              // API 결과가 있으면 해당 데이터 우선 사용
              let styles;
              if (selectedTypeData) {
                styles = selectedTypeData.style_keywords || [];
              } else if (apiResult && displayType === apiResult.result_tone) {
                styles = apiResult.style_keywords || [];
              } else {
                // 로컬 데이터 사용
                const allTypeStyles: Record<PersonalColorType, string[]> = {
                  spring: ['화사함', '발랄함', '생동감', '밝음', '따뜻함'],
                  summer: ['차분함', '세련됨', '우아함', '로맨틱', '부드러움'],
                  autumn: ['따뜻함', '성숙함', '깊이', '풍성함', '고급스러움'],
                  winter: [
                    '강렬함',
                    '고급스러움',
                    '시크함',
                    '도시적',
                    '명확함',
                  ],
                };
                styles = allTypeStyles[displayType as PersonalColorType];
              }

              return (
                <div className="mb-4">
                  <Text strong className="text-gray-700 block mb-2 text-sm">
                    ✨ 당신의 스타일
                  </Text>
                  <div className="flex flex-wrap justify-center gap-2">
                    {styles.map((style, index) => (
                      <Tag
                        key={index}
                        className="px-3 py-1 text-xs border-0 rounded-full"
                        style={{
                          background:
                            'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                          color: 'white',
                        }}
                      >
                        {style}
                      </Tag>
                    ))}
                  </div>
                </div>
              );
            })()}

            {/* 추천 메이크업 - 동적 콘텐츠 */}
            {(() => {
              const mainType = apiResult?.result_tone || result.type;
              const displayType =
                expandedType && expandedType !== 'toggle'
                  ? expandedType
                  : mainType;

              // 선택된 타입에 해당하는 API 데이터 찾기
              let selectedTypeData = null;
              if (apiResult?.top_types) {
                selectedTypeData = apiResult.top_types.find(
                  t => t.type === displayType
                );
              }

              // API 결과가 있으면 해당 데이터 우선 사용
              let makeup;
              if (selectedTypeData) {
                makeup = selectedTypeData.makeup_tips || [];
              } else if (apiResult && displayType === apiResult.result_tone) {
                makeup = apiResult.makeup_tips || [];
              } else {
                // 로컬 데이터 사용
                const allTypeMakeup: Record<PersonalColorType, string[]> = {
                  spring: [
                    '코럴 블러셔',
                    '피치 립',
                    '골든 아이섀도우',
                    '브라운 마스카라',
                  ],
                  summer: [
                    '로즈 블러셔',
                    '더스티핑크 립',
                    '라벤더 아이섀도우',
                    '브라운 마스카라',
                  ],
                  autumn: [
                    '오렌지 블러셔',
                    '브릭레드 립',
                    '골든브라운 아이섀도우',
                    '브라운 마스카라',
                  ],
                  winter: [
                    '푸시아 블러셔',
                    '트루레드 립',
                    '스모키 아이섀도우',
                    '블랙 마스카라',
                  ],
                };
                makeup = allTypeMakeup[displayType as PersonalColorType];
              }

              return (
                <div className="mb-6">
                  <Text strong className="text-gray-700 block mb-2 text-sm">
                    💄 추천 메이크업
                  </Text>
                  <div className="flex flex-wrap justify-center gap-2">
                    {makeup.map((item, index) => (
                      <Tag
                        key={index}
                        color="magenta"
                        className="px-2 py-1 text-xs"
                      >
                        {item}
                      </Tag>
                    ))}
                  </div>
                </div>
              );
            })()}

            {/* 액션 버튼 */}
            <div className="space-y-4">
              {/* 1행: 주요 기능 버튼들 (강조) */}
              <div className="flex gap-3 justify-center flex-wrap">
                <Button
                  size="large"
                  onClick={handleGoToMyPage}
                  className="px-8 shadow-lg"
                  style={{
                    background:
                      'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    border: 'none',
                    borderRadius: '12px',
                    color: 'white',
                    fontWeight: '600',
                    boxShadow: '0 8px 25px rgba(102, 126, 234, 0.4)',
                  }}
                >
                  마이페이지에서 결과 보기
                </Button>
                <Button
                  size="large"
                  icon={<MessageOutlined />}
                  onClick={handleGoToChatbot}
                  className="px-6 shadow-lg"
                  style={{
                    background:
                      'linear-gradient(135deg, #20c997 0%, #17a2b8 100%)',
                    border: 'none',
                    borderRadius: '12px',
                    color: 'white',
                    fontWeight: '600',
                    boxShadow: '0 8px 25px rgba(32, 201, 151, 0.4)',
                  }}
                >
                  AI 컨설턴트와 상담하기
                </Button>
              </div>

              {/* 2행: 보조 기능 버튼들 */}
              <div className="flex gap-3 justify-center flex-wrap">
                <Button
                  size="large"
                  icon={<ReloadOutlined />}
                  onClick={handleRestart}
                  className="px-6"
                  style={{
                    borderColor: '#d1d5db',
                    color: '#6b7280',
                    borderRadius: '10px',
                    background: 'white',
                  }}
                >
                  다시 테스트
                </Button>
                <Button
                  size="large"
                  onClick={handleGoToHome}
                  className="px-8"
                  style={{
                    background:
                      'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    border: 'none',
                    borderRadius: '10px',
                    color: 'white',
                  }}
                >
                  홈으로 가기
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  // 질문 진행 화면
  if (currentQuestion) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}
      >
        <div className="w-full max-w-md mx-auto p-4">
          {/* 메인 카드 */}
          <Card
            className="shadow-2xl border-0"
            style={{
              borderRadius: '20px',
              background: 'rgba(255, 255, 255, 0.95)',
              backdropFilter: 'blur(10px)',
            }}
          >
            {/* 헤더 */}
            <div className="text-center mb-4">
              <div className="flex items-center justify-center mb-3">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white text-lg font-bold"
                  style={{
                    background:
                      'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  }}
                >
                  {progress.currentQuestion}
                </div>
              </div>

              <Title level={4} className="mb-1 text-gray-800">
                {currentQuestion.category}
              </Title>

              <Text className="text-gray-600 text-base">
                {currentQuestion.question}
              </Text>
            </div>

            {/* 진행도 바 */}
            <div className="mb-6">
              <div className="flex justify-between items-center mb-2">
                <Text className="text-sm text-gray-500">진행률</Text>
                <Text className="text-sm font-semibold text-gray-700">
                  {Math.round(
                    (progress.currentQuestion / progress.totalQuestions) * 100
                  )}
                  %
                </Text>
              </div>
              <Progress
                percent={Math.round(
                  (progress.currentQuestion / progress.totalQuestions) * 100
                )}
                strokeColor={{
                  '0%': '#667eea',
                  '100%': '#764ba2',
                }}
                trailColor="#f3f4f6"
                showInfo={false}
              />
            </div>

            {/* 선택지 */}
            <div className="mb-8">
              <Space direction="vertical" size="middle" className="w-full">
                {currentQuestion.options.map(option => (
                  <div
                    key={option.id}
                    className={`
                      w-full p-4 border-2 rounded-xl cursor-pointer transition-all duration-200
                      ${
                        selectedAnswer === option.id
                          ? '!border-purple-400 !bg-purple-50'
                          : '!border-gray-200 !hover:border-purple-300 !hover:bg-gray-50'
                      }
                    `}
                    onClick={() => handleAnswerSelect(option.id)}
                  >
                    <div className="flex items-center">
                      <div
                        className={`
                          w-5 h-5 rounded-full border-2 mr-3 flex items-center justify-center
                          ${
                            selectedAnswer === option.id
                              ? '!border-purple-500 !bg-purple-500'
                              : '!border-gray-300'
                          }
                        `}
                      >
                        {selectedAnswer === option.id && (
                          <div className="w-2 h-2 rounded-full !bg-white"></div>
                        )}
                      </div>
                      <Text className="text-base !text-gray-700">
                        {option.label}
                      </Text>
                    </div>
                  </div>
                ))}
              </Space>
            </div>

            {/* 네비게이션 버튼 */}
            <div className="flex justify-between items-center">
              <Button
                icon={<ArrowLeftOutlined />}
                onClick={handlePrevious}
                disabled={progress.currentQuestion === 1}
                size="large"
                className="flex items-center"
                style={{
                  borderColor: '#d1d5db',
                  color: progress.currentQuestion === 1 ? '#9ca3af' : '#6b7280',
                }}
              >
                이전
              </Button>

              <Button
                type="primary"
                icon={<ArrowRightOutlined />}
                onClick={handleNext}
                disabled={!selectedAnswer || isAnalyzing}
                loading={
                  isAnalyzing &&
                  progress.currentQuestion === progress.totalQuestions
                }
                size="large"
                className="flex items-center px-8"
                style={{
                  background:
                    !selectedAnswer || isAnalyzing
                      ? '#d1d5db'
                      : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  border: 'none',
                  borderRadius: '10px',
                }}
              >
                {progress.currentQuestion === progress.totalQuestions
                  ? isAnalyzing
                    ? '분석 중...'
                    : '결과 보기'
                  : '다음'}
              </Button>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  // 로딩 또는 오류 상태
  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <div className="w-full max-w-md mx-auto p-4">
        <Card
          className="shadow-2xl border-0 text-center"
          style={{
            borderRadius: '20px',
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
          }}
        >
          <Alert
            message="테스트를 불러오는 중입니다..."
            type="info"
            showIcon
            style={{
              background: 'transparent',
              border: 'none',
            }}
          />
        </Card>
      </div>
    </div>
  );
};

export default PersonalColorTest;
