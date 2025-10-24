// 날짜를 'YYYY.MM.DD' 또는 'YYYY.MM.DD HH:mm' 등으로 포맷하는 유틸 함수
export function formatKoreanDate(dateInput: string | number | Date, withTime = false): string {
    if (!dateInput) return '';
    const date = new Date(dateInput);
    if (isNaN(date.getTime())) return '';
    const y = date.getFullYear();
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    const d = date.getDate().toString().padStart(2, '0');
    if (withTime) {
        const hh = date.getHours().toString().padStart(2, '0');
        const mm = date.getMinutes().toString().padStart(2, '0');
        return `${y}.${m}.${d} ${hh}:${mm}`;
    }
    return `${y}.${m}.${d}`;
}
