"""Isolated FastAPI router for Evidence-Based Cardiovascular Risk Age.

Deliberately self-contained: imports nothing from the ECG/AF/legacy-model
code, and vice versa -- nothing in cardiomirai/api.py's existing ECG
pipeline imports anything from this package. A failure here cannot
propagate into /api/analyze-wfdb, and a failure there cannot affect this.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .calculator import calculate_evidence_based_risk
from .prevent_equations import PreventInputs
from .schemas import EvidenceBasedRiskRequest, EvidenceBasedRiskResponse

router = APIRouter(prefix="/api/v1/heart-age", tags=["heart-age"])

DISCLAIMER = (
    "Risk Age is an evidence-based risk communication metric derived from the PREVENT "
    "equations. It is not a direct measurement of biological cardiac aging."
)
AFFILIATION_NOTE = "Cardio MIRAI is not affiliated with or endorsed by the American Heart Association."


@router.post("/calculate", response_model=EvidenceBasedRiskResponse)
def calculate(request: EvidenceBasedRiskRequest) -> EvidenceBasedRiskResponse:
    try:
        inputs = PreventInputs(
            age_years=request.age_years,
            sex=request.sex,
            total_chol_mgdl=request.total_chol_mgdl,
            hdl_chol_mgdl=request.hdl_chol_mgdl,
            sbp_mmhg=request.sbp_mmhg,
            on_antihypertensive_therapy=request.on_antihypertensive_therapy,
            on_statin_therapy=request.on_statin_therapy,
            has_diabetes=request.has_diabetes,
            current_smoker=request.current_smoker,
            egfr_ml_min_1_73m2=request.egfr_ml_min_1_73m2,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = calculate_evidence_based_risk(inputs)
    return EvidenceBasedRiskResponse(
        chronological_age_years=result.chronological_age_years,
        risk_10yr_percent=result.risk_10yr_percent,
        risk_10yr_unavailable_reason=result.risk_10yr_unavailable_reason,
        risk_30yr_percent=result.risk_30yr_percent,
        risk_30yr_unavailable_reason=result.risk_30yr_unavailable_reason,
        risk_age_years=result.risk_age_years,
        risk_age_boundary_label=result.risk_age_boundary_label,
        risk_age_gap_years=result.risk_age_gap_years,
        reference_framework=result.reference_framework,
        disclaimer=DISCLAIMER,
        affiliation_note=AFFILIATION_NOTE,
    )


@router.get("/metadata")
def metadata() -> dict:
    return {
        "model": "Evidence-Based Cardiovascular Risk Age",
        "reference_framework": "AHA PREVENT (base equations, Total CVD outcome)",
        "supported_age_range_10yr": [30, 79],
        "supported_age_range_30yr": [30, 59],
        "optional_equations_supported": False,
        "disclaimer": DISCLAIMER,
        "affiliation_note": AFFILIATION_NOTE,
        "ai_heart_age_status": "Research model under development. No AI Heart Age number is generated.",
    }
