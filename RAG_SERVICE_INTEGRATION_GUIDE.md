# RAG 서비스 통합 가이드

## 📋 개요

`run.py`를 통해 메인 서비스와 RAG 서비스를 **동시에 실행**할 수 있습니다.
- **메인 서비스** (포트 8000): 퍼스널 컬러 진단 API
- **RAG 서비스** (포트 8001): 통합 지식 검색 API

---

## 🚀 빠른 시작

### 1️⃣ 기본 실행 (메인 + RAG 동시)

```bash
python run.py
```

**결과:**
```
🚀 퍼스널컬러 진단 서버를 시작합니다...
💡 데이터베이스 설정이 필요하면 'alembic upgrade head'를 실행하세요.
🌐 호스트: 127.0.0.1
🔌 메인 앱 포트: 8000, RAG 서비스 포트: 8001
📖 메인 API 문서: http://127.0.0.1:8000/docs
📖 RAG API 문서: http://127.0.0.1:8001/docs
⚖️ RUN_BOTH=1 - main 앱과 rag_service 앱을 동시에 실행합니다
```

### 2️⃣ 메인 서비스만 실행

```bash
RUN_BOTH=0 python run.py
```

### 3️⃣ 포트 커스터마이징

```bash
MAIN_PORT=9000 RAG_PORT=9001 python run.py
```

---

## 📡 API 엔드포인트

### 메인 서비스 (http://localhost:8000)

#### 1. RAG 서비스 헬스 체크
```bash
GET /api/rag/health
```

**응답:**
```json
{
  "status": "available",
  "details": {
    "status": "ok",
    "immutable_files": 1,
    "mutable_files": 45,
    "caching_enabled": false,
    "router_model": "gpt-4o-mini"
  }
}
```

#### 2. RAG 서비스에 쿼리 전송
```bash
POST /api/rag/query?query=봄톤에게 어울리는 2025년 트렌드 색상&temperature=0.7&max_tokens=2048
```

**응답:**
```json
{
  "success": true,
  "answer": "봄 웜톤에게 어울리는 2025년 트렌드 색상은...",
  "query": "봄톤에게 어울리는 2025년 트렌드 색상",
  "route": 4,
  "route_description": "불변 + 가변 통합",
  "sources": [
    "personal_color.pdf (File Search)",
    "vogue_fashion.txt (OpenAI RAG)"
  ],
  "metadata": {
    "model": "gpt-4o-mini",
    "source": "hybrid",
    "retrieval_method": "file_search + semantic_search"
  },
  "timestamp": "2025-11-27T10:30:45.123456"
}
```

### RAG 서비스 API (http://localhost:8001)

#### 1. RAG 서비스 헬스 체크
```bash
GET /health
```

#### 2. 통합 지식 쿼리
```bash
POST /query
```

**요청 본문:**
```json
{
  "query": "봄 웜톤에게 어울리는 립스틱 색상",
  "temperature": 0.7,
  "max_tokens": 2048,
  "force_route": null
}
```

---

## 🔌 클라이언트 예제

### Python 예제

```python
import httpx
import asyncio

async def query_rag():
    async with httpx.AsyncClient() as client:
        # 메인 서비스를 통해 RAG 쿼리
        response = await client.get(
            "http://localhost:8000/api/rag/query",
            params={
                "query": "봄톤에게 어울리는 색상",
                "temperature": 0.7
            }
        )
        print(response.json())

asyncio.run(query_rag())
```

### cURL 예제

```bash
# RAG 서비스 상태 확인
curl http://localhost:8000/api/rag/health

# RAG 쿼리 전송
curl -X POST "http://localhost:8000/api/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "봄 웜톤에게 어울리는 2025년 트렌드 색상",
    "temperature": 0.7,
    "max_tokens": 2048
  }'
```

### JavaScript/TypeScript 예제

```typescript
async function queryRAG() {
  const response = await fetch('http://localhost:8000/api/rag/query?query=봄톤 색상', {
    method: 'POST'
  });
  const data = await response.json();
  console.log(data);
}

queryRAG();
```

---

## 🏗️ 아키텍처

```
┌─────────────────────────────────────┐
│      메인 서비스 (포트 8000)         │
│  - User Router (/api/user)          │
│  - Chatbot Router (/api/chatbot)    │
│  - Survey Router (/api/survey)      │
│  - Feedback Router (/api/feedback)  │
│  - Admin Router (/api/admin)        │
│  ┌──────────────────────────────┐   │
│  │ RAG 서비스 프록시             │   │
│  │ GET /api/rag/health          │   │
│  │ POST /api/rag/query          │   │
│  └──────────────────────────────┘   │
└──────────────────┬──────────────────┘
                   │ HTTP (포트 8001)
                   ▼
   ┌────────────────────────────────┐
   │  RAG 서비스 (포트 8001)        │
   │  - FileSearch (퍼스널컬러)     │
   │  - OpenAI RAG (패션트렌드)     │
   │  - 스마트 라우팅 (GPT-4o-mini) │
   └────────────────────────────────┘
```

---

## ⚙️ 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `HOST` | 서버 호스트 | `127.0.0.1` |
| `PORT` | 메인 서비스 포트 (RAG는 PORT+1) | `8000` |
| `MAIN_PORT` | 메인 서비스 포트 (명시적) | `8000` |
| `RAG_PORT` | RAG 서비스 포트 (명시적) | `8001` |
| `MAIN_APP_PATH` | 메인 앱 import 경로 | `main:app` |
| `RAG_APP_PATH` | RAG 앱 import 경로 | `rag_service.api:app` |
| `RUN_BOTH` | 두 서비스 동시 실행 (0=단일, 1=동시) | `1` |
| `RAG_HOST` | RAG 서비스 호스트 (클라이언트 설정) | `127.0.0.1` |

---

## 🔍 구현 상세

### run.py 의 동작

```python
if RUN_BOTH == "1":
    # 두 개 앱을 별도 프로세스로 실행
    p1 = Process(target=_start_uvicorn, args=(MAIN_APP_PATH, HOST, MAIN_PORT, False))
    p2 = Process(target=_start_uvicorn, args=(RAG_APP_PATH, HOST, RAG_PORT, False))
    p1.start()
    p2.start()
    p1.join()
    p2.join()
else:
    # 메인 서비스만 실행 (개발용 reload=True)
    uvicorn.run(MAIN_APP_PATH, host=HOST, port=PORT, reload=True)
```

### main.py 의 RAGServiceClient 클래스

```python
class RAGServiceClient:
    """RAG 서비스 API 클라이언트"""
    
    async def query_rag(self, query: str, temperature: float = 0.7, 
                       max_tokens: int = 2048, force_route: int = None) -> dict:
        """RAG 서비스에 쿼리 전송"""
        # HTTP POST 요청으로 RAG API 호출
        
    async def get_health(self) -> dict:
        """RAG 서비스 헬스 체크"""
        # HTTP GET 요청으로 건강 상태 확인
```

---

## 🧪 테스트 시나리오

### 시나리오 1: 기본 실행 및 헬스 체크

```bash
# 터미널 1: 서비스 실행
python run.py

# 터미널 2: 헬스 체크 (약 2-3초 대기 필요)
curl http://localhost:8000/api/rag/health
```

**예상 결과:**
```json
{"status": "available", "details": {...}}
```

### 시나리오 2: RAG 쿼리

```bash
curl -X GET "http://localhost:8000/api/rag/query?query=봄톤+색상&temperature=0.7"
```

### 시나리오 3: 메인 서비스 API와의 통합

기존의 chatbot, survey 등 엔드포인트에서 필요시 `/api/rag/query`를 호출하여 RAG 결과를 통합할 수 있습니다.

```python
# routers/chatbot_router.py 내부에서
from main import rag_client

@router.post("/chat")
async def chat_endpoint(message: str):
    # RAG 서비스에 쿼리
    rag_result = await rag_client.query_rag(message)
    
    if rag_result.get("success"):
        answer = rag_result.get("answer")
        # 기존 대화에 RAG 결과 통합
        ...
```

---

## 🐛 문제 해결

### 포트 충돌 (Port is already in use)

```bash
# 포트 변경하여 실행
MAIN_PORT=9000 RAG_PORT=9001 python run.py
```

### RAG 서비스 연결 실패

```bash
# RAG 서비스가 실제로 실행 중인지 확인
curl http://localhost:8001/health

# RAG 서비스만 실행해서 테스트
cd rag_service
python -m uvicorn api.app:app --host 127.0.0.1 --port 8001
```

### 의존성 에러

```bash
# RAG 서비스 의존성 확인
pip install -r requirements.txt
pip install google-genai httpx  # 추가 필요 패키지
```

---

## 📊 로그 출력 예시

### 성공적인 시작

```
🚀 퍼스널컬러 진단 서버를 시작합니다...
💡 데이터베이스 설정이 필요하면 'alembic upgrade head'를 실행하세요.
🌐 호스트: 127.0.0.1
🔌 메인 앱 포트: 8000, RAG 서비스 포트: 8001
📖 메인 API 문서: http://127.0.0.1:8000/docs
📖 RAG API 문서: http://127.0.0.1:8001/docs
⚖️ RUN_BOTH=1 - main 앱과 rag_service 앱을 동시에 실행합니다
➡️ main:app -> http://127.0.0.1:8000
➡️ rag_service.api:app  -> http://127.0.0.1:8001
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete
```

---

## 📝 체크리스트

- [ ] `python run.py` 실행 확인
- [ ] 포트 8000 메인 서비스 접속 가능 (http://localhost:8000/docs)
- [ ] 포트 8001 RAG 서비스 접속 가능 (http://localhost:8001/docs)
- [ ] `curl http://localhost:8000/api/rag/health` 정상 응답
- [ ] `curl -X GET http://localhost:8000/api/rag/query?query=테스트` 정상 응답
- [ ] 기존 chatbot/survey 엔드포인트 정상 작동

---

## 🔗 관련 문서

- [RAG 서비스 구현 가이드](./rag_service/FILE_SEARCH_IMPLEMENTATION.md)
- [API 문서](./frontend/README.md)
- [데이터베이스 마이그레이션](./README.md)
