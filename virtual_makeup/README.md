# Virtual Makeup 모듈

퍼스널컬러 기반 메이크업을 적용하는 Gradio 데모 모듈입니다. 현재 브랜치에서는 OpenCV+Mediapipe 방식(`MakeupApplierCV`)만 사용합니다.

## 실행
```bash
python virtual_makeup/gradio_app.py
```
- `.env`에 `OPENAI_API_KEY`가 필요합니다(GPT를 통한 수정 요청 파싱용).
- 첫 실행 시 Mediapipe 모델이 자동 다운로드됩니다.

## 개발/요구사항
- Python 3.10+
- 의존성은 `virtual_makeup/requirements.txt`를 참고하세요.
  ```bash
  pip install -r virtual_makeup/requirements.txt
  ```

## 외부 응답(JSON) 포맷
외부 RAG/모델에서 받는 메이크업 응답 예시는 다음과 같습니다. 색상은 반드시 HEX로 제공합니다.
```json
{
  "personal_color": "봄 웜톤",               // 선택
  "recommendation_reason": "밝은 코랄 추천",  // 선택
  "makeup": {
    "lip":    { "color": "#E8836B" },        // 필수
    "blush":  { "color": "#FFAA80" },        // 필수
    "eyebrow":{ "color": "#5C4033" },        // 필수
    "eyeshadow": { "colors": ["#FFB6C1", "#FF69B4"] },  // 선택
    "eyeliner":  { "color": "#2F2F2F" }                   // 선택
  }
}
```
- 피부 베이스(`skin_base`)는 응답에 넣어도 무시되고 기본값으로 고정됩니다.
- 응답을 전달하지 않으면 `demo_responses.py`의 샘플 4종이 fallback으로 사용됩니다.
