#!/bin/bash

# 배포 스크립트
# EC2 서버에서 수동 배포 또는 GitHub Actions에서 사용

set -e  # 에러 발생 시 스크립트 중단

echo "====================================="
echo "Starting deployment process..."
echo "====================================="

# 환경 변수 파일 확인
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create .env file from .env.example"
    exit 1
fi

echo "✓ .env file found"

# Docker 및 Docker Compose 설치 확인
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed!"
    exit 1
fi

echo "✓ Docker is installed"

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose is not installed!"
    exit 1
fi

echo "✓ Docker Compose is installed"

# Docker Compose 명령어 결정 (docker-compose 또는 docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

echo "Using: $DOCKER_COMPOSE"

# 기존 컨테이너 중지
echo ""
echo "Stopping existing containers..."
$DOCKER_COMPOSE down

# 이미지 빌드
echo ""
echo "Building Docker images..."
$DOCKER_COMPOSE build --no-cache

# 컨테이너 시작
echo ""
echo "Starting containers..."
$DOCKER_COMPOSE up -d

# 컨테이너 상태 확인
echo ""
echo "Container status:"
$DOCKER_COMPOSE ps

# 로그 확인
echo ""
echo "====================================="
echo "Recent logs:"
echo "====================================="
echo ""
echo "--- Database logs ---"
$DOCKER_COMPOSE logs --tail=10 db

echo ""
echo "--- Backend logs ---"
$DOCKER_COMPOSE logs --tail=10 backend

echo ""
echo "--- Frontend logs ---"
$DOCKER_COMPOSE logs --tail=10 frontend

# DB 마이그레이션 실행 (20초 대기 후)
echo ""
echo "Waiting for services to be ready..."
sleep 20

echo ""
echo "Running database migrations..."
docker exec fastapi-prod python -m alembic upgrade head || echo "Warning: Migration failed or already up to date"

# 헬스 체크
echo ""
echo "====================================="
echo "Health check:"
echo "====================================="

sleep 5

# 백엔드 헬스 체크
if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
    echo "✓ Backend is healthy (http://localhost:8000/docs)"
else
    echo "✗ Warning: Backend health check failed"
    echo "  Check logs: $DOCKER_COMPOSE logs backend"
fi

# 프론트엔드 헬스 체크
if curl -f http://localhost:80 > /dev/null 2>&1; then
    echo "✓ Frontend is healthy (http://localhost:80)"
else
    echo "✗ Warning: Frontend health check failed"
    echo "  Check logs: $DOCKER_COMPOSE logs frontend"
fi

# MySQL 헬스 체크
if docker exec mysql-prod mysqladmin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD:-password} --silent > /dev/null 2>&1; then
    echo "✓ Database is healthy"
else
    echo "✗ Warning: Database health check failed"
    echo "  Check logs: $DOCKER_COMPOSE logs db"
fi

echo ""
echo "====================================="
echo "Deployment completed!"
echo "====================================="
echo ""
echo "Access your application:"
echo "  - Frontend: http://localhost"
echo "  - Backend API docs: http://localhost:8000/docs"
echo "  - Backend API: http://localhost:8000/api"
echo ""
echo "Useful commands:"
echo "  - View logs: $DOCKER_COMPOSE logs -f"
echo "  - Stop services: $DOCKER_COMPOSE down"
echo "  - Restart services: $DOCKER_COMPOSE restart"
echo ""
