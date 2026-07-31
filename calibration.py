"""Probability calibration interfaces."""

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class CalibrationReport:
    method: str
    brier_score: float
    calibration_curve: Sequence[tuple[float, float]]
    calibration_slope: float | None = None
    calibration_intercept: float | None = None


class ProbabilityCalibrator:
    """Isotonic or Platt scaling calibration wrapper."""

    def fit(self, probabilities: Sequence[float], labels: Sequence[int], method: str) -> CalibrationReport:
        raise NotImplementedError("Fit isotonic regression or Platt scaling.")

    def transform(self, probabilities: Sequence[float]) -> Sequence[float]:
        raise NotImplementedError("Apply fitted calibration model.")

