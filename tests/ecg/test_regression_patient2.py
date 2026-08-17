import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="module")
def client():
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    from cardiomirai.api import app
    return fastapi_testclient.TestClient(app)


@pytest.fixture(scope="module")
def patient2_response(client):
    with open(FIXTURES / "rec_2.hea", "rb") as hea, open(FIXTURES / "rec_2.dat", "rb") as dat:
        files = [
            ("files", ("rec_2.hea", hea.read(), "application/octet-stream")),
            ("files", ("rec_2.dat", dat.read(), "application/octet-stream")),
        ]
    response = client.post("/api/analyze-wfdb", files=files, data={"age": 21, "sex": "male"})
    assert response.status_code == 200
    return response.json()


def test_patient2_beat_count_improved(patient2_response):
    # Was 19 before the fix; target was ~21-22. Landed at 20 with one gap
    # transparently declined due to insufficient morphological evidence --
    # this is documented, not silently accepted as a full match to target.
    assert patient2_response["qrs_count"] >= 20
    assert patient2_response["qrs_detection_detail"]["recovered"] >= 1


def test_patient2_heart_rate_no_longer_57(patient2_response):
    hr = patient2_response["rr_features"]["heart_rate_bpm"]
    assert hr > 58.0  # was 57.1
    assert 55.0 <= hr <= 70.0  # plausible physiological range for this recording


def test_patient2_rhythm_is_sinus_arrhythmia(patient2_response):
    assert patient2_response["atrial_health"]["current_rhythm"]["value"] == "sinus arrhythmia"


def test_patient2_af_evidence_not_high(patient2_response):
    category = patient2_response["atrial_health"]["current_af_evidence"]["category"]
    assert category != "high"  # was effectively "high" (69%) before the fix


def test_patient2_af_evidence_is_categorical_not_bare_probability(patient2_response):
    af = patient2_response["atrial_health"]["current_af_evidence"]
    assert af["category"] in {"low", "intermediate", "high"}
    assert "not a validated probability" in af["method"]


def test_patient2_atrial_remodeling_preserved_and_separate(patient2_response):
    atrial_health = patient2_response["atrial_health"]
    assert atrial_health["atrial_remodeling"]["status"] == "available"
    assert atrial_health["atrial_remodeling"]["method"] == "PTB-XL trained model (unchanged)"
    # Must be a distinct field/value from current_af_evidence -- not the same concept
    assert "category" not in atrial_health["atrial_remodeling"]


def test_patient2_future_af_risk_is_unavailable_placeholder(patient2_response):
    assert patient2_response["atrial_health"]["future_af_risk"]["status"] == "unavailable"
    assert patient2_response["atrial_health"]["future_af_risk"]["value"] is None


def test_patient2_unique_lead_count_is_one(patient2_response):
    # Patient 2's header lists 2 channels ("ECG I", "ECG I filtered") but they
    # are the same physical lead.
    assert patient2_response["unique_lead_count"] == 1
    assert patient2_response["unique_leads"] == ["I"]
    assert patient2_response["is_duplicate_channel_set"] is True


def test_patient2_stemi_unavailable_not_false_negative(patient2_response):
    stemi = patient2_response["advanced_ecg_interpretation"]["stemi"]
    assert "not available" in stemi["status"].lower()
    assert stemi["status"] != "No STEMI criteria met by research rules"


def test_patient2_axes_unavailable_not_fabricated(patient2_response):
    axes = patient2_response["advanced_ecg_interpretation"]["axes"]
    for axis_name in ("p_axis", "qrs_axis", "t_axis"):
        assert axes[axis_name]["classification"] == "unavailable"
        assert axes[axis_name]["axis_deg"] is None


def test_patient2_chamber_enlargement_unavailable_not_false_negative(patient2_response):
    chamber = patient2_response["advanced_ecg_interpretation"]["chamber_enlargement"]
    assert chamber["right_atrial_enlargement"] == "unavailable"
    assert chamber["biatrial_enlargement"] == "unavailable"
    assert chamber["lvh"]["status"] == "unavailable"


def test_patient2_heart_age_placeholder_only(patient2_response):
    heart_age = patient2_response["heart_age"]
    assert heart_age["status"] == "unavailable"
    assert heart_age["value"] is None


def test_patient2_deterministic(client):
    with open(FIXTURES / "rec_2.hea", "rb") as hea, open(FIXTURES / "rec_2.dat", "rb") as dat:
        files = [
            ("files", ("rec_2.hea", hea.read(), "application/octet-stream")),
            ("files", ("rec_2.dat", dat.read(), "application/octet-stream")),
        ]
    r1 = client.post("/api/analyze-wfdb", files=files, data={"age": 21, "sex": "male"}).json()
    with open(FIXTURES / "rec_2.hea", "rb") as hea, open(FIXTURES / "rec_2.dat", "rb") as dat:
        files = [
            ("files", ("rec_2.hea", hea.read(), "application/octet-stream")),
            ("files", ("rec_2.dat", dat.read(), "application/octet-stream")),
        ]
    r2 = client.post("/api/analyze-wfdb", files=files, data={"age": 21, "sex": "male"}).json()
    assert r1["qrs_count"] == r2["qrs_count"]
    assert r1["atrial_health"]["current_af_evidence"]["category"] == r2["atrial_health"]["current_af_evidence"]["category"]
