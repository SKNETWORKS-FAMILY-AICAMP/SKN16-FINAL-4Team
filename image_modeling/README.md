# 이미지 모델링 - 퍼스널컬러 분류

얼굴 이미지에서 피부 톤을 분석하여 퍼스널컬러(4계절/12타입)를 분류하는 ML 파이프라인입니다.

## 실행 순서

### 1. 데이터 증강
```bash
python augment.py
```
- 입력: `labeled_data/` (원본 라벨링 데이터)
- 출력: `augmented_data/` (증강된 이미지)
- 클래스당 목표 샘플 수만큼 이미지 증강 (회전, 반전, 확대 등)

### 2. 특징 추출
```bash
python extract_features.py
```
- 입력: `augmented_data/`
- 출력: `final_lab_features_wb.csv`
- 얼굴 검출 → 피부 영역 추출 → LAB 색공간 특징 추출

### 3. 4계절 모델 학습
```bash
python train_model.py
```
- 입력: `final_lab_features_wb.csv`
- 출력: `full_season_ml_model.pkl`
- 봄/여름/가을/겨울 4계절 분류 모델

### 4. 12클래스 세부 계절 모델 학습
```bash
python train_subseason_model.py
```
- 입력: `final_lab_features_wb.csv`
- 출력: `full_subseason_ml_model.pkl`
- 봄_라이트, 여름_뮤트 등 12개 세부 타입 분류 모델

### 5. Gradio 데모 실행
```bash
python gradio_app.py
```
- 웹 UI에서 이미지 업로드하여 퍼스널컬러 분석 테스트

## 폴더 구조

```
image_modeling/
├── labeled_data/          # 원본 라벨링 데이터
├── augmented_data/        # 증강된 이미지 데이터
├── augment.py             # 데이터 증강
├── extract_features.py    # LAB 특징 추출
├── train_model.py         # 4계절 모델 학습
├── train_subseason_model.py  # 12클래스 모델 학습
├── landmark_classifier.py # 얼굴 검출 및 피부 영역 추출
├── gradio_app.py          # Gradio 데모 앱
└── *.pkl                  # 학습된 모델 파일
```

## 필요 패키지
- `pip install -r image_modeling/requirements.txt`
