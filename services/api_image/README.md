 # 이미지 모델 API

이 서비스는 `image_modeling` 폴더의 유틸리티(퍼스널 컬러 분류기 및 특징 추출)를 REST API 형태로 래핑하여 제공합니다.

엔드포인트
- `GET /api/image/ping` — 서비스 상태 확인(헬스체크)
- `POST /api/image/predict` — 멀티파트로 `file`(이미지)을 업로드하면 퍼스널 컬러 분류 결과와 시각화(PNG)를 base64 문자열로 반환합니다.
- `POST /api/image/extract_features` — 멀티파트로 `file`(이미지)을 업로드하면 추출된 LAB 특징을 반환합니다.

빠른 실행 방법 (레포지토리 루트에서)

```bash
# 필요한 패키지 설치 (프로젝트의 requirements.txt 사용 권장)
pip install -r requirements.txt

# uvicorn으로 api_image 서비스만 실행
uvicorn services.api_image.main:app --host 0.0.0.0 --port 9000
```

주의 사항
- 서비스는 `image_modeling` 폴더의 모듈을 임포트하여 사용합니다. 다른 작업 디렉터리에서 실행할 경우 레포지토리 루트가 `PYTHONPATH`에 포함되어 있어야 합니다.
- OpenCV의 Haar cascade와 같은 이미지 처리 종속성이 필요합니다. 서버 환경에서는 `opencv-python-headless`를 권장합니다.
- 이미지 시각화는 `data:image/png;base64,...` 형식의 문자열로 응답에 포함됩니다.

추가 권장 사항
- 인증, 요청률 제한(레이트리미팅), 입력 이미지 검증(사이즈/해상도) 및 비동기 작업 큐(예: Celery)를 도입하면 안정적인 운영에 도움이 됩니다.

