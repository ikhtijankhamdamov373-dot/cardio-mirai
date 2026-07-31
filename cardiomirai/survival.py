"""Future AF prediction architecture.

This module is intentionally architecture-only. Longitudinal prediction should
be implemented after follow-up cohorts are available.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class LongitudinalPatientProfile:
    ecg_features: Dict[str, float]
    clinical_variables: Dict[str, float | str]
    echo_variables: Dict[str, float]
    laboratory_variables: Dict[str, float]
    follow_up_years: Optional[float] = None


@dataclass(frozen=True)
class FutureAFRisk:
    risk_1_year: float
    risk_3_year: float
    risk_5_year: float
    model_name: str
    model_version: str


class SurvivalRiskModel:
    """Interface for Cox, XGBoost survival, or DeepSurv models."""

    def predict(self, profile: LongitudinalPatientProfile) -> FutureAFRisk:
        raise NotImplementedError("Implement only after longitudinal outcomes are available.")

