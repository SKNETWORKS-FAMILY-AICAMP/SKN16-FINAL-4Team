"""
퍼스널컬러 안전 증강 (색상 언더톤 보존)
기하학적 변환 + 현실적 촬영 환경 시뮬레이션
"""
import os
import cv2
import numpy as np
from pathlib import Path
import shutil
import random


def augment_image_robust(image, aug_index):
    """
    퍼스널컬러 안전 증강 (10가지)

    Args:
        image: 원본 이미지 (BGR)
        aug_index: 증강 인덱스 (0~9)

    Returns:
        (aug_name, augmented_image)
    """
    h, w = image.shape[:2]

    # 0. 원본
    if aug_index == 0:
        return ('orig', image.copy())

    # 1. 좌우 반전
    elif aug_index == 1:
        return ('flip', cv2.flip(image, 1))

    # 2. 회전 +5도
    elif aug_index == 2:
        M = cv2.getRotationMatrix2D((w/2, h/2), 5, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REFLECT)
        return ('rot5', rotated)

    # 3. 회전 -5도
    elif aug_index == 3:
        M = cv2.getRotationMatrix2D((w/2, h/2), -5, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REFLECT)
        return ('rotm5', rotated)

    # 4. 확대 105%
    elif aug_index == 4:
        new_w, new_h = int(w * 1.05), int(h * 1.05)
        zoomed = cv2.resize(image, (new_w, new_h))
        crop_x = (new_w - w) // 2
        crop_y = (new_h - h) // 2
        cropped = zoomed[crop_y:crop_y+h, crop_x:crop_x+w]
        return ('zin', cropped)

    # 5. 축소 95%
    elif aug_index == 5:
        new_w, new_h = int(w * 0.95), int(h * 0.95)
        zoomed = cv2.resize(image, (new_w, new_h))
        padded = cv2.copyMakeBorder(
            zoomed,
            (h - new_h) // 2, h - new_h - (h - new_h) // 2,
            (w - new_w) // 2, w - new_w - (w - new_w) // 2,
            cv2.BORDER_REFLECT
        )
        return ('zout', padded)

    # 6. 밝기 조절 (Exposure) ±10
    elif aug_index == 6:
        beta = random.uniform(-10, 10)
        adjusted = cv2.convertScaleAbs(image, alpha=1.0, beta=beta)
        return ('exp', adjusted)

    # 7. 대비 조절 (Contrast) ±10%
    elif aug_index == 7:
        alpha = random.uniform(0.9, 1.1)
        adjusted = cv2.convertScaleAbs(image, alpha=alpha, beta=0)
        return ('con', adjusted)

    # 8. Gaussian Blur (3x3) - 스마트폰 초점 실패
    elif aug_index == 8:
        blurred = cv2.GaussianBlur(image, (3, 3), 0)
        return ('blur', blurred)

    # 9. JPEG 압축 (70~95 품질) - 카톡/인스타 업로드
    elif aug_index == 9:
        quality = random.randint(70, 95)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        _, encoded = cv2.imencode('.jpg', image, encode_param)
        compressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        return ('jpeg', compressed)

    else:
        return ('orig', image.copy())


def augment_dataset(input_dir='labeled_data', output_dir='augmented_data_10x',
                    target_per_class=20, max_aug_types=10, balance=True):
    """
    퍼스널컬러 안전 증강 적용

    Args:
        input_dir: 입력 디렉토리
        output_dir: 출력 디렉토리 (증강 개수 표시)
        target_per_class: 클래스당 목표 이미지 수
        max_aug_types: 최대 증강 타입 수 (1~10)
        balance: True면 모든 클래스를 정확히 target_per_class로 맞춤
    """
    # 출력 디렉토리 생성
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    print("=" * 80)
    print(f"퍼스널컬러 안전 증강 ({max_aug_types}가지 증강)")
    print("=" * 80)
    print("\n증강 타입:")
    print("  0. 원본")
    print("  1. 좌우반전")
    print("  2~3. 회전 ±5도")
    print("  4~5. 확대/축소 ±5%")
    print("  6. 밝기조절 ±10 (Exposure)")
    print("  7. 대비조절 ±10% (Contrast)")
    print("  8. Gaussian Blur 3x3 (초점실패)")
    print("  9. JPEG 압축 70~95 (SNS 업로드)")
    print("\n" + "=" * 80)

    total_original = 0
    total_augmented = 0

    for class_name in sorted(os.listdir(input_dir)):
        class_path = os.path.join(input_dir, class_name)

        if not os.path.isdir(class_path):
            continue

        # ERROR 폴더 제외
        if class_name == 'ERROR':
            continue

        output_class_path = os.path.join(output_dir, class_name)
        os.makedirs(output_class_path, exist_ok=True)

        # 원본 이미지 수집
        images = []
        for img_file in sorted(os.listdir(class_path)):
            if not img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue

            img_path = os.path.join(class_path, img_file)
            image = cv2.imread(img_path)

            if image is not None:
                images.append((img_file, image))

        original_count = len(images)
        total_original += original_count

        if original_count == 0:
            print(f"⚠️  {class_name}: 이미지 없음")
            continue

        # 필요한 증강 수 계산
        augmentations_per_image = min(max_aug_types, max(1, target_per_class // original_count))

        print(f"\n[{class_name}]")
        print(f"  원본: {original_count}장")
        print(f"  이미지당 증강: {augmentations_per_image}가지")
        print(f"  목표: {target_per_class}장")

        saved_count = 0
        aug_counter = {}

        # Balance 모드: 정확히 target_per_class 맞추기
        if balance:
            # 원본 이미지를 순환하면서 증강 적용
            img_cycle = 0
            aug_idx = 0

            while saved_count < target_per_class:
                # 현재 이미지 선택 (순환)
                img_file, image = images[img_cycle % original_count]
                base_name = Path(img_file).stem

                # 증강 적용
                aug_name, aug_img = augment_image_robust(image, aug_idx)

                # 파일명 생성
                output_filename = f"{base_name}_aug{aug_idx:03d}.jpg"
                output_path = os.path.join(output_class_path, output_filename)

                # 저장
                cv2.imwrite(output_path, aug_img)
                saved_count += 1

                # 통계
                aug_counter[aug_name] = aug_counter.get(aug_name, 0) + 1

                # 다음 이미지 및 증강 타입으로 이동
                img_cycle += 1
                if img_cycle % original_count == 0:
                    aug_idx = (aug_idx + 1) % max_aug_types

        else:
            # 기존 방식
            for img_file, image in images:
                base_name = Path(img_file).stem

                # 증강 적용
                for aug_idx in range(augmentations_per_image):
                    if saved_count >= target_per_class:
                        break

                    aug_name, aug_img = augment_image_robust(image, aug_idx)

                    # 파일명 생성 (aug001, aug002, ...)
                    output_filename = f"{base_name}_aug{aug_idx:03d}.jpg"
                    output_path = os.path.join(output_class_path, output_filename)

                    # 저장
                    cv2.imwrite(output_path, aug_img)
                    saved_count += 1

                    # 통계
                    aug_counter[aug_name] = aug_counter.get(aug_name, 0) + 1

                if saved_count >= target_per_class:
                    break

        total_augmented += saved_count

        print(f"  저장: {saved_count}장")
        print(f"  증강 분포: {aug_counter}")

    print("\n" + "=" * 80)
    print("✅ 증강 완료!")
    print("=" * 80)

    # 최종 통계
    print(f"\n전체 통계:")
    print(f"  원본 이미지: {total_original}장")
    print(f"  증강 후: {total_augmented}장")
    print(f"  증배율: {total_augmented / total_original:.1f}x")

    # 클래스별 분포
    print("\n클래스별 최종 분포:")
    for class_name in sorted(os.listdir(output_dir)):
        class_path = os.path.join(output_dir, class_name)
        if os.path.isdir(class_path):
            count = len([f for f in os.listdir(class_path)
                        if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
            print(f"  {class_name}: {count}장")


if __name__ == "__main__":
    # 10가지 증강 모두 사용
    augment_dataset(
        input_dir='labeled_data',
        output_dir='augmented_data',  # 최종 증강 데이터
        target_per_class=20,
        max_aug_types=10  # 0~9번 증강 모두 사용
    )