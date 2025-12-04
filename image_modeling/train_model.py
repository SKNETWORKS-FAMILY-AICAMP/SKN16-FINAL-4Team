"""
4계절 ML 모델 학습
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, StratifiedKFold
import pickle

print("=" * 80)
print("4계절 ML 모델 학습")
print("=" * 80)

# 데이터 로드 (화이트 밸런싱 처리된 데이터)
df = pd.read_csv('final_lab_features_wb.csv', encoding='utf-8-sig')

print(f"\n전체 데이터: {len(df)}개")
for season in ['봄', '여름', '가을', '겨울']:
    count = (df['season'] == season).sum()
    print(f"  {season}: {count}개")

# Feature 준비
feature_cols = ['a_median', 'b_median', 'chroma', 'L_raw']

X = df[feature_cols].values
y = df['season'].values

print(f"\n사용 특징: {feature_cols}")

# 여러 모델 비교
models = {
    'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
    'Random Forest (n=100, d=5)': RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42),
    'Random Forest (n=100, d=10)': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
    'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42),
}

print("\n" + "=" * 80)
print("모델 성능 비교 (5-Fold Cross Validation)")
print("=" * 80)

best_model = None
best_score = 0
best_name = ""

for name, model in models.items():
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')

    model.fit(X, y)
    train_acc = model.score(X, y)

    print(f"\n{name}:")
    print(f"  CV Mean:   {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
    print(f"  Train Acc: {train_acc:.3f}")

    if cv_scores.mean() > best_score:
        best_score = cv_scores.mean()
        best_model = model
        best_name = name

print("\n" + "=" * 80)
print(f"최고 모델: {best_name} (CV: {best_score:.3f})")
print("=" * 80)

# 최종 모델 재학습
best_model.fit(X, y)

# 상세 평가
print("\n[전체 데이터 성능]")
y_pred = best_model.predict(X)
acc = (y_pred == y).mean()
print(f"정확도: {(y_pred == y).sum()}/{len(y)} = {acc:.1%}")

print("\n계절별 정확도:")
for season in ['봄', '여름', '가을', '겨울']:
    mask = y == season
    correct = (y_pred[mask] == y[mask]).sum()
    total = mask.sum()
    print(f"  {season}: {correct}/{total} = {correct/total:.1%}")

# Feature Importance
if hasattr(best_model, 'feature_importances_'):
    print("\n특징 중요도:")
    importances = best_model.feature_importances_
    for feat, imp in sorted(zip(feature_cols, importances), key=lambda x: -x[1]):
        print(f"  {feat:<12}: {imp:.3f}")

# 모델 저장
model_data = {
    'model': best_model,
    'feature_cols': feature_cols,
    'model_name': best_name,
    'cv_score': best_score,
    'train_acc': acc,
}

with open('full_season_ml_model.pkl', 'wb') as f:
    pickle.dump(model_data, f)

print(f"\n✅ 모델 저장: full_season_ml_model.pkl")
print(f"   모델: {best_name}")
print(f"   CV Score: {best_score:.1%}")
print(f"   Train Acc: {acc:.1%}")

print("\n" + "=" * 80)
print("완료!")
print("=" * 80)