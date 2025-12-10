import React from 'react';
import { Avatar, Typography, Button } from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import AnimatedEmoji from '@/components/AnimatedEmoji';
import InfluencerImage from '@/components/InfluencerImage';
import { getAvatarRenderInfo } from '@/utils/genderUtils';
import { formatKoreanDate } from '@/utils/dateUtils';

const { Text } = Typography;

export interface ChatMessageData {
    id: string;
    question?: string;
    content?: string;
    customContent?: React.ReactNode;
    isUser: boolean;
    timestamp: string | Date;
    chatRes?: any;
    questionId?: number;
    diagnosisData?: any;
    isWelcome?: boolean;
}

interface ChatMessageProps {
    message: ChatMessageData;
    user?: any;
    activeInfluencerProfile?: any;
    delayedDescriptions?: { [id: string]: boolean };
    isDiagnosisBubble?: boolean;
    shouldShowReportButton?: boolean;
    onViewReport?: () => void;
    onInfluencerClick?: (profile: any) => void;
}

const ChatMessage: React.FC<ChatMessageProps> = ({
    message: msg,
    user,
    activeInfluencerProfile,
    delayedDescriptions = {},
    isDiagnosisBubble = false,
    shouldShowReportButton = false,
    onViewReport,
    onInfluencerClick,
}) => {
    const getInfluencerAvatarInfo = (s: any) => {
        if (!s || typeof s !== 'string') return null;
        const key = s.trim().toLowerCase();

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

    const renderAvatar = () => {
        if (msg.isUser) {
            const avatarConfig = getAvatarRenderInfo(user?.gender, user?.id);
            return (
                <Avatar
                    className={`!ml-3 ${avatarConfig.className}`}
                    size={50}
                    style={{
                        width: 50,
                        height: 50,
                        flexShrink: 0,
                        padding: 0,
                        overflow: 'hidden',
                        background: '#fff',
                        ...avatarConfig.style,
                    }}
                >
                    <InfluencerImage name={user?.nickname} emoji={avatarConfig?.content} />
                </Avatar>
            );
        }

        const inflKey =
            (msg as any).influencer ||
            (msg as any).chatRes?.influencer ||
            (msg as any).chatRes?.raw?.influencer ||
            (msg as any).influencer_id ||
            null;

        const inflFromMsg = getInfluencerAvatarInfo(inflKey);
        const avatarProfile = activeInfluencerProfile || inflFromMsg;

        if (avatarProfile) {
            const { profile } = avatarProfile || {};
            const inflName = ((avatarProfile?.influencer_name || '') as string).toLowerCase();
            const activeName =
                typeof activeInfluencerProfile === 'string'
                    ? (activeInfluencerProfile as string).toLowerCase()
                    : ((activeInfluencerProfile?.influencer_name || '') as string).toLowerCase();
            const activeId = (activeInfluencerProfile && activeInfluencerProfile.influencer_id) ?? null;
            const inflId = (avatarProfile && avatarProfile.influencer_id) ?? null;
            const isActive =
                activeId != null && inflId != null
                    ? String(activeId) === String(inflId)
                    : activeName && inflName && activeName === inflName;

            return (
                <div
                    className={`influencer-avatar-clickable !mr-3 ${isActive ? 'influencer-avatar-active' : ''}`}
                    onClick={() => onInfluencerClick?.(avatarProfile)}
                    aria-label={`Open profile ${avatarProfile.influencer_name} details`}
                    role="button"
                    tabIndex={0}
                    style={{ display: 'inline-flex', alignItems: 'center' }}
                >
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
        <div className={`flex mb-3 ${msg.isUser ? 'justify-end' : 'justify-start'}`}>
            <div
                className={`flex max-w-lg items-start ${msg.isUser ? 'flex-row-reverse' : 'flex-row'}`}
            >
                {renderAvatar()}

                <div className="flex flex-col gap-1">
                    {/* Emotion bubble */}
                    {!msg.isUser && msg.chatRes?.emotion && !isDiagnosisBubble && (
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

                    {/* Main content bubble */}
                    {(msg.isUser ||
                        !msg.chatRes?.emotion ||
                        delayedDescriptions[msg.id] ||
                        typeof delayedDescriptions[msg.id] === 'undefined') && (
                            <div
                                className={`relative px-4 py-2 rounded-lg ${msg.isUser ? 'bg-blue-500 text-white user-balloon' : 'bg-white chatbot-balloon'
                                    }`}
                                style={{
                                    marginLeft: msg.isUser ? 0 : '0',
                                    marginRight: msg.isUser ? '0' : 0,
                                    maxWidth: '100%',
                                    border: msg.isUser ? undefined : '1.5px solid #e5e7eb',
                                    boxShadow: msg.isUser ? undefined : '0 2px 8px rgba(0,0,0,0.04)',
                                }}
                            >
                                {/* Tail pointers */}
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

                                {/* Content */}
                                {msg.customContent ? (
                                    msg.customContent
                                ) : (
                                    <Text className={`whitespace-pre-wrap ${msg.isUser ? '!text-white' : '!text-gray-800'}`}>
                                        {msg.content}
                                    </Text>
                                )}

                                {/* References */}
                                {!msg.isUser && msg.chatRes?.references && msg.chatRes.references.length > 0 && (
                                    <div className="mt-3 pt-2 border-t border-gray-100">
                                        <div className="text-xs text-gray-500 flex flex-wrap gap-1 items-center">
                                            <span>📚 참고:</span>
                                            {msg.chatRes.references.slice(0, 2).map((ref: string, idx: number) => (
                                                <span
                                                    key={idx}
                                                    className="bg-gray-100 px-2 py-0.5 rounded"
                                                    title={ref}
                                                >
                                                    {ref.length > 20 ? ref.substring(0, 20) + '...' : ref}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Footer */}
                                <div className="text-xs mt-1 opacity-70 flex justify-between items-center">
                                    {shouldShowReportButton && (
                                        <Button
                                            type="link"
                                            size="small"
                                            onClick={onViewReport}
                                            className="!p-0 !h-auto !text-xs"
                                            style={{ color: msg.isUser ? '#fff' : '#1890ff' }}
                                        >
                                            🎨 진단 결과 상세보기
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

export default ChatMessage;
