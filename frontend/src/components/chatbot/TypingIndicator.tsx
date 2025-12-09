import React from 'react';
import { Avatar } from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import InfluencerImage from '@/components/InfluencerImage';

interface TypingIndicatorProps {
  activeInfluencerProfile?: any;
}

const TypingAnimation: React.FC<{ size?: number; color?: string }> = ({
  size = 10,
  color = '#9CA3AF',
}) => (
  <svg
    width={size * 3 + 20}
    height={size}
    viewBox={`0 0 ${size * 3 + 20} ${size}`}
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden
  >
    <circle cx={size / 2} cy={size / 2} r={size / 2} fill={color}>
      <animate
        attributeName="opacity"
        values="0.2;1;0.2"
        dur="1s"
        repeatCount="indefinite"
        begin="0s"
      />
    </circle>
    <circle cx={size / 2 + size + 6} cy={size / 2} r={size / 2} fill={color}>
      <animate
        attributeName="opacity"
        values="0.2;1;0.2"
        dur="1s"
        repeatCount="indefinite"
        begin="0.15s"
      />
    </circle>
    <circle cx={size / 2 + (size + 6) * 2} cy={size / 2} r={size / 2} fill={color}>
      <animate
        attributeName="opacity"
        values="0.2;1;0.2"
        dur="1s"
        repeatCount="indefinite"
        begin="0.3s"
      />
    </circle>
  </svg>
);

const TypingIndicator: React.FC<TypingIndicatorProps> = ({ activeInfluencerProfile }) => {
  const renderAvatar = () => {
    if (activeInfluencerProfile) {
      const { profile } = activeInfluencerProfile || {};
      return (
        <div className={`chatbot-avatar-container !mr-2 chatbot-active`}>
          <Avatar
            size={50}
            style={{
              width: 50,
              height: 50,
              flexShrink: 0,
              padding: 0,
              overflow: 'hidden',
              background: '#fff',
            }}
          >
            <InfluencerImage name={profile?.name} emoji={profile?.emoji} />
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
  };

  return (
    <div className="flex justify-start mb-3">
      <div className="flex items-start">
        {renderAvatar()}
        <div className="bg-white border border-gray-200 px-4 py-2 rounded-lg flex items-center">
          <TypingAnimation size={8} color="#6b7280" />
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator;
