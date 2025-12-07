"""
가상 메이크업 적용기 (원본 VirtualMakeup 코드 기반)
"""
import cv2
import numpy as np
import mediapipe as mp
from PIL import Image


class MakeupApplierCV:
    """
    원본 VirtualMakeup 코드 기반 메이크업 적용기
    """

    def __init__(self):
        print("\n" + "="*50)
        print("MakeupApplierCV 초기화")
        print("="*50 + "\n")

        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )

        # 영역 인덱스
        self.regions = {
            # 피부: 이마 상단(151, 10, 338)부터 턱(152)까지 얼굴 전체 윤곽
            '피부': [
                # 이마 상단 중앙
                151, 10, 338,
                # 오른쪽 이마 → 관자놀이 → 턱선
                297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
                397, 365, 379, 378, 400, 377,
                # 턱
                152,
                # 왼쪽 턱선 → 관자놀이 → 이마
                148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109
            ],
            '입술': [
                61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291,
                375, 321, 405, 314, 17, 84, 181, 91, 146, 61
            ],
            # 눈썹: 폐곡선 형성 (하단 안쪽 -> 하단 바깥쪽 -> 꼬리 -> 상단 바깥쪽 -> 상단 안쪽)
            '왼쪽_눈썹': [46, 53, 52, 65, 55, 107, 66, 105, 63, 70],
            '오른쪽_눈썹': [276, 283, 282, 295, 285, 336, 296, 334, 293, 300],
        }

        print("MediaPipe Face Mesh 초기화 완료")

    def hex_to_bgr(self, hex_color: str) -> tuple:
        """HEX 색상을 BGR로 변환"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (rgb[2], rgb[1], rgb[0])

    def get_landmarks(self, image: np.ndarray):
        """얼굴 랜드마크 추출"""
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_image)

        if not results.multi_face_landmarks:
            return None

        h, w = image.shape[:2]
        landmarks = []
        for lm in results.multi_face_landmarks[0].landmark:
            landmarks.append((int(lm.x * w), int(lm.y * h)))

        return landmarks

    def extract_region_mask(self, image, landmarks, region_name):
        """영역 마스크 생성"""
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        indices = self.regions.get(region_name)
        if not indices:
            return mask

        points = np.array([landmarks[i] for i in indices], dtype=np.int32)
        cv2.fillPoly(mask, [points], 255)
        return mask

    def apply_lip_makeup(self, image, landmarks, color_bgr, intensity=0.5):
        """입술 메이크업 (그라데이션)"""
        h, w = image.shape[:2]
        result = image.copy()

        lip_mask = self.extract_region_mask(image, landmarks, '입술')
        if np.sum(lip_mask) == 0:
            return result

        # 거리 변환으로 그라데이션
        dist_transform = cv2.distanceTransform(lip_mask, cv2.DIST_L2, 5)
        dist_transform = cv2.normalize(dist_transform, None, 0, 1, cv2.NORM_MINMAX)
        dist_transform = cv2.GaussianBlur(dist_transform, (15, 15), 0)
        dist_transform = np.power(dist_transform, 0.7)

        color_layer = np.zeros_like(image)
        color_layer[:] = color_bgr

        alpha = (dist_transform * intensity)[:, :, np.newaxis]
        alpha = np.repeat(alpha, 3, axis=2)

        lip_area = lip_mask > 0
        result[lip_area] = (
            (1 - alpha[lip_area]) * result[lip_area] +
            alpha[lip_area] * color_layer[lip_area]
        ).astype(np.uint8)

        # 경계 부드럽게
        blur_mask = cv2.GaussianBlur(lip_mask.astype(np.float32), (9, 9), 0) / 255.0
        blur_mask = blur_mask[:, :, np.newaxis]
        final = (blur_mask * result + (1 - blur_mask) * image).astype(np.uint8)

        return final

    def apply_eyebrow_makeup(self, image, landmarks, color_bgr, intensity=0.4):
        """눈썹 메이크업 - 폐곡선 인덱스로 정확한 영역 지정"""
        result = image.copy()
        h, w = image.shape[:2]

        # 왼쪽 눈썹: 안쪽에서 시작해 반시계방향으로 한 바퀴 도는 순서
        # 하단 안쪽 -> 하단 바깥쪽 -> 꼬리(107) -> 상단 바깥쪽 -> 상단 안쪽
        left_eyebrow_indices = [46, 53, 52, 65, 55, 107, 66, 105, 63, 70]

        # 오른쪽 눈썹: 안쪽에서 시작해 반시계방향으로 한 바퀴 도는 순서
        # 하단 안쪽 -> 하단 바깥쪽 -> 꼬리(336) -> 상단 바깥쪽 -> 상단 안쪽
        right_eyebrow_indices = [276, 283, 282, 295, 285, 336, 296, 334, 293, 300]

        for eyebrow_idx in [left_eyebrow_indices, right_eyebrow_indices]:
            # 눈썹 포인트 추출 (이미 폐곡선 순서)
            brow_pts = np.array([landmarks[i] for i in eyebrow_idx if i < len(landmarks)], dtype=np.int32)

            if len(brow_pts) < 3:
                continue

            # 마스크 생성 (이미 폐곡선 순서로 정렬된 포인트 사용)
            eyebrow_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(eyebrow_mask, [brow_pts], 255)

            # 경계 블러
            eyebrow_mask_blur = cv2.GaussianBlur(eyebrow_mask, (7, 7), 0)
            alpha = (eyebrow_mask_blur.astype(np.float32) / 255.0) * intensity

            # 색상 레이어
            color_layer = np.zeros_like(image)
            color_layer[:] = color_bgr

            # 블렌딩
            alpha_3ch = alpha[:, :, np.newaxis]
            result = ((1 - alpha_3ch) * result + alpha_3ch * color_layer).astype(np.uint8)

        return result

    def apply_eyeliner_makeup(self, image, landmarks, color_bgr,
                               intensity=0.8, thickness=4, tail_ratio=0.32,
                               tail_angle_deg=-15.0):
        """아이라이너 적용 (원본 방식)"""
        result = image.copy()
        h, w = image.shape[:2]
        thickness = max(1, int(round(thickness)))

        face_center_x = float(np.mean(np.array(landmarks)[:, 0]))

        # 상안검 라인 포인트
        left_upper_indices = [33, 246, 161, 160, 159, 158, 157, 173]
        right_upper_indices = [263, 466, 388, 387, 386, 385, 384, 398]

        eyeliner_mask = np.zeros((h, w), dtype=np.uint8)

        for eye_indices, is_left in [(left_upper_indices, True), (right_upper_indices, False)]:
            eye_pts = np.array([landmarks[i] for i in eye_indices if i < len(landmarks)], dtype=np.int32)
            if len(eye_pts) < 2:
                continue

            eye_pts_f = eye_pts.astype(np.float32)

            # 내부/외곽 포인트 결정
            distances = np.abs(eye_pts_f[:, 0] - face_center_x)
            inner_idx = int(np.argmin(distances))
            outer_idx = int(np.argmax(distances))
            inner_pt = eye_pts_f[inner_idx]
            outer_pt = eye_pts_f[outer_idx]

            # 폴리라인으로 눈 라인 그리기
            cv2.polylines(eyeliner_mask, [eye_pts], isClosed=False, color=255, thickness=thickness)

            # 눈꼬리 연장
            direction = outer_pt - inner_pt
            dir_norm = np.linalg.norm(direction)
            if dir_norm < 1e-3:
                continue

            # 꼬리 길이 (눈 길이의 tail_ratio 비율)
            tail_length = dir_norm * tail_ratio

            if tail_length > 0:
                theta = np.deg2rad(tail_angle_deg)

                if is_left:
                    # 왼쪽 눈: 왼쪽 위로
                    wing_dir = np.array([-np.cos(theta), -np.sin(theta)], dtype=np.float32)
                else:
                    # 오른쪽 눈: 오른쪽 위로
                    wing_dir = np.array([np.cos(theta), -np.sin(theta)], dtype=np.float32)

                wing_dir = wing_dir / (np.linalg.norm(wing_dir) + 1e-6)

                # 분절 라인으로 자연스러운 꼬리
                prev_pt = outer_pt
                for t in np.linspace(0.35, 1.0, 4):
                    curr_pt = outer_pt + wing_dir * (tail_length * t)
                    seg_thickness = max(1, int(round(thickness * (1.0 - 0.45 * t))))
                    cv2.line(
                        eyeliner_mask,
                        tuple(prev_pt.astype(np.int32)),
                        tuple(curr_pt.astype(np.int32)),
                        255,
                        thickness=seg_thickness
                    )
                    prev_pt = curr_pt

        if np.sum(eyeliner_mask) == 0:
            return result

        # 경계 부드럽게
        blur_size = max(3, thickness * 2 + 1)
        if blur_size % 2 == 0:
            blur_size += 1
        soft_mask = cv2.GaussianBlur(eyeliner_mask, (blur_size, blur_size), 0)
        soft_mask = soft_mask.astype(np.float32) / 255.0

        alpha = np.clip(soft_mask * intensity, 0, 0.9)
        alpha = alpha[:, :, np.newaxis]
        alpha = np.repeat(alpha, 3, axis=2)

        color_layer = np.zeros_like(image)
        color_layer[:] = color_bgr

        result = ((1 - alpha) * result + alpha * color_layer).astype(np.uint8)

        return result

    def apply_eyeshadow_makeup(self, image, landmarks, colors, style="gradient", intensity=0.5):
        """
        아이섀도우 메이크업
        style: "gradient" (자연스러운 그라데이션), "smoky" (스모키), "glitter" (글리터)
        colors: 그라데이션용 색상 리스트 (HEX)
        """
        result = image.copy()
        h, w = image.shape[:2]

        # 눈 윗부분 영역 (눈꺼풀)
        left_eye_upper = [157, 158, 159, 160, 161, 246, 33, 130, 226, 247, 30, 29, 27, 28, 56, 190]
        right_eye_upper = [384, 385, 386, 387, 388, 466, 263, 359, 446, 467, 260, 259, 257, 258, 286, 414]

        # 색상 변환
        if not colors or len(colors) == 0:
            colors = ["#D2B48C"]  # 기본 베이지

        main_color_bgr = self.hex_to_bgr(colors[0])

        # 두 번째 색상 (그라데이션/스모키용)
        if len(colors) > 1:
            secondary_color_bgr = self.hex_to_bgr(colors[1])
        else:
            # 더 어두운 색상 생성
            secondary_color_bgr = tuple(max(0, c - 40) for c in main_color_bgr)

        # 세 번째 색상 (강조색)
        if len(colors) > 2:
            accent_color_bgr = self.hex_to_bgr(colors[2])
        else:
            accent_color_bgr = tuple(max(0, c - 80) for c in main_color_bgr)

        for eye_indices in [left_eye_upper, right_eye_upper]:
            eye_pts = np.array([landmarks[i] for i in eye_indices if i < len(landmarks)], dtype=np.int32)
            if len(eye_pts) < 3:
                continue

            # 눈꺼풀 마스크
            eye_mask = np.zeros((h, w), dtype=np.uint8)
            hull = cv2.convexHull(eye_pts)
            cv2.fillConvexPoly(eye_mask, hull, 255)

            # 위로 확장 (눈꺼풀 영역 확대)
            kernel = np.ones((7, 7), np.uint8)
            eye_mask = cv2.dilate(eye_mask, kernel, iterations=2)

            # 거리 변환으로 그라데이션 생성
            dist = cv2.distanceTransform(eye_mask, cv2.DIST_L2, 5)
            if dist.max() > 0:
                dist = dist / dist.max()

            dist = cv2.GaussianBlur(dist, (21, 21), 0)

            if style == "smoky":
                # 스모키: 더 진하고 넓게, 경계 흐림
                alpha_base = np.power(dist, 0.4) * intensity * 1.5
                alpha_base = np.clip(alpha_base, 0, 1)

                # 메인 색상 (밝은)
                color_layer1 = np.zeros_like(image)
                color_layer1[:] = main_color_bgr

                # 강조 색상 (어두운) - 외곽
                color_layer2 = np.zeros_like(image)
                color_layer2[:] = accent_color_bgr

                # 내부는 밝게, 외곽은 어둡게
                inner_mask = (dist > 0.5).astype(np.float32)
                inner_mask = cv2.GaussianBlur(inner_mask, (31, 31), 0)

                alpha1 = alpha_base * inner_mask
                alpha2 = alpha_base * (1 - inner_mask) * 0.7

                alpha1_3ch = alpha1[:, :, np.newaxis]
                alpha2_3ch = alpha2[:, :, np.newaxis]

                result = ((1 - alpha1_3ch) * result + alpha1_3ch * color_layer1).astype(np.uint8)
                result = ((1 - alpha2_3ch) * result + alpha2_3ch * color_layer2).astype(np.uint8)

            elif style == "glitter":
                # 글리터: 반짝이 효과 추가
                alpha_base = np.power(dist, 0.6) * intensity

                # 베이스 색상
                color_layer = np.zeros_like(image)
                color_layer[:] = main_color_bgr

                alpha_3ch = alpha_base[:, :, np.newaxis]
                result = ((1 - alpha_3ch) * result + alpha_3ch * color_layer).astype(np.uint8)

                # 글리터 점들 추가
                glitter_mask = (eye_mask > 0)
                glitter_points = np.where(glitter_mask)

                if len(glitter_points[0]) > 0:
                    # 랜덤 글리터 위치
                    num_glitters = min(50, len(glitter_points[0]) // 10)
                    np.random.seed(42)  # 일관성 위해
                    indices = np.random.choice(len(glitter_points[0]), num_glitters, replace=False)

                    for idx in indices:
                        py, px = glitter_points[0][idx], glitter_points[1][idx]
                        # 밝은 점 (하이라이트)
                        brightness = np.random.randint(200, 255)
                        size = np.random.randint(1, 3)
                        cv2.circle(result, (px, py), size, (brightness, brightness, brightness), -1)

            else:  # gradient (기본)
                alpha_base = np.power(dist, 0.7) * intensity

                color_layer = np.zeros_like(image)
                color_layer[:] = main_color_bgr

                alpha_3ch = alpha_base[:, :, np.newaxis]
                result = ((1 - alpha_3ch) * result + alpha_3ch * color_layer).astype(np.uint8)

        return result

    def apply_blush_makeup(self, image, landmarks, color_bgr, intensity=0.4):
        """볼터치 메이크업"""
        result = image.copy()
        h, w = image.shape[:2]

        # 피부 마스크 생성 (머리카락 영역 제외용)
        face_outline = self.regions.get('피부', [])
        skin_mask = np.zeros((h, w), dtype=np.uint8)
        if face_outline:
            face_pts = np.array([landmarks[i] for i in face_outline], dtype=np.int32)
            cv2.fillPoly(skin_mask, [face_pts], 255)

        # 볼 영역 랜드마크
        left_cheek_indices = [50, 101, 118, 119, 120, 121, 128, 217, 116, 117, 111, 100, 36, 47]
        right_cheek_indices = [280, 330, 347, 348, 349, 350, 357, 437, 345, 346, 340, 329, 266, 277]

        for cheek_indices in [left_cheek_indices, right_cheek_indices]:
            cheek_pts = np.array([landmarks[i] for i in cheek_indices if i < len(landmarks)], dtype=np.int32)
            if len(cheek_pts) < 3:
                continue

            cheek_mask = np.zeros((h, w), dtype=np.uint8)
            hull = cv2.convexHull(cheek_pts)
            cv2.fillConvexPoly(cheek_mask, hull, 255)

            # 마스크 확장
            kernel = np.ones((15, 15), np.uint8)
            cheek_mask = cv2.dilate(cheek_mask, kernel, iterations=2)

            # 피부 영역과 AND 연산 (머리카락 영역 제외)
            cheek_mask = cv2.bitwise_and(cheek_mask, skin_mask)

            # 그라데이션
            dist_transform = cv2.distanceTransform(cheek_mask, cv2.DIST_L2, 5)
            if dist_transform.max() > 0:
                dist_transform = dist_transform / dist_transform.max()

            dist_transform = cv2.GaussianBlur(dist_transform, (51, 51), 0)
            dist_transform = np.power(dist_transform, 0.5)

            color_layer = np.zeros_like(image)
            color_layer[:] = color_bgr

            alpha = dist_transform * intensity
            alpha = np.clip(alpha, 0, 1)
            alpha = alpha[:, :, np.newaxis]
            alpha = np.repeat(alpha, 3, axis=2)

            result = ((1 - alpha) * result + alpha * color_layer).astype(np.uint8)

        return result

    def apply_skin_base(self, image, landmarks, intensity=0.3, skin_type="tone_up", warmth=0.0):
        """
        피부 베이스 메이크업
        skin_type: "tone_up" (밝게), "tone_down" (어둡게), "warm" (따뜻하게), "cool" (차갑게)
        intensity: 효과 강도 (0.0 ~ 1.0)
        warmth: 색온도 조절 (-1.0 차갑게 ~ 1.0 따뜻하게)
        """
        result = image.copy()
        h, w = image.shape[:2]

        # 피부 마스크
        face_outline = self.regions.get('피부', [])
        if not face_outline:
            return result

        face_pts = np.array([landmarks[i] for i in face_outline], dtype=np.int32)
        skin_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(skin_mask, [face_pts], 255)

        # 눈, 눈썹, 입술 제외 (작은 kernel로 최소한의 여백만)
        for region in ['왼쪽_눈썹', '오른쪽_눈썹', '입술']:
            exclude_mask = self.extract_region_mask(image, landmarks, region)
            kernel = np.ones((5, 5), np.uint8)
            exclude_mask = cv2.dilate(exclude_mask, kernel, iterations=1)
            skin_mask = cv2.subtract(skin_mask, exclude_mask)

        if np.sum(skin_mask) == 0:
            return result

        # 경계 부드럽게
        skin_mask_float = skin_mask.astype(np.float32) / 255.0
        skin_mask_blurred = cv2.GaussianBlur(skin_mask_float, (31, 31), 0)

        # HSV 변환
        hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)

        if skin_type == "tone_up":
            # 톤업: 밝기 증가
            brightness_boost = 1 + (intensity * 0.3)
            hsv[:, :, 2] = np.clip(hsv[:, :, 2] * brightness_boost, 0, 255)
        elif skin_type == "tone_down":
            # 톤다운: 밝기 감소
            brightness_reduction = 1 - (intensity * 0.25)
            hsv[:, :, 2] = np.clip(hsv[:, :, 2] * brightness_reduction, 0, 255)
        elif skin_type == "warm":
            # 따뜻하게: 채도 살짝 올리고 색상을 따뜻한 쪽으로
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1 + intensity * 0.1), 0, 255)
        elif skin_type == "cool":
            # 차갑게: 채도 낮추고 밝기 살짝 올림
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1 - intensity * 0.15), 0, 255)
            hsv[:, :, 2] = np.clip(hsv[:, :, 2] * (1 + intensity * 0.1), 0, 255)

        modified = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # warmth 적용 (색온도)
        if warmth != 0:
            if warmth > 0:
                # 따뜻하게: R 증가, B 감소
                modified = modified.astype(np.float32)
                modified[:, :, 2] = np.clip(modified[:, :, 2] + warmth * 20, 0, 255)  # R
                modified[:, :, 0] = np.clip(modified[:, :, 0] - warmth * 15, 0, 255)  # B
                modified = modified.astype(np.uint8)
            else:
                # 차갑게: B 증가, R 감소
                modified = modified.astype(np.float32)
                modified[:, :, 0] = np.clip(modified[:, :, 0] - warmth * 20, 0, 255)  # B
                modified[:, :, 2] = np.clip(modified[:, :, 2] + warmth * 15, 0, 255)  # R
                modified = modified.astype(np.uint8)

        alpha = skin_mask_blurred * intensity
        alpha = alpha[:, :, np.newaxis]
        alpha = np.repeat(alpha, 3, axis=2)

        result = ((1 - alpha) * result + alpha * modified).astype(np.uint8)

        return result

    def apply_makeup(self, image_path: str, makeup_response: dict,
                     output_path: str = None) -> Image.Image:
        """전체 메이크업 적용"""
        # 이미지 로드
        if isinstance(image_path, str):
            image = cv2.imread(image_path)
        else:
            image = cv2.cvtColor(np.array(image_path), cv2.COLOR_RGB2BGR)

        if image is None:
            raise ValueError(f"이미지를 로드할 수 없습니다: {image_path}")

        # 랜드마크 추출
        landmarks = self.get_landmarks(image)
        if landmarks is None:
            print("얼굴을 찾을 수 없습니다")
            return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        makeup = makeup_response.get("makeup", {})
        result = image.copy()

        # 0. 피부 베이스
        skin_base = makeup.get("skin_base", {})
        if skin_base:
            result = self.apply_skin_base(
                result, landmarks,
                intensity=skin_base.get("intensity", 0.3),
                skin_type=skin_base.get("type", "tone_up"),
                warmth=skin_base.get("warmth", 0.0)
            )
            print(f"피부 베이스 적용: {skin_base.get('type')} ({skin_base.get('intensity'):.0%})")

        # 1. 볼터치
        blush = makeup.get("blush", {})
        if blush:
            color_bgr = self.hex_to_bgr(blush.get("color", "#FFAA80"))
            result = self.apply_blush_makeup(
                result, landmarks,
                color_bgr=color_bgr,
                intensity=blush.get("intensity", 0.4)
            )
            print(f"볼터치 적용: {blush.get('color')} ({blush.get('intensity'):.0%})")

        # 2. 아이섀도우
        eyeshadow = makeup.get("eyeshadow", {})
        if eyeshadow:
            colors = eyeshadow.get("colors", ["#D2B48C"])
            style = eyeshadow.get("style", "gradient")
            result = self.apply_eyeshadow_makeup(
                result, landmarks,
                colors=colors,
                style=style,
                intensity=eyeshadow.get("intensity", 0.5)
            )
            print(f"아이섀도우 적용: {style} 스타일, {colors}")

        # 3. 아이라이너
        eyeliner = makeup.get("eyeliner", {})
        if eyeliner:
            color_bgr = self.hex_to_bgr(eyeliner.get("color", "#2F2F2F"))
            result = self.apply_eyeliner_makeup(
                result, landmarks,
                color_bgr=color_bgr,
                intensity=eyeliner.get("intensity", 0.8),
                thickness=eyeliner.get("thickness", 4),
                tail_ratio=eyeliner.get("tail_length", 0.32),
                tail_angle_deg=eyeliner.get("angle", -15.0)
            )
            print(f"아이라이너 적용: {eyeliner.get('color')} (두께: {eyeliner.get('thickness')}, 꼬리: {eyeliner.get('tail_length'):.0%}, 각도: {eyeliner.get('angle')}°)")

        # 3. 눈썹
        eyebrow = makeup.get("eyebrow", {})
        if eyebrow:
            color_bgr = self.hex_to_bgr(eyebrow.get("color", "#5C4033"))
            result = self.apply_eyebrow_makeup(
                result, landmarks,
                color_bgr=color_bgr,
                intensity=eyebrow.get("intensity", 0.4)
            )
            print(f"눈썹 적용: {eyebrow.get('color')} ({eyebrow.get('intensity'):.0%})")

        # 4. 입술
        lip = makeup.get("lip", {})
        if lip:
            color_bgr = self.hex_to_bgr(lip.get("color", "#E8836B"))
            result = self.apply_lip_makeup(
                result, landmarks,
                color_bgr=color_bgr,
                intensity=lip.get("intensity", 0.5)
            )
            print(f"입술 적용: {lip.get('color')} ({lip.get('intensity'):.0%})")

        # PIL 이미지로 변환
        result_pil = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))

        if output_path:
            result_pil.save(output_path)
            print(f"저장 완료: {output_path}")

        return result_pil


def test():
    """테스트"""
    from demo_responses import DEFAULT_MAKEUP

    applier = MakeupApplierCV()
    print(DEFAULT_MAKEUP)


if __name__ == "__main__":
    test()