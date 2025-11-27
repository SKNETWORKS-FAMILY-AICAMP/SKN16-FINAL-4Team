@echo off
REM ==============================================================================
REM Windows 자동 크롤링 배치 파일
REM 작업 스케줄러에서 실행될 파일
REM ==============================================================================

cd /d C:\projects\bai\SKN16-FINAL-4Team

REM Python 가상환경 활성화
call C:\venvs\bai\Scripts\activate.bat

REM 크롤링 스케줄러 실행
python rag_service\tools\scheduler.py schedule

REM 오류 발생 시 로그 기록
if errorlevel 1 (
    echo Error occurred at %date% %time% >> C:\projects\bai\SKN16-FINAL-4Team\data\logs\error.log
)

pause
