import React from 'react';
import { Modal, Avatar, Tag, Typography, Button, Spin } from 'antd';
import { useNavigate } from 'react-router-dom';
import InfluencerImage from './InfluencerImage';

import type { InfluencerHistoryItem } from '@/api/chatbot';

const { Title, Text } = Typography;

interface Props {
  open: boolean;
  onCancel: () => void;
  influencerInfo: InfluencerHistoryItem | null;
}

const InfluencerProfileModal: React.FC<Props> = ({ open, onCancel, influencerInfo }) => {
  const navigate = useNavigate();
  const { profile } = influencerInfo || {};

  // debug: log resolved image path when modal opens
  React.useEffect(() => {
    if (open && influencerInfo) {
      try {
        const candidate = (influencerInfo && (profile)) || (influencerInfo && influencerInfo.influencer_name ? `/profiles/${encodeURIComponent(influencerInfo.influencer_name)}.png` : null);
        // eslint-disable-next-line no-console
        console.debug('[InfluencerProfileModal] opening modal, resolved image=', candidate, 'profile=', influencerInfo);
      } catch (e) {
        // ignore
      }
    }
  }, [open, influencerInfo]);

  const startChat = () => {
    const inflId = influencerInfo?.influencer_id || influencerInfo?.influencer_name || '';
    navigate(`/chatbot?infl_id=${encodeURIComponent(inflId)}`, { state: { influencerProfile: influencerInfo } });
    if (onCancel) onCancel();
  };

  return (
    <Modal open={open} onCancel={onCancel} footer={null} centered width={720} styles={{body: { padding: 0, borderRadius: 12 }}}>
      {influencerInfo ? (
        <div style={{ borderRadius: 16, background: '#fff', boxShadow: '0 8px 28px rgba(15,23,42,0.08)', overflow: 'hidden' }}>
          {/* Large image header */}
          <div style={{ width: '100%', height: 220, background: profile?.color || '#f3f4f6', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ width: 180, height: 180, borderRadius: 12, boxShadow: '0 8px 24px rgba(15,23,42,0.12)', border: '6px solid rgba(255,255,255,0.9)', background: '#fff', position: 'relative' }}>
              <InfluencerImage name={profile?.name} emoji={profile?.emoji || '🌟'} imgStyle={{ width: '100%', height: '100%', objectFit: 'fill' }} />
              {/* small emoji badge */}
              <div style={{ position: 'absolute', right: -22, top: -22 }}>
                <Avatar size={48} style={{ background: 'rgba(255,255,255,0.5)', fontSize: 22 }}>{profile?.emoji || '🌟'}</Avatar>
              </div>
            </div>
          </div>

          <div style={{ padding: 20, display: 'flex', gap: 20 }}>
            {/* Left: intro and tags */}
            <div style={{ flex: 1 }}>
              <Title level={3} style={{ marginBottom: 6 }}>{influencerInfo.influencer_name}</Title>
              {profile?.characteristics && <Text type="secondary">{profile.characteristics}</Text>}

              {profile?.greeting && (
                <div style={{ marginTop: 12 }}>
                  <Text strong>{profile.greeting}</Text>
                </div>
              )}

              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {(Array.isArray(profile?.subscriber_name) ? profile.subscriber_name : (profile?.subscriber_name ? [profile.subscriber_name] : [])).map((s: string, i: number) => (
                  <Tag key={`sub-${i}`} color="cyan" style={{ fontWeight: 600 }}>{s}</Tag>
                ))}
                {(Array.isArray(profile?.expertise) ? profile.expertise : (profile?.expertise ? [profile.expertise] : [])).map((t: string, i: number) => (
                  <Tag key={`exp-${i}`} color="green" style={{ fontWeight: 600 }}>{t}</Tag>
                ))}
              </div>

              {profile?.closing && (
                <div style={{ marginTop: 16, padding: 12, borderRadius: 8, background: '#fafafa' }}>
                  <Text type="secondary">{profile.closing}</Text>
                </div>
              )}
            </div>

            {/* Right: stats & actions */}
            <div style={{ width: 220, display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ background: '#fafafa', padding: 12, borderRadius: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text type="secondary">평점</Text>
                  <Text strong>{influencerInfo.average_rating || '-'}</Text>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 8 }}>
                <Button type="primary" block onClick={startChat}>상담 시작</Button>
                <Button onClick={onCancel} block>닫기</Button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <Spin />
        </div>
      )}
    </Modal>
  );
};

export default InfluencerProfileModal;
