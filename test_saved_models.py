"""Smoke-test saved Cardio MIRAI PTB-XL model artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features-table", type=Path, default=Path("features_table.csv"))
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--target-column", type=str, default=None)
    parser.add_argument("--n", type=int, default=5)
    args = parser.parse_args()

    if not args.features_table.exists():
        raise SystemExit(f"features_table.csv not found: {args.features_table}")

    with (args.models_dir / "feature_columns.json").open("r", encoding="utf-8") as handle:
        feature_columns = json.load(handle)
    with (args.models_dir / "model_metadata.json").open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)

    target_column = args.target_column or metadata.get("target_column")
    if not target_column:
        raise SystemExit("Target column not provided and not found in model_metadata.json.")

    frame = pd.read_csv(args.features_table)
    missing = [column for column in feature_columns + [target_column] if column not in frame.columns]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    model = joblib.load(args.models_dir / "atrial_gradient_boosting_model.pkl")
    scaler = joblib.load(args.models_dir / "feature_scaler.pkl")
    logistic = joblib.load(args.models_dir / "atrial_logistic_model.pkl")

    sample = frame[feature_columns + [target_column]].head(args.n)
    gradient_probability = model.predict_proba(sample[feature_columns])[:, 1]
    logistic_probability = logistic.predict_proba(scaler.transform(sample[feature_columns]))[:, 1]
    gradient_class = (gradient_probability >= 0.5).astype(int)

    for idx, row in sample.reset_index(drop=True).iterrows():
        print(
            {
                "row": int(idx),
                "gradient_probability": float(gradient_probability[idx]),
                "logistic_probability": float(logistic_probability[idx]),
                "predicted_class": int(gradient_class[idx]),
                "true_class": int(row[target_column]),
            }
        )


if __name__ == "__main__":
    main()

