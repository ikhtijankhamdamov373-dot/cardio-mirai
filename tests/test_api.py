"""
Tests for the existing Cardio MIRAI FastAPI backend.

These tests exercise `cardiomirai.api` through FastAPI's TestClient,
including the Priority 1 (model path resolution) and Priority 2 (upload
security) fixes made directly to `cardiomirai/api.py`.
"""

from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from cardiomirai import api as api_module

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def client():
    return TestClient(api_module.app)


# ---------------------------------------------------------------------------
# Priority 1: model directory resolution
# ---------------------------------------------------------------------------

def test_model_dir_resolves_without_moving_artifacts():
    """The artifacts ship at the project root, not <root>/models/ as the
    README describes. _resolve_model_dir() must find them either way,
    without any file being moved on disk."""
    assert api_module.MODEL_DIR.exists()
    for name in api_module._REQUIRED_MODEL_FILES:
        assert (api_module.MODEL_DIR / name).exists()


def test_model_dir_prefers_documented_models_subfolder(tmp_path, monkeypatch):
    """If a properly populated models/ subfolder exists, it should be
    preferred over the project-root fallback."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    for name in api_module._REQUIRED_MODEL_FILES:
        (models_dir / name).write_text("stub")

    monkeypatch.setattr(api_module, "PROJECT_ROOT", tmp_path)
    resolved = api_module._resolve_model_dir()
    assert resolved == models_dir


def test_model_dir_respects_env_override(tmp_path, monkeypatch):
    custom_dir = tmp_path / "custom-models"
    custom_dir.mkdir()
    for name in api_module._REQUIRED_MODEL_FILES:
        (custom_dir / name).write_text("stub")

    monkeypatch.setenv("CARDIO_MIRAI_MODEL_DIR", str(custom_dir))
    resolved = api_module._resolve_model_dir()
    assert resolved == custom_dir


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
# See test_unsupported_extension_is_rejected_before_saving and
# test_unsupported_single_txt_file_is_rejected below — the Priority 2 fix
# changed this from a generic "no complete record" message to an explicit
# "Unsupported file type" message, rejected before the file is even saved.

# ---------------------------------------------------------------------------
# File-size limits (Priority 2)
# ---------------------------------------------------------------------------

def test_oversized_file_is_rejected_with_413(client, monkeypatch):
    # Use a small limit so the test doesn't need to upload real megabytes.
    monkeypatch.setattr(api_module, "MAX_FILE_SIZE_BYTES", 1024)
    oversized = b"0" * (2048)
    res = client.post(
        "/api/analyze-wfdb",
        files=[("files", ("huge.dat", oversized, "application/octet-stream"))],
    )
    assert res.status_code == 413
    assert "exceeds the maximum allowed size" in res.json()["detail"]


def test_oversized_total_upload_is_rejected_with_413(client, monkeypatch):
    monkeypatch.setattr(api_module, "MAX_FILE_SIZE_BYTES", 10 * 1024 * 1024)
    monkeypatch.setattr(api_module, "MAX_TOTAL_UPLOAD_BYTES", 1024)
    payload = b"0" * 2048
    res = client.post(
        "/api/analyze-wfdb",
        files=[("files", ("a.dat", payload, "application/octet-stream"))],
    )
    assert res.status_code == 413
    assert "Total upload size exceeds" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Unsupported file type rejection (extension allowlist)
# ---------------------------------------------------------------------------

def test_unsupported_extension_is_rejected_before_saving(client):
    res = client.post(
        "/api/analyze-wfdb",
        files=[("files", ("script.exe", b"MZ\x90\x00", "application/octet-stream"))],
    )
    assert res.status_code == 400
    assert "Unsupported file type" in res.json()["detail"]


def test_unsupported_single_txt_file_is_rejected(client):
    res = client.post(
        "/api/analyze-wfdb",
        files=[("files", ("notes.txt", b"not an ecg", "text/plain"))],
    )
    assert res.status_code == 400
    assert "Unsupported file type" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------

def test_path_traversal_filename_is_sanitized_not_written_outside_target():
    unsafe = "../../../etc/passwd.hea"
    safe = api_module._safe_name(unsafe)
    assert "/" not in safe
    assert ".." not in safe
    assert safe == "passwd.hea"


def test_null_byte_in_filename_is_stripped():
    safe = api_module._safe_name("record\x00.hea")
    assert "\x00" not in safe


# ---------------------------------------------------------------------------
# ZIP archive validation and zip-slip protection
# ---------------------------------------------------------------------------

def test_malicious_zip_with_path_traversal_member_is_neutralized(client, tmp_path):
    """A ZIP containing a '../../evil.hea' entry must not be written outside
    the temporary extraction directory."""
    evil_zip = tmp_path / "evil.zip"
    with ZipFile(evil_zip, "w") as zf:
        zf.writestr("../../../../tmp/evil_traversal.hea", "malicious header content")

    with evil_zip.open("rb") as z:
        res = client.post(
            "/api/analyze-wfdb",
            files=[("files", ("evil.zip", z, "application/zip"))],
        )

    # The malicious member is skipped entirely (no matching .dat, and it's
    # not extracted outside the sandbox), so the request fails cleanly with
    # "no complete record" rather than writing files outside the temp dir.
    assert res.status_code == 400
    assert not Path("/tmp/evil_traversal.hea").exists()


def test_invalid_zip_file_returns_clear_400(client):
    res = client.post(
        "/api/analyze-wfdb",
        files=[("files", ("broken.zip", b"not actually a zip file", "application/zip"))],
    )
    assert res.status_code == 400
    assert "not a valid ZIP archive" in res.json()["detail"]


def test_zip_with_too_many_members_is_rejected(client, tmp_path, monkeypatch):
    monkeypatch.setattr(api_module, "MAX_ZIP_MEMBER_COUNT", 2)
    many_zip = tmp_path / "many.zip"
    with ZipFile(many_zip, "w") as zf:
        for i in range(5):
            zf.writestr(f"file_{i}.hea", "x")

    with many_zip.open("rb") as z:
        res = client.post(
            "/api/analyze-wfdb",
            files=[("files", ("many.zip", z, "application/zip"))],
        )
    assert res.status_code == 400
    assert "too many files" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Internal error exposure
# ---------------------------------------------------------------------------

def test_unreadable_record_error_does_not_leak_temp_path(client, tmp_path):
    """A .hea/.dat pair that parses as a pair but fails to load must not
    leak the server's temp-directory path in the response."""
    bad_hea = tmp_path / "broken.hea"
    bad_dat = tmp_path / "broken.dat"
    bad_hea.write_text("not a real wfdb header\n")
    bad_dat.write_bytes(b"\x00\x01\x02")

    with bad_hea.open("rb") as h, bad_dat.open("rb") as d:
        res = client.post(
            "/api/analyze-wfdb",
            files=[
                ("files", ("broken.hea", h, "application/octet-stream")),
                ("files", ("broken.dat", d, "application/octet-stream")),
            ],
        )
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "/tmp" not in detail
    assert str(tmp_path) not in detail


# ---------------------------------------------------------------------------
# Timeout / network-error handling is verified on the frontend in
# frontend/__tests__/api.test.ts (AbortController-based timeout, ApiError
# wrapping of network failures). The backend itself has no client-facing
# timeout to test directly.
# ---------------------------------------------------------------------------
