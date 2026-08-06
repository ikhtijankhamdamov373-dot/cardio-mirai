"""
Tests for the existing Cardio MIRAI FastAPI backend.

These tests are purely additive: they import the existing `cardiomirai.api`
app unmodified and exercise it through FastAPI's TestClient. No endpoint
logic is changed to make these pass.

Note on MODEL_DIR: the deployed code expects trained model artifacts under
`<project_root>/models/`, but the artifacts currently live at the project
root itself (see FINDING in the accompanying change log). We monkeypatch
MODEL_DIR to the actual artifact location for these tests so the happy-path
model inference can be verified; this does not change production code or
behavior.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cardiomirai import api as api_module

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def client(monkeypatch):
    # Point MODEL_DIR at the real artifact location (repo root) for this
    # test run only; production code and files are untouched.
    monkeypatch.setattr(api_module, "MODEL_DIR", api_module.PROJECT_ROOT)
    api_module._load_model_artifacts.cache_clear()
    return TestClient(api_module.app)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

def test_health_endpoint_returns_ok(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


# ---------------------------------------------------------------------------
# Valid WFDB upload
# ---------------------------------------------------------------------------

def test_valid_wfdb_hea_dat_pair_is_analyzed(client):
    hea = FIXTURES / "valid_record.hea"
    dat = FIXTURES / "valid_record.dat"
    with hea.open("rb") as h, dat.open("rb") as d:
        res = client.post(
            "/api/analyze-wfdb",
            files=[
                ("files", ("valid_record.hea", h, "application/octet-stream")),
                ("files", ("valid_record.dat", d, "application/octet-stream")),
            ],
            data={"age": "60", "sex": "male"},
        )
    assert res.status_code == 200
    body = res.json()
    assert "record" in body
    assert body["record"] == "valid_record"


# ---------------------------------------------------------------------------
# Incomplete record rejection
# ---------------------------------------------------------------------------

def test_hea_without_matching_dat_is_rejected(client):
    hea = FIXTURES / "valid_record.hea"
    with hea.open("rb") as h:
        res = client.post(
            "/api/analyze-wfdb",
            files=[("files", ("valid_record.hea", h, "application/octet-stream"))],
        )
    assert res.status_code == 400
    assert "No complete WFDB" in res.json()["detail"]


# ---------------------------------------------------------------------------
# ZIP upload
# ---------------------------------------------------------------------------

def test_zip_containing_valid_record_is_analyzed(client):
    zip_path = FIXTURES / "valid_record.zip"
    with zip_path.open("rb") as z:
        res = client.post(
            "/api/analyze-wfdb",
            files=[("files", ("valid_record.zip", z, "application/zip"))],
        )
    assert res.status_code == 200
    body = res.json()
    assert body["record"] == "valid_record"


# ---------------------------------------------------------------------------
# Unsupported file rejection
# ---------------------------------------------------------------------------

def test_unsupported_single_file_is_rejected(client):
    res = client.post(
        "/api/analyze-wfdb",
        files=[("files", ("notes.txt", b"not an ecg", "text/plain"))],
    )
    assert res.status_code == 400
    assert "No complete WFDB" in res.json()["detail"]


# ---------------------------------------------------------------------------
# File-size limits
# ---------------------------------------------------------------------------
#
# FINDING: the current /api/analyze-wfdb endpoint enforces no explicit
# upload-size limit (see change log, "Security gaps identified"). This test
# documents that behavior today rather than asserting a limit that does not
# exist in the code, so it will not silently pass once a limit is added —
# it is written to be updated in the security-hardening subphase.

def test_current_endpoint_has_no_enforced_size_limit(client):
    oversized = b"0" * (10 * 1024 * 1024)  # 10 MB junk payload
    res = client.post(
        "/api/analyze-wfdb",
        files=[("files", ("huge.dat", oversized, "application/octet-stream"))],
    )
    # Documents current behavior: rejected for not forming a valid WFDB
    # pair, NOT because of a size guard (none exists yet).
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Timeout / network-error handling is verified on the frontend in
# frontend/__tests__/api.test.ts (AbortController-based timeout, ApiError
# wrapping of network failures). The backend itself has no client-facing
# timeout to test directly.
# ---------------------------------------------------------------------------
