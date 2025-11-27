# Windows 작업 스케줄러 설정 가이드

## 개요
Windows 작업 스케줄러를 사용하여 매주 월요일 04:00에 자동으로 크롤링을 실행합니다.

## 사전 준비

### 1. 필수 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 배치 파일 확인
- 경로: `rag_service/tools/run_crawler.bat`
- 가상환경 경로가 올바른지 확인: `C:\venvs\bai`

## Windows 작업 스케줄러 설정 (2가지 방법)

### 방법 1: GUI를 통한 설정 (권장 - 쉬움)

#### 단계 1: 작업 스케줄러 열기
1. Windows 검색 -> "작업 스케줄러" 검색
2. 또는 `Win + R` -> `taskschd.msc` 입력

#### 단계 2: 새 작업 만들기
1. 오른쪽 패널에서 "작업 만들기..." 클릭
2. **일반 탭**:
   - 이름: `Vogue Korea 자동 크롤링`
   - 설명: `매주 월요일 04:00에 패션/뷰티 트렌드 크롤링`
   - ☑ "사용자가 로그인하지 않아도 실행"
   - ☑ "최고 권한으로 실행"

#### 단계 3: 트리거 설정
1. **트리거 탭** -> "새로 만들기..."
2. 설정:
   - 작업 시작: `일정에 따라`
   - 매주 반복
   - 요일: `월요일` ✓
   - 시간: `04:00:00`
   - ☑ "사용"

#### 단계 4: 작업 설정
1. **작업 탭** -> "새로 만들기..."
2. 설정:
   - 프로그램/스크립트: `C:\projects\bai\SKN16-FINAL-4Team\rag_service\tools\run_crawler.bat`
   - 시작 위치: `C:\projects\bai\SKN16-FINAL-4Team`

#### 단계 5: 조건 설정 (선택사항)
1. **조건 탭**:
   - ☐ "컴퓨터가 유휴 상태일 때만 작업 실행"
   - ☑ "AC 전원이 필요" (필요시)

#### 단계 6: 완료
1. "확인" 클릭
2. 작업이 목록에 나타남

---

### 방법 2: PowerShell을 통한 설정 (고급 - 자동화)

#### PowerShell을 관리자 권한으로 실행

```powershell
# 1. 작업 트리거 설정
$trigger = New-ScheduledTaskTrigger `
  -Weekly `
  -DaysOfWeek Monday `
  -At 04:00AM

# 2. 작업 작업 설정
$action = New-ScheduledTaskAction `
  -Execute "C:\projects\bai\SKN16-FINAL-4Team\rag_service\tools\run_crawler.bat" `
  -WorkingDirectory "C:\projects\bai\SKN16-FINAL-4Team"

# 3. 작업 설정
$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable

# 4. 작업 등록
Register-ScheduledTask `
  -TaskName "Vogue Korea 자동 크롤링" `
  -Trigger $trigger `
  -Action $action `
  -Settings $settings `
  -RunLevel Highest `
  -Force
```

---

## 실행 및 테스트

### 테스트 실행 (즉시)
```bash
python rag_service/tools/scheduler.py test
```

### 스케줄러 상태 확인
```bash
python rag_service/tools/scheduler.py status
```

### 작업 스케줄러에서 확인
1. 작업 스케줄러 열기
2. `Vogue Korea 자동 크롤링` 작업 선택
3. 오른쪽 클릭 -> "실행"으로 즉시 테스트 가능

---

## 로그 파일

### 로그 위치
- 크롤링 로그: `data/logs/crawler_schedule.log`
- 오류 로그: `data/logs/error.log`

### 로그 확인
```bash
# 최근 크롤링 로그 보기
Get-Content "C:\projects\bai\SKN16-FINAL-4Team\data\logs\crawler_schedule.log" -Tail 100

# 또는 텍스트 에디터로 열기
notepad "C:\projects\bai\SKN16-FINAL-4Team\data\logs\crawler_schedule.log"
```

---

## 문제 해결

### 작업이 실행되지 않는 경우

#### 1. 배치 파일 경로 확인
```bash
# 배치 파일이 존재하는지 확인
dir C:\projects\bai\SKN16-FINAL-4Team\rag_service\tools\run_crawler.bat
```

#### 2. 가상환경 경로 확인
```bash
# 실제 가상환경 위치 확인
dir C:\venvs\bai\Scripts\activate.bat
```

#### 3. 수동 테스트
```bash
# 배치 파일 직접 실행 테스트
C:\projects\bai\SKN16-FINAL-4Team\rag_service\tools\run_crawler.bat
```

#### 4. 작업 스케줄러 로그 확인
1. 작업 스케줄러 열기
2. 작업 선택 -> "기록" 탭에서 오류 메시지 확인

### 크롤링이 실패하는 경우

#### 1. 인터넷 연결 확인
- Vogue Korea 사이트 접근 가능 여부 확인

#### 2. 로그 파일 확인
```bash
tail -n 50 "C:\projects\bai\SKN16-FINAL-4Team\data\logs\crawler_schedule.log"
```

#### 3. 수동으로 테스트
```bash
python rag_service/tools/scheduler.py test
```

---

## 작업 중지/삭제

### 작업 중지
1. 작업 스케줄러 열기
2. `Vogue Korea 자동 크롤링` 선택
3. 오른쪽 클릭 -> "사용 안 함"

### 작업 삭제 (PowerShell)
```powershell
# 관리자 권한 필요
Unregister-ScheduledTask -TaskName "Vogue Korea 자동 크롤링" -Confirm:$false
```

---

## 다른 시간으로 변경하기

### PowerShell을 통한 수정
```powershell
# 예: 매주 수요일 10:00으로 변경
$trigger = New-ScheduledTaskTrigger `
  -Weekly `
  -DaysOfWeek Wednesday `
  -At 10:00AM

$task = Get-ScheduledTask -TaskName "Vogue Korea 자동 크롤링"
$task | Set-ScheduledTask -Trigger $trigger
```

---

## Python 스케줄러 (대안 - 개발 중)

배포 전 로컬 개발 환경에서 테스트:

```bash
# 스케줄러 실행 (터미널 유지 필요)
python rag_service/tools/scheduler.py schedule
```

**주의**: 이 방법은 Python 프로세스가 실행 중이어야 하므로 프로덕션에는 부적합합니다.
Windows 작업 스케줄러를 사용하는 것이 권장됩니다.

---

## 수동 크롤링 (즉시 실행)

언제든지 수동으로 크롤링을 실행할 수 있습니다:

```bash
python rag_service/tools/scrape_mutable_data.py
```

---

## 요약

| 항목 | 설정값 |
|------|--------|
| **실행 시간** | 매주 월요일 04:00 |
| **스크립트** | `run_crawler.bat` |
| **로그** | `data/logs/crawler_schedule.log` |
| **대상** | 패션 + 뷰티 (각 20개 기사) |
| **중복 처리** | skip_existing=True (신규만 추가) |

---

## 지원

설정 중 문제가 발생하면 로그 파일을 확인하고 필요시 수동 테스트를 실행해주세요.
