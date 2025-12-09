# 멀티스테이지 빌드 - Stage 1: 빌드 단계
FROM node:20-alpine as build

# 작업 디렉토리 설정
WORKDIR /app

# package.json과 package-lock.json 복사
COPY package*.json ./

# 소스 코드 복사
# .env 파일을 빌드에 사용하기 위해 먼저 복사합니다.
# .env 파일이 이미 공인 IP 주소(15.165.155.233:8000)를 포함하고 있어야 합니다.


# 의존성 설치
RUN npm ci



# 소스 코드 복사
COPY . .


ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}


# 프로덕션 빌드
RUN npm run build

# Stage 2: 프로덕션 단계 (Nginx)
FROM nginx:alpine

# 빌드된 파일을 Nginx 디렉토리로 복사
COPY --from=build /app/dist /usr/share/nginx/html

# Nginx 설정 파일 복사 (API 프록시 설정)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 포트 노출
EXPOSE 80

# Nginx 실행
CMD ["nginx", "-g", "daemon off;"]
