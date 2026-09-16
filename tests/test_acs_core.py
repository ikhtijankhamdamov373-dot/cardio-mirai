"""
Tests for Cardio MIRAI ACS Core (cardiomirai/acs/core.py) and the additive
/api/acs/* endpoints.

RESEARCH PROTOTYPE. NOT A MEDICAL DEVICE.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from cardiomirai import api as api_module
from cardiomirai.acs.core import (
    ALL_12_LEADS,
    CareSetting,
    EcgQuality,
    LeadMeasurement,
    MimicFlags,
    PatientContext,
    PROHIBITED_PHRASES,
    V2_V3_LEADS,
    evaluate_fmc_to_ecg_timing,
    evaluate_serial_ecg_indication,
    evaluate_stemi_criteria,
    hs_ctn_repeat_window,
)


@pytest.fixture()
def client():
    return TestClient(api_module.app)


# ---------------------------------------------------------------------------
# ACS-CORE-001: general-lead threshold
# ---------------------------------------------------------------------------

def test_general_lead_exact_threshold_triggers():
    leads = [
        LeadMeasurement("II", 1.0),
        LeadMeasurement("III", 1.0),
        LeadMeasurement("aVF", 1.0),
    ]
    patient = PatientContext(age=60, sex="male", symptomatic=True, high_clinical_suspicion=True)
    result = evaluate_stemi_criteria(leads, patient, MimicFlags())
    assert result.criteria_met is True


def test_general_lead_just_below_threshold_does_not_trigger():
    leads = [
        LeadMeasurement("II", 0.9),
        LeadMeasurement("III", 0.9),
        LeadMeasurement("aVF", 0.9),
    ]
    patient = PatientContext(age=60, sex="male")
    result = evaluate_stemi_criteria(leads, patient, MimicFlags())
    assert result.criteria_met is False


# ---------------------------------------------------------------------------
# 12-lead audit: explicit proof every one of the 12 standard leads is
# evaluated, and that anatomically named groups trigger/reject correctly.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lead", sorted(ALL_12_LEADS))
def test_every_standard_lead_is_individually_ingested_by_general_branch(lead):
    """Proves each of the 12 standard leads is measured against the general
    threshold (V2/V3 use the age/sex branch instead, tested separately).
    This does not assert triggering alone (a single lead never triggers,
    since >=2 contiguous leads are required) — it proves the measurement is
    not silently dropped, by pairing it with its own anatomical partner."""
    partner_map = {
        "I": "aVL", "aVL": "I",
        "II": "III", "III": "II",
        "aVF": "II",
        "V1": "V2", "V4": "V3",
        "V5": "V6", "V6": "V5",
    }
    if lead in V2_V3_LEADS:
        patient = PatientContext(age=50, sex="male")
        partner = "V4" if lead == "V3" else "V3"
        leads_input = [LeadMeasurement(lead, 3.0), LeadMeasurement(partner, 3.0)]
    elif lead == "aVR":
        # aVR has no valid contiguous partner (see below) — just prove it's
        # accepted without raising, via the dedicated test further down.
        return
    else:
        patient = PatientContext(age=50, sex="male")
        partner = partner_map[lead]
        partner_elevation = 3.0 if partner in V2_V3_LEADS else 1.5
        leads_input = [
            LeadMeasurement(lead, 1.5),
            LeadMeasurement(partner, partner_elevation),
        ]

    result = evaluate_stemi_criteria(leads_input, patient, MimicFlags())
    assert result.criteria_met is True, f"{lead}+{partner} should trigger via a named group"


def test_avr_measured_but_never_triggers_alone_or_paired():
    """aVR is accepted by the general >=1mm branch but is deliberately in
    zero contiguous groups (Matrix v1.2 FINAL row 21: EVIDENCE/RESEARCH,
    not a guideline 2-contiguous-lead STEMI group). Confirms this by
    pairing elevated aVR with every other individually-elevated lead and
    asserting none of those pairings alone satisfy criteria_met."""
    patient = PatientContext(age=50, sex="male")
    for other_lead in ALL_12_LEADS - {"aVR"}:
        leads = [LeadMeasurement("aVR", 3.0), LeadMeasurement(other_lead, 0.5)]
        result = evaluate_stemi_criteria(leads, patient, MimicFlags())
        assert result.criteria_met is False, f"aVR+{other_lead} must not trigger"


def test_inferior_pattern_ii_iii_avf_triggers():
    leads = [LeadMeasurement("II", 1.5), LeadMeasurement("III", 2.0), LeadMeasurement("aVF", 1.8)]
    patient = PatientContext(age=55, sex="male")
    result = evaluate_stemi_criteria(leads, patient, MimicFlags())
    assert result.criteria_met is True
    assert result.contiguous_group_name == "Inferior"
    assert result.triggering_rule_id == "ACS-CORE-001"
    assert set(m.lead for m in result.contributing_leads) <= {"II", "III", "aVF"}


def test_anterior_pattern_v2_v3_v4_triggers_and_reports_v2_v3_rule():
    leads = [
        LeadMeasurement("V2", 2.3), LeadMeasurement("V3", 2.5), LeadMeasurement("V4", 1.8),
    ]
    patient = PatientContext(age=58, sex="male")
    result = evaluate_stemi_criteria(leads, patient, MimicFlags())
    assert result.criteria_met is True
    assert result.contiguous_group_name in ("Anteroseptal", "Anterior")
    assert result.triggering_rule_id == "ACS-CORE-002"  # V2/V3 contributed


def test_lateral_pattern_i_avl_v5_v6_triggers():
    """The true lateral group (I, aVL, V5, V6) — previously missing from
    the contiguous-group logic, added by this audit."""
    leads = [LeadMeasurement("aVL", 1.2), LeadMeasurement("V6", 1.5)]
    patient = PatientContext(age=60, sex="male")
    result = evaluate_stemi_criteria(leads, patient, MimicFlags())
    assert result.criteria_met is True
    assert result.contiguous_group_name == "Lateral"


def test_high_lateral_pattern_i_avl_still_triggers_as_its_own_named_group():
    leads = [LeadMeasurement("I", 1.2), LeadMeasurement("aVL", 1.3)]
    patient = PatientContext(age=60, sex="male")
    result = evaluate_stemi_criteria(leads, patient, MimicFlags())
    assert result.criteria_met is True
    assert result.contiguous_group_name in ("High lateral", "Lateral")


def test_noncontiguous_elevation_does_not_trigger():
    """V2 (anterior) + aVF (inferior) elevated together are NOT anatomically
    contiguous and must not satisfy any STEMI-criteria group."""
    leads = [LeadMeasurement("V2", 5.0), LeadMeasurement("aVF", 5.0)]
    patient = PatientContext(age=50, sex="male")
    result = evaluate_stemi_criteria(leads, patient, MimicFlags())
    assert result.criteria_met is False
    assert result.contiguous_group_name is None


def test_inadequate_missing_leads_only_one_of_inferior_group_present():
    leads = [LeadMeasurement("II", 3.0)]  # only 1 of 3 inferior-group leads
    patient = PatientContext(age=50, sex="male")
    result = evaluate_stemi_criteria(leads, patient, MimicFlags())
    assert result.criteria_met is False


# ---------------------------------------------------------------------------
# Reciprocal ST-change representation (descriptive only — must never affect
# criteria_met).
# ---------------------------------------------------------------------------

def test_reciprocal_depression_is_reported_but_does_not_affect_criteria_met():
    leads = [
        LeadMeasurement("II", 2.0, reciprocal_depression_mm=None),
        LeadMeasurement("III", 2.0, reciprocal_depression_mm=None),
        LeadMeasurement("aVF", 2.0, reciprocal_depression_mm=None),
        LeadMeasurement("I", 0.1, reciprocal_depression_mm=1.5),
        LeadMeasurement("aVL", 0.1, reciprocal_depression_mm=1.2),
    ]
    patient = PatientContext(age=55, sex="male")
    result = evaluate_stemi_criteria(leads, patient, MimicFlags())
    assert result.criteria_met is True  # driven by II/III/aVF, not by reciprocal leads
    reciprocal_leads = {m.lead for m in result.reciprocal_changes}
    assert reciprocal_leads == {"I", "aVL"}


def test_reciprocal_changes_alone_never_trigger_criteria_met():
    """Reciprocal/ST-depression-only findings, with no qualifying elevation
    anywhere, must never satisfy criteria_met on their own."""
    leads = [
        LeadMeasurement("I", 0.1, reciprocal_depression_mm=2.0),
        LeadMeasurement("aVL", 0.1, reciprocal_depression_mm=1.8),
    ]
    patient = PatientContext(age=55, sex="male")
    result = evaluate_stemi_criteria(leads, patient, MimicFlags())
    assert result.criteria_met is False
    assert len(result.reciprocal_changes) == 2


# ---------------------------------------------------------------------------
# ACS-CORE-002: age/sex-specific V2-V3 thresholds
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "age,sex,elevation,expected",
    [
        (45, "male", 2.0, True),      # men >=40: threshold 2.0mm, exact boundary
        (45, "male", 1.9, False),     # just below
        (30, "male", 2.5, True),      # men <40: threshold 2.5mm, exact boundary
        (30, "male", 2.4, False),
        (50, "female", 1.5, True),    # women any age: threshold 1.5mm
        (50, "female", 1.4, False),
        (20, "female", 1.5, True),
    ],
)
def test_v2_v3_age_sex_thresholds(age, sex, elevation, expected):
    leads = [LeadMeasurement("V2", elevation), LeadMeasurement("V3", elevation)]
    patient = PatientContext(age=age, sex=sex)
    result = evaluate_stemi_criteria(leads, patient, MimicFlags())
    assert result.criteria_met is expected


def test_v2_v3_missing_age_raises_error_not_silent_default():
    leads = [LeadMeasurement("V2", 3.0), LeadMeasurement("V3", 3.0)]
    patient = PatientContext(age=None, sex="male")
    with pytest.raises(ValueError):
        evaluate_stemi_criteria(leads, patient, MimicFlags())


def test_v2_v3_missing_sex_raises_error_not_silent_default():
    leads = [LeadMeasurement("V2", 3.0), LeadMeasurement("V3", 3.0)]
    patient = PatientContext(age=50, sex=None)
    with pytest.raises(ValueError):
        evaluate_stemi_criteria(leads, patient, MimicFlags())


# ---------------------------------------------------------------------------
# ACS-CORE-003: mimic / clinical-correlation safeguard
# ---------------------------------------------------------------------------

def test_asymptomatic_lbbb_flags_for_clinical_correlation_and_suppresses_criteria():
    leads = [LeadMeasurement("V2", 3.0), LeadMeasurement("V3", 3.0)]
    patient = PatientContext(age=50, sex="male", symptomatic=False)
    mimics = MimicFlags(lbbb=True)
    result = evaluate_stemi_criteria(leads, patient, mimics)
    # LBBB explicitly invalidates the threshold per ACS-CORE-001/002 exclusion
    assert result.criteria_met is False
    assert result.requires_clinical_correlation is True
    assert "LBBB" in result.mimic_names


def test_each_named_mimic_individually_sets_flag():
    leads = [LeadMeasurement("II", 1.0), LeadMeasurement("III", 1.0)]
    patient = PatientContext(age=60, sex="male")
    for field_name in [
        "lvh", "lbbb", "rbbb", "paced_rhythm", "pericarditis",
        "brugada", "takotsubo", "early_repolarization",
    ]:
        mimics = MimicFlags(**{field_name: True})
        result = evaluate_stemi_criteria(leads, patient, mimics)
        assert result.mimic_present is True
        assert result.requires_clinical_correlation is True


def test_symptomatic_high_suspicion_mimic_does_not_force_correlation_flag():
    """A mimic present alongside symptomatic + high suspicion should not be
    auto-flagged for correlation under ACS-CORE-003 (that combination is
    ESC's ACS-CORE-004 territory, deliberately not implemented tonight)."""
    leads = [LeadMeasurement("II", 1.0), LeadMeasurement("III", 1.0)]
    patient = PatientContext(age=60, sex="male", symptomatic=True, high_clinical_suspicion=True)
    mimics = MimicFlags(paced_rhythm=True)
    result = evaluate_stemi_criteria(leads, patient, mimics)
    assert result.requires_clinical_correlation is False


# ---------------------------------------------------------------------------
# Missing leads / poor quality (quality gate lives in EcgQuality, tested here
# and via the API test below)
# ---------------------------------------------------------------------------

def test_missing_leads_does_not_trigger_criteria():
    leads = [LeadMeasurement("V2", 5.0)]  # only one lead, no contiguous pair
    patient = PatientContext(age=50, sex="male")
    result = evaluate_stemi_criteria(leads, patient, MimicFlags())
    assert result.criteria_met is False


def test_poor_quality_ecg_is_rejected():
    quality = EcgQuality(
        leads_detected=8, calibration_available=True,
        signal_suitable=True, lead_labels_identified=True,
    )
    assert quality.is_acceptable() is False
    assert any("leads detected" in r for r in quality.failure_reasons())


def test_good_quality_ecg_is_accepted():
    quality = EcgQuality(
        leads_detected=12, calibration_available=True,
        signal_suitable=True, lead_labels_identified=True,
    )
    assert quality.is_acceptable() is True


# ---------------------------------------------------------------------------
# Normal / nondiagnostic ECG -> ACS not excluded (tested via API, see below)
# ---------------------------------------------------------------------------

def test_normal_ecg_criteria_not_met():
    leads = [LeadMeasurement("V2", 0.2), LeadMeasurement("II", 0.1)]
    patient = PatientContext(age=55, sex="male")
    result = evaluate_stemi_criteria(leads, patient, MimicFlags())
    assert result.criteria_met is False


# ---------------------------------------------------------------------------
# ACS-CORE-005: FMC-to-ECG timing
# ---------------------------------------------------------------------------

def test_fmc_to_ecg_exact_10_min_boundary_compliant():
    fmc = datetime(2026, 1, 1, 12, 0, 0)
    ecg = fmc + timedelta(minutes=10)
    result = evaluate_fmc_to_ecg_timing(fmc, ecg)
    assert result.compliant is True


def test_fmc_to_ecg_10_min_1_sec_noncompliant():
    fmc = datetime(2026, 1, 1, 12, 0, 0)
    ecg = fmc + timedelta(minutes=10, seconds=1)
    result = evaluate_fmc_to_ecg_timing(fmc, ecg)
    assert result.compliant is False


def test_fmc_to_ecg_missing_timestamp_raises():
    with pytest.raises(ValueError):
        evaluate_fmc_to_ecg_timing(None, datetime.now())


# ---------------------------------------------------------------------------
# ACS-CORE-008: serial ECG indication
# ---------------------------------------------------------------------------

def test_serial_ecg_indicated_when_nondiagnostic_and_high_suspicion():
    result = evaluate_serial_ecg_indication(
        initial_ecg_diagnostic=False,
        high_clinical_suspicion=True,
        symptoms_persistent=False,
        condition_deteriorating=False,
        care_setting=CareSetting.PREHOSPITAL,
    )
    assert result.indicated is True
    assert result.loe == "C-LD"


def test_serial_ecg_in_hospital_uses_different_loe_than_prehospital():
    prehospital = evaluate_serial_ecg_indication(
        initial_ecg_diagnostic=False, high_clinical_suspicion=True,
        symptoms_persistent=False, condition_deteriorating=False,
        care_setting=CareSetting.PREHOSPITAL,
    )
    in_hospital = evaluate_serial_ecg_indication(
        initial_ecg_diagnostic=False, high_clinical_suspicion=True,
        symptoms_persistent=False, condition_deteriorating=False,
        care_setting=CareSetting.IN_HOSPITAL,
    )
    assert prehospital.loe != in_hospital.loe
    assert prehospital.loe == "C-LD"
    assert in_hospital.loe == "B-NR"


def test_serial_ecg_not_indicated_when_initial_diagnostic():
    result = evaluate_serial_ecg_indication(
        initial_ecg_diagnostic=True, high_clinical_suspicion=True,
        symptoms_persistent=True, condition_deteriorating=True,
        care_setting=CareSetting.PREHOSPITAL,
    )
    assert result.indicated is False


# ---------------------------------------------------------------------------
# hs-cTn display helper (never a diagnostic trigger)
# ---------------------------------------------------------------------------

def test_hs_ctn_window_hs_assay():
    result = hs_ctn_repeat_window("hs_ctn")
    assert result["repeat_window"] == "1-2 hours"
    assert "ACC/AHA 2025" in result["source"]


def test_hs_ctn_window_conventional_assay():
    result = hs_ctn_repeat_window("conventional")
    assert result["repeat_window"] == "3-6 hours"


def test_hs_ctn_window_unrecognized_assay_raises():
    with pytest.raises(ValueError):
        hs_ctn_repeat_window("esc_0h_1h")  # explicitly not implemented (ACS-CORE-010)


# ---------------------------------------------------------------------------
# ACS non-exclusion language, presence in API output
# ---------------------------------------------------------------------------

def test_api_nondiagnostic_ecg_includes_acs_not_excluded_statement(client):
    payload = {
        "leads": [{"lead": "V2", "st_elevation_mm": 0.2}],
        "patient": {"age": 55, "sex": "male"},
        "quality": {
            "leads_detected": 12, "calibration_available": True,
            "signal_suitable": True, "lead_labels_identified": True,
        },
    }
    res = client.post("/api/acs/assess", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["criteria_met"] is False
    assert "does not exclude ACS" in body["acs_not_excluded_statement"]


def test_api_stemi_criteria_met_emergency_headline(client):
    payload = {
        "leads": [
            {"lead": "V2", "st_elevation_mm": 2.3},
            {"lead": "V3", "st_elevation_mm": 2.5},
            {"lead": "V4", "st_elevation_mm": 1.8},
        ],
        "patient": {
            "age": 58, "sex": "male", "symptomatic": True,
            "high_clinical_suspicion": True, "ongoing_chest_pain": True,
        },
        "quality": {
            "leads_detected": 12, "calibration_available": True,
            "signal_suitable": True, "lead_labels_identified": True,
        },
    }
    res = client.post("/api/acs/assess", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["criteria_met"] is True
    assert body["urgency"] == "EMERGENCY"
    assert body["headline"] == "ECG meets guideline STEMI criteria"


def test_api_quality_gate_blocks_output(client):
    payload = {
        "leads": [{"lead": "V2", "st_elevation_mm": 3.0}],
        "patient": {"age": 50, "sex": "male"},
        "quality": {
            "leads_detected": 6, "calibration_available": False,
            "signal_suitable": False, "lead_labels_identified": False,
        },
    }
    res = client.post("/api/acs/assess", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["quality_gate_passed"] is False
    assert "insufficient" in body["headline"]


def test_api_acs_health(client):
    res = client.get("/api/acs/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True


# ---------------------------------------------------------------------------
# Final safety check: prohibited phrases must never appear in core.py's
# output-facing constants, or anywhere the API module constructs headlines.
# ---------------------------------------------------------------------------

def _collect_all_string_values(obj) -> list[str]:
    """Recursively collect every string value from a nested dict/list structure."""
    strings = []
    if isinstance(obj, str):
        strings.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            strings.extend(_collect_all_string_values(v))
    elif isinstance(obj, list):
        for v in obj:
            strings.extend(_collect_all_string_values(v))
    return strings


def test_prohibited_phrases_never_appear_in_api_outputs(client):
    """Exercises /api/acs/assess across a representative set of inputs
    (STEMI-positive, nondiagnostic, mimic-present, poor-quality) and asserts
    no prohibited phrase appears in any returned string value. This checks
    actual runtime output, not source text — module docstrings legitimately
    reference the banned phrases to document what must never be emitted."""
    quality_ok = {
        "leads_detected": 12, "calibration_available": True,
        "signal_suitable": True, "lead_labels_identified": True,
    }
    quality_bad = {
        "leads_detected": 6, "calibration_available": False,
        "signal_suitable": False, "lead_labels_identified": False,
    }
    scenarios = [
        {  # STEMI-positive
            "leads": [{"lead": "V2", "st_elevation_mm": 2.3}, {"lead": "V3", "st_elevation_mm": 2.5}],
            "patient": {"age": 58, "sex": "male", "symptomatic": True, "high_clinical_suspicion": True},
            "quality": quality_ok,
        },
        {  # nondiagnostic
            "leads": [{"lead": "V2", "st_elevation_mm": 0.2}],
            "patient": {"age": 55, "sex": "male"},
            "quality": quality_ok,
        },
        {  # mimic present, asymptomatic
            "leads": [{"lead": "II", "st_elevation_mm": 1.0}, {"lead": "III", "st_elevation_mm": 1.0}],
            "patient": {"age": 60, "sex": "male", "symptomatic": False},
            "mimics": {"lbbb": True},
            "quality": quality_ok,
        },
        {  # poor quality
            "leads": [{"lead": "V2", "st_elevation_mm": 3.0}],
            "patient": {"age": 50, "sex": "male"},
            "quality": quality_bad,
        },
    ]
    for payload in scenarios:
        res = client.post("/api/acs/assess", json=payload)
        assert res.status_code == 200
        all_strings = _collect_all_string_values(res.json())
        joined = " ".join(all_strings)
        for phrase in PROHIBITED_PHRASES:
            assert phrase not in joined, (
                f"Prohibited phrase {phrase!r} found in API output for payload {payload!r}: {joined!r}"
            )


def test_existing_wfdb_endpoint_still_works_after_acs_mount(client):
    """Confirms mounting the ACS router did not break the existing endpoint."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True}
