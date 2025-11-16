import React, { useState } from 'react';
import { formatKoreanDate } from '@/utils/dateUtils';
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
  Spin,
  Dropdown,
} from 'antd';
import {
  DeleteOutlined,
  ExclamationCircleOutlined,
  CalendarOutlined,
  MoreOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  useCurrentUser,
  useDeleteCurrentUser,
  useUserStats,
} from '@/hooks/useUser';
import { getAvatarRenderInfo } from '@/utils/genderUtils';
import RouterPaths from '@/routes/Router';
import { useSurveyResultsLive, useDeleteSurvey } from '@/hooks/useSurvey';
import type { SurveyResultDetail } from '@/api/survey';
import DiagnosisDetailModal from '@/components/DiagnosisDetailModal';

const { Title, Text } = Typography;

/**
 * 마이페이지 컴포넌트
 */
const MyPage: React.FC = () => {
  const { data: user, isLoading } = useCurrentUser();
  const { data: userStats, isLoading: isLoadingStats } = useUserStats();
  const { data: surveyResults, isLoading: isLoadingSurveys } =
    useSurveyResultsLive();
  const navigate = useNavigate();
  const deleteCurrentUser = useDeleteCurrentUser();
  const deleteSurvey = useDeleteSurvey();

  // 상세보기 모달 상태
  const [selectedResult, setSelectedResult] =
    useState<SurveyResultDetail | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  // 페이징 상태
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 5;

  // AI 전문가 상담으로 이동
  const handleAIConsultation = () => {
    // navigate(RouterPaths.PersonalColorTest); // 기존 설문 방식 (비활성화)
    navigate(RouterPaths.Chatbot); // 대화형 진단으로 변경
  };

  // 진단 결과 상세보기
  const handleViewDetail = (result: SurveyResultDetail) => {
    setSelectedResult(result);
    setIsDetailModalOpen(true);
  };

  // 상세보기 모달 닫기 - 컴포넌트 초기화
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

  // 아바타 렌더링: getAvatarRenderInfo를 직접 사용

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
    <div className="min-h-screen bg-gray-50 pt-8 pb-8 mt-1">
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
                  const avatarConfig = getAvatarRenderInfo(
                    user?.gender,
                    user?.id
                  );
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

              {/* 진단 기록, 저장된 결과, 채팅 세션 데이터 */}
              <div className="p-2">
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center">
                    <div className="text-xl font-bold text-blue-600 mb-1">
                      {isLoadingStats ? '-' : userStats?.total_surveys || 0}
                    </div>
                    <Text className="!text-gray-600 text-sm">진단 기록</Text>
                  </div>
                  <div className="text-center">
                    <div className="text-xl font-bold text-green-600 mb-1">
                      {isLoadingStats ? '-' : userStats?.saved_results || 0}
                    </div>
                    <Text className="!text-gray-600 text-sm">저장된 결과</Text>
                  </div>
                  <div className="text-center">
                    <div className="text-xl font-bold text-purple-600 mb-1">
                      {isLoadingStats ? '-' : userStats?.chat_sessions || 0}
                    </div>
                    <Text className="!text-gray-600 text-sm">AI 상담</Text>
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
                        ? formatKoreanDate(user.create_date)
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
                <div className="flex items-center justify-between">
                  <Title level={4} className="mb-6 text-gray-800">
                    최근 진단 기록
                  </Title>
                  <Text className="!text-gray-500 !text-sm">
                    총 {surveyResults?.length || 0}건
                  </Text>
                </div>

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
                      AI 전문가와 대화하며 퍼스널컬러 진단을 받아보세요.
                    </Text>
                    <div className="mt-6">
                      <Button
                        type="primary"
                        size="large"
                        icon={<MessageOutlined />}
                        onClick={handleAIConsultation}
                      >
                        AI 전문가와 퍼스널컬러 상담하기
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <List
                      itemLayout="vertical"
                      size="large"
                      pagination={{
                        current: currentPage,
                        pageSize: pageSize,
                        total: surveyResults.length,
                        onChange: (page) => setCurrentPage(page),
                        showSizeChanger: false,
                        showQuickJumper: true,
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
                                  {formatKoreanDate(result.created_at, true)}
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
                      <div className="flex justify-center">
                        <Button
                          type="primary"
                          icon={<MessageOutlined />}
                          onClick={() => navigate(RouterPaths.Chatbot)}
                          size="large"
                        >
                          AI 전문가와 퍼스널컬러 상담하기
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
      <DiagnosisDetailModal
        open={isDetailModalOpen}
        onClose={handleCloseDetailModal}
        selectedResult={selectedResult}
        onDelete={handleDeleteSurvey}
        showDeleteButton={true}
        recentResults={selectedResult ? [selectedResult] : []}
      />
    </div>
  );
};

export default MyPage;
