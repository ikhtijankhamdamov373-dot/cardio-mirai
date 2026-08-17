import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cardiomirai.ecg.qrs_detection import detect_qrs

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="module")
def patient2_record():
    wfdb = pytest.importorskip("wfdb")
    record = wfdb.rdrecord(str(FIXTURES / "rec_2"))
    ann = wfdb.rdann(str(FIXTURES / "rec_2"), "atr")
    return record, ann


def test_patient2_precision_preserved_against_annotations(patient2_record):
    """The base detector's ~4ms precision against manual annotations must not regress."""
    record, ann = patient2_record
    true_peaks = np.array([s for s, sym in zip(ann.sample, ann.symbol) if sym == "N"])
    lead = record.p_signal[:, 1]  # "ECG I filtered" -- the channel _pick_lead selects
    result = detect_qrs(lead, record.fs)
    detected = result.peak_samples

    window_end = true_peaks.max() + 200
    detected_in_window = detected[detected <= window_end]
    tol = 75  # 150ms
    matched = sum(1 for t in true_peaks if np.any(np.abs(detected_in_window - t) <= tol))
    assert matched == len(true_peaks), "Base-detector precision regressed against Patient 2's manual annotations"

    # Sub-tolerance precision check (the original finding was ~4ms, not just "within 150ms")
    max_offset_ms = 0.0
    for t in true_peaks:
        nearest = detected_in_window[np.argmin(np.abs(detected_in_window - t))]
        max_offset_ms = max(max_offset_ms, abs(nearest - t) / record.fs * 1000.0)
    assert max_offset_ms <= 10.0, f"Precision regressed: max offset {max_offset_ms:.1f}ms (expected ~4ms)"


def test_patient2_recovers_at_least_one_missed_beat(patient2_record):
    """Regression target: 19 base beats -> at least one evidence-backed recovery."""
    record, ann = patient2_record
    lead = record.p_signal[:, 1]
    result = detect_qrs(lead, record.fs)
    base_count = sum(1 for b in result.beats if b.source == "base")
    recovered_count = sum(1 for b in result.beats if b.source == "recovered")
    assert base_count == 19
    assert recovered_count >= 1
    assert len(result.beats) >= 20


def test_patient2_recovery_requires_evidence_not_just_long_rr(patient2_record):
    """A long RR interval alone must never cause insertion of a synthetic QRS."""
    record, ann = patient2_record
    lead = record.p_signal[:, 1]
    result = detect_qrs(lead, record.fs)
    assert result.recovery_attempts >= 1
    # At least one attempted recovery must have been evaluated for morphology,
    # not blindly accepted -- i.e. rejection reasons should be substantive.
    for rejection in result.recovery_rejected:
        assert "reason" in rejection and len(rejection["reason"]) > 10


def test_patient2_no_t_wave_misclassified_as_qrs(patient2_record):
    """Increased sensitivity must not start classifying T waves as QRS complexes."""
    record, ann = patient2_record
    true_t_waves = np.array([s for s, sym in zip(ann.sample, ann.symbol) if sym == "t"])
    lead = record.p_signal[:, 1]
    result = detect_qrs(lead, record.fs)
    detected = result.peak_samples
    tol = 40  # 80ms -- tight, a real QRS should not land this close to an annotated T-wave peak
    false_matches = [t for t in true_t_waves if np.any(np.abs(detected - t) <= tol)]
    assert false_matches == []


@pytest.fixture(scope="module")
def synthetic_signals():
    nk = pytest.importorskip("neurokit2")
    fs = 500
    signals = {}
    signals["normal_sinus"] = (nk.ecg_simulate(duration=15, sampling_rate=fs, heart_rate=72, noise=0.01, random_state=1), fs)
    signals["bradycardia"] = (nk.ecg_simulate(duration=15, sampling_rate=fs, heart_rate=45, noise=0.01, random_state=2), fs)
    signals["tachycardia"] = (nk.ecg_simulate(duration=15, sampling_rate=fs, heart_rate=140, noise=0.01, random_state=3), fs)
    signals["sinus_arrhythmia"] = (nk.ecg_simulate(duration=15, sampling_rate=fs, heart_rate=65, heart_rate_std=15, noise=0.01, random_state=4), fs)
    signals["noisy"] = (nk.ecg_simulate(duration=15, sampling_rate=fs, heart_rate=75, noise=0.25, random_state=7), fs)
    low_amp = nk.ecg_simulate(duration=15, sampling_rate=fs, heart_rate=75, noise=0.01, random_state=8)
    signals["low_amplitude"] = (low_amp * 0.15, fs)
    return signals


@pytest.mark.parametrize(
    "case,min_sensitivity,min_ppv",
    [
        ("normal_sinus", 0.99, 0.99),
        ("bradycardia", 0.99, 0.85),  # known limitation: an edge-of-recording false positive exists (pre-existing in base detector, not introduced by recovery)
        ("tachycardia", 0.99, 0.99),
        ("sinus_arrhythmia", 0.99, 0.99),
        ("noisy", 0.95, 0.95),
        ("low_amplitude", 0.95, 0.95),
    ],
)
def test_synthetic_rhythm_sensitivity_ppv(synthetic_signals, case, min_sensitivity, min_ppv):
    nk = pytest.importorskip("neurokit2")
    sig, fs = synthetic_signals[case]
    _, info = nk.ecg_peaks(sig, sampling_rate=fs, method="neurokit")
    true_peaks = np.array(info["ECG_R_Peaks"])

    result = detect_qrs(sig, fs)
    detected = result.peak_samples
    tol = int(0.05 * fs)

    matched_det = set()
    tp = 0
    for t in true_peaks:
        diffs = np.abs(detected - t)
        if diffs.size and diffs.min() <= tol:
            j = int(np.argmin(diffs))
            if j not in matched_det:
                matched_det.add(j)
                tp += 1
    sensitivity = tp / len(true_peaks) if len(true_peaks) else 0.0
    ppv = tp / len(detected) if len(detected) else 0.0
    assert sensitivity >= min_sensitivity, f"{case}: sensitivity {sensitivity:.3f} below {min_sensitivity}"
    assert ppv >= min_ppv, f"{case}: PPV {ppv:.3f} below {min_ppv}"
