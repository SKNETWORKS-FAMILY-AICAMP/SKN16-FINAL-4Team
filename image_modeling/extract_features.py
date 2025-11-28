"""
화이트 밸런싱 적용한 훈련 데이터 재생성 및 모델 재훈련
"""
import os
import sys
import cv2
import numpy as np
import pandas as pd
from pathlib import Path

# 상위 디렉토리 path 추가
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from landmark_classifier import RobustLandmarkClassifier

def main():
    """화이트 밸런싱 적용하여 LAB features 재추출"""

    # 분류기 초기화 (화이트 밸런싱 5% 활성화)
    classifier = RobustLandmarkClassifier()

    # 증강된 이미지 폴더 (원본 훈련에 사용한 데이터 - 231개 샘플)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    labeled_data_dir = os.path.join(current_dir, 'augmented_data')

    # 결과 저장
    results = []
    total = 0
    success = 0
    failed = 0

    # 12개 클래스
    classes = [
        '가을_딥', '가을_소프트', '가을_트루',
        '겨울_딥', '겨울_브라이트', '겨울_트루',
        '봄_라이트', '봄_브라이트', '봄_트루',
        '여름_라이트', '여름_뮤트', '여름_트루'
    ]

    print("=" * 80)
    print("화이트 밸런싱 적용한 훈련 데이터 생성")
    print("=" * 80)

    for class_name in classes:
        class_dir = os.path.join(labeled_data_dir, class_name)
        if not os.path.exists(class_dir):
            print(f"⚠️  폴더 없음: {class_name}")
            continue

        # 계절과 서브타입 분리
        season, subtype = class_name.split('_')

        # 이미지 파일 목록
        image_files = [f for f in os.listdir(class_dir)
                      if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        print(f"\n[{class_name}] {len(image_files)}개 이미지 처리 중...")

        for img_file in image_files:
            total += 1
            img_path = os.path.join(class_dir, img_file)

            try:
                # 이미지 로드
                image = cv2.imread(img_path)
                if image is None:
                    print(f"  ❌ 로드 실패: {img_file}")
                    failed += 1
                    continue

                # 얼굴 검출 및 피부 영역 추출 (화이트 밸런싱 5% 적용됨)
                skin, masks, vis, eyes_detected = classifier.detect_face_and_extract_skin(image)

                if skin is None or masks is None:
                    print(f"  ❌ 얼굴 검출 실패: {img_file}")
                    failed += 1
                    continue

                # LAB 특징 추출 (화이트 밸런싱된 이미지에서)
                features = classifier.extract_robust_lab_features(skin, masks)

                # 결과 저장
                results.append({
                    'season': season,
                    'subtype': subtype,
                    'a_median': features['a_median'],
                    'b_median': features['b_median'],
                    'chroma': features['chroma'],
                    'L_normalized': features['L_normalized'],
                    'L_raw': features['L_cheek_raw'],
                    'warmth_score': features['warmth_score'],
                    'season_group': f"{season}_{'웜' if features['warmth_score'] > 0 else '쿨'}",
                    'folder': class_name,
                    'filename': img_file,
                    'eyes_detected': eyes_detected
                })

                success += 1

                if success % 10 == 0:
                    print(f"  진행 중... {success}/{total}")

            except Exception as e:
                print(f"  ❌ 오류 ({img_file}): {e}")
                failed += 1
                continue

    # DataFrame 생성
    df = pd.DataFrame(results)

    # CSV 저장
    output_path = 'final_lab_features_wb.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print("\n" + "=" * 80)
    print("처리 완료")
    print("=" * 80)
    print(f"✅ 성공: {success}개")
    print(f"❌ 실패: {failed}개")
    print(f"📊 총 샘플: {len(df)}개")
    print(f"💾 저장 위치: {output_path}")
    print("=" * 80)

    # 클래스별 통계
    print("\n[클래스별 샘플 수]")
    class_counts = df.groupby(['season', 'subtype']).size()
    print(class_counts)

    return df

if __name__ == "__main__":
    df = main()