"""Evidence-Based Cardiovascular Risk calculator -- orchestrates the base
PREVENT equations and Risk Age, enforcing the officially supported age
ranges (which differ between the 10-year and 30-year models -- do not
apply one range to both, per explicit correction).
"""

from __future__ import annotations

from dataclasses import dataclass

from .prevent_equations import PreventInputs, total_cvd_risk_10yr, total_cvd_risk_30yr
from .risk_age import compute_risk_age

# Officially supported age ranges (NOT the same for both horizons):
AGE_10YR_MIN, AGE_10YR_MAX = 30, 79
AGE_30YR_MIN, AGE_30YR_MAX = 30, 59


@dataclass
class EvidenceBasedRiskResult:
    chronological_age_years: float
    risk_10yr_percent: float | None
    risk_10yr_unavailable_reason: str | None
    risk_30yr_percent: float | None
    risk_30yr_unavailable_reason: str | None
    risk_age_years: float | None
    risk_age_boundary_label: str | None
    risk_age_gap_years: float | None
    reference_framework: str = "AHA PREVENT (base equations, Total CVD outcome)"


def calculate_evidence_based_risk(inputs: PreventInputs) -> EvidenceBasedRiskResult:
    age = inputs.age_years

    # 10-year: officially supported 30-79.
    if AGE_10YR_MIN <= age <= AGE_10YR_MAX:
        risk_10yr = total_cvd_risk_10yr(inputs)
        risk_10yr_pct = round(risk_10yr * 100.0, 1)
        risk_10yr_reason = None
    else:
        risk_10yr = None
        risk_10yr_pct = None
        risk_10yr_reason = f"10-year PREVENT risk is only supported for ages {AGE_10YR_MIN}-{AGE_10YR_MAX}."

    # 30-year: officially supported 30-59 ONLY -- distinct, narrower range.
    if AGE_30YR_MIN <= age <= AGE_30YR_MAX:
        risk_30yr = total_cvd_risk_30yr(inputs)
        risk_30yr_pct = round(risk_30yr * 100.0, 1)
        risk_30yr_reason = None
    else:
        risk_30yr_pct = None
        risk_30yr_reason = f"30-Year CVD Risk: Not available for this age range (supported: {AGE_30YR_MIN}-{AGE_30YR_MAX})."

    # Risk Age is derived from the 10-year base model, so it shares that
    # model's applicability -- if 10-year risk itself isn't available,
    # Risk Age can't be either.
    risk_age_years = None
    risk_age_boundary = None
    risk_age_gap = None
    if risk_10yr is not None:
        ra = compute_risk_age(inputs.sex, risk_10yr)
        risk_age_years = ra.risk_age_years
        risk_age_boundary = ra.boundary_label
        if risk_age_years is not None:
            risk_age_gap = round(risk_age_years - age, 1)

    return EvidenceBasedRiskResult(
        chronological_age_years=age,
        risk_10yr_percent=risk_10yr_pct,
        risk_10yr_unavailable_reason=risk_10yr_reason,
        risk_30yr_percent=risk_30yr_pct,
        risk_30yr_unavailable_reason=risk_30yr_reason,
        risk_age_years=risk_age_years,
        risk_age_boundary_label=risk_age_boundary,
        risk_age_gap_years=risk_age_gap,
    )
