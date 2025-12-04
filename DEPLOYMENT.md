# 배포 가이드 (CI/CD with GitHub Actions)

## 목차
1. [개요](#개요)
2. [사전 요구사항](#사전-요구사항)
3. [GitHub Secrets 설정](#github-secrets-설정)
4. [EC2 서버 설정](#ec2-서버-설정)
5. [로컬 개발 환경 설정](#로컬-개발-환경-설정)
6. [배포 프로세스](#배포-프로세스)
7. [트러블슈팅](#트러블슈팅)

---

## 개요

이 프로젝트는 GitHub Actions를 사용하여 main 브랜치에 푸시될 때마다 자동으로 EC2 서버에 배포됩니다.

### 아키텍처
- **프론트엔드**: React + Vite + Nginx
- **백엔드**: FastAPI + Python 3.11
- **데이터베이스**: MySQL 8.0
- **컨테이너**: Docker + Docker Compose
- **레지스트리**: Docker Hub
- **CI/CD**: GitHub Actions

---

## 사전 요구사항

### 1. Docker Hub 계정
- [Docker Hub](https://hub.docker.com/)에서 계정 생성
- Access Token 생성 (Account Settings > Security > New Access Token)

### 2. EC2 인스턴스
- Ubuntu 20.04 이상 권장
- Docker 및 Docker Compose 설치 필요
- 포트 80, 8000, 3306 오픈 필요

### 3. GitHub 저장소
- main 브랜치 접근 권한
- Secrets 설정 권한

---

## GitHub Secrets 설정

GitHub 저장소의 Settings > Secrets and variables > Actions에서 다음 시크릿을 추가하세요:

| Secret Name | 설명 | 예시 |
|------------|------|------|
| `DOCKERHUB_USERNAME` | Docker Hub 사용자명 | `myusername` |
| `DOCKERHUB_TOKEN` | Docker Hub Access Token | `dckr_pat_xxxxx...` |
| `SSH_HOST` | EC2 인스턴스 퍼블릭 IP 또는 도메인 | `52.79.123.456` |
| `SSH_USER` | EC2 SSH 접속 사용자명 | `ubuntu` |
| `SSH_KEY` | EC2 SSH 개인키 (PEM 파일 내용) | `-----BEGIN RSA PRIVATE KEY-----...` |

### SSH 키 설정 방법
```bash
# EC2 PEM 파일 내용 전체 복사
cat your-key.pem
# 출력된 내용을 SSH_KEY 시크릿에 붙여넣기
```

---

## EC2 서버 설정

### 1. Docker 설치

```bash
# 시스템 업데이트
sudo apt-get update
sudo apt-get upgrade -y

# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 설치 확인
docker --version
docker-compose --version
```

### 2. 프로젝트 디렉토리 설정

```bash
# 홈 디렉토리에 app 폴더 생성
mkdir -p ~/app
cd ~/app

# Git 저장소 클론 (또는 파일 업로드)
git clone https://github.com/your-username/your-repo.git .

# 또는 수동으로 파일 업로드
# docker-compose.yml과 .env 파일만 필요합니다
```

### 3. 환경 변수 설정

```bash
# .env 파일 생성
cd ~/app
cp .env.example .env
nano .env
```

**.env 파일 예시**:
```env
# Docker Hub
DOCKERHUB_USERNAME=your-dockerhub-username

# MySQL
MYSQL_ROOT_PASSWORD=secure-root-password-123
MYSQL_DATABASE=personal_color_db
MYSQL_USER=app_user
MYSQL_PASSWORD=secure-app-password-456

# Database URL
DB_URL=mysql+pymysql://app_user:secure-app-password-456@db:3306/personal_color_db

# FastAPI
SECRET_KEY=your-very-long-random-secret-key-here
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production

# OpenAI
OPENAI_API_KEY=sk-proj-your-actual-api-key
EMOTION_MODEL_ID=ft:gpt-4.1-nano-2025-04-14:personal:model:xxxxx
DEFAULT_MODEL=gpt-4.1-nano-2025-04-14
```

### 4. 보안 그룹 설정 (AWS)

EC2 인스턴스의 보안 그룹에서 다음 포트를 열어주세요:

| 포트 | 프로토콜 | 용도 |
|-----|---------|------|
| 22 | TCP | SSH |
| 80 | TCP | HTTP (프론트엔드) |
| 443 | TCP | HTTPS (선택사항) |
| 8000 | TCP | FastAPI (개발용, 선택사항) |

---

## 로컬 개발 환경 설정

### 1. 환경 변수 설정

```bash
# 프로젝트 루트에서
cp .env.example .env

# .env 파일 수정
# 로컬 개발용 설정 예시:
DB_URL=mysql+pymysql://root:password@localhost:3306/personal_color_db
OPENAI_API_KEY=sk-proj-your-api-key
```

### 2. Docker Compose로 실행

```bash
# 이미지 빌드 및 컨테이너 시작
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 컨테이너 상태 확인
docker-compose ps
```

### 3. 데이터베이스 마이그레이션

```bash
# 백엔드 컨테이너에서 마이그레이션 실행
docker exec fastapi-prod python -m alembic upgrade head
```

### 4. 접속 확인

- **프론트엔드**: http://localhost
- **백엔드 API 문서**: http://localhost:8000/docs
- **백엔드 API**: http://localhost:8000/api

---

## 배포 프로세스

### 자동 배포 (GitHub Actions)

1. 코드 변경 후 커밋 & 푸시
```bash
git add .
git commit -m "feat: 새로운 기능 추가"
git push origin main
```

2. GitHub Actions 자동 실행
   - 백엔드/프론트엔드 Docker 이미지 빌드
   - Docker Hub에 이미지 푸시
   - EC2 서버에 SSH 접속
   - 최신 이미지 다운로드 및 배포

3. 배포 확인
   - GitHub Actions 탭에서 워크플로우 실행 상태 확인
   - EC2 서버에서 로그 확인

### 수동 배포 (EC2 서버에서)

```bash
# EC2 서버 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 프로젝트 디렉토리로 이동
cd ~/app

# Docker Hub 로그인
docker login -u your-username

# 최신 이미지 다운로드
docker-compose pull

# 컨테이너 재시작
docker-compose down
docker-compose up -d

# 마이그레이션 실행
docker exec fastapi-prod python -m alembic upgrade head

# 로그 확인
docker-compose logs -f
```

---

## 트러블슈팅

### 1. 이미지 빌드 실패

**증상**: GitHub Actions에서 이미지 빌드 중 실패
**해결**:
```bash
# Dockerfile 문법 확인
# .dockerignore 파일 확인
# requirements.txt 또는 package.json 의존성 확인
```

### 2. 데이터베이스 연결 실패

**증상**: 백엔드가 DB에 연결하지 못함
**해결**:
```bash
# .env 파일의 DB_URL 확인
# MySQL 컨테이너 상태 확인
docker-compose logs db

# MySQL 헬스체크 확인
docker exec mysql-prod mysqladmin ping -h localhost -u root -p
```

### 3. 프론트엔드 API 연결 실패

**증상**: 프론트엔드에서 백엔드 API 호출 실패
**해결**:
- nginx.conf 프록시 설정 확인
- 백엔드 컨테이너 상태 확인
- CORS 설정 확인 (main.py)

### 4. GitHub Actions SSH 연결 실패

**증상**: Deploy via SSH 단계에서 실패
**해결**:
- SSH_HOST 시크릿 확인 (IP 주소 정확한지)
- SSH_KEY 시크릿 확인 (PEM 파일 전체 내용 포함)
- EC2 보안 그룹에서 22번 포트 오픈 확인
- EC2 인스턴스 상태 확인

### 5. 로그 확인 방법

```bash
# 모든 컨테이너 로그
docker-compose logs -f

# 특정 컨테이너 로그
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db

# 실시간 로그 스트림
docker-compose logs -f --tail=100
```

### 6. 컨테이너 재시작

```bash
# 모든 컨테이너 재시작
docker-compose restart

# 특정 컨테이너만 재시작
docker-compose restart backend
```

### 7. 데이터베이스 초기화

```bash
# 주의: 모든 데이터 삭제됨!
docker-compose down -v
docker-compose up -d
docker exec fastapi-prod python -m alembic upgrade head
```

---

## 유용한 명령어

### Docker Compose

```bash
# 컨테이너 상태 확인
docker-compose ps

# 컨테이너 시작
docker-compose up -d

# 컨테이너 중지
docker-compose down

# 이미지 재빌드 및 시작
docker-compose up -d --build

# 볼륨 포함 완전 삭제
docker-compose down -v
```

### Docker 이미지 관리

```bash
# 사용하지 않는 이미지 삭제
docker image prune -a

# 사용하지 않는 볼륨 삭제
docker volume prune

# 전체 정리
docker system prune -a --volumes
```

### 데이터베이스 접속

```bash
# MySQL 컨테이너에 접속
docker exec -it mysql-prod mysql -u app_user -p

# 데이터베이스 확인
SHOW DATABASES;
USE personal_color_db;
SHOW TABLES;
```

---

## 참고 자료

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
