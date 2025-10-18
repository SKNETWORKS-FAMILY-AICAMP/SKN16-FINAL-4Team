import React, { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Typography,
  Button,
  Avatar,
  Modal,
  message,
  List,
  Tag,
  Spin,
  Divider,
  Tabs,
  Tooltip,
  Dropdown,
} from 'antd';
import {
  UserOutlined,
  ManOutlined,
  WomanOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  CalendarOutlined,
  TrophyOutlined,
  MoreOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useCurrentUser, useDeleteCurrentUser } from '@/hooks/useUser';
import { useSurveyResultsLive, useDeleteSurvey } from '@/hooks/useSurvey';
import { getAvatarRenderInfo } from '@/utils/genderUtils';
import RouterPaths from '@/routes/Router';
import type { SurveyResultDetail } from '@/api/survey';
import type { PersonalColorType } from '@/types/personalColor';

const { Title, Text } = Typography;

/**
 * 마이페이지 컴포넌트
 */
const MyPage: React.FC = () => {
  const { data: user, isLoading } = useCurrentUser();
  const { data: surveyResults, isLoading: isLoadingSurveys } =
    useSurveyResultsLive();
  const navigate = useNavigate();
  const deleteCurrentUser = useDeleteCurrentUser();
  const deleteSurvey = useDeleteSurvey();

  // 상세보기 모달 상태
  const [selectedResult, setSelectedResult] =
    useState<SurveyResultDetail | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // 퍼스널 컬러 테스트로 이동
  const handleGoToTest = () => {
    navigate(RouterPaths.PersonalColorTest);
  };

  // 진단 결과 상세보기
  const handleViewDetail = (result: SurveyResultDetail) => {
    setSelectedResult(result);
    setIsDetailModalOpen(true);
  };

  // 상세보기 모달 닫기
  const handleCloseDetailModal = () => {
    setIsDetailModalOpen(false);
    setSelectedResult(null);
  };

  // 진단 기록 삭제 확인
  const handleDeleteSurvey = (surveyId: number, resultName: string) => {
    Modal.confirm({
      title: '진단 기록 삭제',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div className="mt-4">
          <p>정말로 이 진단 기록을 삭제하시겠습니까?</p>
          <p className="text-gray-600 text-sm mt-2">
            <strong>{resultName}</strong>
          </p>
          <p className="text-red-500 text-sm mt-2">
            삭제된 기록은 복구할 수 없습니다.
          </p>
        </div>
      ),
      okText: '삭제',
      okType: 'danger',
      cancelText: '취소',
      onOk() {
        return deleteSurvey.mutateAsync(surveyId);
      },
    });
  };

  // 회원 탈퇴 확인 모달
  const handleDeleteAccount = () => {
    Modal.confirm({
      title: '비밀번호 확인',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div className="mt-4">
          <p className="mb-3">
            탈퇴하면 모든 데이터가 삭제되며 복구할 수 없습니다.
          </p>
          <input
            id="password-input"
            type="password"
            placeholder="비밀번호를 입력해주세요"
            className="w-full p-2 border border-gray-300 rounded"
          />
        </div>
      ),
      okText: '탈퇴하기',
      okType: 'danger',
      cancelText: '취소',
      onOk() {
        const passwordInput = document.getElementById(
          'password-input'
        ) as HTMLInputElement;
        const password = passwordInput?.value;

        if (!password) {
          message.error('비밀번호를 입력해주세요.');
          return Promise.reject();
        }

        return deleteCurrentUser
          .mutateAsync({ password })
          .then(() => {
            navigate(RouterPaths.Home);
          })
          .catch(() => {
            return Promise.reject();
          });
      },
    });
  };

  // 성별에 따른 아바타 렌더링
  const getGenderAvatar = () => {
    const avatarInfo = getAvatarRenderInfo(user?.gender, user?.id);

    if (avatarInfo.content) {
      // 이모티콘 방식
      return avatarInfo;
    } else {
      // 아이콘 방식 (fallback)
      let icon;
      switch (avatarInfo.iconType) {
        case 'man':
          icon = <ManOutlined />;
          break;
        case 'woman':
          icon = <WomanOutlined />;
          break;
        default:
          icon = <UserOutlined />;
          break;
      }
      return {
        content: icon,
        className: avatarInfo.className,
        style: avatarInfo.style,
      };
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center pt-20">
        <div>로딩 중...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center pt-20">
        <Card className="shadow-xl border-0" style={{ borderRadius: '16px' }}>
          <div className="text-center p-8">
            <Title level={3}>로그인이 필요합니다</Title>
            <Text>마이페이지를 보려면 로그인해주세요.</Text>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pt-20 pb-8 mt-4">
      <div className="max-w-6xl mx-auto px-4">
        <Title level={2} className="mb-8 !text-gray-800">
          마이페이지
        </Title>

        <Row gutter={[32, 32]}>
          {/* 왼쪽 박스 - 프로필 정보 */}
          <Col xs={24} lg={10}>
            <Card
              className="shadow-sm border border-gray-200"
              style={{ borderRadius: '8px' }}
            >
              {/* 아바타, 닉네임, 이름 센터 배치 */}
              <div className="flex flex-col items-center justify-center py-2 border-b border-gray-100">
                {(() => {
                  const avatarConfig = getGenderAvatar();

                  return (
                    <Avatar
                      size={100}
                      className={`${avatarConfig.className} mb-4`}
                      style={avatarConfig.style}
                    >
                      {typeof avatarConfig.content === 'string' ? (
                        <span style={{ fontSize: '50px' }}>
                          {avatarConfig.content}
                        </span>
                      ) : (
                        avatarConfig.content
                      )}
                    </Avatar>
                  );
                })()}
                <div className="flex items-center gap-2">
                  <Title level={3} className="!mb-2 !text-gray-800 text-center">
                    @{user.nickname}
                  </Title>
                  <Text className="!text-gray-500 text-lg text-center">
                    {user.username}
                  </Text>
                </div>
              </div>

              {/* 진단 기록, 저장된 결과 데이터 */}
              <div className="p-2">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600 mb-1">
                      {surveyResults?.length || 0}
                    </div>
                    <Text className="text-gray-600">진단 기록</Text>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600 mb-1">
                      {surveyResults?.length || 0}
                    </div>
                    <Text className="text-gray-600">저장된 결과</Text>
                  </div>
                </div>
              </div>
            </Card>
          </Col>

          {/* 오른쪽 박스 - 상세 정보 */}
          <Col xs={24} lg={14}>
            <Card
              className="shadow-sm border border-gray-200"
              style={{ borderRadius: '8px' }}
            >
              <div className="px-6 py-2">
                <Title level={4} className="mb-6 text-gray-800">
                  상세 정보
                </Title>

                <div className="grid grid-cols-2 gap-6">
                  {/* 첫 번째 행 */}
                  <div className="flex flex-col py-3 border-b border-gray-100">
                    <Text strong className="text-gray-700 mb-2">
                      이메일
                    </Text>
                    <Text className="text-gray-900">{user.email}</Text>
                  </div>

                  <div className="flex flex-col py-3 border-b border-gray-100">
                    <Text strong className="text-gray-700 mb-2">
                      성별
                    </Text>
                    <Text className="text-gray-900">
                      {user.gender || '미설정'}
                    </Text>
                  </div>

                  {/* 두 번째 행 */}
                  <div className="flex flex-col py-3">
                    <Text strong className="text-gray-700 mb-2">
                      가입일
                    </Text>
                    <Text className="text-gray-900">
                      {user.create_date
                        ? new Date(user.create_date).toLocaleDateString('ko-KR')
                        : '정보 없음'}
                    </Text>
                  </div>

                  <div className="flex flex-col py-3">
                    <Text strong className="text-gray-700 mb-2">
                      계정 상태
                    </Text>
                    <div className="flex items-center">
                      <div
                        className={`w-2 h-2 rounded-full mr-2 ${
                          user.is_active ? 'bg-green-500' : 'bg-red-500'
                        }`}
                      ></div>
                      <Text
                        className={
                          user.is_active ? 'text-green-600' : 'text-red-600'
                        }
                      >
                        {user.is_active ? '활성' : '탈퇴'}
                      </Text>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </Col>
        </Row>

        {/* 최근 진단 기록 섹션 */}
        <Row className="mt-8">
          <Col span={24}>
            <Card
              className="shadow-sm border border-gray-200"
              style={{ borderRadius: '8px' }}
            >
              <div className="px-6 py-2">
                <Title level={4} className="mb-6 text-gray-800">
                  최근 진단 기록
                </Title>

                {isLoadingSurveys ? (
                  <div className="text-center py-12">
                    <Spin size="large" />
                    <div className="mt-4">
                      <Text className="text-gray-500">
                        진단 기록을 불러오는 중...
                      </Text>
                    </div>
                  </div>
                ) : !surveyResults || surveyResults.length === 0 ? (
                  <div className="text-center py-12 bg-gray-50 rounded-lg">
                    <Text className="text-gray-500 text-base">
                      아직 진단 기록이 없습니다.
                    </Text>
                    <Text className="text-gray-400 text-sm block mt-2">
                      진단을 완료하면 AI 상담도 이용할 수 있습니다.
                    </Text>
                    <div className="mt-6 space-y-3">
                      <div>
                        <Button
                          type="primary"
                          size="large"
                          onClick={handleGoToTest}
                        >
                          첫 진단 시작하기
                        </Button>
                      </div>
                      <div>
                        <Button
                          disabled
                          icon={<MessageOutlined />}
                          className="text-gray-400"
                        >
                          AI 상담 받기 (진단 후 이용 가능)
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <List
                      itemLayout="vertical"
                      size="large"
                      pagination={{
                        pageSize: 5,
                        showSizeChanger: false,
                        showQuickJumper: false,
                      }}
                      dataSource={surveyResults}
                      renderItem={result => (
                        <List.Item
                          key={result.id}
                          className="bg-white border border-gray-100 rounded-lg p-4 hover:shadow-md transition-shadow"
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="flex items-center mb-2">
                                <Text className="!text-gray-500 text-sm flex items-center">
                                  <CalendarOutlined className="mr-1" />
                                  {new Date(
                                    result.created_at
                                  ).toLocaleDateString('ko-KR', {
                                    year: 'numeric',
                                    month: 'long',
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit',
                                  })}
                                </Text>
                              </div>

                              <div className="mb-2">
                                <Text strong className="text-lg !text-gray-800">
                                  {result.result_name ||
                                    `${result.result_tone.toUpperCase()} 타입`}
                                </Text>
                              </div>

                              {result.result_description && (
                                <Text className="!text-gray-600 text-sm block mb-2">
                                  {result.result_description.length > 100
                                    ? `${result.result_description.substring(
                                        0,
                                        100
                                      )}...`
                                    : result.result_description}
                                </Text>
                              )}
                            </div>

                            <div className="flex items-center gap-2">
                              <Button
                                type="link"
                                onClick={() => handleViewDetail(result)}
                                className="text-blue-600"
                              >
                                상세보기
                              </Button>
                              <Dropdown
                                menu={{
                                  items: [
                                    {
                                      key: 'delete',
                                      label: '삭제',
                                      icon: <DeleteOutlined />,
                                      danger: true,
                                      onClick: () =>
                                        handleDeleteSurvey(
                                          result.id,
                                          result.result_name ||
                                            `${result.result_tone.toUpperCase()} 타입`
                                        ),
                                    },
                                  ],
                                }}
                                trigger={['click']}
                              >
                                <Button
                                  type="text"
                                  icon={<MoreOutlined />}
                                  size="small"
                                />
                              </Dropdown>
                            </div>
                          </div>
                        </List.Item>
                      )}
                    />

                    <div className="text-center pt-4 border-t border-gray-100 space-y-3">
                      <div className="flex justify-center gap-3">
                        <Button
                          type="default"
                          icon={<MessageOutlined />}
                          onClick={() => navigate(RouterPaths.Chatbot)}
                        >
                          AI 상담 받기
                        </Button>
                        <Button type="primary" onClick={handleGoToTest}>
                          새 진단 시작하기
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </Col>
        </Row>

        {/* 계정 관리 섹션 */}
        <Row className="mt-8">
          <Col span={24}>
            <Card
              className="shadow-sm border border-red-200"
              style={{ borderRadius: '8px' }}
            >
              <div className="px-6 py-2">
                <Title level={4} className="mb-4 text-red-600">
                  계정 관리
                </Title>
                <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                  <div className="flex justify-between items-center">
                    <div>
                      <Text strong className="text-red-700">
                        회원 탈퇴
                      </Text>
                      <div className="mt-1">
                        <Text className="text-red-600 text-sm">
                          탈퇴 시 모든 개인정보와 진단 기록이 영구적으로
                          삭제됩니다.
                        </Text>
                      </div>
                    </div>
                    <Button
                      danger
                      icon={<DeleteOutlined />}
                      onClick={handleDeleteAccount}
                    >
                      회원 탈퇴
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          </Col>
        </Row>
      </div>

      {/* 진단 결과 상세보기 모달 */}
      <Modal
        title="진단 결과 상세"
        open={isDetailModalOpen}
        onCancel={handleCloseDetailModal}
        footer={[
          <Button
            key="delete"
            danger
            icon={<DeleteOutlined />}
            onClick={() => {
              if (selectedResult) {
                handleDeleteSurvey(
                  selectedResult.id,
                  selectedResult.result_name ||
                    `${selectedResult.result_tone.toUpperCase()} 타입`
                );
                handleCloseDetailModal();
              }
            }}
          >
            삭제
          </Button>,
          <Button key="close" onClick={handleCloseDetailModal}>
            닫기
          </Button>,
        ]}
        width={700}
      >
        {selectedResult && (
          <div className="space-y-6 py-2">
            {/* Top Types 결과 - Tabs UI */}
            {selectedResult.top_types &&
              selectedResult.top_types.length > 0 && (
                <div>
                  <div className="flex justify-between">
                    <Title level={5} className="mb-4 flex items-center">
                      <TrophyOutlined className="mr-2 text-yellow-500" />
                      퍼스널컬러 분석 결과
                    </Title>
                    <Text className="!text-gray-500 flex items-center">
                      <CalendarOutlined className="mr-1" />
                      {new Date(selectedResult.created_at).toLocaleDateString(
                        'ko-KR',
                        {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        }
                      )}
                    </Text>
                  </div>

                  <Tabs
                    defaultActiveKey={selectedResult.top_types[0]?.type}
                    items={selectedResult.top_types
                      .slice(0, 3)
                      .map((typeData, index) => {
                        const isHighestScore = index === 0;

                        // 타입별 정보
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
                        const typeInfo =
                          typeNames[typeData.type] || typeNames.spring;

                        // 배경 스타일 (PersonalColorTest와 동일)
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
                          allBackgrounds[typeData.type as PersonalColorType];

                        // 컬러 데이터 (PersonalColorTest와 동일)
                        const colorData = {
                          swatches: typeData.color_palette || [],
                          keyColors:
                            typeData.color_palette?.map(
                              (_, idx) => `색상 ${idx + 1}`
                            ) || [],
                        };

                        return {
                          key: typeData.type,
                          label: (
                            <div className="flex items-center px-2 gap-1">
                              {isHighestScore && (
                                <Tag color="gold" className="ml-1 text-xs">
                                  추천
                                </Tag>
                              )}
                              <span className="mr-1">{typeInfo.emoji}</span>
                              <span
                                className={
                                  isHighestScore
                                    ? 'font-bold text-purple-600'
                                    : ''
                                }
                              >
                                {typeData.name}
                              </span>
                            </div>
                          ),
                          children: (
                            <div className="space-y-4">
                              {/* 메인 타입 카드 (PersonalColorTest와 동일) */}
                              <div
                                className="p-4 rounded-2xl text-center transition-all duration-300"
                                style={{
                                  background: displayStyle.background,
                                  color: displayStyle.color,
                                }}
                              >
                                <Title
                                  level={3}
                                  style={{
                                    color: displayStyle.color,
                                    margin: 0,
                                  }}
                                >
                                  {typeData.name}
                                </Title>
                                <Text
                                  style={{
                                    color: displayStyle.color,
                                    fontSize: '14px',
                                    display: 'block',
                                    marginTop: '8px',
                                  }}
                                >
                                  {typeData.description}
                                </Text>
                              </div>

                              {/* 컬러 팔레트 (PersonalColorTest와 동일) */}
                              {colorData.swatches.length > 0 && (
                                <div>
                                  <Text
                                    strong
                                    className="!text-gray-700 block mb-2 text-sm"
                                  >
                                    🎨 당신만의 컬러 팔레트
                                  </Text>
                                  <div className="flex flex-wrap justify-center gap-3 mb-3">
                                    {colorData.swatches
                                      .slice(0, 8)
                                      .map((color, colorIndex) => (
                                        <Tooltip
                                          key={colorIndex}
                                          title={`${color} 복사`}
                                          placement="top"
                                        >
                                          <div
                                            className="cursor-pointer transition-transform hover:scale-110 active:scale-95 group"
                                            onClick={() => {
                                              navigator.clipboard.writeText(
                                                color
                                              );
                                              message.success(
                                                `${color} 복사됨!`
                                              );
                                            }}
                                          >
                                            <div
                                              className="w-12 h-12 rounded-full border-2 border-white shadow-lg group-hover:shadow-xl transition-shadow"
                                              style={{ backgroundColor: color }}
                                            />
                                            <Text className="text-xs text-center block mt-1 !text-gray-600">
                                              {color}
                                            </Text>
                                          </div>
                                        </Tooltip>
                                      ))}
                                  </div>
                                </div>
                              )}

                              {/* 스타일 키워드 */}
                              {typeData.style_keywords &&
                                typeData.style_keywords.length > 0 && (
                                  <div>
                                    <Text
                                      strong
                                      className="!text-gray-700 block mb-2 text-sm"
                                    >
                                      ✨ 스타일 키워드
                                    </Text>
                                    <div className="flex flex-wrap gap-2">
                                      {typeData.style_keywords.map(
                                        (keyword, keywordIndex) => (
                                          <Tag
                                            key={keywordIndex}
                                            color="geekblue"
                                          >
                                            {keyword}
                                          </Tag>
                                        )
                                      )}
                                    </div>
                                  </div>
                                )}

                              {/* 메이크업 팁 */}
                              {typeData.makeup_tips &&
                                typeData.makeup_tips.length > 0 && (
                                  <div>
                                    <Text
                                      strong
                                      className="!text-gray-700 block mb-2 text-sm"
                                    >
                                      💄 메이크업 팁
                                    </Text>
                                    <div className="flex flex-wrap gap-2">
                                      {typeData.makeup_tips.map(
                                        (tip, tipIndex) => (
                                          <Tag key={tipIndex} color="volcano">
                                            {tip}
                                          </Tag>
                                        )
                                      )}
                                    </div>
                                  </div>
                                )}
                            </div>
                          ),
                        };
                      })}
                    className="mb-4"
                  />
                </div>
              )}

            {/* 컬러 팔레트 (기존 코드 유지하되 top_types가 있을 때는 숨김) */}
            {selectedResult.color_palette &&
              selectedResult.color_palette.length > 0 &&
              (!selectedResult.top_types ||
                selectedResult.top_types.length === 0) && (
                <div>
                  <Title level={5} className="mb-3">
                    추천 컬러 팔레트
                  </Title>
                  <div className="flex flex-wrap gap-2">
                    {selectedResult.color_palette.map((color, index) => (
                      <div
                        key={index}
                        className="flex items-center bg-white border rounded-lg p-2 shadow-sm"
                      >
                        <div
                          className="w-6 h-6 rounded mr-2 border"
                          style={{ backgroundColor: color }}
                        />
                        <Text className="text-sm">{color}</Text>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {/* 스타일 키워드 (기존 코드 유지하되 top_types가 있을 때는 숨김) */}
            {selectedResult.style_keywords &&
              selectedResult.style_keywords.length > 0 &&
              (!selectedResult.top_types ||
                selectedResult.top_types.length === 0) && (
                <div>
                  <Title level={5} className="mb-3">
                    스타일 키워드
                  </Title>
                  <div className="flex flex-wrap gap-2">
                    {selectedResult.style_keywords.map((keyword, index) => (
                      <Tag key={index} color="geekblue">
                        {keyword}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}

            {/* 메이크업 팁 (기존 코드 유지하되 top_types가 있을 때는 숨김) */}
            {selectedResult.makeup_tips &&
              selectedResult.makeup_tips.length > 0 &&
              (!selectedResult.top_types ||
                selectedResult.top_types.length === 0) && (
                <div>
                  <Title level={5} className="mb-3">
                    메이크업 팁
                  </Title>
                  <div className="flex flex-wrap gap-2">
                    {selectedResult.makeup_tips.map((tip, index) => (
                      <Tag key={index} color="volcano">
                        {tip}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}

            {/* 상세 분석 (AI 생성) */}
            {selectedResult.detailed_analysis && (
              <div>
                <Divider />
                <Title level={5} className="mb-3">
                  AI 상세 분석
                </Title>
                <div className="bg-gradient-to-r from-purple-50 to-pink-50 p-4 rounded-lg">
                  <Text className="!text-gray-700 leading-relaxed whitespace-pre-line">
                    {selectedResult.detailed_analysis}
                  </Text>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default MyPage;
