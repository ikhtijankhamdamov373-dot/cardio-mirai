"""Train production PTB-XL atrial remodeling models for Cardio MIRAI.

This script trains real models from a real `features_table.csv`. It never
creates dummy artifacts. If the feature table or target column is missing, it
raises an error and saves nothing.

Example:

    py -3 scripts/train_ptbxl_production_models.py --features-table features_table.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


FEATURE_COLUMNS = [
    "age",
    "sex",
    "p_duration_ms",
    "p_amplitude_mv",
    "p_axis_deg",
    "pr_interval_ms",
    "qrs_duration_ms",
    "qtc_ms",
    "ptfv1_mv_ms",
]

TARGET_CANDIDATES = [
    "atrial_abnormality",
    "current_atrial_abnormality",
    "target",
    "label",
    "y",
]


def load_xgboost_classifier(random_state: int) -> Any | None:
    try:
        from xgboost import XGBClassifier
    except Exception:
        return None
    return XGBClassifier(
        n_estimators=400,
        max_depth=3,
        learning_rate=0.04,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="binary:logistic",
        eval_metric="auc",
        random_state=random_state,
        n_jobs=1,
    )


def resolve_target_column(frame: pd.DataFrame, requested: str | None) -> str:
    if requested:
        if requested not in frame.columns:
            raise ValueError(f"Requested target column not found: {requested}")
        return requested
    for candidate in TARGET_CANDIDATES:
        if candidate in frame.columns:
            return candidate
    raise ValueError(
        "Target column not found. Pass --target-column. Tried: "
        + ", ".join(TARGET_CANDIDATES)
    )


def validate_feature_table(frame: pd.DataFrame, target_column: str) -> None:
    missing = [column for column in FEATURE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required feature columns: {missing}")
    if target_column not in frame.columns:
        raise ValueError(f"Missing target column: {target_column}")
    values = set(frame[target_column].dropna().unique().tolist())
    if not values.issubset({0, 1, False, True}):
        raise ValueError(f"Target must be binary 0/1. Found values: {sorted(values)}")


def metrics(y_true: np.ndarray, probability: np.ndarray, threshold: float = 0.5) -> dict:
    prediction = (probability >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, prediction, labels=[0, 1]).ravel()
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    ppv = tp / (tp + fp) if (tp + fp) else 0.0
    npv = tn / (tn + fn) if (tn + fn) else 0.0
    return {
        "auc": float(roc_auc_score(y_true, probability)),
        "accuracy": float(accuracy_score(y_true, prediction)),
        "sensitivity": float(recall_score(y_true, prediction, zero_division=0)),
        "specificity": float(specificity),
        "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)),
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "ppv": float(ppv),
        "npv": float(npv),
        "brier_score": float(brier_score_loss(y_true, probability)),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }


def calibration_points(y_true: np.ndarray, probability: np.ndarray) -> list[dict]:
    prob_true, prob_pred = calibration_curve(y_true, probability, n_bins=10, strategy="uniform")
    return [
        {"predicted": float(pred), "observed": float(obs)}
        for pred, obs in zip(prob_pred, prob_true)
    ]


def assert_reload_identity(
    output_dir: Path,
    logistic_model: LogisticRegression,
    gradient_model: Any,
    scaler: Pipeline,
    x_test: pd.DataFrame,
) -> None:
    sample = x_test.head(min(10, len(x_test)))
    before_logistic = logistic_model.predict_proba(scaler.transform(sample))[:, 1]
    before_gradient = gradient_model.predict_proba(sample)[:, 1]

    loaded_logistic = joblib.load(output_dir / "atrial_logistic_model.pkl")
    loaded_gradient = joblib.load(output_dir / "atrial_gradient_boosting_model.pkl")
    loaded_scaler = joblib.load(output_dir / "feature_scaler.pkl")

    after_logistic = loaded_logistic.predict_proba(loaded_scaler.transform(sample))[:, 1]
    after_gradient = loaded_gradient.predict_proba(sample)[:, 1]

    if not np.allclose(before_logistic, after_logistic, rtol=0, atol=1e-12):
        raise RuntimeError("Reload verification failed for logistic model.")
    if not np.allclose(before_gradient, after_gradient, rtol=0, atol=1e-12):
        raise RuntimeError("Reload verification failed for gradient boosting model.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features-table", type=Path, default=Path("features_table.csv"))
    parser.add_argument("--target-column", type=str, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("models"))
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    if not args.features_table.exists():
        raise SystemExit(f"features_table.csv not found: {args.features_table}")

    frame = pd.read_csv(args.features_table)
    target_column = resolve_target_column(frame, args.target_column)
    validate_feature_table(frame, target_column)

    x = frame[FEATURE_COLUMNS].copy()
    y = frame[target_column].astype(int).copy()

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=args.test_size,
        stratify=y,
        random_state=args.random_state,
    )

    scaler = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    logistic_model = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=args.random_state,
    )
    logistic_model.fit(x_train_scaled, y_train)

    gradient_model = load_xgboost_classifier(args.random_state)
    gradient_model_name = "XGBoost"
    if gradient_model is None:
        gradient_model = HistGradientBoostingClassifier(
            max_iter=300,
            learning_rate=0.04,
            l2_regularization=0.01,
            random_state=args.random_state,
        )
        gradient_model_name = "HistGradientBoostingClassifier"
    gradient_model.fit(x_train, y_train)

    logistic_probability = logistic_model.predict_proba(x_test_scaled)[:, 1]
    gradient_probability = gradient_model.predict_proba(x_test)[:, 1]
    logistic_metrics = metrics(y_test.to_numpy(), logistic_probability)
    gradient_metrics = metrics(y_test.to_numpy(), gradient_probability)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(logistic_model, args.output_dir / "atrial_logistic_model.pkl")
    joblib.dump(gradient_model, args.output_dir / "atrial_gradient_boosting_model.pkl")
    joblib.dump(scaler, args.output_dir / "feature_scaler.pkl")
    with (args.output_dir / "feature_columns.json").open("w", encoding="utf-8") as handle:
        json.dump(FEATURE_COLUMNS, handle, indent=2)

    metadata = {
        "dataset": "PTB-XL",
        "records_used": int(len(frame)),
        "model_target": "current atrial abnormality",
        "target_column": target_column,
        "warning": "not future AF prediction",
        "random_state": args.random_state,
        "test_size": args.test_size,
        "feature_columns": FEATURE_COLUMNS,
        "missing_value_strategy": "median imputation fitted on training split",
        "normalization": "StandardScaler fitted on training split for logistic regression only",
        "gradient_model_type": gradient_model_name,
        "logistic_auc": logistic_metrics["auc"],
        "gradient_boosting_auc": gradient_metrics["auc"],
        "logistic_metrics": logistic_metrics,
        "gradient_boosting_metrics": gradient_metrics,
        "calibration": {
            "logistic": calibration_points(y_test.to_numpy(), logistic_probability),
            "gradient_boosting": calibration_points(y_test.to_numpy(), gradient_probability),
        },
        "missing_value_defaults": {
            "age": 0.0,
            "sex": 0.0,
        },
    }
    with (args.output_dir / "model_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    assert_reload_identity(args.output_dir, logistic_model, gradient_model, scaler, x_test)

    print("Logistic metrics")
    print(json.dumps(logistic_metrics, indent=2))
    print("Gradient boosting metrics")
    print(json.dumps(gradient_metrics, indent=2))
    print("Reload verification passed.")


if __name__ == "__main__":
    main()

