"""PREVENT base-model equations -- Total CVD outcome, 10-year and 30-year.

Independently implemented in Python from the verified coefficient tables in
_prevent_coefficients.py and the variable-transformation logic confirmed
against PooledCohort's reference implementation (age centering at 55,
non-HDL-C centering at 3.5 mmol/L, HDL-C centering at 1.3 mmol/L, piecewise
SBP terms split at 110 mmHg, etc.). This module deliberately does NOT accept
a BMI parameter: the Total CVD outcome's BMI coefficients are exactly zero
in the official table (BMI only enters the HF-specific equation), so BMI is
excluded from the function signature entirely rather than accepted and
silently multiplied by zero -- removing any possibility of a future
accidental cross-wire with HF-specific terms.

Final risk formula: risk = exp(linear_predictor) / (1 + exp(linear_predictor)),
confirmed from PooledCohort's own source code as the AHA-published simplified
logistic-style translation of the underlying age-scale Cox model (the
original paper describes this simplification explicitly, reporting R^2>=0.99
against the full model).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._prevent_coefficients import BASE_10YR_CVD_COEFS, BASE_30YR_CVD_COEFS
from .units import non_hdl_mmoll, hdl_mgdl_to_mmoll

Sex = str  # "female" | "male"


@dataclass
class PreventInputs:
    age_years: float
    sex: Sex  # "female" or "male"
    total_chol_mgdl: float
    hdl_chol_mgdl: float
    sbp_mmhg: float
    on_antihypertensive_therapy: bool
    on_statin_therapy: bool
    has_diabetes: bool
    current_smoker: bool
    egfr_ml_min_1_73m2: float

    def __post_init__(self) -> None:
        if self.sex not in ("female", "male"):
            raise ValueError(f"sex must be 'female' or 'male', got {self.sex!r}")
        if self.total_chol_mgdl <= self.hdl_chol_mgdl:
            raise ValueError(
                f"total cholesterol ({self.total_chol_mgdl} mg/dL) must exceed "
                f"HDL cholesterol ({self.hdl_chol_mgdl} mg/dL) -- non-HDL-C cannot be <= 0"
            )
        if self.egfr_ml_min_1_73m2 <= 0:
            raise ValueError(f"eGFR must be positive, got {self.egfr_ml_min_1_73m2}")
        if self.sbp_mmhg <= 0:
            raise ValueError(f"systolic blood pressure must be positive, got {self.sbp_mmhg}")


def _linear_predictor(inputs: PreventInputs, coefs: dict[str, dict[str, float]]) -> float:
    """Build the PREVENT linear predictor from a verified coefficient table.

    Every transform here corresponds 1:1 to a named coefficient in the table
    -- kept explicit (not a generic dot-product over a feature vector) so a
    reviewer can check each line against the published variable definitions
    directly.
    """
    c = {name: table[inputs.sex] for name, table in coefs.items()}

    age_per_10 = (inputs.age_years - 55.0) / 10.0
    non_hdl = non_hdl_mmoll(inputs.total_chol_mgdl, inputs.hdl_chol_mgdl) - 3.5
    hdl = (hdl_mgdl_to_mmoll(inputs.hdl_chol_mgdl) - 1.3) / 0.3
    sbp_low = (min(inputs.sbp_mmhg, 110.0) - 110.0) / 20.0
    sbp_high = (max(inputs.sbp_mmhg, 110.0) - 130.0) / 20.0
    diabetes = 1.0 if inputs.has_diabetes else 0.0
    smoking = 1.0 if inputs.current_smoker else 0.0
    egfr_low = (min(inputs.egfr_ml_min_1_73m2, 60.0) - 60.0) / -15.0
    egfr_high = (max(inputs.egfr_ml_min_1_73m2, 60.0) - 90.0) / -15.0
    bp_meds = 1.0 if inputs.on_antihypertensive_therapy else 0.0
    statin = 1.0 if inputs.on_statin_therapy else 0.0
    treated_sbp_high = sbp_high * bp_meds
    treated_non_hdl = non_hdl * statin

    total = (
        c["coef_age_per_10_years"] * age_per_10
        + c["coef_age_per_10_years_squared"] * age_per_10 ** 2
        + c["coef_non_hdl_c_per_1_mmol_l"] * non_hdl
        + c["coef_hdl_c_per_0.3_mmol_l"] * hdl
        + c["coef_sbp_lt110_per_20_mmhg"] * sbp_low
        + c["coef_sbp_gteq110_per_20_mmhg"] * sbp_high
        + c["coef_diabetes"] * diabetes
        + c["coef_current_smoking"] * smoking
        + c["coef_egfr_lt60_per_15_ml"] * egfr_low
        + c["coef_egfr_gteq60_per_15_ml"] * egfr_high
        + c["coef_anti_hypertensive_use"] * bp_meds
        + c["coef_statin_use"] * statin
        + c["coef_treated_sbp_gteq110_mm_hg_per_20_mm_hg"] * treated_sbp_high
        + c["coef_treated_non_hdl_c"] * treated_non_hdl
        + c["coef_age_per_10yr_x_non_hdl_c_per_1_mmol_l"] * age_per_10 * non_hdl
        + c["coef_age_per_10yr_x_hdl_c_per_0.3_mml_l"] * age_per_10 * hdl
        + c["coef_age_per_10yr_x_sbp_gteq110_mm_hg_per_20_mmhg"] * age_per_10 * sbp_high
        + c["coef_age_per_10yr_x_diabetes"] * age_per_10 * diabetes
        + c["coef_age_per_10yr_x_current_smoking"] * age_per_10 * smoking
        + c["coef_age_per_10yr_x_egfr_lt60_per_15_ml"] * age_per_10 * egfr_low
        + c["const"]
    )
    return total


def _logistic(linear_predictor: float) -> float:
    # Numerically stable logistic transform.
    if linear_predictor >= 0:
        z = math.exp(-linear_predictor)
        return 1.0 / (1.0 + z)
    z = math.exp(linear_predictor)
    return z / (1.0 + z)


def total_cvd_risk_10yr(inputs: PreventInputs) -> float:
    """10-year predicted risk of Total CVD (ASCVD + heart failure), as a probability in [0,1]."""
    lp = _linear_predictor(inputs, BASE_10YR_CVD_COEFS)
    return _logistic(lp)


def total_cvd_risk_30yr(inputs: PreventInputs) -> float:
    """30-year predicted risk of Total CVD, as a probability in [0,1].

    Caller is responsible for age-range gating (officially supported for
    ages 30-59 only) -- this function computes the mathematical result
    unconditionally; see calculator.py for the supported-range enforcement.
    """
    lp = _linear_predictor(inputs, BASE_30YR_CVD_COEFS)
    return _logistic(lp)
