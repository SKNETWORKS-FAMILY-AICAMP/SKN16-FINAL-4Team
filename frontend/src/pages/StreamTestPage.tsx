import React, { useState } from 'react';
import { Button, Input, Card, Typography, Space, Spin } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import { chatbotApi } from '@/api/chatbot';

const { Title, Text } = Typography;
const { TextArea } = Input;

/**
 * 스트리밍 테스트 페이지
 * 백엔드 스트리밍 API가 제대로 작동하는지 확인하기 위한 간단한 테스트 페이지
 */
const StreamTestPage: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [streamedResponse, setStreamedResponse] = useState('');
  const [historyId, setHistoryId] = useState<number | undefined>();
  const [isStreaming, setIsStreaming] = useState(false);
  const [metadata, setMetadata] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSendMessage = async () => {
    if (!question.trim() || isStreaming) return;

    setIsStreaming(true);
    setStreamedResponse('');
    setMetadata(null);
    setError(null);

    let accumulatedContent = '';

    try {
      await chatbotApi.analyze(
        { 
          question: question.trim(), 
          history_id: historyId 
        },
        (data) => {
          console.log('📦 Received chunk:', data);

          if (data.type === 'history_id' && data.history_id) {
            setHistoryId(data.history_id);
            console.log('🆔 History ID:', data.history_id);
          } else if (data.type === 'content' && data.content) {
            accumulatedContent += data.content;
            setStreamedResponse(accumulatedContent);
          } else if (data.type === 'metadata') {
            console.log('📊 Metadata:', data);
            setMetadata({
              emotion: data.emotion,
              primary_tone: data.primary_tone,
              sub_tone: data.sub_tone,
              recommendations: data.recommendations,
              references: data.references,
            });
          } else if (data.type === 'error') {
            console.error('❌ Stream error:', data.error);
            setError(data.error || 'Unknown error');
          } else if (data.type === 'done') {
            console.log('✅ Stream completed');
          }
        }
      );

      console.log('🎉 Streaming finished successfully');
    } catch (err: any) {
      console.error('💥 Error during streaming:', err);
      setError(err.message || 'Failed to stream response');
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(to bottom right, #f3e7ff, #e0f2fe)',
      padding: '40px 20px'
    }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <Title level={2} style={{ textAlign: 'center', marginBottom: '30px' }}>
          🧪 스트리밍 API 테스트
        </Title>

        <Card style={{ marginBottom: '20px' }}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <div>
              <Text strong>질문 입력:</Text>
              <TextArea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="퍼스널컬러에 대해 질문해보세요..."
                autoSize={{ minRows: 2, maxRows: 4 }}
                disabled={isStreaming}
                style={{ marginTop: '8px' }}
              />
            </div>

            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSendMessage}
              disabled={!question.trim() || isStreaming}
              loading={isStreaming}
              block
            >
              {isStreaming ? '스트리밍 중...' : '전송'}
            </Button>

            {historyId && (
              <div style={{ padding: '8px', background: '#f0f0f0', borderRadius: '4px' }}>
                <Text type="secondary">History ID: {historyId}</Text>
              </div>
            )}
          </Space>
        </Card>

        {isStreaming && (
          <Card style={{ marginBottom: '20px', background: '#fffbeb' }}>
            <Space>
              <Spin />
              <Text>실시간으로 응답을 받는 중...</Text>
            </Space>
          </Card>
        )}

        {error && (
          <Card style={{ marginBottom: '20px', background: '#fee2e2', borderColor: '#dc2626' }}>
            <Text type="danger" strong>에러: {error}</Text>
          </Card>
        )}

        {streamedResponse && (
          <Card 
            title="📝 스트리밍 응답" 
            style={{ marginBottom: '20px' }}
          >
            <div style={{ 
              whiteSpace: 'pre-wrap', 
              wordBreak: 'break-word',
              minHeight: '100px',
              padding: '12px',
              background: '#f9fafb',
              borderRadius: '4px'
            }}>
              {streamedResponse}
            </div>
          </Card>
        )}

        {metadata && (
          <Card title="📊 메타데이터">
            <Space direction="vertical" style={{ width: '100%' }}>
              {metadata.emotion && (
                <div>
                  <Text strong>Emotion:</Text> {metadata.emotion}
                </div>
              )}
              {metadata.primary_tone && (
                <div>
                  <Text strong>Primary Tone:</Text> {metadata.primary_tone}
                </div>
              )}
              {metadata.sub_tone && (
                <div>
                  <Text strong>Sub Tone:</Text> {metadata.sub_tone}
                </div>
              )}
              {metadata.recommendations && metadata.recommendations.length > 0 && (
                <div>
                  <Text strong>Recommendations:</Text>
                  <ul>
                    {metadata.recommendations.map((rec: string, idx: number) => (
                      <li key={idx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}
              {metadata.references && metadata.references.length > 0 && (
                <div>
                  <Text strong>References:</Text>
                  <ul>
                    {metadata.references.map((ref: string, idx: number) => (
                      <li key={idx}>{ref}</li>
                    ))}
                  </ul>
                </div>
              )}
            </Space>
          </Card>
        )}

        <Card style={{ marginTop: '20px', background: '#f0f9ff' }}>
          <Title level={5}>💡 사용 방법</Title>
          <ul>
            <li>위 입력창에 질문을 입력하고 전송 버튼을 클릭하세요</li>
            <li>실시간으로 응답이 스트리밍되는 것을 확인할 수 있습니다</li>
            <li>응답이 완료되면 메타데이터(감정, 톤, 추천 등)도 표시됩니다</li>
            <li>History ID가 유지되어 대화 컨텍스트가 이어집니다</li>
          </ul>
        </Card>
      </div>
    </div>
  );
};

export default StreamTestPage;
