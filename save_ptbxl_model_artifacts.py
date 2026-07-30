"""Save trained PTB-XL atrial remodeling model artifacts.

Use this helper at the end of the PTB-XL training notebook/script after the
models and scaler are trained.

Expected variables in your training code:

- logistic_model
- gradient_boosting_model
- scaler

Then call:

    save_artifacts(logistic_model, gradient_boosting_model, scaler)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib


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


def save_artifacts(
    logistic_model: Any,
    gradient_boosting_model: Any,
    scaler: Any,
    output_dir: str | Path = "models",
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    joblib.dump(logistic_model, output / "atrial_logistic_model.pkl")
    joblib.dump(gradient_boosting_model, output / "atrial_gradient_boosting_model.pkl")
    joblib.dump(scaler, output / "feature_scaler.pkl")

    with (output / "feature_columns.json").open("w", encoding="utf-8") as handle:
        json.dump(FEATURE_COLUMNS, handle, indent=2)

    metadata = {
        "dataset": "PTB-XL",
        "records_used": 21799,
        "model_target": "current atrial abnormality",
        "logistic_auc": 0.851,
        "gradient_boosting_auc": 0.907,
        "warning": "not future AF prediction",
        "missing_value_defaults": {
            "age": 0.0,
            "sex": 0.0
        }
    }
    with (output / "model_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)


if __name__ == "__main__":
    raise SystemExit(
        "Import save_artifacts() from your training script after fitting the models. "
        "This helper does not train models by itself."
    )

