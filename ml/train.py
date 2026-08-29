import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from sklearn.metrics import (
    roc_auc_score,
    classification_report,
    confusion_matrix,
    accuracy_score
)

from xgboost import XGBClassifier


# =========================================================
# 1. LOAD DATASET
# =========================================================

df = pd.read_csv("events.csv")

print("=" * 60)
print("DATASET")
print("=" * 60)

print("Dataset Shape:", df.shape)


# =========================================================
# 2. TARGET
# =========================================================

target_col = "recovered"

df = df[df[target_col].isin([0, 1])].copy()

y = df[target_col]


# =========================================================
# 3. FEATURES
# =========================================================

numeric_features = [
    "amount",
    "customer_age_days",
    "prev_payment_count",
    "prev_success_count",
    "prev_failure_count",
    "historical_success_rate",
    "days_since_last_success",
    "customer_activity_score",
    "attempt_number",
    "hours_since_failure",
    "invoice_age_days",
    "prev_recovery_actions",
    "prev_recovery_outcomes"
]


categorical_features = [
    "event_type",
    "failure_category",
    "payment_method",
    "gateway_provider",
    "merchant_category",
    "user_device"
]


feature_cols = numeric_features + categorical_features

X = df[feature_cols].copy()


# =========================================================
# 4. CHECK REQUIRED COLUMNS
# =========================================================

missing_cols = [
    col for col in feature_cols + [target_col]
    if col not in df.columns
]

if missing_cols:
    raise ValueError(
        f"Missing columns in events.csv: {missing_cols}"
    )


# =========================================================
# 5. DATASET INFORMATION
# =========================================================

print("\nTarget Distribution:")
print(y.value_counts())

print("\nTarget Percentage:")
print(y.value_counts(normalize=True).round(4))

print("\nMissing Values:")
print(X.isnull().sum())


# =========================================================
# 6. TRAIN / TEST SPLIT
# =========================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\nTraining Samples:", len(X_train))
print("Testing Samples :", len(X_test))


# =========================================================
# 7. PREPROCESSING
# =========================================================

numeric_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(strategy="median")
        )
    ]
)


categorical_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(strategy="most_frequent")
        ),
        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False
            )
        )
    ]
)


preprocessor = ColumnTransformer(
    transformers=[
        (
            "numeric",
            numeric_pipeline,
            numeric_features
        ),
        (
            "categorical",
            categorical_pipeline,
            categorical_features
        )
    ]
)


# =========================================================
# 8. XGBOOST MODEL
# =========================================================

model = XGBClassifier(
    n_estimators=250,
    max_depth=4,
    learning_rate=0.04,
    min_child_weight=3,
    subsample=0.85,
    colsample_bytree=0.85,
    objective="binary:logistic",
    eval_metric="logloss",
    random_state=42,
    n_jobs=-1
)


# =========================================================
# 9. COMPLETE ML PIPELINE
# =========================================================

pipeline = Pipeline(
    steps=[
        (
            "preprocessor",
            preprocessor
        ),
        (
            "model",
            model
        )
    ]
)


# =========================================================
# 10. TRAIN
# =========================================================

print("\nTraining XGBoost model...")

pipeline.fit(
    X_train,
    y_train
)

print("Training completed.")


# =========================================================
# 11. PREDICTION
# =========================================================

y_pred = pipeline.predict(X_test)

y_pred_proba = pipeline.predict_proba(X_test)[:, 1]


# =========================================================
# 12. EVALUATION
# =========================================================

roc_auc = roc_auc_score(
    y_test,
    y_pred_proba
)

accuracy = accuracy_score(
    y_test,
    y_pred
)


print("\n" + "=" * 60)
print("HELD-OUT TEST EVALUATION")
print("=" * 60)

print(f"ROC-AUC Score : {roc_auc:.4f}")
print(f"Accuracy Score: {accuracy:.4f}")
print("Threshold     : 0.50")


print("\nClassification Report:")

print(
    classification_report(
        y_test,
        y_pred,
        target_names=[
            "Unrecovered (0)",
            "Recovered (1)"
        ]
    )
)


# =========================================================
# 13. CONFUSION MATRIX
# =========================================================

print("\nConfusion Matrix:")

print(
    confusion_matrix(
        y_test,
        y_pred
    )
)


# =========================================================
# 14. FEATURE IMPORTANCE
# =========================================================

trained_model = pipeline.named_steps["model"]

trained_preprocessor = pipeline.named_steps["preprocessor"]


feature_names = trained_preprocessor.get_feature_names_out()


importance = pd.DataFrame({
    "feature": feature_names,
    "importance": trained_model.feature_importances_
})


importance = importance.sort_values(
    by="importance",
    ascending=False
)


print("\nTop 20 Feature Importance:")

print(
    importance.head(20).to_string(index=False)
)


# =========================================================
# 15. SAVE COMPLETE PIPELINE
# =========================================================

joblib.dump(
    pipeline,
    "xgb_recovery_pipeline.joblib"
)


# Save original feature structure
joblib.dump(
    feature_cols,
    "feature_names.joblib"
)


print("\n" + "=" * 60)
print("MODEL SAVED SUCCESSFULLY")
print("=" * 60)

print("xgb_recovery_pipeline.joblib")
print("feature_names.joblib")

print("\nTraining pipeline completed successfully.")