import React from 'react';
import { Modal, Avatar, Tag, Typography, Button, Spin, Row, Col } from 'antd';
import InfluencerImage from './InfluencerImage';
const { Title, Text } = Typography;

interface Props {
  open: boolean;
  onCancel: () => void;
  profile: any | null;
}

const InfluencerProfileModal: React.FC<Props> = ({ open, onCancel, profile }) => {
  // debug: log resolved image path when modal opens
  React.useEffect(() => {
    if (open && profile) {
      try {
        const candidate = (profile && (profile.profile || profile.image)) || (profile && profile.name ? `/profiles/${encodeURIComponent(profile.name)}.png` : null);
        // eslint-disable-next-line no-console
        console.debug('[InfluencerProfileModal] opening modal, resolved image=', candidate, 'profile=', profile);
      } catch (e) {
        // ignore
      }
    }
  }, [open, profile]);

  return (
    <Modal open={open} onCancel={onCancel} footer={null} centered width={460} styles={{
        body: { padding: 0, borderRadius: 12 }
    }}>
      {profile ? (
        <div style={{ borderRadius: 16, background: '#fff', boxShadow: '0 8px 28px rgba(15,23,42,0.08)', overflow: 'hidden', borderLeft: '4px solid ' + (profile.color || '#7c3aed') }}>
          <div style={{ padding: 18 }}>
            {/* 프로필 사진과 오른쪽 이모지 */}
            <Row align="middle" gutter={16}>
              <Col>
                <Avatar size={84} style={{ border: '4px solid #fff' }}>
                  <InfluencerImage profile={profile} name={profile?.name} emoji={profile?.emoji || '🌟'} imgStyle={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                </Avatar>
              </Col>
              <Col flex="auto">
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <Avatar size={48} style={{ background: profile.color, fontSize: 22, lineHeight: '48px' }}>{profile.emoji || '🌟'}</Avatar>
                </div>
              </Col>
            </Row>

            {/* 이름과 characteristics(secondary) */}
            <div style={{ marginTop: 12 }}>
              <Title level={4} style={{ margin: 0 }}>{profile.name}</Title>
              {profile.characteristics && <div style={{ marginTop: 6 }}><Text type="secondary">{profile.characteristics}</Text></div>}
            </div>

            {/* greeting */}
            {profile.greeting && (
              <div style={{ marginTop: 20 }}>
                <Title level={5}>{profile.greeting}</Title>
              </div>
            )}

            {/* subscriber_name, expertise 태그 */}
            <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {(Array.isArray(profile.subscriber_name) ? profile.subscriber_name : (profile.subscriber_name ? [profile.subscriber_name] : [])).map((s: string, i: number) => (
                <Tag key={`sub-${i}`} color="cyan" style={{ fontWeight: 600 }}>{s}</Tag>
              ))}
              {(Array.isArray(profile.expertise) ? profile.expertise : (profile.expertise ? [profile.expertise] : [])).map((t: string, i: number) => (
                <Tag key={`exp-${i}`} color="green" style={{ fontWeight: 600 }}>{t}</Tag>
              ))}
            </div>

            {/* closing + 닫기 버튼 */}
            <Row style={{ display: 'flex', flexDirection: 'column', marginTop: 14 }}>
              <Col flex="auto">
                {profile.closing && (
                  <div style={{ padding: '10px 12px', borderRadius: 8, background: '#fafafa' }}>
                    <Text type="secondary">{profile.closing}</Text>
                  </div>
                )}
              </Col>
              <Col flex="auto" className='text-right'>
                <Button onClick={onCancel} type='primary' style={{ borderRadius: 20 }}>닫기</Button>
              </Col>
            </Row>
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
