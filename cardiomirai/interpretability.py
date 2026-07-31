"""Interpretability contracts for patient-level explanations."""

from dataclasses import dataclass
from typing import Sequence

from .models import FeatureBundle


@dataclass(frozen=True)
class FeatureAttribution:
    name: str
    value: float | str
    contribution: float
    direction: str


class SHAPExplainer:
    """SHAP explanation interface for tabular ECG feature models."""

    def explain(self, features: FeatureBundle) -> Sequence[FeatureAttribution]:
        raise NotImplementedError("Connect SHAP explainer for trained Gradient Boosting or XGBoost model.")

