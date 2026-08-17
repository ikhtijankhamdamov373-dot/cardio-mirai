import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cardiomirai.ecg.af_evidence import assess_af_evidence


def test_patient2_profile_is_not_high():
    """The exact failure case this module was built to fix: sinus arrhythmia with
    strong P-QRS association must not be scored as high AF evidence."""
    result = assess_af_evidence(
        rr_cv=0.293, rr_irregularity_index=100.0, p_wave_presence_ratio=100.0,
        pr_consistency=90.0, fibrillatory_baseline_power=0.2,
        signal_quality_index=80.0, beat_count=20, recovered_beat_fraction=0.05,
    )
    assert result.category != "high"


def test_strong_p_evidence_caps_at_low_regardless_of_rr_irregularity():
    result = assess_af_evidence(
        rr_cv=0.5, rr_irregularity_index=100.0, p_wave_presence_ratio=95.0,
        pr_consistency=80.0, fibrillatory_baseline_power=0.1,
        signal_quality_index=90.0, beat_count=25,
    )
    assert result.category == "low"


def test_classic_af_profile_scores_high():
    result = assess_af_evidence(
        rr_cv=0.28, rr_irregularity_index=85.0, p_wave_presence_ratio=8.0,
        pr_consistency=0.0, fibrillatory_baseline_power=0.7,
        signal_quality_index=85.0, beat_count=24,
    )
    assert result.category == "high"


def test_regular_sinus_scores_low():
    result = assess_af_evidence(
        rr_cv=0.04, rr_irregularity_index=8.0, p_wave_presence_ratio=98.0,
        pr_consistency=95.0, fibrillatory_baseline_power=0.1,
        signal_quality_index=90.0, beat_count=22,
    )
    assert result.category == "low"


def test_ambiguous_p_wave_zone_does_not_silently_default_low():
    """Regression for a bug found during development: 40-55% P-wave presence
    fell through an elif chain to an unintended 'low' default."""
    result = assess_af_evidence(
        rr_cv=0.22, rr_irregularity_index=60.0, p_wave_presence_ratio=45.0,
        pr_consistency=30.0, fibrillatory_baseline_power=0.3,
        signal_quality_index=75.0, beat_count=18,
    )
    assert result.category == "intermediate"


def test_low_signal_quality_never_reaches_high():
    result = assess_af_evidence(
        rr_cv=0.30, rr_irregularity_index=75.0, p_wave_presence_ratio=30.0,
        pr_consistency=20.0, fibrillatory_baseline_power=0.4,
        signal_quality_index=35.0, beat_count=15,
    )
    assert result.category != "high"


def test_evidence_lists_are_populated_and_explainable():
    result = assess_af_evidence(
        rr_cv=0.28, rr_irregularity_index=85.0, p_wave_presence_ratio=8.0,
        pr_consistency=0.0, fibrillatory_baseline_power=0.7,
        signal_quality_index=85.0, beat_count=24,
    )
    assert len(result.evidence_for) >= 2
    assert result.confidence > 0
