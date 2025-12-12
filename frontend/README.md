# 🎨 Personal Color Frontend

퍼스널 컬러 진단 서비스의 React + TypeScript + Vite 프론트엔드 애플리케이션입니다.

## 🚀 빠른 시작

### 필수 요구사항

- **Node.js**: 22+
- **패키지 매니저**: npm 또는 yarn

### 설치 및 실행

```bash
# 프로젝트 폴더로 이동
cd frontend

# 의존성 설치
npm install

# 환경변수 설정
cp .env.example .env

# 개발 서버 실행 (http://localhost:5173)
npm run dev
```

## ⚙️ 기술 스택

### 핵심 프레임워크

- **React 18.3.1** - UI 라이브러리
- **TypeScript 5.9.3** - 정적 타입 검사
- **Vite 7.1.7** - 빌드 도구 및 개발 서버
- **React Router DOM 7.9.4** - 라우팅

### UI 및 스타일링

- **Ant Design 5.27.4** - UI 컴포넌트 라이브러리
- **Tailwind CSS 4.1.14** - 유틸리티 CSS 프레임워크
- **@ant-design/icons** - 아이콘 패키지

### 상태 관리 및 API

- **TanStack Query 5.90.3** - 서버 상태 관리
- **Axios 1.12.2** - HTTP 클라이언트

### 개발 도구

- **ESLint** - 코드 문법 검사
- **Prettier** - 코드 포맷터
- **Husky** - Git hooks 관리
- **lint-staged** - 커밋 전 코드 검사

## 🛠️ 사용 가능한 스크립트

```bash
npm run dev          # 개발 서버 실행
npm run build        # 프로덕션 빌드
npm run preview      # 빌드 결과 미리보기
npm run lint         # ESLint 검사
npm run lint:fix     # ESLint 자동 수정
npm run format       # Prettier 포맷팅
npm run format:check # Prettier 포맷팅 검사
npm run type-check   # TypeScript 타입 검사
```

## 🌐 API 통신

### TanStack Query 훅 사용법

```tsx
import { useUser } from '@/hooks/useUser';

function UserProfile() {
  // 사용자 데이터 조회
  const { data: user, isLoading, error } = useUser();

  if (isLoading) return <div>로딩 중...</div>;
  if (error) return <div>오류 발생</div>;

  return (
    <div>
      <h1>안녕하세요, {user?.name}님!</h1>
    </div>
  );
}
```

### API 클라이언트 설정

```typescript
// src/api/client.ts
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### 환경 변수

```bash
# .env
VITE_API_BASE_URL=http://localhost:8000
```

## 🎨 스타일링 가이드

### Ant Design + Tailwind CSS 조합

```tsx
import { Button, Card } from 'antd';
import { cn } from '@/utils/cn';

function ExampleComponent() {
  return (
    <Card className="shadow-lg rounded-lg">
      <Button
        type="primary"
        className={cn(
          'w-full transition-all duration-200',
          'hover:shadow-md hover:scale-105'
        )}
      >
        퍼스널 컬러 테스트 시작
      </Button>
    </Card>
  );
}
```

### 조건부 클래스 유틸리티

```tsx
import { cn } from '@/utils/cn';

// 조건부 스타일 적용
<div
  className={cn('base-styles', isActive && 'active-styles', {
    'error-styles': hasError,
  })}
/>;
```

### 색상 팔레트

```css
/* Primary Colors */
--primary-blue: #1677ff;
--primary-purple: #7c3aed;

/* Gradient */
background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
```

## 📋 코딩 컨벤션

### 네이밍 규칙

- **컴포넌트**: PascalCase (`PersonalColorTest.tsx`)
- **파일/폴더**: PascalCase for components, camelCase for utilities
- **변수/함수**: camelCase (`getUserProfile`)
- **상수**: UPPER_SNAKE_CASE (`PERSONAL_COLOR_TYPES`)
- **타입/인터페이스**: PascalCase (`PersonalColorResult`)

### 파일 구조 규칙

```typescript
// 컴포넌트 파일 구조
import React from 'react';
import { Button } from 'antd';
import type { ComponentProps } from './types';

interface Props extends ComponentProps {
  // 컴포넌트 특화 props
}

export function ComponentName({ ...props }: Props) {
  return (
    // JSX
  );
}

export default ComponentName;
```

### Git 커밋 컨벤션

```bash
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 수정
style: 코드 포맷팅
refactor: 코드 리팩토링
test: 테스트 추가/수정
chore: 빌드 설정, 패키지 업데이트
```

## 🔧 개발 환경 설정

### VS Code 추천 확장 프로그램

```json
{
  "recommendations": [
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "ms-vscode.vscode-typescript-next"
  ]
}
```

### 자동 포맷팅 설정

```json
// .vscode/settings.json
{
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  }
}
```

## 🚀 배포

### 빌드

```bash
# 타입 체크 후 빌드
npm run build

# 빌드 결과 미리보기
npm run preview
```

### 환경별 설정

```bash
# 개발 환경
VITE_API_BASE_URL=http://localhost:8000

# 프로덕션 환경
VITE_API_BASE_URL=https://api.yourproject.com
```

## 🤝 기여 가이드

### 개발 프로세스

1. **브랜치 생성**: `feature/기능명` 또는 `fix/버그명`
2. **개발 진행**: ESLint, Prettier 규칙 준수
3. **커밋**: 컨벤션에 맞는 커밋 메시지 작성
4. **Pull Request**: 코드 리뷰 후 병합

### 코드 품질 체크

```bash
# 전체 검사 실행
npm run lint && npm run type-check && npm run format:check
```

## 📄 추가 리소스

- **React 18 문서**: https://react.dev/
- **Ant Design 컴포넌트**: https://ant.design/components/
- **Tailwind CSS 문서**: https://tailwindcss.com/docs
- **TanStack Query 가이드**: https://tanstack.com/query/latest
- **Vite 설정 가이드**: https://vitejs.dev/config/
