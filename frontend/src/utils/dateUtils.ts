// 날짜를 'YYYY.MM.DD' 또는 'YYYY.MM.DD HH:mm' 등으로 포맷하는 유틸 함수
import dayjs from './dayjsTimezoneSetup';

export function formatKoreanDate(
  dateInput: string | number | Date,
  withTime = false
): string {
  if (!dateInput) return '';
  // Normalize input to UTC first, then convert to Asia/Seoul timezone.
  // This handles ISO strings with or without explicit offsets and Date objects
  // so the displayed time is correctly shown in Korean local time.
  const d = dayjs(dateInput).utc().tz('Asia/Seoul');
  if (!d.isValid()) return '';
  if (withTime) {
    return d.format('YYYY.MM.DD HH:mm');
  }
  return d.format('YYYY.MM.DD');
}
