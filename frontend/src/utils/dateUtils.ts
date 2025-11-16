// 날짜를 'YYYY.MM.DD' 또는 'YYYY.MM.DD HH:mm' 등으로 포맷하는 유틸 함수
import dayjs from './dayjsTimezoneSetup';

export function formatKoreanDate(
  dateInput: string | number | Date,
  withTime = false
): string {
  if (!dateInput) return '';
  const d = dayjs(dateInput).tz('Asia/Seoul');
  if (!d.isValid()) return '';
  if (withTime) {
    return d.format('YYYY.MM.DD HH:mm');
  }
  return d.format('YYYY.MM.DD');
}
