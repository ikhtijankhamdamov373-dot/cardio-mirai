"""
Cardio MIRAI ACS API — additive router, mounted onto the existing FastAPI
app without modifying any existing endpoint.

RESEARCH PROTOTYPE. NOT A MEDICAL DEVICE. NOT FOR CLINICAL USE.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .core import (
    ACS_NOT_EXCLUDED_STATEMENT,
    CareSetting,
    DECISION_SUPPORT_DISCLAIMER,
    EcgQuality,
    LeadMeasurement,
    MimicFlags,
    NSTEMI_CANNOT_BE_DETERMINED_STATEMENT,
    PatientContext,
    QUALITY_INSUFFICIENT_STATEMENT,
    STEMI_CRITERIA_MET_HEADLINE,
    STEMI_CRITERIA_NOT_MET_HEADLINE,
    Urgency,
    evaluate_fmc_to_ecg_timing,
    evaluate_serial_ecg_indication,
    evaluate_stemi_criteria,
    hs_ctn_repeat_window,
)

router = APIRouter(prefix="/api/acs", tags=["acs-research-prototype"])


class LeadInput(BaseModel):
    lead: str
    st_elevation_mm: float
    reciprocal_depression_mm: Optional[float] = None


class MimicInput(BaseModel):
    lvh: bool = False
    lbbb: bool = False
    rbbb: bool = False
    paced_rhythm: bool = False
    pericarditis: bool = False
    brugada: bool = False
    takotsubo: bool = False
    early_repolarization: bool = False


class PatientInput(BaseModel):
    age: Optional[int] = Field(default=None, ge=0, le=130)
    sex: Optional[str] = None
    symptomatic: bool = False
    high_clinical_suspicion: bool = False
    ongoing_chest_pain: bool = False


class EcgQualityInput(BaseModel):
    leads_detected: int = 0
    calibration_available: bool = False
    signal_suitable: bool = False
    lead_labels_identified: bool = False


class StemiAssessRequest(BaseModel):
    leads: list[LeadInput]
    patient: PatientInput
    mimics: MimicInput = MimicInput()
    quality: EcgQualityInput


@router.get("/health")
def acs_health() -> dict:
    return {"ok": True, "module": "acs-research-prototype"}


@router.post("/assess")
def assess_stemi(request: StemiAssessRequest) -> dict:
    """
    Research-prototype deterministic STEMI-criteria assessment.

    NOT A DIAGNOSIS. Implements ACS-CORE-001/002/003 only. Never returns
    "STEMI diagnosed", "NSTEMI diagnosed", "No ACS", or "ACS excluded".
    """
    quality = EcgQuality(
        leads_detected=request.quality.leads_detected,
        calibration_available=request.quality.calibration_available,
        signal_suitable=request.quality.signal_suitable,
        lead_labels_identified=request.quality.lead_labels_identified,
    )

    if not quality.is_acceptable():
        return {
            "quality_gate_passed": False,
            "quality_failure_reasons": quality.failure_reasons(),
            "headline": QUALITY_INSUFFICIENT_STATEMENT,
            "urgency": Urgency.INDETERMINATE.value,
            "disclaimer": DECISION_SUPPORT_DISCLAIMER,
        }

    patient = PatientContext(
        age=request.patient.age,
        sex=request.patient.sex,
        symptomatic=request.patient.symptomatic,
        high_clinical_suspicion=request.patient.high_clinical_suspicion,
        ongoing_chest_pain=request.patient.ongoing_chest_pain,
    )
    mimics = MimicFlags(**request.mimics.model_dump())
    leads = [
        LeadMeasurement(
            lead=l.lead,
            st_elevation_mm=l.st_elevation_mm,
            reciprocal_depression_mm=l.reciprocal_depression_mm,
        )
        for l in request.leads
    ]

    try:
        result = evaluate_stemi_criteria(leads, patient, mimics)
    except ValueError as exc:
        return {"quality_gate_passed": True, "error": str(exc)}

    if result.criteria_met and not result.requires_clinical_correlation:
        urgency = Urgency.EMERGENCY
        headline = STEMI_CRITERIA_MET_HEADLINE
    elif result.criteria_met and result.requires_clinical_correlation:
        urgency = Urgency.HIGH
        headline = STEMI_CRITERIA_MET_HEADLINE + " — requires clinical correlation (possible mimic)"
    else:
        urgency = Urgency.HIGH if patient.high_clinical_suspicion else Urgency.ROUTINE
        headline = STEMI_CRITERIA_NOT_MET_HEADLINE

    return {
        "quality_gate_passed": True,
        "criteria_met": result.criteria_met,
        "requires_clinical_correlation": result.requires_clinical_correlation,
        "mimic_present": result.mimic_present,
        "mimic_names": result.mimic_names,
        "contiguous_leads": sorted(result.contiguous_group) if result.contiguous_group else [],
        "contiguous_group_name": result.contiguous_group_name,
        "triggering_rule_id": result.triggering_rule_id,
        "contributing_measurements": [
            {"lead": m.lead, "st_elevation_mm": m.st_elevation_mm}
            for m in result.contributing_leads
        ],
        "reciprocal_changes": [
            {"lead": m.lead, "reciprocal_depression_mm": m.reciprocal_depression_mm}
            for m in result.reciprocal_changes
        ],
        "thresholds_applied": result.thresholds_applied,
        "urgency": urgency.value,
        "headline": headline,
        "acs_not_excluded_statement": (
            None if result.criteria_met else ACS_NOT_EXCLUDED_STATEMENT
        ),
        "nstemi_note": NSTEMI_CANNOT_BE_DETERMINED_STATEMENT,
        "source": (
            "2025 ACC/AHA ACS Guideline (STEMI/NSTE-ACS management) / "
            "2023 ESC ACS Guideline (diagnosis and ECG guidance) / "
            "Fifth Universal Definition of Myocardial Infarction (2026) "
            "(definition and classification)"
        ),
        "disclaimer": DECISION_SUPPORT_DISCLAIMER,
    }


class FmcTimingRequest(BaseModel):
    fmc_time: datetime
    ecg_time: datetime


@router.post("/timing/fmc-to-ecg")
def timing_fmc_to_ecg(request: FmcTimingRequest) -> dict:
    """ACS-CORE-005."""
    result = evaluate_fmc_to_ecg_timing(request.fmc_time, request.ecg_time)
    return {
        "compliant": result.compliant,
        "elapsed_minutes": round(result.elapsed_minutes, 2),
        "threshold_minutes": result.threshold_minutes,
        "source": result.source,
    }


class SerialEcgRequest(BaseModel):
    initial_ecg_diagnostic: bool
    high_clinical_suspicion: bool = False
    symptoms_persistent: bool = False
    condition_deteriorating: bool = False
    care_setting: str = "prehospital"


@router.post("/serial-ecg-indication")
def serial_ecg_indication(request: SerialEcgRequest) -> dict:
    """ACS-CORE-008."""
    setting = (
        CareSetting.PREHOSPITAL
        if request.care_setting == "prehospital"
        else CareSetting.IN_HOSPITAL
    )
    result = evaluate_serial_ecg_indication(
        initial_ecg_diagnostic=request.initial_ecg_diagnostic,
        high_clinical_suspicion=request.high_clinical_suspicion,
        symptoms_persistent=request.symptoms_persistent,
        condition_deteriorating=request.condition_deteriorating,
        care_setting=setting,
    )
    return {
        "indicated": result.indicated,
        "reasons": result.reasons,
        "care_setting": result.care_setting.value,
        "cor": result.cor,
        "loe": result.loe,
    }


class HsCtnWindowRequest(BaseModel):
    assay_type: str


@router.post("/hs-ctn-repeat-window")
def hs_ctn_window(request: HsCtnWindowRequest) -> dict:
    """Display-only helper, never a diagnostic trigger. ESC 0h/1h and 0h/2h
    algorithms (ACS-CORE-010) are intentionally not implemented here."""
    try:
        return hs_ctn_repeat_window(request.assay_type)
    except ValueError as exc:
        return {"error": str(exc)}
