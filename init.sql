-- 데이터베이스 초기화 스크립트
-- Docker Compose로 MySQL 컨테이너 시작 시 자동 실행됩니다.

-- 데이터베이스가 없으면 생성 (docker-compose.yml에서 이미 생성됨)
CREATE DATABASE IF NOT EXISTS personal_color_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE personal_color_db;

-- 타임존 설정
SET time_zone = '+09:00';

-- 초기 설정 완료 메시지
SELECT 'Database initialization completed!' as status;
