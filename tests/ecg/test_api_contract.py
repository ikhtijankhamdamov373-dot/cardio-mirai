"""Structural API-contract tests -- properties that must hold for ANY valid
ECG analysis response, independent of which specific case produced it.
Per-case clinical expectations (rhythm, HR range, AF category, etc.) live
in test_regression_suite.py's manifest-driven cases instead.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "cases" / "patient_002"


@pytest.fixture(scope="module")
def client():
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    from cardiomirai.api import app
    return fastapi_testclient.TestClient(app)


def _analyze(client):
    with open(FIXTURE_DIR / "rec_2.hea", "rb") as hea, open(FIXTURE_DIR / "rec_2.dat", "rb") as dat:
        files = [
            ("files", ("rec_2.hea", hea.read(), "application/octet-stream")),
            ("files", ("rec_2.dat", dat.read(), "application/octet-stream")),
        ]
        return client.post("/api/analyze-wfdb", files=files, data={"age": 21, "sex": "male"}).json()


def test_result_is_deterministic(client):
    r1 = _analyze(client)
    r2 = _analyze(client)
    assert r1["qrs_count"] == r2["qrs_count"]
    assert r1["atrial_health"]["current_af_evidence"]["category"] == r2["atrial_health"]["current_af_evidence"]["category"]
    assert r1["rr_features"]["heart_rate_bpm"] == r2["rr_features"]["heart_rate_bpm"]


def test_af_evidence_and_atrial_remodeling_are_structurally_separate(client):
    """The whole point of Priority 7: these must never be presented as, or
    collapsible into, the same field."""
    atrial_health = _analyze(client)["atrial_health"]
    af = atrial_health["current_af_evidence"]
    remodeling = atrial_health["atrial_remodeling"]
    assert "category" in af and "category" not in remodeling
    assert af.get("method", "") != remodeling.get("method", "")
    assert "not a validated probability" in af["method"]
    assert "PTB-XL" in remodeling["method"]


def test_future_af_risk_is_always_a_placeholder(client):
    future_risk = _analyze(client)["atrial_health"]["future_af_risk"]
    assert future_risk["status"] == "unavailable"
    assert future_risk["value"] is None


def test_heart_age_is_placeholder_only_never_a_fabricated_score(client):
    heart_age = _analyze(client)["heart_age"]
    assert heart_age["status"] == "unavailable"
    assert heart_age["value"] is None
    assert "coming soon" in heart_age["note"].lower()


def test_legacy_af_fields_still_present_for_backward_compatibility(client):
    result = _analyze(client)
    assert "af_detection_score" in result
    assert "af_probability" in result
    assert isinstance(result["af_detection_score"], (int, float))
