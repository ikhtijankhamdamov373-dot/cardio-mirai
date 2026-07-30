"""Validation utilities for Cardio MIRAI ECG models.

This script is intentionally model-agnostic. It expects a CSV with at least:

- y_true: binary label
- y_score: predicted probability or score
- patient_id: optional, used to warn about patient-level grouping
- dataset: optional, used for per-dataset reporting

Example:

    py -3 scripts/validate_ecg_model.py predictions.csv --out validation_report
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    auc,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_curve,
)


def metrics_for_frame(frame: pd.DataFrame, threshold: float = 0.5) -> dict:
    y_true = frame["y_true"].astype(int).to_numpy()
    y_score = frame["y_score"].astype(float).to_numpy()
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr, tpr, _ = roc_curve(y_true, y_score)
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    ppv = tp / (tp + fp) if (tp + fp) else 0.0
    npv = tn / (tn + fn) if (tn + fn) else 0.0
    return {
        "n": len(frame),
        "auc": auc(fpr, tpr),
        "sensitivity": recall_score(y_true, y_pred, zero_division=0),
        "specificity": specificity,
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "ppv": ppv,
        "npv": npv,
        "brier_score": brier_score_loss(y_true, y_score),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def write_calibration_plot(frame: pd.DataFrame, output_path: Path) -> None:
    y_true = frame["y_true"].astype(int).to_numpy()
    y_score = frame["y_score"].astype(float).to_numpy()
    prob_true, prob_pred = calibration_curve(y_true, y_score, n_bins=10, strategy="uniform")
    plt.figure(figsize=(5, 5))
    plt.plot([0, 1], [0, 1], "--", color="#999999", label="Ideal")
    plt.plot(prob_pred, prob_true, marker="o", color="#175ca8", label="Model")
    plt.xlabel("Predicted probability")
    plt.ylabel("Observed frequency")
    plt.title("Calibration curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions_csv", type=Path)
    parser.add_argument("--out", type=Path, default=Path("validation_report"))
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()

    frame = pd.read_csv(args.predictions_csv)
    missing = {"y_true", "y_score"} - set(frame.columns)
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")

    args.out.mkdir(parents=True, exist_ok=True)

    reports = []
    reports.append({"dataset": "overall", **metrics_for_frame(frame, args.threshold)})
    if "dataset" in frame.columns:
        for dataset, subset in frame.groupby("dataset"):
            if subset["y_true"].nunique() < 2:
                continue
            reports.append({"dataset": dataset, **metrics_for_frame(subset, args.threshold)})

    report = pd.DataFrame(reports)
    report.to_csv(args.out / "metrics.csv", index=False)
    write_calibration_plot(frame, args.out / "calibration_curve.png")

    if "patient_id" not in frame.columns:
        print("Warning: no patient_id column found. Prefer patient-level splits for publication validation.")
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()

