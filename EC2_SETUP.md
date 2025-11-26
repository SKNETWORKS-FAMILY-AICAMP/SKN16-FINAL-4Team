# EC2 서버 배포 가이드 (빠른 시작)

## 1. EC2 서버에 접속

```bash
ssh -i your-key.pem ec2-user@your-ec2-ip
```

## 2. 필수 소프트웨어 설치

### Docker 설치
```bash
# Docker 설치
sudo yum update -y
sudo yum install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# 재로그인 (docker 그룹 적용)
exit
# 다시 SSH 접속
ssh -i your-key.pem ec2-user@your-ec2-ip

# Docker 확인
docker --version
```

### Docker Compose 설치
```bash
# Docker Compose V2 (docker compose 명령어)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# 확인
docker-compose --version
```

## 3. 프로젝트 설정

### Git 저장소 클론
```bash
cd ~
git clone https://github.com/your-username/your-repo.git app
cd app
```

### 환경 변수 설정
```bash
# .env 파일 생성
cp .env.example .env
nano .env
```

**.env 파일 내용** (실제 값으로 변경):
```env
DOCKERHUB_USERNAME=wonjun525

MYSQL_ROOT_PASSWORD=myapipassword
MYSQL_DATABASE=myapi_db
MYSQL_USER=myapi_user
MYSQL_PASSWORD=myapipassword

DB_URL=mysql+pymysql://myapi_user:myapipassword@db:3306/myapi_db

SECRET_KEY=내 키
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production

OPENAI_API_KEY=내 키
DEFAULT_MODEL=gpt-4.1-nano-2025-04-14
```

## 4. 배포 실행

### 방법 1: 배포 스크립트 사용 (권장)
```bash
chmod +x deploy.sh
./deploy.sh
```

### 방법 2: Docker Compose 직접 사용
```bash
# 빌드 및 시작
docker-compose build
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 마이그레이션
docker exec fastapi-prod python -m alembic upgrade head
```

## 5. 확인

### 서비스 상태 확인
```bash
docker-compose ps
```

### 접속 테스트
```bash
# 프론트엔드
curl http://localhost:80

# 백엔드 API 문서
curl http://localhost:8000/docs

# 백엔드 헬스체크
curl http://localhost:8000/api/health || echo "Create health endpoint if needed"
```

### 웹 브라우저에서 확인
- 프론트엔드: `http://your-ec2-ip`
- 백엔드 API: `http://your-ec2-ip:8000/docs`

## 6. 문제 해결

### 로그 확인
```bash
# 모든 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

### 컨테이너 재시작
```bash
docker-compose restart
```

### 완전히 재배포
```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
docker exec fastapi-prod python -m alembic upgrade head
```

### 디스크 공간 확인
```bash
df -h
docker system df
docker system prune -a  # 사용하지 않는 이미지 삭제
```

## 7. GitHub Actions 자동 배포 설정

### GitHub Secrets 추가
GitHub 저장소 > Settings > Secrets and variables > Actions

필요한 Secrets:
- `DOCKERHUB_USERNAME`: wonjun525
- `DOCKERHUB_TOKEN`: Docker Hub Access Token
- `SSH_HOST`: EC2 퍼블릭 IP
- `SSH_USER`: ec2-user
- `SSH_KEY`: PEM 파일 내용 전체

### 자동 배포 테스트
```bash
# 로컬에서
git add .
git commit -m "test: CI/CD 테스트"
git push origin main
```

GitHub Actions 탭에서 워크플로우 실행 확인

## 8. 유용한 명령어

```bash
# 컨테이너 상태
docker-compose ps

# 실시간 로그
docker-compose logs -f --tail=100

# 특정 컨테이너 접속
docker exec -it fastapi-prod bash
docker exec -it frontend-prod sh
docker exec -it mysql-prod bash

# MySQL 접속
docker exec -it mysql-prod mysql -u myapi_user -p myapi_db

# 컨테이너 중지
docker-compose down

# 볼륨 포함 삭제 (데이터 초기화)
docker-compose down -v

# 이미지 재빌드
docker-compose build --no-cache

# 특정 서비스만 재시작
docker-compose restart backend
```

## 9. 포트 설정 (AWS 보안 그룹)

다음 포트를 오픈해야 합니다:

| 포트 | 용도 |
|-----|------|
| 22 | SSH |
| 80 | HTTP (프론트엔드) |
| 8000 | FastAPI (선택사항, 개발용) |
| 443 | HTTPS (SSL 설정 시) |

## 10. 업데이트 방법

### 수동 업데이트
```bash
cd ~/app
git pull origin main
./deploy.sh
```

### GitHub Actions 자동 업데이트
main 브랜치에 푸시하면 자동으로 배포됩니다.
