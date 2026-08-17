"""Current-AF-evidence classifier: categorical (Low/Intermediate/High), multi-feature.

This directly replaces the old `af_score` (0-100, presented as "AF
probability"). Root-cause finding from the Patient 2 investigation: the old
formula weighted RR-variability terms (CV, RMSSD, pNN50, entropy) so
heavily that they alone could push the score past 70 regardless of P-wave
evidence, and the one safety cap requiring `rr_cv < 0.12` could never fire
for genuine sinus arrhythmia -- whose defining feature IS an elevated
RR-CV. That produced a 69% "AF probability" for a recording with 100%
P-wave presence and confirmed sinus P-QRS association.

This module is deliberately NOT a single weighted sum. It requires
*multiple, independent, compatible* features before reaching "high", and
strong P-QRS evidence actively caps the category rather than only slowing
its rise. It never claims a validated probability -- only a conservative
categorical assessment with itemized supporting/opposing evidence, because
no calibrated/validated AF classifier exists yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AfEvidence:
    category: str  # "low" | "intermediate" | "high"
    confidence: float
    evidence_for: list[str] = field(default_factory=list)
    evidence_against: list[str] = field(default_factory=list)
    rr_irregularity_index: float | None = None  # advanced-measurements reference only

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "confidence": self.confidence,
            "evidence_for": self.evidence_for,
            "evidence_against": self.evidence_against,
            "method": "multi-feature evidence weighting (RR variability, P-wave/PR evidence, "
                      "fibrillatory baseline, signal quality) -- categorical only; "
                      "not a validated probability.",
        }


def assess_af_evidence(
    *,
    rr_cv: float | None,
    rr_irregularity_index: float | None,
    p_wave_presence_ratio: float,
    pr_consistency: float | None,
    fibrillatory_baseline_power: float,
    signal_quality_index: float,
    beat_count: int,
    recovered_beat_fraction: float = 0.0,
) -> AfEvidence:
    rr_cv = rr_cv or 0.0
    pr_consistency = pr_consistency if pr_consistency is not None else 50.0
    evidence_for: list[str] = []
    evidence_against: list[str] = []

    low_quality = signal_quality_index < 50.0
    few_beats = beat_count < 6

    strong_p_evidence = p_wave_presence_ratio >= 70.0 and pr_consistency >= 60.0
    moderate_p_evidence = p_wave_presence_ratio >= 55.0
    p_absent = p_wave_presence_ratio < 40.0

    high_rr_irregularity = rr_cv >= 0.16
    fibrillatory_activity = fibrillatory_baseline_power >= 0.55

    if strong_p_evidence:
        evidence_against.append(
            f"P waves are present before {p_wave_presence_ratio:.0f}% of analyzable QRS complexes with consistent "
            f"PR timing (consistency {pr_consistency:.0f}%) -- this is strong evidence FOR organized atrial "
            f"activity (sinus origin), which argues against AF regardless of RR variability."
        )
    elif moderate_p_evidence:
        evidence_against.append(f"P waves are present before {p_wave_presence_ratio:.0f}% of analyzable QRS complexes, though PR consistency is only {pr_consistency:.0f}%.")
    elif p_absent:
        evidence_for.append(f"P waves are not reliably identified before QRS complexes ({p_wave_presence_ratio:.0f}% presence).")

    if high_rr_irregularity:
        evidence_for.append(f"RR intervals are substantially irregular (CV {rr_cv:.2f}).")
    elif rr_cv >= 0.08:
        evidence_for.append(f"RR intervals show mild-to-moderate irregularity (CV {rr_cv:.2f}) -- compatible with AF but equally compatible with sinus arrhythmia, ectopy, or artifact.")
    else:
        evidence_against.append(f"RR intervals are close to regular (CV {rr_cv:.2f}).")

    if fibrillatory_activity:
        evidence_for.append(f"Fibrillatory baseline power ({fibrillatory_baseline_power:.2f}) is elevated in the 4-9 Hz band.")
    else:
        evidence_against.append(f"No substantial fibrillatory baseline activity detected ({fibrillatory_baseline_power:.2f}).")

    if low_quality:
        evidence_against.append(f"Signal quality is reduced (index {signal_quality_index:.0f}); RR-based irregularity is less reliable under these conditions.")
    if few_beats:
        evidence_against.append(f"Only {beat_count} beats are available for rhythm assessment -- limited evidence base.")
    if recovered_beat_fraction > 0.15:
        evidence_against.append(f"{recovered_beat_fraction*100:.0f}% of beats required missed-beat recovery -- some RR variability may reflect residual detection uncertainty rather than confirmed rhythm irregularity.")

    # Decision logic: strong, consistent P-wave/PR evidence is an explicit,
    # independent cap at "low" -- it is never simply outweighed by a large
    # RR term, which is precisely the failure mode this module replaces.
    # Otherwise, count independent AF-supporting factors explicitly rather
    # than chaining elif branches (which previously left a dead zone at
    # 40-55% P-wave presence that fell through to an unintended default).
    supporting_factors = sum([
        high_rr_irregularity,
        not moderate_p_evidence,  # covers both "ambiguous" (40-55%) and "absent" (<40%) P-wave presence
        fibrillatory_activity,
    ])

    if strong_p_evidence:
        category = "low"
        confidence = 0.80 if not low_quality else 0.55
    elif low_quality or few_beats:
        category = "intermediate" if supporting_factors >= 2 else "low"
        confidence = 0.35
        evidence_against.append("Assessment limited by signal quality/beat count; not classified as high without more reliable evidence.")
    elif supporting_factors >= 3:
        category = "high"
        confidence = 0.75
    elif supporting_factors == 2:
        category = "intermediate"
        confidence = 0.55
    elif supporting_factors == 1 and high_rr_irregularity and moderate_p_evidence:
        category = "intermediate"
        confidence = 0.40
        evidence_against.append("RR irregularity is present, but partial P-wave evidence argues against classifying this as high-likelihood AF; sinus arrhythmia, ectopy, or artifact remain plausible explanations.")
    else:
        category = "low"
        confidence = 0.65

    return AfEvidence(
        category=category,
        confidence=round(confidence, 2),
        evidence_for=evidence_for,
        evidence_against=evidence_against,
        rr_irregularity_index=rr_irregularity_index,
    )
