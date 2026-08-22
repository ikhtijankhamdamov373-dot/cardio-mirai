"""Cardio MIRAI growing ECG validation suite.

Each subfolder under fixtures/cases/ is one clinical case: WFDB record
files plus a case.json manifest of QUALITATIVE expectations (ranges and
categories, not brittle exact values -- consistent with "do not hardcode
these values" from the Patient 2 investigation). Optional real .atr
annotations, when present, are used for objective R-peak sensitivity and
T-wave-false-positive checks against ground truth, not just plausibility.

To add a new case later: drop <record>.hea/.dat(/.atr) and a case.json
into a new fixtures/cases/<case_id>/ folder. No test code changes needed
-- this file auto-discovers every case.json under fixtures/cases/.

The intent (explicitly requested): every future engine version must keep
passing every case ever added here, not just the newest one -- so a
change that fixes one rhythm type can't silently regress another without
being caught immediately.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cases"


def _discover_cases() -> list[Path]:
    if not FIXTURES.exists():
        return []
    return sorted(FIXTURES.glob("*/case.json"))


CASE_MANIFESTS = _discover_cases()
CASE_IDS = [str(p.parent.name) for p in CASE_MANIFESTS]


@pytest.fixture(scope="module")
def client():
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    from cardiomirai.api import app
    return fastapi_testclient.TestClient(app)


def _load_manifest(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def _post_case(client, case_dir: Path, manifest: dict) -> dict:
    record = manifest["record"]
    hea_path = case_dir / f"{record}.hea"
    dat_path = case_dir / f"{record}.dat"
    demographics = manifest.get("demographics", {})
    with open(hea_path, "rb") as hea, open(dat_path, "rb") as dat:
        files = [
            ("files", (hea_path.name, hea.read(), "application/octet-stream")),
            ("files", (dat_path.name, dat.read(), "application/octet-stream")),
        ]
    response = client.post("/api/analyze-wfdb", files=files, data=demographics)
    assert response.status_code == 200, f"{manifest['case_id']}: analysis failed: {response.text[:500]}"
    return response.json()


# Maps a manifest "lead_gated_unavailable" entry to a (getter, unavailable-check) pair.
_LEAD_GATE_CHECKS = {
    "stemi": lambda r: "not available" in r["advanced_ecg_interpretation"]["stemi"]["status"].lower(),
    "qrs_axis": lambda r: r["advanced_ecg_interpretation"]["axes"]["qrs_axis"]["classification"] == "unavailable",
    "p_axis": lambda r: r["advanced_ecg_interpretation"]["axes"]["p_axis"]["classification"] == "unavailable",
    "t_axis": lambda r: r["advanced_ecg_interpretation"]["axes"]["t_axis"]["classification"] == "unavailable",
    "chamber_atrial_enlargement": lambda r: r["advanced_ecg_interpretation"]["chamber_enlargement"]["right_atrial_enlargement"] == "unavailable",
    "lvh": lambda r: r["advanced_ecg_interpretation"]["chamber_enlargement"]["lvh"]["status"] == "unavailable",
    "bbb": lambda r: r["advanced_ecg_interpretation"]["bundle_branch_block"].get("status") == "unavailable",
    "ischemia": lambda r: r["advanced_ecg_interpretation"]["ischemia_status"]["status"] == "unavailable",
    "infarction": lambda r: r["advanced_ecg_interpretation"]["infarction_status"]["status"] == "unavailable",
}


@pytest.mark.parametrize("manifest_path", CASE_MANIFESTS, ids=CASE_IDS)
def test_case_qualitative_expectations(client, manifest_path):
    manifest = _load_manifest(manifest_path)
    case_dir = manifest_path.parent
    result = _post_case(client, case_dir, manifest)
    exp = manifest.get("expectations", {})
    case_id = manifest["case_id"]

    if "qrs_count" in exp:
        lo, hi = exp["qrs_count"]["min"], exp["qrs_count"]["max"]
        assert lo <= result["qrs_count"] <= hi, f"{case_id}: qrs_count {result['qrs_count']} outside [{lo},{hi}]"

    if "heart_rate_bpm" in exp:
        hr = result["rr_features"]["heart_rate_bpm"]
        lo, hi = exp["heart_rate_bpm"]["min"], exp["heart_rate_bpm"]["max"]
        assert hr is not None and lo <= hr <= hi, f"{case_id}: heart_rate_bpm {hr} outside [{lo},{hi}]"

    if "rhythm_primary_contains" in exp:
        primary = result["atrial_health"]["current_rhythm"]["value"] or ""
        assert exp["rhythm_primary_contains"] in primary, f"{case_id}: rhythm '{primary}' does not contain '{exp['rhythm_primary_contains']}'"

    if "af_evidence_category_not" in exp:
        category = result["atrial_health"]["current_af_evidence"]["category"]
        assert category not in exp["af_evidence_category_not"], f"{case_id}: af_evidence category '{category}' was disallowed"

    if "af_evidence_category_is" in exp:
        category = result["atrial_health"]["current_af_evidence"]["category"]
        assert category == exp["af_evidence_category_is"], f"{case_id}: af_evidence category '{category}' != expected '{exp['af_evidence_category_is']}'"

    if "unique_lead_count" in exp:
        assert result["unique_lead_count"] == exp["unique_lead_count"], f"{case_id}: unique_lead_count mismatch"

    if "unique_leads" in exp:
        assert result["unique_leads"] == exp["unique_leads"], f"{case_id}: unique_leads mismatch"

    if "is_duplicate_channel_set" in exp:
        assert result["is_duplicate_channel_set"] == exp["is_duplicate_channel_set"], f"{case_id}: is_duplicate_channel_set mismatch"

    if "atrial_remodeling_status" in exp:
        assert result["atrial_health"]["atrial_remodeling"]["status"] == exp["atrial_remodeling_status"], f"{case_id}: atrial_remodeling status mismatch"

    for gate_key in exp.get("lead_gated_unavailable", []):
        checker = _LEAD_GATE_CHECKS.get(gate_key)
        assert checker is not None, f"{case_id}: unknown lead_gated_unavailable key '{gate_key}' -- add it to _LEAD_GATE_CHECKS"
        assert checker(result), f"{case_id}: expected '{gate_key}' to be gated unavailable, but it wasn't"


@pytest.mark.parametrize("manifest_path", CASE_MANIFESTS, ids=CASE_IDS)
def test_case_annotation_validation(client, manifest_path):
    """Only runs meaningful checks for cases that ship real .atr ground truth."""
    manifest = _load_manifest(manifest_path)
    case_dir = manifest_path.parent
    av = manifest.get("annotation_validation")
    atr_path = case_dir / f"{manifest['record']}.atr"
    if not av or not atr_path.exists():
        pytest.skip(f"{manifest['case_id']}: no annotation_validation block or no .atr file")

    wfdb = pytest.importorskip("wfdb")
    from cardiomirai.ecg.qrs_detection import detect_qrs
    from cardiomirai.api import _pick_lead

    record = wfdb.rdrecord(str(case_dir / manifest["record"]))
    ann = wfdb.rdann(str(case_dir / manifest["record"]), "atr")
    true_beats = np.array([s for s, sym in zip(ann.sample, ann.symbol) if sym == av["atr_symbol_true_beat"]])
    true_t_waves = np.array([s for s, sym in zip(ann.sample, ann.symbol) if sym == av.get("atr_symbol_t_wave")]) if av.get("atr_symbol_t_wave") else np.array([])

    lead, _selected, _usable = _pick_lead(record.p_signal, record.sig_name)
    result = detect_qrs(lead, record.fs)
    detected = result.peak_samples

    if true_beats.size:
        tol = int(av["r_peak_match_tolerance_ms"] / 1000.0 * record.fs)
        window_end = true_beats.max() + tol
        detected_in_window = detected[detected <= window_end]
        matched = sum(1 for t in true_beats if np.any(np.abs(detected_in_window - t) <= tol))
        sensitivity = matched / len(true_beats)
        min_sens = av.get("min_r_peak_sensitivity_in_annotated_window", 1.0)
        assert sensitivity >= min_sens, f"{manifest['case_id']}: annotated-window R-peak sensitivity {sensitivity:.3f} below required {min_sens}"

    if true_t_waves.size:
        tol_t = int(av["t_wave_false_positive_tolerance_ms"] / 1000.0 * record.fs)
        false_matches = [t for t in true_t_waves if np.any(np.abs(detected - t) <= tol_t)]
        max_allowed = av.get("max_t_wave_false_positives", 0)
        assert len(false_matches) <= max_allowed, f"{manifest['case_id']}: {len(false_matches)} T-waves misclassified as QRS (max allowed {max_allowed})"


def test_at_least_one_case_registered():
    """Sanity check that the suite itself is wired up correctly."""
    assert len(CASE_MANIFESTS) >= 1, "No cases found under tests/ecg/fixtures/cases/ -- suite is not actually running anything"
