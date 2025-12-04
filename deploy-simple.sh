#!/bin/bash

# 간단한 배포 스크립트 (buildx 불필요)
# EC2에서 직접 이미지를 빌드하고 배포합니다

set -e

echo "========================================="
echo "Simple Deployment (No Buildx Required)"
echo "========================================="

# .env 파일 확인
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    exit 1
fi

# 환경변수 로드
export $(cat .env | grep -v '^#' | xargs)

echo "✓ Environment variables loaded"

# Docker Compose 명령어 결정
if command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    DC="docker compose"
fi

echo "Using: $DC"

# 기존 컨테이너 중지
echo ""
echo "Stopping containers..."
$DC down 2>/dev/null || true

# 이미지 빌드
echo ""
echo "Building images..."

# 백엔드 빌드
echo "- Building backend..."
docker build -t ${DOCKERHUB_USERNAME}/skn16-fastapi:latest . || {
    echo "Backend build failed!"
    exit 1
}

# 프론트엔드 빌드
echo "- Building frontend..."
docker build -t ${DOCKERHUB_USERNAME}/skn16-frontend:latest ./frontend || {
    echo "Frontend build failed!"
    exit 1
}

echo "✓ Images built successfully"

# 컨테이너 시작
echo ""
echo "Starting containers..."
$DC up -d --no-build

# 상태 확인
echo ""
echo "Container status:"
$DC ps

# 대기
echo ""
echo "Waiting for services (30 seconds)..."
sleep 30

# 마이그레이션
echo ""
echo "Running migrations..."
docker exec fastapi-prod python -m alembic upgrade head 2>/dev/null || echo "Migration skipped"

# 헬스체크
echo ""
echo "========================================="
echo "Health Check"
echo "========================================="

# 백엔드
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "✓ Backend OK (http://localhost:8000/docs)"
else
    echo "✗ Backend check failed"
    $DC logs --tail=20 backend
fi

# 프론트엔드
if curl -s http://localhost > /dev/null 2>&1; then
    echo "✓ Frontend OK (http://localhost)"
else
    echo "✗ Frontend check failed"
    $DC logs --tail=20 frontend
fi

# DB
if docker exec mysql-prod mysqladmin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD} --silent 2>/dev/null; then
    echo "✓ Database OK"
else
    echo "✗ Database check failed"
    $DC logs --tail=20 db
fi

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "View logs: $DC logs -f"
echo "Stop: $DC down"
echo ""
