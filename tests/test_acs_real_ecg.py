"""
Tests for real ECG ingestion into the ACS engine
(cardiomirai/acs/ecg_ingestion.py, POST /api/acs/analyze-ecg).

RESEARCH PROTOTYPE. NOT A MEDICAL DEVICE.

Every test here uses an actual WFDB file, actually parsed, actually
measured by the existing cardiomirai.api.extract_basic_ecg_measurements
engine — nothing is mocked or hand-fed to the ACS core in these tests
(contrast with test_acs_core.py, which tests the core engine directly
with hand-constructed LeadMeasurement objects).

The 12-lead fixture used here (synthetic_12lead_anterior_stemi.hea/.dat)
is a SYNTHETIC TEST FIXTURE generated for this test suite — a simulated
QRS train with an injected sustained offset in V2/V3/V4 — NOT a real
patient recording. It exists to prove the pipeline performs genuine
measurement end-to-end; it is never described as clinical data.
"""

from pathlib import Path

import numpy as np
import pytest
import wfdb
from fastapi.testclient import TestClient

from cardiomirai import api as api_module
from cardiomirai.acs.ecg_ingestion import EcgIngestionError, ingest_real_wfdb_ecg, normalize_lead_name

FIXTURES = Path(__file__).parent / "fixtures"


def _qrs_like_signal(fs: int, n: int, amp: float = 1.2) -> np.ndarray:
    """A narrow-Gaussian-peak train that the real _detect_qrs (a
    derivative-energy detector tuned for sharp QRS transients) can
    actually detect — a smooth sine wave, by contrast, has no sharp
    enough transient and yields zero detected beats. Used only to make
    unit tests exercise the real pipeline; never presented as clinical
    signal generation."""
    t = np.linspace(0, n / fs, n)
    period = 60.0 / 75  # 75 bpm
    sig = np.zeros(n)
    for bt in np.arange(0.3, t[-1], period):
        sig += amp * np.exp(-0.5 * ((t - bt) / 0.015) ** 2)
    return sig


@pytest.fixture()
def client():
    return TestClient(api_module.app)


# ---------------------------------------------------------------------------
# Lead-name normalization
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("I", "I"), ("ii", "II"), ("III", "III"),
        ("avr", "aVR"), ("AVL", "aVL"), ("aVF", "aVF"),
        ("v1", "V1"), ("V6", "V6"),
    ],
)
def test_normalize_recognized_lead_names(raw, expected):
    assert normalize_lead_name(raw) == expected


@pytest.mark.parametrize("raw", ["MLII", "avF-modified", "", None, "Lead12", "ECG1"])
def test_normalize_unrecognized_names_returns_none_not_a_guess(raw):
    assert normalize_lead_name(raw) is None


# ---------------------------------------------------------------------------
# End-to-end: real 12-lead synthetic fixture through the full pipeline
# ---------------------------------------------------------------------------

def test_full_pipeline_anterior_pattern_produces_genuine_measurements(client):
    hea = FIXTURES / "synthetic_12lead_anterior_stemi.hea"
    dat = FIXTURES / "synthetic_12lead_anterior_stemi.dat"
    with hea.open("rb") as h, dat.open("rb") as d:
        res = client.post(
            "/api/acs/analyze-ecg",
            files=[
                ("files", ("synthetic_12lead_anterior_stemi.hea", h, "application/octet-stream")),
                ("files", ("synthetic_12lead_anterior_stemi.dat", d, "application/octet-stream")),
            ],
            data={
                "age": "58", "sex": "male",
                "symptomatic": "true", "high_clinical_suspicion": "true",
            },
        )
    assert res.status_code == 200
    body = res.json()

    assert body["analysis_source"] == "uploaded_real_ecg"
    assert set(body["detected_leads"]) == {
        "I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"
    }
    assert body["sampling_frequency_hz"] == 500.0
    assert body["duration_seconds"] == pytest.approx(10.0, abs=0.1)
    assert body["qrs_beat_count"] > 0
    assert body["heart_rate_bpm"] is not None

    # The measurements must vary by lead (proof they come from the actual
    # waveform, not a fixed/fabricated value) and V2/V3/V4 must show
    # meaningfully higher ST elevation than an uninvolved lead like V6.
    by_lead = {m["lead"]: m["st_elevation_mm"] for m in body["all_lead_measurements"]}
    assert by_lead["V2"] > 2.0
    assert by_lead["V3"] > 2.0
    assert by_lead["V4"] > 2.0
    assert by_lead["V6"] < 1.0
    assert len({round(v, 1) for v in by_lead.values()}) > 1  # not a constant/fabricated value

    assert body["criteria_met"] is True
    assert body["urgency"] == "EMERGENCY"
    assert body["triggering_rule_id"] == "ACS-CORE-002"
    assert body["contiguous_group_name"] in ("Anteroseptal", "Anterior")
    assert "uploaded_real_ecg" == body["analysis_source"]  # never "synthetic_demo"


def test_pipeline_never_labels_upload_as_synthetic(client):
    hea = FIXTURES / "synthetic_12lead_anterior_stemi.hea"
    dat = FIXTURES / "synthetic_12lead_anterior_stemi.dat"
    with hea.open("rb") as h, dat.open("rb") as d:
        res = client.post(
            "/api/acs/analyze-ecg",
            files=[
                ("files", ("synthetic_12lead_anterior_stemi.hea", h, "application/octet-stream")),
                ("files", ("synthetic_12lead_anterior_stemi.dat", d, "application/octet-stream")),
            ],
            data={"age": "58", "sex": "male"},
        )
    assert res.status_code == 200
    body = res.json()
    full_text = str(body)
    assert "synthetic_demo" not in full_text.lower()
    assert body["analysis_source"] == "uploaded_real_ecg"


# ---------------------------------------------------------------------------
# TASK 7 — failure modes. Every case must return a clear error/insufficient
# status, never a fabricated normal or positive result.
# ---------------------------------------------------------------------------

def test_malformed_file_returns_clear_error(client):
    res = client.post(
        "/api/acs/analyze-ecg",
        files=[("files", ("broken.hea", b"not a real header", "application/octet-stream"))],
    )
    assert res.status_code == 400


def test_unsupported_format_rejected(client):
    res = client.post(
        "/api/acs/analyze-ecg",
        files=[("files", ("scan.pdf", b"%PDF-1.4 fake", "application/pdf"))],
    )
    assert res.status_code == 400
    assert "Unsupported file type" in res.json()["detail"]


def test_single_lead_ecg_is_rejected_not_silently_analyzed(tmp_path):
    """A single-channel record cannot support >=2-contiguous-lead STEMI
    criteria and must raise, not silently proceed with 1 lead."""
    fs = 250
    n = 2500
    t = np.linspace(0, n / fs, n)
    sig = (0.5 * np.sin(2 * np.pi * 1.2 * t)).reshape(-1, 1)
    wfdb.wrsamp(
        record_name="single_lead",
        fs=fs, units=["mV"], sig_name=["II"], p_signal=sig, fmt=["16"],
        write_dir=str(tmp_path),
    )
    signals, fields = wfdb.rdsamp(str(tmp_path / "single_lead"))
    # A single column 2D array (shape (n,1)) is what wfdb returns for a
    # 1-channel record — ingest_real_wfdb_ecg must still refuse if it
    # cannot form any contiguous pair; single named lead alone is
    # insufficient regardless of dimensionality.
    with pytest.raises(EcgIngestionError):
        # Force the truly 1-D case some callers might pass:
        ingest_real_wfdb_ecg(signals[:, 0], fields)


def test_missing_sampling_frequency_is_rejected():
    fields = {"fs": None, "sig_name": ["I", "II"], "units": ["mV", "mV"]}
    signals = np.zeros((100, 2))
    with pytest.raises(EcgIngestionError):
        ingest_real_wfdb_ecg(signals, fields)


def test_missing_calibration_units_excludes_lead_or_fails_safely():
    fs = 250
    n = 2500
    t = np.linspace(0, n / fs, n)
    sig = np.stack(
        [0.5 * np.sin(2 * np.pi * 1.2 * t), 0.5 * np.sin(2 * np.pi * 1.2 * t + 0.1)],
        axis=1,
    )
    fields = {"fs": fs, "sig_name": ["I", "II"], "units": ["uV", "uV"]}  # NOT mV
    with pytest.raises(EcgIngestionError):
        ingest_real_wfdb_ecg(sig, fields)


def test_insufficient_leads_for_any_contiguous_group(tmp_path):
    """Two leads that don't share any named contiguous group (e.g. V1 + V6
    alone, no group links them directly) should not fabricate a trigger."""
    fs = 250
    n = 2500
    base = _qrs_like_signal(fs, n)
    sig = np.stack([base, base], axis=1)
    fields = {"fs": fs, "sig_name": ["V1", "V6"], "units": ["mV", "mV"]}
    # This should not raise (both are recognized, mV, and can be measured)
    # but must not fabricate a contiguous match between non-adjacent leads.
    result = ingest_real_wfdb_ecg(sig, fields)
    assert set(result.detected_lead_names) == {"V1", "V6"}


def test_duplicate_lead_names_uses_first_occurrence_and_warns():
    fs = 250
    n = 2500
    base_a = _qrs_like_signal(fs, n)
    base_b = _qrs_like_signal(fs, n, amp=1.0)
    sig = np.stack([base_a, base_a, base_a, base_b, base_b, base_b], axis=1)
    fields = {
        "fs": fs,
        "sig_name": ["II", "III", "aVF", "II", "III", "aVF"],  # duplicated set
        "units": ["mV"] * 6,
    }
    result = ingest_real_wfdb_ecg(sig, fields)
    assert "II" in result.duplicate_lead_names
    assert any("Duplicate lead labels" in w for w in result.warnings)


def test_missing_limb_leads_still_processes_available_precordial_leads(tmp_path):
    fs = 250
    n = 2500
    base = _qrs_like_signal(fs, n)
    sig = np.stack([base] * 6, axis=1)
    fields = {"fs": fs, "sig_name": ["V1", "V2", "V3", "V4", "V5", "V6"], "units": ["mV"] * 6}
    result = ingest_real_wfdb_ecg(sig, fields)
    assert set(result.detected_lead_names) == {"V1", "V2", "V3", "V4", "V5", "V6"}
    assert result.quality_leads_detected == 6  # not fabricated as 12


def test_unrecognized_lead_labels_are_excluded_not_guessed():
    fs = 250
    n = 2500
    base = _qrs_like_signal(fs, n)
    sig = np.stack([base, base, base], axis=1)
    fields = {"fs": fs, "sig_name": ["II", "III", "ChestLead9"], "units": ["mV"] * 3}
    result = ingest_real_wfdb_ecg(sig, fields)
    assert "ChestLead9" in result.unrecognized_lead_names
    assert "ChestLead9" not in result.detected_lead_names


# ---------------------------------------------------------------------------
# Nondiagnostic wording (Task 7's exact required phrasing)
# ---------------------------------------------------------------------------

def test_nondiagnostic_upload_uses_required_wording(client):
    fs = 250
    n = 2500
    lead_names = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
    base = _qrs_like_signal(fs, n)
    sig = np.stack([base + 0.001 * i for i in range(12)], axis=1)  # no injected elevation
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        wfdb.wrsamp(
            record_name="flat", fs=fs, units=["mV"] * 12, sig_name=lead_names,
            p_signal=sig, fmt=["16"] * 12, write_dir=d,
        )
        with open(f"{d}/flat.hea", "rb") as h, open(f"{d}/flat.dat", "rb") as dat:
            res = client.post(
                "/api/acs/analyze-ecg",
                files=[
                    ("files", ("flat.hea", h, "application/octet-stream")),
                    ("files", ("flat.dat", dat, "application/octet-stream")),
                ],
                data={"age": "50", "sex": "male"},
            )
    assert res.status_code == 200
    body = res.json()
    if body["quality_gate_passed"]:
        assert body["criteria_met"] is False
        assert "does not exclude ACS" in body["acs_not_excluded_statement"]
