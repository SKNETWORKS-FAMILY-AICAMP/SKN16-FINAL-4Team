import React, { useState } from 'react';
import { Modal, Button, Typography, Rate } from 'antd';

const { Title, Text } = Typography;

interface Props {
  open: boolean;
  onCancel: () => void;
  // numeric rating 1..5 will be passed to onFeedback
  onFeedback: (rating: number) => Promise<void> | void;
  isLoading?: boolean;
}

const FeedbackModal: React.FC<Props> = ({ open, onCancel, onFeedback, isLoading }) => {
  const [rating, setRating] = useState<number>(0);

  const handleSubmit = async () => {
    if (rating <= 0) return;
    await onFeedback(rating);
  };

  return (
    <Modal
      title="챗봇 사용 만족도"
      open={open}
      onCancel={onCancel}
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

        <div className="mb-4">
          <Rate
            allowHalf={false}
            count={5}
            value={rating}
            onChange={value => setRating(value)}
            style={{ fontSize: 28 }}
          />
        </div>

        <div>
          <Button
            size="large"
            type="primary"
            loading={isLoading}
            onClick={handleSubmit}
            style={{
              background: 'linear-gradient(135deg, #52c41a 0%, #389e0d 100%)',
              border: 'none',
              borderRadius: '10px',
              minWidth: '160px',
            }}
            disabled={isLoading || rating <= 0}
          >
            제출하기
          </Button>
        </div>

        <div className="mt-4">
          <Button type="text" onClick={onCancel} className="!text-gray-500">
            피드백 없이 나가기
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default FeedbackModal;
