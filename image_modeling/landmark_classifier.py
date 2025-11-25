"""
개선된 눈 위치 기반 피부톤 분류기
- Eye-based 동적 ROI
- L 절대값 대신 a, b 중심 분류
- 얼굴 내부 정규화 (이마/볼/턱 비율)
- Median + outlier 제거 (percentile 10~90)
"""
import cv2
import numpy as np
from personal_color_classifier import PersonalColorClassifier


class RobustLandmarkClassifier(PersonalColorClassifier):
    """조명에 강건한 눈 위치 기반 분류기"""

    def __init__(self):
        super().__init__()
        # 눈 검출기 추가
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )

    def apply_white_balance(self, image):
        """
        Gray World 화이트 밸런스
        - 이미지의 평균 색상을 회색(중립)으로 조정
        - a*, b* 값의 색편향(cast) 제거
        """
        # LAB 변환
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        L, a, b = cv2.split(lab)

        # Gray World: a, b 채널의 평균을 128(중립)로 조정
        a_mean = np.mean(a)
        b_mean = np.mean(b)

        # 중립값(128)으로 5%만 shift (피부톤 보존)
        strength = 0.05  # 5% 강도
        a_shift = (a_mean - 128) * strength
        b_shift = (b_mean - 128) * strength

        a_corrected = np.clip(a.astype(float) - a_shift, 0, 255).astype(np.uint8)
        b_corrected = np.clip(b.astype(float) - b_shift, 0, 255).astype(np.uint8)

        # LAB 재결합
        lab_corrected = cv2.merge([L, a_corrected, b_corrected])

        # BGR 변환
        image_wb = cv2.cvtColor(lab_corrected, cv2.COLOR_LAB2BGR)

        print(f"[DEBUG] 화이트 밸런스 (5%): a {a_mean:.1f}→{a_mean-a_shift:.1f}, b {b_mean:.1f}→{b_mean-b_shift:.1f}")

        return image_wb

    def detect_face_and_extract_skin(self, image):
        """
        얼굴 검출 및 눈 위치 기반 볼 영역 추출
        """
        # 화이트밸런스 보정 활성화 (조명 정규화)
        image_wb = self.apply_white_balance(image)

        # 그레이스케일 변환 (보정된 이미지 사용)
        gray = cv2.cvtColor(image_wb, cv2.COLOR_BGR2GRAY)

        # 얼굴 검출
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
        )

        if len(faces) == 0:
            return None, None, None, None

        # 가장 큰 얼굴 선택
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

        # 얼굴 영역 (화이트밸런스 보정된 이미지 사용)
        face_roi = image_wb[y:y+h, x:x+w]
        gray_face = gray[y:y+h, x:x+w]

        # 얼굴 영역 내에서 눈 검출
        eyes = self.eye_cascade.detectMultiScale(
            gray_face, scaleFactor=1.1, minNeighbors=10, minSize=(20, 20)
        )

        # 눈 위치 기반 ROI 계산
        h_roi, w_roi = face_roi.shape[:2]

        # 눈 검출 필터링 (너무 큰 것, 너무 아래 있는 것 제외)
        valid_eyes = []
        for (ex, ey, ew, eh) in eyes:
            # 눈 크기 검증: 얼굴 너비의 10~25%
            if not (0.1 * w_roi <= ew <= 0.25 * w_roi):
                continue
            # 눈 위치 검증: 얼굴 상단 20~45% 사이
            eye_center_y = ey + eh // 2
            if not (0.2 * h_roi <= eye_center_y <= 0.45 * h_roi):
                continue
            valid_eyes.append((ex, ey, ew, eh))

        if len(valid_eyes) >= 2:
            # 유효한 눈이 2개 이상 검출된 경우
            # x 좌표로 정렬 (왼쪽/오른쪽)
            valid_eyes = sorted(valid_eyes, key=lambda e: e[0])
            left_eye = valid_eyes[0]
            right_eye = valid_eyes[-1]

            # 눈의 중심점
            left_eye_y = left_eye[1] + left_eye[3] // 2
            right_eye_y = right_eye[1] + right_eye[3] // 2
            eye_line_y = (left_eye_y + right_eye_y) // 2

            # 눈 기준선 아래로 광대 위치 추정
            cheekbone_y = eye_line_y + int(h_roi * 0.15)
            lower_cheek_y = cheekbone_y + int(h_roi * 0.12)

            # 이마 영역 (눈 위)
            forehead_y = max(int(h_roi * 0.15), eye_line_y - int(h_roi * 0.15))

            # 턱 영역 (광대 아래보다 더 아래)
            chin_y = min(int(h_roi * 0.75), lower_cheek_y + int(h_roi * 0.15))

            eyes_detected = True
        else:
            # 눈 검출 실패: 폴백 (비율 기반)
            lower_cheek_y = int(h_roi * 0.50)  # 0.55 → 0.50 (조금 위로)
            forehead_y = int(h_roi * 0.15)
            chin_y = int(h_roi * 0.70)          # 0.75 → 0.70 (조금 위로)
            eyes_detected = False

        # 피부 영역 추출
        ycrcb = cv2.cvtColor(face_roi, cv2.COLOR_BGR2YCrCb)
        lower_skin = np.array([0, 110, 50], dtype=np.uint8)
        upper_skin = np.array([255, 200, 155], dtype=np.uint8)
        skin_mask = cv2.inRange(ycrcb, lower_skin, upper_skin)

        # 어두운 픽셀 제외
        gray_check = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        dark_mask = gray_check > 15
        skin_mask = cv2.bitwise_and(skin_mask, skin_mask, mask=dark_mask.astype(np.uint8) * 255)

        # 모폴로지 연산
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)

        # 3개 영역 마스크 생성 (메이크업/경계 회피)
        # 1) 이마 (눈썹~머리카락 사이, 중앙보다 양옆)
        forehead_mask = np.zeros_like(skin_mask)
        forehead_x = int(w_roi * 0.30)  # 0.25 → 0.30 (더 중앙으로)
        forehead_w = int(w_roi * 0.40)  # 0.50 → 0.40 (양옆 조금만)
        forehead_h = int(h_roi * 0.08)  # 0.10 → 0.08 (머리카락 경계 피하기)
        forehead_mask[
            forehead_y:min(forehead_y+forehead_h, h_roi),
            forehead_x:forehead_x+forehead_w
        ] = 255

        # 2) 광대 아래 (콧방울 옆, 입선 위, 다크서클/팔자 피하기)
        cheek_mask = np.zeros_like(skin_mask)
        left_cheek_x = int(w_roi * 0.15)   # 0.12 → 0.15 (콧방울에서 조금 떨어짐)
        left_cheek_w = int(w_roi * 0.18)   # 0.20 → 0.18 (약간 좁게)
        cheek_h = int(w_roi * 0.12)        # 0.15 → 0.12 (입술 경계 피하기)

        cheek_mask[
            lower_cheek_y:min(lower_cheek_y+cheek_h, h_roi),
            left_cheek_x:left_cheek_x+left_cheek_w
        ] = 255

        right_cheek_x = int(w_roi * 0.67)  # 0.68 → 0.67
        cheek_mask[
            lower_cheek_y:min(lower_cheek_y+cheek_h, h_roi),
            right_cheek_x:right_cheek_x+left_cheek_w
        ] = 255

        # 3) 턱 (입술 바로 아래 피하고, 턱선 안쪽 평평한 부분만)
        chin_mask = np.zeros_like(skin_mask)
        chin_x = int(w_roi * 0.35)         # 0.30 → 0.35 (더 중앙)
        chin_w = int(w_roi * 0.30)         # 0.40 → 0.30 (좁게)
        chin_h = int(h_roi * 0.08)         # 0.10 → 0.08 (턱선 경계 피하기)
        chin_mask[
            chin_y:min(chin_y+chin_h, h_roi),
            chin_x:chin_x+chin_w
        ] = 255

        # 각 영역 추출
        forehead_final = cv2.bitwise_and(skin_mask, forehead_mask)
        cheek_final = cv2.bitwise_and(skin_mask, cheek_mask)
        chin_final = cv2.bitwise_and(skin_mask, chin_mask)

        # 시각화 (화이트 밸런스 보정된 이미지 사용)
        vis_image = image_wb.copy()
        cv2.rectangle(vis_image, (x, y), (x+w, y+h), (0, 255, 0), 2)

        # 눈 표시
        if eyes_detected and len(valid_eyes) >= 2:
            for (ex, ey, ew, eh) in valid_eyes[:2]:
                cv2.rectangle(vis_image,
                            (x+ex, y+ey),
                            (x+ex+ew, y+ey+eh),
                            (255, 255, 0), 2)

        # 이마 (파란색)
        cv2.rectangle(vis_image,
                     (x+forehead_x, y+forehead_y),
                     (x+forehead_x+forehead_w, y+forehead_y+forehead_h),
                     (255, 0, 0), 2)

        # 볼 (빨간색)
        cv2.rectangle(vis_image,
                     (x+left_cheek_x, y+lower_cheek_y),
                     (x+left_cheek_x+left_cheek_w, y+lower_cheek_y+cheek_h),
                     (0, 0, 255), 2)
        cv2.rectangle(vis_image,
                     (x+right_cheek_x, y+lower_cheek_y),
                     (x+right_cheek_x+left_cheek_w, y+lower_cheek_y+cheek_h),
                     (0, 0, 255), 2)

        # 턱 (녹색)
        cv2.rectangle(vis_image,
                     (x+chin_x, y+chin_y),
                     (x+chin_x+chin_w, y+chin_y+chin_h),
                     (0, 255, 0), 2)

        # 라벨
        label = "Robust Eye-based ROI" if eyes_detected else "Robust Fallback ROI"
        cv2.putText(vis_image, label,
                   (x+10, y+h-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        return face_roi, (forehead_final, cheek_final, chin_final), vis_image, eyes_detected

    def extract_robust_lab_features(self, skin_pixels, masks):
        """
        조명에 강건한 LAB 특징 추출
        - L은 얼굴 내부 정규화
        - a, b는 median + outlier 제거
        - Chroma (C*) 계산

        Args:
            skin_pixels: 피부 영역 이미지 (BGR)
            masks: (forehead_mask, cheek_mask, chin_mask) 튜플

        Returns:
            dict: {
                'a_median': a 중간값,
                'b_median': b 중간값,
                'chroma': 채도 C* = sqrt(a² + b²),
                'L_normalized': 얼굴 내부 정규화된 L값,
                'L_cheek_raw': 볼 L 원본값 (참고용),
                'warmth_score': 웜/쿨 점수 (b 중심)
            }
        """
        forehead_mask, cheek_mask, chin_mask = masks

        # LAB 변환
        lab = cv2.cvtColor(skin_pixels, cv2.COLOR_BGR2LAB)

        # 피부색 필터용 HSV/YCrCb 변환
        hsv = cv2.cvtColor(skin_pixels, cv2.COLOR_BGR2HSV)
        ycrcb = cv2.cvtColor(skin_pixels, cv2.COLOR_BGR2YCrCb)

        # 각 영역 LAB 추출
        def extract_region_lab(mask):
            """단일 영역의 robust LAB 추출 (피부색 필터 + outlier 제거)"""
            masked_lab = lab[mask > 0]
            masked_hsv = hsv[mask > 0]
            masked_ycrcb = ycrcb[mask > 0]

            if len(masked_lab) == 0:
                return None, None, None

            L_vals = masked_lab[:, 0].astype(float)
            a_vals = masked_lab[:, 1].astype(float)
            b_vals = masked_lab[:, 2].astype(float)

            # HSV 값
            H_vals = masked_hsv[:, 0].astype(float)
            S_vals = masked_hsv[:, 1].astype(float)
            V_vals = masked_hsv[:, 2].astype(float)

            # YCrCb 값
            Y_vals = masked_ycrcb[:, 0].astype(float)
            Cr_vals = masked_ycrcb[:, 1].astype(float)
            Cb_vals = masked_ycrcb[:, 2].astype(float)

            # 🔴 피부색 필터 (밝기 하드컷 제거, YCrCb 기반으로만)
            skin_mask = np.logical_and(
                (Cr_vals >= 133) & (Cr_vals <= 173),
                (Cb_vals >= 77) & (Cb_vals <= 127),
            )

            # 피부색 필터 적용
            if np.sum(skin_mask) >= 10:
                L_vals = L_vals[skin_mask]
                a_vals = a_vals[skin_mask]
                b_vals = b_vals[skin_mask]
            else:
                # 최소한 너무 극단적인 어두운 것만 제외
                relaxed_mask = L_vals > 50  # 80 대신 50으로 완화
                if np.sum(relaxed_mask) >= 10:
                    L_vals = L_vals[relaxed_mask]
                    a_vals = a_vals[relaxed_mask]
                    b_vals = b_vals[relaxed_mask]

            if len(L_vals) < 10:  # 최소 픽셀 수
                return None, None, None

            # L, a, b 각각에 대해 10~90 percentile outlier 제거
            L_p10, L_p90 = np.percentile(L_vals, [10, 90])
            a_p10, a_p90 = np.percentile(a_vals, [10, 90])
            b_p10, b_p90 = np.percentile(b_vals, [10, 90])

            # 모든 조건을 만족하는 픽셀만 선택
            outlier_mask = np.logical_and.reduce([
                (L_vals >= L_p10) & (L_vals <= L_p90),
                (a_vals >= a_p10) & (a_vals <= a_p90),
                (b_vals >= b_p10) & (b_vals <= b_p90)
            ])

            if np.sum(outlier_mask) < 5:
                outlier_mask = np.ones(len(L_vals), dtype=bool)

            # Median 계산 (하이라이트·기미·모공 그림자 제거)
            L_med = np.median(L_vals[outlier_mask])
            a_med = np.median(a_vals[outlier_mask])
            b_med = np.median(b_vals[outlier_mask])

            return L_med, a_med, b_med

        # 각 영역 추출
        L_forehead, a_forehead, b_forehead = extract_region_lab(forehead_mask)
        L_cheek, a_cheek, b_cheek = extract_region_lab(cheek_mask)
        L_chin, a_chin, b_chin = extract_region_lab(chin_mask)

        print(f"[DEBUG] 이마 LAB: L={L_forehead}, a={a_forehead}, b={b_forehead}")
        print(f"[DEBUG] 볼 LAB: L={L_cheek}, a={a_cheek}, b={b_cheek}")
        print(f"[DEBUG] 턱 LAB: L={L_chin}, a={a_chin}, b={b_chin}")

        # 볼 영역이 없으면 실패
        if L_cheek is None or a_cheek is None or b_cheek is None:
            raise ValueError("볼 영역에서 유효한 피부를 찾을 수 없습니다.")

        # 표준 LAB 스케일로 변환 (OpenCV → 표준)
        def opencv_to_standard(L, a, b):
            """OpenCV LAB (0-255) → 표준 LAB (L:0-100, a/b:-128~127)"""
            L_std = (L / 255.0) * 100
            a_std = a - 128
            b_std = b - 128
            return L_std, a_std, b_std

        L_cheek_std, a_cheek_std, b_cheek_std = opencv_to_standard(L_cheek, a_cheek, b_cheek)

        # Chroma 계산 (채도)
        chroma = np.sqrt(a_cheek_std**2 + b_cheek_std**2)

        # L 정규화 (얼굴 내부 비율)
        if L_forehead is not None and L_chin is not None:
            # 이마와 턱의 평균 대비 볼의 비율
            L_reference = 0.5 * L_forehead + 0.5 * L_chin
            if L_reference > 0:
                L_normalized = L_cheek / L_reference
            else:
                L_normalized = 1.0
        else:
            # 이마나 턱이 없으면 정규화 불가 → 1.0
            L_normalized = 1.0

        # Warmth는 절대 b* 값 그대로 사용
        # b* > 0 = 웜톤 (노란기)
        # b* < 0 = 쿨톤 (파란기)
        # 얼굴 내부 비교는 조명 영향을 받으므로 절대 사용 금지!
        warmth_score = b_cheek_std

        print(f"[DEBUG] Warmth: b*={b_cheek_std:+.2f} ({'Warm' if b_cheek_std > 0 else 'Cool'})")

        # 결과 반환
        features = {
            'a_median': a_cheek_std,
            'b_median': b_cheek_std,
            'chroma': chroma,
            'L_normalized': L_normalized,
            'L_cheek_raw': L_cheek_std,
            'warmth_score': warmth_score,
            # OpenCV 스케일도 반환 (기존 호환성)
            'L_opencv': L_cheek,
            'a_opencv': a_cheek,
            'b_opencv': b_cheek,
        }

        print("\n" + "=" * 80)
        print("[Robust LAB Features]")
        print("=" * 80)
        print(f"a (표준): {a_cheek_std:+.2f}  (Red-Green axis)")
        print(f"b (표준): {b_cheek_std:+.2f}  (Yellow-Blue axis)")
        print(f"Chroma:  {chroma:.2f}  (Saturation)")
        print(f"L (정규화): {L_normalized:.3f}  (Cheek/Reference ratio)")
        print(f"L (원본): {L_cheek_std:.1f}  (Raw lightness)")
        print(f"Warmth Score: {warmth_score:+.2f}  (Higher = Warmer)")
        print("=" * 80)

        return features

    def extract_lab_values(self, skin_pixels, mask):
        """
        기존 인터페이스 호환성 유지
        (HybridClassifier가 이 메서드를 호출하므로)
        """
        # mask가 튜플이면 새 방식
        if isinstance(mask, tuple):
            features = self.extract_robust_lab_features(skin_pixels, mask)
            # 기존 형식으로 반환 (L, a, b)
            return features['L_cheek_raw'], features['a_median'], features['b_median']
        else:
            # 단일 마스크면 기존 방식
            lab = cv2.cvtColor(skin_pixels, cv2.COLOR_BGR2LAB)
            masked_lab = lab[mask > 0]

            if len(masked_lab) == 0:
                raise ValueError("유효한 피부 영역을 찾을 수 없습니다.")

            # Median + outlier 제거
            L_vals = masked_lab[:, 0]
            a_vals = masked_lab[:, 1]
            b_vals = masked_lab[:, 2]

            valid_idx = L_vals > 5
            if np.sum(valid_idx) > 0:
                L_vals = L_vals[valid_idx]
                a_vals = a_vals[valid_idx]
                b_vals = b_vals[valid_idx]

            if len(L_vals) >= 10:
                L_p10, L_p90 = np.percentile(L_vals, [10, 90])
                outlier_mask = (L_vals >= L_p10) & (L_vals <= L_p90)
                if np.sum(outlier_mask) >= 5:
                    L_med = np.median(L_vals[outlier_mask])
                    a_med = np.median(a_vals[outlier_mask])
                    b_med = np.median(b_vals[outlier_mask])
                else:
                    L_med = np.median(L_vals)
                    a_med = np.median(a_vals)
                    b_med = np.median(b_vals)
            else:
                L_med = np.mean(L_vals)
                a_med = np.mean(a_vals)
                b_med = np.mean(b_vals)

            # 표준 스케일
            L = (L_med / 255.0) * 100
            a = a_med - 128
            b = b_med - 128

            return L, a, b


def test_robust_classifier(image_path):
    """
    개선된 분류기 테스트
    """
    import matplotlib.pyplot as plt

    # 이미지 로드 (BGR 그대로 유지)
    image = cv2.imread(image_path)
    if image is None:
        print(f"이미지 로드 실패: {image_path}")
        return

    # Robust 분류기 (BGR 입력)
    classifier = RobustLandmarkClassifier()

    print("=" * 80)
    print("Robust Landmark-based Classifier 테스트")
    print("=" * 80)

    # 추출 (BGR 이미지 그대로 전달)
    skin, masks, vis, eyes_detected = classifier.detect_face_and_extract_skin(image)

    if skin is not None and masks is not None:
        try:
            # Robust LAB 특징 추출
            features = classifier.extract_robust_lab_features(skin, masks)

            # 웜/쿨 판정
            if features['warmth_score'] > 0:
                tone = "Warm (웜톤)"
            else:
                tone = "Cool (쿨톤)"

            print(f"\n판정: {tone}")
            print(f"  → b={features['b_median']:+.2f} (높을수록 웜)")
            print(f"  → a={features['a_median']:+.2f} (보조 지표)")

        except ValueError as e:
            print(f"❌ 특징 추출 실패: {e}")
    else:
        print("❌ 얼굴 검출 실패")

    # 시각화 (BGR → RGB 변환)
    plt.figure(figsize=(10, 6))
    vis_rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)
    plt.imshow(vis_rgb)
    plt.title("Robust Eye-based ROI\n(Blue=Forehead, Red=Cheek, Green=Chin)", fontsize=12)
    plt.axis('off')

    if skin is not None and masks is not None:
        plt.text(10, 30,
                f"a: {features['a_median']:+.1f}\nb: {features['b_median']:+.1f}\nC*: {features['chroma']:.1f}\n"
                f"L_norm: {features['L_normalized']:.2f}\nWarmth: {features['warmth_score']:+.1f}",
                fontsize=10, color='white',
                bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))

    plt.tight_layout()
    plt.savefig('robust_classifier_test.png', dpi=150, bbox_inches='tight')
    print(f"\n✓ 시각화 저장: robust_classifier_test.png")
    plt.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        test_image = "augmented_data/겨울_트루/48.jpg"
        print(f"기본 이미지로 테스트: {test_image}")
        test_robust_classifier(test_image)
    else:
        test_robust_classifier(sys.argv[1])