import React from 'react';
import { Typography, Button, Card, Row, Col, Space } from 'antd';
import { HeartOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import RouterPaths from '@/routes/Router';

const { Title, Paragraph } = Typography;

const HomePage: React.FC = () => {
  const navigate = useNavigate();

  const handleStartTest = () => {
    // navigate(RouterPaths.PersonalColorTest); // 기존 설문 방식 (비활성화)
    navigate(RouterPaths.Chatbot); // 대화형 진단으로 변경
  };

  return (
    <main className="max-w-6xl mx-auto px-4 py-12">
      <div className="text-center mb-16">
        <Title level={1} className="gradient-text text-5xl mb-4">
          나만의 퍼스널 컬러를 찾아보세요
        </Title>
        <Paragraph className="text-xl !text-gray-600 mb-8 max-w-2xl mx-auto">
          사진 업로드와 AI 전문가와의 대화를 통해 가장 어울리는 퍼스널 컬러를 분석해드립니다.<br />
          이미지 분석과 맞춤형 상담으로 정확한 진단을 받아보세요.
        </Paragraph>
        <Space size="large">
          <Button
            type="primary"
            size="large"
            icon={<PlayCircleOutlined />}
            className="px-8 py-6 h-auto"
            onClick={handleStartTest}
          >
            AI 전문가와 상담하기
          </Button>
        </Space>
      </div>

      {/* Features Section */}
      <Row gutter={[32, 32]} className="mb-16">
        <Col xs={24} md={8}>
          <Card className="text-center h-full card-hover" variant={'outlined'}>
            <div className="text-4xl mb-4">📷</div>
            <Title level={4}>이미지 업로드 분석</Title>
            <Paragraph className="!text-gray-600">
              사진을 업로드하면 AI가 얼굴 분석을 통해 정확한 퍼스널 컬러를 진단합니다.
            </Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="text-center h-full card-hover" variant={'outlined'}>
            <div className="text-4xl mb-4">💬</div>
            <Title level={4}>AI 전문가와 대화</Title>
            <Paragraph className="text-gray-600">
              전문적인 AI와 자연스러운 대화를 통해 맞춤형 퍼스널 컬러 상담을 받아보세요.
            </Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="text-center h-full card-hover" variant={'outlined'}>
            <div className="text-4xl mb-4">🎨</div>
            <Title level={4}>정확한 AI 분석</Title>
            <Paragraph className="!text-gray-600">
              이미지 분석과 대화 내용을 종합하여 가장 정확한 퍼스널 컬러를 추천드립니다.
            </Paragraph>
          </Card>
        </Col>
      </Row>

      {/* CTA Section */}
      <Card className="text-center !bg-gradient-to-r from-blue-500 to-purple-600 border-0">
        <div className="text-white">
          <Title level={2} className="!text-white mb-4">
            지금 바로 시작해보세요!
          </Title>
          <Paragraph className="!text-blue-100 text-lg mb-6">
            무료 회원가입 후 AI 전문가와 대화하며 나만의 퍼스널 컬러를 발견해보세요
          </Paragraph>
          <Button
            type="default"
            size="large"
            icon={<HeartOutlined />}
            className="px-8 py-6 h-auto"
            onClick={handleStartTest}
          >
            무료로 AI 상담 시작하기
          </Button>
        </div>
      </Card>
    </main>
  );
};

export default HomePage;