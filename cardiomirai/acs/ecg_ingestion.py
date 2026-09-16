"""
Cardio MIRAI ACS — real ECG ingestion.

RESEARCH PROTOTYPE. NOT A MEDICAL DEVICE. NOT FOR CLINICAL USE.

This module converts a genuinely uploaded, genuinely parsed WFDB ECG record
into inputs for the ACS Core deterministic engine (cardiomirai/acs/core.py).

It does NOT implement any new signal processing. Every measurement here is
computed by calling `extract_basic_ecg_measurements` in `cardiomirai/api.py`
— the existing, already-implemented, already-tested ST-segment/QRS/LVH/BBB
measurement engine that has been running in production for the AF/Atrial
Health endpoint. This module's only job is:

1. Normalize lead names from whatever a WFDB header declares to the
   standard 12-lead names the ACS Core engine expects.
2. Convert millivolt ST measurements to millimetres (the unit ACS Core's
   guideline thresholds are stated in) using the standard clinical
   calibration (1 mV = 10 mm), with an explicit unit check first — this is
   a unit conversion of a real measurement, not a fabrication.
3. Apply per-lead quality gating so a noisy/absent lead is excluded rather
   than silently measured anyway.
4. Surface known STEMI mimics (LVH, LBBB, RBBB) that the existing
   measurement engine already detects, so the ACS-CORE-003 safeguard can
   act on them automatically for a real upload.
5. Refuse — with a clear, specific error — rather than proceed, whenever
   the input is inadequate (missing sampling frequency, non-mV units,
   too few detected beats, too few usable leads).

The import of cardiomirai.api is deliberately deferred (inside the
function body, not at module load time) because cardiomirai/api.py itself
imports this package's router at import time (see the "ACS research-
prototype module" mount point in cardiomirai/api.py) — a top-level import
here would be circular. By the time any request actually reaches this
module, cardiomirai.api has already finished importing, so the deferred
import resolves cleanly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .core import LeadMeasurement, MimicFlags

# Standard clinical ECG calibration: 1 mV = 10 mm at standard gain (10 mm/mV).
# This is the unit ACS Core's guideline thresholds are stated in (Fourth/
# Fifth Universal Definition, ACC/AHA 2025 Table 3, ESC 2023 all state
# thresholds in mm). Only applied after confirming the source unit is mV.
MM_PER_MV = 10.0

# Matches the threshold already used elsewhere in cardiomirai/api.py
# (_usable_lead_count) for "is this lead's signal usable at all" — reused
# here for consistency rather than inventing a second quality threshold.
MIN_LEAD_QUALITY = 35.0

MIN_QRS_BEATS_REQUIRED = 3

_LEAD_ALIASES = {
    "I": "I", "II": "II", "III": "III",
    "AVR": "aVR", "AVL": "aVL", "AVF": "aVF",
    "V1": "V1", "V2": "V2", "V3": "V3", "V4": "V4", "V5": "V5", "V6": "V6",
}


def normalize_lead_name(raw_name: str) -> Optional[str]:
    """Maps a WFDB-declared lead label to a canonical 12-lead name, or
    returns None if unrecognized. Does not guess — an unrecognized label
    is reported as unrecognized, never mapped to a plausible-looking lead."""
    if not raw_name:
        return None
    key = raw_name.strip().upper().replace(" ", "")
    return _LEAD_ALIASES.get(key)


@dataclass
class RealEcgIngestionResult:
    lead_measurements: list[LeadMeasurement]
    mimics: MimicFlags
    detected_lead_names: list[str]           # canonical names successfully matched
    unrecognized_lead_names: list[str]       # raw names that didn't map to any of the 12
    duplicate_lead_names: list[str]          # canonical names that appeared more than once
    excluded_low_quality_leads: list[str]    # canonical names dropped for poor signal quality
    sampling_frequency_hz: float
    duration_seconds: float
    heart_rate_bpm: Optional[float]
    qrs_beat_count: int
    quality_leads_detected: int              # count of the 12 standard leads usably present
    quality_calibration_available: bool
    quality_signal_suitable: bool
    quality_lead_labels_identified: bool
    warnings: list[str]


class EcgIngestionError(ValueError):
    """Raised when the uploaded ECG cannot be safely processed. Callers
    must surface this as a clear error, never fall back to synthetic or
    demo data."""


def measure_array_to_lead_inputs(
    array: np.ndarray,
    fs: float,
    canonical_by_index: dict,
) -> tuple[list[LeadMeasurement], MimicFlags, Optional[float], int, list[str], list[str]]:
    """
    Shared core: given an already physically-calibrated (mV) waveform array
    and a mapping of column-index -> canonical 12-lead name (already
    normalized and unit-checked by the caller), run it through the SAME
    existing ECG Core measurement function used everywhere else in this
    repository, and convert the result into ACS Core inputs.

    Used by both the real-WFDB path (ingest_real_wfdb_ecg, below) and the
    image/PDF digitization path (cardiomirai/acs/image_ingestion.py) — one
    measurement path, two ingestion sources, exactly as instructed ("do not
    build another clinical ECG interpretation algorithm").

    Returns (lead_measurements, mimics, heart_rate_bpm, qrs_beat_count,
    excluded_low_quality_leads, warnings). Raises EcgIngestionError if too
    few QRS beats are detected or no lead survives quality filtering.
    """
    from cardiomirai import api as core_api  # deferred: see module docstring

    warnings: list[str] = []

    lead_names_for_measurement = [None] * array.shape[1]
    for idx, canonical in canonical_by_index.items():
        lead_names_for_measurement[idx] = canonical
    lead_names_for_measurement = [
        name or f"unrecognized_{i}" for i, name in enumerate(lead_names_for_measurement)
    ]

    measurements = core_api.extract_basic_ecg_measurements(
        array, fs, lead_names_for_measurement, sex=None
    )

    qrs_beat_count = int(measurements.get("heart_rate", {}).get("r_peak_count", 0))
    if qrs_beat_count < MIN_QRS_BEATS_REQUIRED:
        raise EcgIngestionError(
            f"Only {qrs_beat_count} QRS complex(es) detected — at least "
            f"{MIN_QRS_BEATS_REQUIRED} are required to compute a reliable "
            "J-point-anchored ST measurement. The recording may be too short, "
            "too noisy, or not a genuine ECG waveform."
        )

    heart_rate_bpm = measurements.get("heart_rate", {}).get("heart_rate_bpm")

    st_segment = measurements.get("st_segment", {})
    st_by_lead = {
        item["lead"]: item["st_level_mv"] for item in st_segment.get("lead_measurements", [])
    }

    lead_measurements: list[LeadMeasurement] = []
    excluded_low_quality: list[str] = []
    for idx, canonical in canonical_by_index.items():
        column = array[:, idx]
        quality = core_api._lead_quality(column)
        if quality < MIN_LEAD_QUALITY:
            excluded_low_quality.append(canonical)
            continue
        st_mv = st_by_lead.get(canonical)
        if st_mv is None:
            continue  # assess_st_segment itself could not measure this lead
        if st_mv >= 0:
            lead_measurements.append(
                LeadMeasurement(lead=canonical, st_elevation_mm=round(st_mv * MM_PER_MV, 2))
            )
        else:
            lead_measurements.append(
                LeadMeasurement(
                    lead=canonical,
                    st_elevation_mm=0.0,
                    reciprocal_depression_mm=round(abs(st_mv) * MM_PER_MV, 2),
                )
            )

    if excluded_low_quality:
        warnings.append(f"Excluded leads with poor signal quality: {sorted(excluded_low_quality)}")

    if not lead_measurements:
        raise EcgIngestionError(
            "No lead produced a usable ST measurement after quality filtering. "
            "Cannot proceed without fabricating a value."
        )

    lvh_status = measurements.get("lvh", {}).get("status", "")
    bbb_status = measurements.get("bbb", {}).get("status", "")
    mimics = MimicFlags(
        lvh=(lvh_status == "LVH criteria met"),
        lbbb=("LBBB-like" in bbb_status),
        rbbb=("RBBB-like" in bbb_status),
    )
    if mimics.lvh:
        warnings.append("LVH criteria met on real measurement — ACS-CORE-003 correlation flag will apply.")
    if mimics.lbbb or mimics.rbbb:
        warnings.append(f"Bundle branch block pattern detected ({bbb_status}) — ACS-CORE-003 correlation flag will apply.")

    return lead_measurements, mimics, heart_rate_bpm, qrs_beat_count, excluded_low_quality, warnings


def ingest_real_wfdb_ecg(signals, fields: dict) -> RealEcgIngestionResult:
    """
    Convert a loaded WFDB record (as returned by wfdb.rdsamp / this repo's
    wfdb_loader.load_wfdb_pair) into ACS Core inputs.

    Raises EcgIngestionError for any condition that would otherwise require
    fabricating a measurement — missing sampling frequency, no recognized
    standard leads, non-mV units on every lead, or too few detected beats
    to trust a rhythm/QRS-anchored ST measurement.
    """
    warnings: list[str] = []

    array = np.asarray(signals, dtype=float)
    fs = fields.get("fs")
    if not fs or fs <= 0:
        raise EcgIngestionError(
            "Sampling frequency is missing or invalid in the uploaded ECG's header. "
            "Cannot compute time-based measurements without it."
        )
    fs = float(fs)

    raw_lead_names = list(fields.get("sig_name", []))
    raw_units = list(fields.get("units", []))
    if array.ndim == 1:
        raise EcgIngestionError(
            "Only a single signal channel was found. A 12-lead ECG requires "
            "multiple named leads; a single-channel record cannot be assessed "
            "for STEMI criteria, which require >=2 contiguous leads."
        )

    duration_seconds = array.shape[0] / fs if fs else 0.0

    # --- Lead-name normalization -----------------------------------------
    canonical_by_index: dict[int, str] = {}
    unrecognized: list[str] = []
    seen_canonical: dict[str, int] = {}
    duplicates: list[str] = []

    for idx, raw_name in enumerate(raw_lead_names):
        canonical = normalize_lead_name(raw_name)
        if canonical is None:
            unrecognized.append(raw_name)
            continue
        if canonical in seen_canonical:
            duplicates.append(canonical)
            continue  # keep the first occurrence only; never average/guess
        seen_canonical[canonical] = idx
        canonical_by_index[idx] = canonical

    if not canonical_by_index:
        raise EcgIngestionError(
            "None of the uploaded ECG's lead labels could be recognized as "
            "standard 12-lead names (I, II, III, aVR, aVL, aVF, V1-V6). "
            f"Raw labels found: {raw_lead_names!r}."
        )
    if unrecognized:
        warnings.append(f"Unrecognized lead labels ignored: {sorted(set(unrecognized))}")
    if duplicates:
        warnings.append(
            f"Duplicate lead labels found for {sorted(set(duplicates))}; "
            "only the first occurrence of each was used."
        )

    # --- Unit check (per matched lead) ------------------------------------
    non_mv_leads = []
    for idx, canonical in list(canonical_by_index.items()):
        unit = raw_units[idx].strip().lower() if idx < len(raw_units) and raw_units[idx] else None
        if unit not in ("mv", "millivolt", "millivolts"):
            non_mv_leads.append((canonical, unit))
            del canonical_by_index[idx]  # exclude rather than guess a scale factor

    if non_mv_leads:
        warnings.append(
            "Excluded leads with non-millivolt or unspecified units (refusing to "
            f"guess a scale factor): {non_mv_leads}"
        )
    if not canonical_by_index:
        raise EcgIngestionError(
            "No lead had a recognized millivolt unit after filtering. Cannot "
            "safely convert amplitudes to millimetres without a confirmed unit."
        )

    lead_measurements, mimics, heart_rate_bpm, qrs_beat_count, excluded_low_quality, measure_warnings = (
        measure_array_to_lead_inputs(array, fs, canonical_by_index)
    )
    warnings.extend(measure_warnings)

    quality_leads_detected = len(lead_measurements) + len(excluded_low_quality)
    # "detected" for the quality-gate display counts leads that were at
    # least identifiable and unit-valid, even if later excluded for quality
    # — the gate's own failure_reasons() will explain why fewer than 12
    # produced usable measurements.
    quality_calibration_available = True  # confirmed by the unit check above
    quality_signal_suitable = len(lead_measurements) > 0
    quality_lead_labels_identified = len(canonical_by_index) >= 1 and not unrecognized

    return RealEcgIngestionResult(
        lead_measurements=lead_measurements,
        mimics=mimics,
        detected_lead_names=sorted(canonical_by_index.values()),
        unrecognized_lead_names=sorted(set(unrecognized)),
        duplicate_lead_names=sorted(set(duplicates)),
        excluded_low_quality_leads=sorted(excluded_low_quality),
        sampling_frequency_hz=fs,
        duration_seconds=round(duration_seconds, 2),
        heart_rate_bpm=heart_rate_bpm,
        qrs_beat_count=qrs_beat_count,
        quality_leads_detected=quality_leads_detected,
        quality_calibration_available=quality_calibration_available,
        quality_signal_suitable=quality_signal_suitable,
        quality_lead_labels_identified=quality_lead_labels_identified,
        warnings=warnings,
    )
