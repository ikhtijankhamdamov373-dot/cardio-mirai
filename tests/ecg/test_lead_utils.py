import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cardiomirai.ecg.lead_utils import (
    canonicalize_lead_name,
    has_unique_leads,
    unique_lead_count,
    unique_lead_names,
)


def test_duplicate_filtered_channel_collapses_to_one_lead():
    # Exactly Patient 2's real header: "ECG I" + "ECG I filtered"
    assert unique_lead_names(["ECG I", "ECG I filtered"]) == ["I"]
    assert unique_lead_count(["ECG I", "ECG I filtered"]) == 1


def test_full_12_lead_set_stays_12_unique():
    leads = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
    assert unique_lead_count(leads) == 12
    assert unique_lead_names(leads) == leads


def test_mit_bih_style_alias_recognized():
    assert canonicalize_lead_name("MLII") == "II"


def test_has_unique_leads_reports_missing():
    ok, missing = has_unique_leads(["ECG I", "ECG I filtered"], {"I", "aVF"})
    assert ok is False
    assert missing == {"aVF"}
    ok2, missing2 = has_unique_leads(["I", "aVF"], {"I", "aVF"})
    assert ok2 is True
    assert missing2 == set()
