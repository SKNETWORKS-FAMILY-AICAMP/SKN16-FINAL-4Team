import dayjs from 'dayjs';
import type { ChatMessageData } from '@/components/chatbot/ChatMessage';

export const parseRawChatRes = (raw: any): any | undefined => {
  if (!raw) return undefined;
  try {
    return typeof raw === 'string' ? JSON.parse(raw) : raw;
  } catch (e) {
    return undefined;
  }
};

export const mapInfluencerRespItems = (items: any[], inflId: string | number): ChatMessageData[] => {
  return (items || []).map((m: any, idx: number) => {
    const isUser = (m.role || '').toString().toLowerCase() === 'user';
    let chatRes = undefined as any;
    try {
      if (m.raw) chatRes = parseRawChatRes(m.raw);
    } catch (e) {
      chatRes = undefined;
    }
    return {
      id: `infl-${inflId}-${idx}-${m.history_id || ''}`,
      content: m.text || '',
      isUser,
      timestamp: m.created_at ? String(m.created_at) : new Date().toISOString(),
      chatRes,
      questionId: undefined,
    } as ChatMessageData;
  });
};

export const historyItemsToChatMessages = (items: any[], historyId?: number): ChatMessageData[] => {
  const out: ChatMessageData[] = [];
  let baseTs = Date.now() - (items?.length || 0) * 2000;
  
  for (const it of items || []) {
    const userTsIso = it.question_created_at
      ? String(it.question_created_at)
      : new Date(baseTs).toISOString();
    const isWelcome = !it.question || it.question.trim() === '';

    if (!isWelcome) {
      out.push({
        id: `h-${historyId}-${it.question_id}-u`,
        content: it.question || '',
        isUser: true,
        timestamp: userTsIso,
      });
    }
    
    baseTs = Math.max(baseTs + 1000, dayjs(userTsIso).valueOf() + 500);
    const botTsIso = it.created_at ? String(it.created_at) : new Date(baseTs).toISOString();

    out.push({
      id: `h-${historyId}-${it.question_id}-b`,
      content: it.answer || '',
      isUser: false,
      timestamp: botTsIso,
      chatRes: it.chat_res,
      isWelcome: isWelcome,
    });
    
    baseTs = Math.max(baseTs + 1000, dayjs(botTsIso).valueOf() + 500);
  }
  
  return out;
};

export const extractBotContentFromItem = (item: any): string => {
  let botContent = item.answer;
  if (!botContent || botContent.trim() === '') {
    botContent = item.chat_res?.description || '답변을 준비 중입니다...';
  }
  
  try {
    const trimmed = (botContent || '').trim();
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      const parsed = JSON.parse(trimmed);
      if (parsed && typeof parsed === 'object') {
        return (
          parsed.description ||
          parsed.answer ||
          item.chat_res?.description ||
          '답변을 준비 중입니다...'
        );
      }
    }
  } catch (e) {
    // ignore parse errors
  }
  
  return botContent;
};

export const sanitizeForChat = (obj: any): any => {
  if (!obj) return obj;
  if (typeof obj === 'string') {
    return obj.length > 500 ? obj.substring(0, 500) + '...[truncated]' : obj;
  }
  if (Array.isArray(obj)) {
    return obj.map(sanitizeForChat);
  }
  if (typeof obj === 'object') {
    const newObj: any = {};
    for (const key in obj) {
      if (
        key.toLowerCase().includes('base64') ||
        key.toLowerCase().includes('image_data') ||
        key.toLowerCase().includes('encoded_image')
      ) {
        newObj[key] = '[Image Data Omitted]';
      } else {
        newObj[key] = sanitizeForChat(obj[key]);
      }
    }
    return newObj;
  }
  return obj;
};

export const isDiagnosisBubble = (msg?: any): boolean => {
  if (msg && msg.customContent && typeof msg.customContent === 'object') {
    return true;
  }
  return false;
};

export const groupMessagesByDate = (msgs: ChatMessageData[]) => {
  const map = new Map<string, ChatMessageData[]>();
  
  for (const m of msgs) {
    const d = dayjs(m.timestamp).tz('Asia/Seoul');
    const key = `${d.year()}-${String(d.month() + 1).padStart(2, '0')}-${String(d.date()).padStart(2, '0')}`;
    if (!map.has(key)) {
      map.set(key, []);
    }
    map.get(key)!.push(m);
  }

  const keys = Array.from(map.keys()).sort((a, b) => a.localeCompare(b));

  return keys.map((k) => {
    const items = (map.get(k) || [])
      .slice()
      .sort((x, y) => dayjs(x.timestamp).valueOf() - dayjs(y.timestamp).valueOf());
    const date = items.length > 0 ? dayjs(items[0].timestamp).toDate() : new Date(k);
    return { key: k, items, date };
  });
};

export const formatDateHeader = (d: Date): string => {
  const today = new Date();
  const isSameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();

  if (isSameDay(d, today)) return '오늘';
  
  const weekdays = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일'];
  return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일 ${weekdays[d.getDay()]}`;
};
