import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(timezone);

// Asia/Seoul 타임존을 기본으로 사용할 경우 아래처럼 설정 가능
// dayjs.tz.setDefault('Asia/Seoul');

export default dayjs;
