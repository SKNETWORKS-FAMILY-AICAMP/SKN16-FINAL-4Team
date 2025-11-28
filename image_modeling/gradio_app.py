"""
하이브리드 퍼스널 컬러 분석 Gradio 앱
- 새 라벨링 기준 적용
- 12클래스 (세부 계절) 분류
- 테스트 이미지 기반 threshold 적용
"""
import gradio as gr
import cv2
import numpy as np
import pickle
import sys
import os

# 상위 디렉토리를 path에 추가
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, parent_dir)
from landmark_classifier import RobustLandmarkClassifier

# ML 모델 로드 (4계절)
print("ML 모델 로드 중...")
with open(os.path.join(current_dir, 'full_season_ml_model.pkl'), 'rb') as f:
    season_model_data = pickle.load(f)

season_model = season_model_data['model']
print(f"✅ 4계절 모델 로드 완료: {season_model_data['model_name']}")

# ML 모델 로드 (12클래스 세부 계절)
with open(os.path.join(current_dir, 'full_subseason_ml_model.pkl'), 'rb') as f:
    subseason_model_data = pickle.load(f)

subseason_model = subseason_model_data['model']
feature_cols = subseason_model_data['feature_cols']
print(f"✅ 12클래스 모델 로드 완료: {subseason_model_data['model_name']}")
print(f"   CV Score: {subseason_model_data['cv_score']:.1%}")
print(f"   클래스: {subseason_model_data['classes']}")

# 분류기 초기화
classifier = RobustLandmarkClassifier()

def classify_personal_color(a_median, b_median, chroma, L_raw):
    """
    퍼스널 컬러 분류 (테스트 이미지 기반 threshold)

    테스트 데이터 분석 결과:
    - 봄_라이트: a=+13, b=+6, L=83.9
    - 여름_뮤트: a=+10, b=+6, L=78.8
    - 가을: b=+14~+18, L=58~76
    - 겨울_딥: a=+11, b=+11, L=61.2
    """
    features = [[a_median, b_median, chroma, L_raw]]

    # ========== 1단계: 웜/쿨 판단 (복합 조건) ==========
    # 조건 1: b* > 12 → 명확한 웜톤 (가을)
    # 조건 2: L* >= 83 → 밝은 웜톤 (봄)
    # 조건 3: 나머지 → 쿨톤 (여름/겨울)

    if b_median > 12:
        tone = "웜톤"
        # ========== 2단계: 웜톤 내 계절 판단 (L* 기준) ==========
        # L >= 76: 봄
        # L < 76: 가을
        if L_raw >= 77:
            season = '봄'
        else:
            season = '가을'
    elif L_raw >= 83 and a_median >= 10:
        # 매우 밝고 a*도 충분히 높은 경우 → 봄 (b*가 낮아도)
        tone = "웜톤"
        season = '봄'
    else:
        tone = "쿨톤"
        # ========== 2단계: 쿨톤 내 계절 판단 (복합 조건) ==========
        # L >= 76: 여름 (밝음)
        # L < 76: 겨울 (어두움)
        if L_raw >= 79:
            season = '여름'
        else:
            season = '겨울'

    # ML 모델 확률 (참고용)
    season_proba = season_model.predict_proba(features)[0]
    season_conf = max(season_proba)

    # ========== 3단계: 세부 타입 분류 (새 라벨링 기준) ==========
    # 각 계절 내에서 세부 타입 결정
    subtype_ranges = {
        '봄': {
            '라이트': {'b': (-20, 20), 'L': (72, 90), 'a': (-2, 15)},
            '트루': {'b': (17, 22), 'L': (69, 75), 'a': (3, 6)},
            '브라이트': {'b': (22, 28), 'L': (66, 74), 'a': (6, 9)},
        },
        '여름': {
            '라이트': {'b': (-10, 3), 'L': (80, 90), 'a': (9, 12)},
            '트루': {'b': (-4, 2), 'L': (65, 70), 'a': (7, 10)},
            '뮤트': {'b': (2, 12), 'L': (58, 85), 'a': (5, 11)},
        },
        '가을': {
            '소프트': {'b': (16, 18), 'L': (58, 72), 'a': (8, 11)},
            '딥': {'b': (15, 19), 'L': (74, 76), 'a': (10, 11)},
        },
        '겨울': {
            '브라이트': {'b': (-12, -6), 'L': (68, 72), 'a': (6, 8)},
            '트루': {'b': (-6, 8), 'L': (75, 82), 'a': (3, 7)},
            '딥': {'b': (-20, 12), 'L': (55, 79), 'a': (-3, 14)},
        },
    }

    # 해당 계절의 세부 타입 중 가장 적합한 것 선택
    best_subtype = ''
    best_score = -999

    if season in subtype_ranges:
        for subtype_name, ranges in subtype_ranges[season].items():
            score = 0
            # 각 범위에 얼마나 가까운지 점수 계산
            b_min, b_max = ranges['b']
            L_min, L_max = ranges['L']
            a_min, a_max = ranges['a']

            # 범위 내에 있으면 +1, 가까우면 거리에 따라 감점
            if b_min <= b_median <= b_max:
                score += 1
            else:
                dist = min(abs(b_median - b_min), abs(b_median - b_max))
                score -= dist * 0.1

            if L_min <= L_raw <= L_max:
                score += 1
            else:
                dist = min(abs(L_raw - L_min), abs(L_raw - L_max))
                score -= dist * 0.1

            if a_min <= a_median <= a_max:
                score += 1
            else:
                dist = min(abs(a_median - a_min), abs(a_median - a_max))
                score -= dist * 0.1

            if score > best_score:
                best_score = score
                best_subtype = subtype_name

    subtype = best_subtype
    subseason = f"{season}_{subtype}"

    # 확신도 (4계절 분류 기준)
    confidence = "높음" if season_conf > 0.6 else "중간" if season_conf > 0.4 else "낮음"

    # 이유 설명
    reason_parts = []
    if b_median > 12:
        reason_parts.append(f"웜/쿨: b*={b_median:+.1f} > 11 → 웜톤")
    elif L_raw >= 83 and a_median >= 10:
        reason_parts.append(f"웜/쿨: L*={L_raw:.1f} >= 83 and a*={a_median:+.1f} >= 10 (매우 밝음+높은 a*) → 웜톤 (봄)")
    else:
        reason_parts.append(f"웜/쿨: b*={b_median:+.1f} ≤ 12 and L*={L_raw:.1f} < 83 → 쿨톤")

    if tone == "웜톤" and not (L_raw >= 83 and b_median <= 11):
        reason_parts.append(f"봄/가을: L*={L_raw:.1f} {'≥' if L_raw >= 77 else '<'} 77 → {season}")
    elif tone == "쿨톤":
        reason_parts.append(f"여름/겨울: L*={L_raw:.1f} {'≥' if L_raw >= 79 else '<'} 79 → {season}")

    reason_parts.append(f"세부 타입: {subtype} (매칭 점수: {best_score:.1f}/3)")
    reason = "\n".join(reason_parts)

    return season, tone, subtype, subseason, reason, confidence, season_conf


def analyze_personal_color(image):
    """
    이미지에서 퍼스널 컬러 분석
    """
    if image is None:
        return None, "이미지를 업로드해주세요."

    try:
        # RGB → BGR 변환 (Gradio는 RGB로 전달)
        if isinstance(image, np.ndarray):
            img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = image

        # 얼굴 검출 및 ROI 추출
        skin, masks, vis_bgr, eyes_detected = classifier.detect_face_and_extract_skin(img_bgr)

        if skin is None or masks is None:
            return None, "❌ 얼굴을 찾을 수 없습니다. 정면 얼굴 사진을 업로드해주세요."

        # LAB 특징 추출
        features = classifier.extract_robust_lab_features(skin, masks)

        a_median = features['a_median']
        b_median = features['b_median']
        chroma = features['chroma']
        L_raw = features['L_cheek_raw']

        # 분류
        season, tone, subtype, subseason, reason, confidence, conf_score = classify_personal_color(
            a_median, b_median, chroma, L_raw
        )

        # 시각화 이미지 (BGR → RGB)
        vis_rgb = cv2.cvtColor(vis_bgr, cv2.COLOR_BGR2RGB)

        # 계절별 이모지
        season_emoji = {
            '봄': '🌸',
            '여름': '☀️',
            '가을': '🍂',
            '겨울': '❄️'
        }

        # 확신도 이모지
        confidence_emoji = {
            '높음': '✅',
            '중간': '⚠️',
            '낮음': '❌'
        }

        # 결과 텍스트
        result_text = f"""
# {season_emoji.get(season, '')} {season} {subtype} ({tone})

## 📊 분석 결과

**퍼스널 컬러**: **{subseason}**
**기본 계절**: {season}톤
**세부 타입**: {subtype}
**기본 톤**: {tone}
**확신도**: {confidence_emoji.get(confidence, '⚠️')} {confidence} ({conf_score:.0%})

## 🔬 측정값

| 지표 | 값 | 설명 |
|------|-----|------|
| **a*** | {a_median:+.1f} | Red-Green (-60~+60) |
| **b*** | {b_median:+.1f} | Yellow-Blue (-60~+60) |
| **Chroma** | {chroma:.1f} | 채도 (색의 선명도) |
| **L*** | {L_raw:.1f} | 밝기 (0~100) |

## 💡 분류 근거

{reason}

## 📈 테스트 데이터 기반 분류 기준

### 웜/쿨 판정:
- **b* > 12**: 웜톤 (명확한 가을/봄)
- **L* >= 83 AND a* >= 10**: 웜톤 (매우 밝은 봄)
- **나머지**: 쿨톤 (여름/겨울)

### 계절 판정:
- **웜톤**: L* >= 77 → 봄, L* < 76 → 가을
- **쿨톤**: L* >= 79 → 여름, L* < 79 → 겨울

### 현재 이미지 위치
- **b* = {b_median:+.1f}**: {'명확한 웜톤 (> 11)' if b_median > 11 else '경계 영역 (≤ 11)'}
- **L* = {L_raw:.1f}**: {'매우 밝음 (≥ 83)' if L_raw >= 83 else '밝음 (76~83)' if L_raw >= 76 else '중간~어두움 (< 76)'}

## 👁️ 검출 모드

{'✅ Eye-based ROI (눈 검출 성공)' if eyes_detected else '⚠️ Fallback ROI (눈 검출 실패)'}

---

### 색상 영역 설명
- 🟦 **이마** (Forehead)
- 🟥 **볼** (Cheek) - 주요 분석 영역
- 🟩 **턱** (Chin)
"""

        return vis_rgb, result_text

    except Exception as e:
        import traceback
        error_msg = f"❌ 분석 실패:\n{str(e)}\n\n{traceback.format_exc()}"
        return None, error_msg


# Gradio 인터페이스
print("\n" + "="*80)
print("Gradio 앱 초기화 중...")
print("="*80)

demo = gr.Interface(
    fn=analyze_personal_color,
    inputs=gr.Image(label="얼굴 사진 업로드"),
    outputs=[
        gr.Image(label="ROI 검출 결과"),
        gr.Markdown(label="분석 결과")
    ],
    title="🎨 퍼스널 컬러 분석 (12클래스)",
    description="""
    **얼굴 사진을 업로드하면 퍼스널 컬러(12클래스)를 자동으로 분석합니다.**

    - 📷 정면 얼굴 사진 권장
    - 💡 다양한 조명 환경 지원
    - 🎯 12클래스 세부 분류 (봄/여름/가을/겨울 × 라이트/트루/딥 등)

    ### 분류 방식 (테스트 데이터 기반)
    1. **웜/쿨 판정**: b* > 12 OR (L* >= 83 AND a* >= 10) → 웜톤, 나머지 → 쿨톤
    2. **계절 분류**: 웜톤(L* 기준), 쿨톤(L* 기준)
    3. **세부 타입**: 범위 매칭 기반
    """
)

if __name__ == "__main__":
    print("\n✅ Gradio 앱 준비 완료!")
    print("="*80)
    print("🌐 브라우저에서 앱이 열립니다...")
    print("="*80 + "\n")

    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )