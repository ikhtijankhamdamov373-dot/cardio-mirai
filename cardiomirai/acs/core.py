"""
Cardio MIRAI ACS Core — deterministic guideline-rule engine.

RESEARCH PROTOTYPE. NOT A MEDICAL DEVICE. NOT FOR CLINICAL USE.

This module implements ONLY the rules marked implementation-ready in
`cardio-mirai-acs-matrix-v1.2-FINAL.md`, Part 4, Section A (ACS Core v1.0):

  - ACS-CORE-001  General-lead STEMI ST-elevation threshold
  - ACS-CORE-002  Sex/age-specific V2-V3 STEMI threshold
  - ACS-CORE-003  Mimic / clinical-correlation safeguard (asymptomatic LBBB etc.)
  - ACS-CORE-005  First-medical-contact -> ECG 10-minute timing
  - ACS-CORE-008  Serial ECG indication (nondiagnostic initial ECG)

Deliberately NOT implemented here (see the delivery report for why):
  - ACS-CORE-004  ESC symptomatic-LBBB-equivalent rule (out of scope for tonight)
  - ACS-CORE-006 / ACS-CORE-007  Reperfusion/transfer timing rules — regional
    pathway not validated; explicitly excluded by this task's instructions
  - ACS-CORE-009  hs-cTn repeat-window support is implemented as a passive
    display helper only (see `hs_ctn_repeat_window`), never as a diagnostic
    trigger, consistent with "NSTEMI cannot be determined from ECG alone"
  - ACS-CORE-010  ESC 0h/1h and 0h/2h algorithms — UNRESOLVED numeric cutoffs,
    explicitly excluded per instructions

No output of this module ever states "STEMI diagnosed," "NSTEMI diagnosed,"
"No ACS," or "ACS excluded." See `OUTPUT LANGUAGE CONTRACT` below and the
final safety-check grep in the test suite.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# OUTPUT LANGUAGE CONTRACT
# ---------------------------------------------------------------------------
# These are the ONLY headline strings this module is allowed to produce for
# a STEMI-criteria result. Do not construct alternative phrasing elsewhere
# in the codebase for this concept — import these constants instead, so a
# single source of truth exists for the safety-critical wording.
STEMI_CRITERIA_MET_HEADLINE = "ECG meets guideline STEMI criteria"
STEMI_CRITERIA_NOT_MET_HEADLINE = "STEMI criteria not detected on this ECG"
ACS_NOT_EXCLUDED_STATEMENT = (
    "A nondiagnostic ECG does not exclude ACS. Clinical assessment, serial "
    "ECG and cardiac troponin testing may be required."
)
NSTEMI_CANNOT_BE_DETERMINED_STATEMENT = "NSTEMI cannot be determined from ECG alone"
DECISION_SUPPORT_DISCLAIMER = (
    "Cardio MIRAI provides decision support and does not replace clinical diagnosis."
)
QUALITY_INSUFFICIENT_STATEMENT = (
    "ECG quality is insufficient for reliable assessment. Please repeat ECG acquisition."
)

# Explicitly banned phrases — enforced by tests/test_acs_core.py's safety-grep
# test AND by never being written anywhere in this module.
PROHIBITED_PHRASES = (
    "STEMI diagnosed",
    "NSTEMI diagnosed",
    "No ACS",
    "ACS excluded",
    "Safe to discharge",
)


class Urgency(str, Enum):
    EMERGENCY = "EMERGENCY"
    HIGH = "HIGH"
    ROUTINE = "ROUTINE"
    INDETERMINATE = "INDETERMINATE"  # used only for quality-gate failures


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------

@dataclass
class LeadMeasurement:
    """A single lead's J-point ST measurement, in millimetres (1 mm = 0.1 mV).

    `reciprocal_depression_mm` is purely descriptive/reportable — per the
    Fifth Universal Definition of Myocardial Infarction (2026) and both the
    2023 ESC and 2025 ACC/AHA ACS guidelines, reciprocal ST depression is a
    supportive/confirmatory finding, not itself a separate deterministic
    threshold rule in ACS Core v1.0. It must never influence
    `criteria_met` — only the explainability/reporting output.
    """

    lead: str
    st_elevation_mm: float
    reciprocal_depression_mm: Optional[float] = None


# ---------------------------------------------------------------------------
# Anatomically named, explicit contiguous-lead groups.
#
# Named per standard 12-lead anatomical territories so the triggered group
# can be reported by name (e.g. "Inferior") in explainability, not just as
# a bare set of lead labels. Each entry's `leads` set is checked by subset
# overlap (>=2 elevated leads within the named group), so e.g. an isolated
# V1+V2 elevation still correctly satisfies the Anteroseptal group without
# needing every listed lead to be elevated.
#
# IMPORTANT: aVR is intentionally absent from every group below. It is
# still measured by the general-lead >=1mm branch (see
# evaluate_stemi_criteria), but no standard 2-contiguous-lead STEMI group
# includes aVR — ST elevation in aVR is a separate, non-guideline-graded
# research finding (Matrix v1.2 FINAL, row 21: aVR/inferolateral pattern,
# EVIDENCE/RESEARCH), not part of ACS-CORE-001/002. Do not add aVR to a
# group here without an explicit, separately-approved rule for it.
#
# V7-V9 (posterior) and V3R/V4R (right-sided) are intentionally absent.
# They are not implemented anywhere in this engine (Matrix v1.2 FINAL,
# rows 4-5: embedded supportive text, not independently graded) — adding
# them here would risk the engine "detecting" a posterior/RV pattern from
# leads that were never actually acquired. If/when they are implemented,
# they must be gated on the caller explicitly confirming those leads were
# acquired, never inferred from a 12-lead set that lacks them.
# ---------------------------------------------------------------------------
NamedContiguousGroup = tuple[str, frozenset]

CONTIGUOUS_GROUPS_NAMED: list[NamedContiguousGroup] = [
    ("Inferior", frozenset({"II", "III", "aVF"})),
    ("High lateral", frozenset({"I", "aVL"})),
    ("Lateral", frozenset({"I", "aVL", "V5", "V6"})),
    ("Anteroseptal", frozenset({"V1", "V2", "V3", "V4"})),
    ("Anterior", frozenset({"V2", "V3", "V4"})),
    ("Anterolateral", frozenset({"V3", "V4", "V5", "V6"})),
]

# Backward-compatible plain-set view, kept for any external code relying on
# the previous shape.
CONTIGUOUS_GROUPS = [leads for _name, leads in CONTIGUOUS_GROUPS_NAMED]

V2_V3_LEADS = {"V2", "V3"}

ALL_12_LEADS = {"I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"}


@dataclass
class MimicFlags:
    """Known STEMI-mimic conditions, per ACC/AHA 2025 Table 3 footnote."""

    lvh: bool = False
    lbbb: bool = False
    rbbb: bool = False
    paced_rhythm: bool = False
    pericarditis: bool = False
    brugada: bool = False
    takotsubo: bool = False
    early_repolarization: bool = False

    def any_present(self) -> bool:
        return any(
            [
                self.lvh,
                self.lbbb,
                self.rbbb,
                self.paced_rhythm,
                self.pericarditis,
                self.brugada,
                self.takotsubo,
                self.early_repolarization,
            ]
        )

    def present_names(self) -> list[str]:
        names = []
        if self.lvh:
            names.append("LVH")
        if self.lbbb:
            names.append("LBBB")
        if self.rbbb:
            names.append("RBBB")
        if self.paced_rhythm:
            names.append("paced rhythm")
        if self.pericarditis:
            names.append("pericarditis")
        if self.brugada:
            names.append("Brugada pattern")
        if self.takotsubo:
            names.append("Takotsubo pattern")
        if self.early_repolarization:
            names.append("early repolarization")
        return names


@dataclass
class PatientContext:
    age: Optional[int] = None
    sex: Optional[str] = None  # "male" | "female"
    symptomatic: bool = False
    high_clinical_suspicion: bool = False
    ongoing_chest_pain: bool = False


@dataclass
class EcgQuality:
    leads_detected: int = 0
    required_leads: int = 12
    calibration_available: bool = False
    signal_suitable: bool = False
    lead_labels_identified: bool = False

    def is_acceptable(self) -> bool:
        return (
            self.leads_detected >= self.required_leads
            and self.calibration_available
            and self.signal_suitable
            and self.lead_labels_identified
        )

    def failure_reasons(self) -> list[str]:
        reasons = []
        if self.leads_detected < self.required_leads:
            reasons.append(
                f"Only {self.leads_detected}/{self.required_leads} leads detected"
            )
        if not self.calibration_available:
            reasons.append("Calibration not available")
        if not self.signal_suitable:
            reasons.append("Signal not suitable for analysis")
        if not self.lead_labels_identified:
            reasons.append("Lead labels not identified")
        return reasons


# ---------------------------------------------------------------------------
# ACS-CORE-001 / ACS-CORE-002 — STEMI ST-elevation threshold
# ---------------------------------------------------------------------------

def _v2_v3_threshold_mm(age: Optional[int], sex: Optional[str]) -> float:
    """ACS-CORE-002. Raises ValueError if age/sex is missing — per the
    matrix's explicit test requirement, this must never silently default."""
    if age is None or sex is None:
        raise ValueError(
            "Age and sex are required to apply the V2-V3 STEMI threshold "
            "(ACS-CORE-002, thresholds sourced from ACC/AHA 2025 Table 3 / "
            "ESC 2023 Section 3.2.1, both aligned with the Fifth Universal "
            "Definition of Myocardial Infarction 2026)."
        )
    sex_normalized = sex.strip().lower()
    if sex_normalized not in ("male", "female"):
        raise ValueError(f"Unrecognized sex value: {sex!r}")

    if sex_normalized == "male":
        return 2.0 if age >= 40 else 2.5
    return 1.5  # female, any age


@dataclass
class StemiCriteriaResult:
    criteria_met: bool
    contributing_leads: list[LeadMeasurement] = field(default_factory=list)
    contiguous_group: Optional[frozenset] = None
    contiguous_group_name: Optional[str] = None
    triggering_rule_id: Optional[str] = None
    thresholds_applied: dict = field(default_factory=dict)
    mimic_present: bool = False
    mimic_names: list[str] = field(default_factory=list)
    requires_clinical_correlation: bool = False
    reciprocal_changes: list[LeadMeasurement] = field(default_factory=list)


def evaluate_stemi_criteria(
    leads: list[LeadMeasurement],
    patient: PatientContext,
    mimics: MimicFlags,
) -> StemiCriteriaResult:
    """
    Implements ACS-CORE-001, ACS-CORE-002, and ACS-CORE-003 together, since
    the mimic safeguard (003) modifies how a positive 001/002 result should
    be presented, not just whether it fires.

    ACS-CORE-001: >=1 mm at J-point in >=2 contiguous leads, all leads
                  except V2-V3, absent known LVH/LBBB.
    ACS-CORE-002: V2-V3 specific age/sex thresholds.
    ACS-CORE-003: if a mimic is present AND the patient is asymptomatic or
                  suspicion is not high, this result must not be presented
                  as an unqualified STEMI-criteria-met finding.

    Accepts any subset of the 12 standard leads (see ALL_12_LEADS). Every
    lead not in V2/V3 — including I, II, III, aVR, aVL, aVF — is evaluated
    against the general >=1mm threshold. aVR is deliberately excluded from
    every contiguous group (see CONTIGUOUS_GROUPS_NAMED) and therefore can
    never, by itself or in combination, satisfy criteria_met — this is
    intentional (aVR is not part of any guideline-defined 2-contiguous-lead
    STEMI group) and is covered by test_avr_measured_but_never_triggers.
    """
    v2v3_threshold = None
    elevated: list[LeadMeasurement] = []
    reciprocal: list[LeadMeasurement] = []

    for measurement in leads:
        if measurement.reciprocal_depression_mm is not None:
            reciprocal.append(measurement)

        if measurement.lead in V2_V3_LEADS:
            if v2v3_threshold is None:
                v2v3_threshold = _v2_v3_threshold_mm(patient.age, patient.sex)
            if measurement.st_elevation_mm >= v2v3_threshold:
                elevated.append(measurement)
        else:
            if measurement.st_elevation_mm >= 1.0:
                elevated.append(measurement)

    elevated_lead_names = {m.lead for m in elevated}
    matched_group_name = None
    matched_group = None
    for name, group in CONTIGUOUS_GROUPS_NAMED:
        overlap = group & elevated_lead_names
        if len(overlap) >= 2:
            matched_group_name = name
            matched_group = frozenset(overlap)
            break

    criteria_met = matched_group is not None

    # ACS-CORE-001/002 explicitly exclude known LVH/LBBB from validity.
    if mimics.lvh or mimics.lbbb:
        criteria_met = False

    triggering_rule_id = None
    if criteria_met and matched_group:
        # ACS-CORE-002 fires if any contributing lead is V2/V3; otherwise
        # the general-lead ACS-CORE-001 rule fired.
        triggering_rule_id = (
            "ACS-CORE-002" if matched_group & V2_V3_LEADS else "ACS-CORE-001"
        )

    result = StemiCriteriaResult(
        criteria_met=criteria_met,
        contributing_leads=[m for m in elevated if m.lead in (matched_group or set())],
        contiguous_group=matched_group,
        contiguous_group_name=matched_group_name,
        triggering_rule_id=triggering_rule_id,
        thresholds_applied={
            "general_leads_mm": 1.0,
            "v2_v3_mm": v2v3_threshold,
        },
        mimic_present=mimics.any_present(),
        mimic_names=mimics.present_names(),
        reciprocal_changes=reciprocal,
    )

    # ACS-CORE-003: asymptomatic / low-suspicion + mimic present => flag for
    # mandatory clinical correlation, regardless of the raw threshold result.
    if mimics.any_present() and not (patient.symptomatic and patient.high_clinical_suspicion):
        result.requires_clinical_correlation = True

    return result


# ---------------------------------------------------------------------------
# ACS-CORE-005 — FMC-to-ECG timing
# ---------------------------------------------------------------------------

@dataclass
class TimingResult:
    compliant: bool
    elapsed_minutes: float
    threshold_minutes: float = 10.0
    source: str = "ACC/AHA 2025, Section 3.1.1 Rec.1 / Section 3.1.2 Rec.1 (COR 1, LOE B-NR)"


def evaluate_fmc_to_ecg_timing(fmc_time: datetime, ecg_time: datetime) -> TimingResult:
    """ACS-CORE-005. Both timestamps are required; callers must not pass
    None and expect a silent pass."""
    if fmc_time is None or ecg_time is None:
        raise ValueError("Both fmc_time and ecg_time are required for ACS-CORE-005.")
    elapsed = (ecg_time - fmc_time).total_seconds() / 60.0
    return TimingResult(compliant=elapsed <= 10.0, elapsed_minutes=elapsed)


# ---------------------------------------------------------------------------
# ACS-CORE-008 — Serial ECG indication
# ---------------------------------------------------------------------------

class CareSetting(str, Enum):
    PREHOSPITAL = "prehospital"
    IN_HOSPITAL = "in_hospital"


@dataclass
class SerialEcgResult:
    indicated: bool
    reasons: list[str]
    care_setting: CareSetting
    cor: str = "1"
    loe: str = ""  # set per care setting below; never averaged/merged


def evaluate_serial_ecg_indication(
    initial_ecg_diagnostic: bool,
    high_clinical_suspicion: bool,
    symptoms_persistent: bool,
    condition_deteriorating: bool,
    care_setting: CareSetting,
) -> SerialEcgResult:
    """ACS-CORE-008. Two separately graded recommendations by care setting;
    LOE must never be merged across settings (C-LD prehospital, B-NR
    in-hospital, per ACC/AHA 2025 Sections 3.1.1/3.1.2)."""
    reasons = []
    indicated = False
    if not initial_ecg_diagnostic:
        if high_clinical_suspicion:
            reasons.append("High clinical suspicion of ACS")
            indicated = True
        if symptoms_persistent:
            reasons.append("Symptoms persistent")
            indicated = True
        if condition_deteriorating:
            reasons.append("Clinical condition deteriorating")
            indicated = True

    loe = "C-LD" if care_setting == CareSetting.PREHOSPITAL else "B-NR"
    return SerialEcgResult(
        indicated=indicated,
        reasons=reasons,
        care_setting=care_setting,
        loe=loe,
    )


# ---------------------------------------------------------------------------
# Passive display-only helper (NOT a diagnostic trigger) for hs-cTn timing.
# Corresponds to the matrix's ACC/AHA-only general window; the ESC named
# 0h/1h and 0h/2h algorithm (ACS-CORE-010) is explicitly NOT implemented
# because its numeric cutoffs (Supplementary Table S4) remain unresolved.
# ---------------------------------------------------------------------------

def hs_ctn_repeat_window(assay_type: str) -> dict:
    """Returns display-only text; never used to compute a diagnostic result."""
    assay_type_normalized = assay_type.strip().lower()
    if assay_type_normalized == "hs_ctn":
        window = "1-2 hours"
    elif assay_type_normalized == "conventional":
        window = "3-6 hours"
    else:
        raise ValueError(f"Unrecognized assay_type: {assay_type!r}")
    return {
        "repeat_window": window,
        "source": "ACC/AHA 2025, Section 3.1.2 Recommendation 4 (COR 1, LOE B-NR)",
        "note": NSTEMI_CANNOT_BE_DETERMINED_STATEMENT,
    }
