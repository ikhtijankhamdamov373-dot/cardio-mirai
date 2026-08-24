"""Request/response schemas for the Evidence-Based Cardiovascular Risk endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceBasedRiskRequest(BaseModel):
    age_years: float = Field(..., ge=1, le=120)
    sex: str = Field(..., description="'female' or 'male'")
    total_chol_mgdl: float = Field(..., gt=0)
    hdl_chol_mgdl: float = Field(..., gt=0)
    sbp_mmhg: float = Field(..., gt=0)
    on_antihypertensive_therapy: bool = False
    on_statin_therapy: bool = False
    has_diabetes: bool = False
    current_smoker: bool = False
    egfr_ml_min_1_73m2: float = Field(..., gt=0)


class EvidenceBasedRiskResponse(BaseModel):
    chronological_age_years: float
    risk_10yr_percent: float | None
    risk_10yr_unavailable_reason: str | None
    risk_30yr_percent: float | None
    risk_30yr_unavailable_reason: str | None
    risk_age_years: float | None
    risk_age_boundary_label: str | None
    risk_age_gap_years: float | None
    reference_framework: str
    disclaimer: str
    affiliation_note: str
