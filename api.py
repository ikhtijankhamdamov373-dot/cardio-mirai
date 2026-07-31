"""FastAPI backend for Cardio MIRAI WFDB ECG analysis."""

from __future__ import annotations

import json
import logging
import math
import shutil
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable
from zipfile import ZipFile

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .wfdb_loader import find_wfdb_pairs, load_wfdb_pair, wfdb_metadata


app = FastAPI(title="Cardio MIRAI WFDB Backend", version="2.0.0-alpha")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_MISSING_MESSAGE = "Trained PTB-XL model files not found. Please run training script first."
MODEL_TARGET = "current atrial abnormality"
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ModelArtifactsMissing(RuntimeError):
    """Raised when trained PTB-XL model artifacts are unavailable."""


class ModelInferenceError(RuntimeError):
    """Raised when required morphology features cannot be inferred safely."""


def _safe_name(name: str) -> str:
    return Path(name).name.replace("\\", "_").replace("/", "_")


@lru_cache(maxsize=1)
def _load_model_artifacts() -> dict:
    logistic_path = MODEL_DIR / "atrial_logistic_model.pkl"
    gb_path = MODEL_DIR / "atrial_gradient_boosting_model.pkl"
    scaler_path = MODEL_DIR / "feature_scaler.pkl"
    columns_path = MODEL_DIR / "feature_columns.json"
    metadata_path = MODEL_DIR / "model_metadata.json"
    required = [logistic_path, scaler_path, columns_path, metadata_path]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise ModelArtifactsMissing(MODEL_MISSING_MESSAGE)

    with columns_path.open("r", encoding="utf-8") as handle:
        feature_columns = json.load(handle)
    with metadata_path.open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)

    return {
        "logistic_model": joblib.load(logistic_path),
        "gradient_boosting_model": joblib.load(gb_path) if gb_path.exists() else None,
        "scaler": joblib.load(scaler_path),
        "feature_columns": feature_columns,
        "metadata": metadata,
    }


def _parse_demographics_from_fields(fields: dict) -> tuple[float | None, str | None]:
    age: float | None = None
    sex: str | None = None
    for comment in fields.get("comments", []) or []:
        text = str(comment).strip()
        lowered = text.lower()
        if lowered.startswith("age"):
            try:
                age = float(text.split(":", 1)[1].strip())
            except (IndexError, ValueError):
                pass
        if lowered.startswith("sex"):
            try:
                sex = text.split(":", 1)[1].strip().lower()
            except IndexError:
                pass
    return age, sex


def _encode_sex(value: str | None) -> float | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"male", "m", "1"}:
        return 1.0
    if normalized in {"female", "f", "0"}:
        return 0.0
    return None


def _feature_is_missing(value) -> bool:
    if value is None:
        return True
    try:
        return not np.isfinite(float(value))
    except (TypeError, ValueError):
        return True


def _artifact_training_defaults(artifacts: dict) -> dict[str, float]:
    """Return training-time feature fallbacks when saved with the model artifacts."""

    columns = artifacts["feature_columns"]
    metadata_defaults = artifacts["metadata"].get("missing_value_defaults", {}) or {}
    defaults = {
        key: float(value)
        for key, value in metadata_defaults.items()
        if key in columns and not _feature_is_missing(value)
    }

    scaler = artifacts.get("scaler")
    imputer = getattr(scaler, "named_steps", {}).get("imputer") if scaler is not None else None
    statistics = getattr(imputer, "statistics_", None)
    if statistics is not None and len(statistics) == len(columns):
        for column, statistic in zip(columns, statistics):
            if column not in defaults and not _feature_is_missing(statistic):
                defaults[column] = float(statistic)

    return defaults


def _feature_alias_value(features: dict, canonical_name: str):
    aliases = {
        "ptfv1_mv_ms": ["ptfv1_mv_ms", "ptfv1", "PTFV1", "ptfv1_ms", "ptfv1_mvms"],
        "pr_interval_ms": ["pr_interval_ms", "pr_mean_ms", "PR", "pr_interval"],
        "p_duration_ms": ["p_duration_ms", "p_wave_duration_ms", "P_duration_ms"],
        "p_amplitude_mv": ["p_amplitude_mv", "p_amp_mv", "P_amplitude_mv"],
        "p_axis_deg": ["p_axis_deg", "p_axis", "P_axis_deg"],
        "qrs_duration_ms": ["qrs_duration_ms", "qrs_ms", "QRS_duration_ms"],
        "qtc_ms": ["qtc_ms", "QTc", "qtc"],
    }
    for name in aliases.get(canonical_name, [canonical_name]):
        if name in features and not _feature_is_missing(features[name]):
            return features[name]
    return None


async def _save_uploads(files: Iterable[UploadFile], target_dir: Path) -> list[Path]:
    saved_paths: list[Path] = []
    for upload in files:
        path = target_dir / _safe_name(upload.filename or "uploaded_ecg")
        with path.open("wb") as output:
            shutil.copyfileobj(upload.file, output)
        saved_paths.append(path)
    return saved_paths


def _extract_zip_files(paths: list[Path], target_dir: Path) -> list[Path]:
    all_paths = list(paths)
    for path in paths:
        if path.suffix.lower() == ".zip":
            extract_dir = target_dir / f"{path.stem}_unzipped"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with ZipFile(path) as archive:
                archive.extractall(extract_dir)
            all_paths.extend([item for item in extract_dir.rglob("*") if item.is_file()])
    return all_paths


def _lead_quality(signal: np.ndarray) -> float:
    clean = np.asarray(signal, dtype=float)
    finite_ratio = float(np.mean(np.isfinite(clean))) if clean.size else 0.0
    if finite_ratio == 0.0:
        return 0.0
    clean = np.nan_to_num(clean, nan=np.nanmedian(clean[np.isfinite(clean)]))
    amplitude = float(np.nanpercentile(clean, 95) - np.nanpercentile(clean, 5))
    flatline_penalty = 60.0 if amplitude < 1e-6 else 0.0
    noise = float(np.nanstd(np.diff(clean))) if len(clean) > 2 else 0.0
    noise_ratio = min(100.0, noise / (amplitude or 1.0) * 100.0)
    return max(0.0, min(100.0, finite_ratio * 100.0 - noise_ratio * 1.4 - flatline_penalty))


def _usable_lead_count(signals: np.ndarray) -> int:
    if signals.ndim == 1:
        return 1 if _lead_quality(signals) >= 35.0 else 0
    return sum(1 for idx in range(signals.shape[1]) if _lead_quality(signals[:, idx]) >= 35.0)


def _pick_lead(signals: np.ndarray, lead_names: list[str]) -> tuple[np.ndarray, str, int]:
    if signals.ndim == 1:
        return signals.astype(float), lead_names[0] if lead_names else "lead_1", _usable_lead_count(signals)
    preferred = ["II", "MLII", "I", "III", "aVF", "aVL", "aVR", "V1"]
    usable_leads = _usable_lead_count(signals)
    for name in preferred:
        if name in lead_names:
            return signals[:, lead_names.index(name)].astype(float), name, usable_leads
    qualities = [_lead_quality(signals[:, idx]) for idx in range(signals.shape[1])]
    best_idx = int(np.argmax(qualities)) if qualities else 0
    best_name = lead_names[best_idx] if best_idx < len(lead_names) else f"lead_{best_idx + 1}"
    return signals[:, best_idx].astype(float), best_name, usable_leads


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    window = max(1, int(window))
    kernel = np.ones(window) / window
    return np.convolve(values, kernel, mode="same")


def _detect_qrs(signal: np.ndarray, fs: float) -> np.ndarray:
    """Lightweight Pan-Tompkins-style fallback QRS detector."""

    centered = signal - np.nanmedian(signal)
    derivative = np.diff(centered, prepend=centered[0])
    energy = _moving_average(derivative * derivative, int(0.12 * fs))
    threshold = np.nanmean(energy) + 1.6 * np.nanstd(energy)
    refractory = max(1, int(0.25 * fs))
    candidates = np.flatnonzero(energy > threshold)
    peaks: list[int] = []
    last_peak = -refractory

    for candidate in candidates:
        if candidate - last_peak < refractory:
            continue
        left = max(0, candidate - int(0.08 * fs))
        right = min(len(centered), candidate + int(0.08 * fs))
        if right <= left:
            continue
        local_peak = left + int(np.argmax(np.abs(centered[left:right])))
        peaks.append(local_peak)
        last_peak = local_peak

    return np.array(sorted(set(peaks)), dtype=int)


def _sample_entropy(values: np.ndarray) -> float:
    if len(values) < 5:
        return 0.0
    diffs = np.diff(values)
    spread = np.std(diffs)
    if spread == 0:
        return 0.0
    hist, _ = np.histogram(diffs / spread, bins=8, density=True)
    hist = hist[hist > 0]
    return float(-np.sum(hist * np.log(hist)) / 10.0)


def _shannon_entropy(values: np.ndarray) -> float:
    if len(values) < 5:
        return 0.0
    hist, _ = np.histogram(values, bins=min(12, max(4, len(values) // 2)), density=True)
    hist = hist[hist > 0]
    total = float(np.sum(hist))
    if total == 0.0:
        return 0.0
    probabilities = hist / total
    return float(-np.sum(probabilities * np.log2(probabilities)))


def _poincare(rr_ms: np.ndarray) -> tuple[float, float]:
    if rr_ms.size < 2:
        return 0.0, 0.0
    diff_rr = np.diff(rr_ms)
    sd1 = math.sqrt(0.5) * float(np.std(diff_rr))
    sd2_term = max(0.0, 2 * float(np.std(rr_ms)) ** 2 - 0.5 * float(np.std(diff_rr)) ** 2)
    sd2 = math.sqrt(sd2_term)
    return sd1, sd2


def _turning_point_ratio(values: np.ndarray) -> float:
    if len(values) < 3:
        return 0.0
    turns = 0
    for i in range(1, len(values) - 1):
        if (values[i] > values[i - 1] and values[i] > values[i + 1]) or (
            values[i] < values[i - 1] and values[i] < values[i + 1]
        ):
            turns += 1
    return float(turns / (len(values) - 2))


def _p_wave_features(signal: np.ndarray, qrs: np.ndarray, fs: float) -> dict:
    if len(qrs) == 0:
        return {
            "p_wave_presence_ratio": 0.0,
            "pr_mean_ms": None,
            "pr_sd_ms": None,
            "pr_consistency": 0.0,
            "p_duration_ms": None,
            "p_amplitude_mv": None,
            "missing_p_wave_percent": 100.0,
        }

    centered = signal - np.nanmedian(signal)
    noise = float(np.nanstd(centered))
    p_threshold = max(noise * 0.08, 1e-6)
    found_pr: list[float] = []
    p_amplitudes: list[float] = []
    p_durations: list[float] = []

    for peak in qrs:
        start = max(0, peak - int(0.25 * fs))
        end = max(0, peak - int(0.12 * fs))
        if end <= start:
            continue
        segment = centered[start:end]
        if segment.size < 3:
            continue
        local_idx = int(np.argmax(np.abs(segment)))
        amplitude = float(abs(segment[local_idx]))
        if amplitude >= p_threshold:
            p_sample = start + local_idx
            found_pr.append((peak - p_sample) / fs * 1000.0)
            p_amplitudes.append(amplitude)
            half_amp = amplitude * 0.5
            left = local_idx
            right = local_idx
            while left > 0 and abs(segment[left]) >= half_amp:
                left -= 1
            while right < len(segment) - 1 and abs(segment[right]) >= half_amp:
                right += 1
            duration_ms = max(40.0, min(180.0, (right - left) / fs * 1000.0))
            p_durations.append(duration_ms)

    presence_ratio = len(found_pr) / len(qrs) * 100.0
    pr_mean = float(np.mean(found_pr)) if found_pr else None
    pr_sd = float(np.std(found_pr)) if len(found_pr) > 1 else None
    pr_consistency = float(max(0.0, 100.0 - (pr_sd or 45.0) * 2.2))

    return {
        "p_wave_presence_ratio": round(presence_ratio, 1),
        "pr_mean_ms": round(pr_mean, 1) if pr_mean is not None else None,
        "pr_sd_ms": round(pr_sd, 1) if pr_sd is not None else None,
        "pr_consistency": round(pr_consistency, 1),
        "p_duration_ms": round(float(np.mean(p_durations)), 1) if p_durations else None,
        "p_amplitude_mv": round(float(np.mean(p_amplitudes)), 4) if p_amplitudes else None,
        "missing_p_wave_percent": round(100.0 - presence_ratio, 1),
    }


def _signal_quality(signal: np.ndarray, fs: float, qrs_count: int, usable_leads: int, lead_count: int) -> dict:
    finite_ratio = float(np.mean(np.isfinite(signal))) if signal.size else 0.0
    signal = np.nan_to_num(signal, nan=np.nanmedian(signal[np.isfinite(signal)]) if np.any(np.isfinite(signal)) else 0.0)
    centered = signal - np.nanmedian(signal)
    noise = float(np.nanstd(np.diff(centered))) if len(centered) > 2 else 0.0
    amplitude = float(np.nanpercentile(centered, 95) - np.nanpercentile(centered, 5)) or 1.0
    flatline_score = 100.0 if amplitude < 1e-6 else 0.0
    noise_ratio = min(100.0, noise / amplitude * 100.0)
    baseline = _moving_average(centered, int(max(fs, 1)))
    baseline_wander = min(100.0, float(np.nanstd(baseline) / amplitude * 100.0))
    duration_seconds = len(signal) / fs if fs else 0.0
    qrs_rate_per_min = qrs_count / duration_seconds * 60.0 if duration_seconds else 0.0
    qrs_success = 100.0 if 35.0 <= qrs_rate_per_min <= 220.0 else max(0.0, min(100.0, qrs_rate_per_min / 35.0 * 100.0))
    usable_lead_ratio = usable_leads / max(1, lead_count)
    sqi = max(
        0.0,
        min(
            100.0,
            95.0
            - (1.0 - finite_ratio) * 80.0
            - noise_ratio * 1.45
            - baseline_wander * 1.05
            - flatline_score
            + usable_lead_ratio * 8.0
            + qrs_success * 0.08,
        ),
    )
    return {
        "signal_quality_index": round(sqi, 1),
        "missing_data_percent": round((1.0 - finite_ratio) * 100.0, 1),
        "flatline_score": round(flatline_score, 1),
        "noise_score": round(noise_ratio, 1),
        "baseline_wander_score": round(baseline_wander, 1),
        "qrs_detection_success": round(qrs_success, 1),
        "usable_leads": int(usable_leads),
    }


def _fibrillatory_power(signal: np.ndarray, fs: float) -> tuple[float, float | None]:
    centered = signal - _moving_average(signal, int(max(fs * 0.6, 1)))
    if len(centered) < int(fs * 2):
        return 0.0, None
    spectrum = np.abs(np.fft.rfft(centered)) ** 2
    freqs = np.fft.rfftfreq(len(centered), d=1.0 / fs)
    total_mask = (freqs >= 1.0) & (freqs <= 20.0)
    f_mask = (freqs >= 4.0) & (freqs <= 9.0)
    total_power = float(np.sum(spectrum[total_mask])) or 1.0
    f_power = float(np.sum(spectrum[f_mask]))
    dominant = float(freqs[f_mask][np.argmax(spectrum[f_mask])]) if np.any(f_mask) else None
    return round(min(1.0, f_power / total_power), 3), round(dominant, 2) if dominant is not None else None


def _qrs_duration_ms(signal: np.ndarray, qrs: np.ndarray, fs: float) -> float | None:
    if len(qrs) == 0:
        return None
    centered = signal - np.nanmedian(signal)
    durations: list[float] = []
    for peak in qrs[: min(len(qrs), 20)]:
        start = max(0, peak - int(0.08 * fs))
        end = min(len(centered), peak + int(0.08 * fs))
        segment = np.abs(centered[start:end])
        if segment.size < 3:
            continue
        threshold = max(np.max(segment) * 0.18, 1e-9)
        active = np.flatnonzero(segment >= threshold)
        if active.size:
            durations.append((active[-1] - active[0] + 1) / fs * 1000.0)
    return round(float(np.mean(durations)), 1) if durations else None


def _qrs_bounds(signal: np.ndarray, qrs: np.ndarray, fs: float) -> list[tuple[int, int, int]]:
    centered = signal - np.nanmedian(signal)
    bounds: list[tuple[int, int, int]] = []
    for peak in qrs[: min(len(qrs), 30)]:
        start = max(0, peak - int(0.09 * fs))
        end = min(len(centered), peak + int(0.11 * fs))
        segment = np.abs(centered[start:end])
        if segment.size < 3:
            continue
        threshold = max(float(np.max(segment)) * 0.16, 1e-9)
        active = np.flatnonzero(segment >= threshold)
        if active.size:
            bounds.append((start + int(active[0]), int(peak), start + int(active[-1])))
    return bounds


def _qtc_ms(rr_mean_ms: float, qrs_duration_ms: float | None, pr_mean_ms: float | None) -> float | None:
    if rr_mean_ms <= 0:
        return None
    # Approximate QT from available intervals when explicit T-wave delineation is not yet available.
    qt_ms = 360.0 + max(0.0, (qrs_duration_ms or 90.0) - 90.0) * 0.45 + max(0.0, (pr_mean_ms or 160.0) - 160.0) * 0.15
    return round(qt_ms / math.sqrt(rr_mean_ms / 1000.0), 1)


def assess_rhythm(rr_intervals: np.ndarray) -> dict:
    rr_ms = np.asarray(rr_intervals, dtype=float)
    rr_ms = rr_ms[np.isfinite(rr_ms)]
    if rr_ms.size == 0:
        return {
            "mean_rr_ms": None,
            "rr_sd_ms": None,
            "rr_cv": None,
            "rmssd_ms": None,
            "heart_rate_bpm": None,
            "regularity": "unavailable",
        }
    rr_mean = float(np.mean(rr_ms))
    rr_sd = float(np.std(rr_ms))
    rr_cv = float(rr_sd / rr_mean) if rr_mean else 0.0
    rmssd = float(math.sqrt(np.mean(np.diff(rr_ms) ** 2))) if rr_ms.size > 1 else 0.0
    if rr_cv < 0.08:
        regularity = "regular"
    elif rr_cv < 0.16:
        regularity = "mildly irregular"
    else:
        regularity = "irregular"
    return {
        "mean_rr_ms": round(rr_mean, 1),
        "rr_sd_ms": round(rr_sd, 1),
        "rr_cv": round(rr_cv, 3),
        "rmssd_ms": round(rmssd, 1),
        "heart_rate_bpm": round(60000.0 / rr_mean, 1) if rr_mean else None,
        "regularity": regularity,
    }


def calculate_qt_qtc(signal: np.ndarray, fs: float, qrs: np.ndarray | None = None, rr_mean_ms: float | None = None, sex: str | None = None) -> dict:
    if qrs is None:
        qrs = _detect_qrs(signal, fs)
    if rr_mean_ms is None and len(qrs) > 1:
        rr_mean_ms = float(np.mean(np.diff(qrs) / fs * 1000.0))
    bounds = _qrs_bounds(signal, qrs, fs)
    centered = signal - np.nanmedian(signal)
    qt_values: list[float] = []
    for onset, peak, _offset in bounds[:12]:
        search_start = min(len(centered), peak + int(0.12 * fs))
        search_end = min(len(centered), peak + int(0.52 * fs))
        if search_end <= search_start + 5:
            continue
        segment = centered[search_start:search_end]
        t_local = int(np.argmax(np.abs(segment)))
        t_peak = search_start + t_local
        baseline = float(np.nanmedian(centered[max(0, onset - int(0.08 * fs)):onset])) if onset > 0 else 0.0
        t_amp = abs(centered[t_peak] - baseline)
        threshold = max(t_amp * 0.15, 1e-6)
        t_offset = None
        for idx in range(t_peak, search_end):
            if abs(centered[idx] - baseline) <= threshold:
                t_offset = idx
                break
        if t_offset is not None:
            qt_values.append((t_offset - onset) / fs * 1000.0)
    qt_ms = float(np.mean(qt_values)) if qt_values else None
    if qt_ms is None or not rr_mean_ms:
        return {
            "qt_ms": None,
            "qtc_bazett_ms": None,
            "qtc_fridericia_ms": None,
            "prolonged_qtc": "unavailable",
            "method": "T-wave offset unavailable",
        }
    rr_sec = rr_mean_ms / 1000.0
    qtc_bazett = qt_ms / math.sqrt(rr_sec)
    qtc_fridericia = qt_ms / (rr_sec ** (1.0 / 3.0))
    sex_value = (sex or "").strip().lower()
    threshold = 470.0 if sex_value in {"female", "f", "0"} else 450.0 if sex_value in {"male", "m", "1"} else 460.0
    return {
        "qt_ms": round(qt_ms, 1),
        "qtc_bazett_ms": round(qtc_bazett, 1),
        "qtc_fridericia_ms": round(qtc_fridericia, 1),
        "prolonged_qtc": "flagged" if qtc_fridericia >= threshold else "not flagged",
        "sex_specific_threshold_ms": threshold,
        "method": "research T-offset estimate",
    }


def _lead_signal(signals: np.ndarray, lead_names: list[str], name: str) -> np.ndarray | None:
    if signals.ndim == 1 or name not in lead_names:
        return None
    return signals[:, lead_names.index(name)].astype(float)


def estimate_qrs_axis(signals: np.ndarray, lead_names: list[str], fs: float, qrs: np.ndarray | None = None) -> dict:
    lead_i = _lead_signal(signals, lead_names, "I")
    lead_avf = _lead_signal(signals, lead_names, "aVF")
    if lead_i is None or lead_avf is None:
        return {"axis_deg": None, "classification": "unavailable", "method": "requires leads I and aVF"}
    if qrs is None:
        qrs = _detect_qrs(lead_i, fs)
    if len(qrs) == 0:
        return {"axis_deg": None, "classification": "unavailable", "method": "QRS not detected"}

    def net_qrs(lead: np.ndarray) -> float:
        centered = lead - np.nanmedian(lead)
        values = []
        for peak in qrs[: min(len(qrs), 12)]:
            start = max(0, peak - int(0.04 * fs))
            end = min(len(centered), peak + int(0.06 * fs))
            if end > start:
                segment = centered[start:end]
                values.append(float(np.nanmax(segment) + np.nanmin(segment)))
        return float(np.mean(values)) if values else 0.0

    net_i = net_qrs(lead_i)
    net_avf = net_qrs(lead_avf)
    axis = math.degrees(math.atan2(net_avf, net_i))
    if axis < -180:
        axis += 360
    if -30.0 <= axis <= 90.0:
        classification = "normal axis"
    elif -90.0 <= axis < -30.0:
        classification = "left axis deviation"
    elif 90.0 < axis <= 180.0:
        classification = "right axis deviation"
    else:
        classification = "extreme axis"
    return {"axis_deg": round(axis, 1), "classification": classification, "method": "net QRS in leads I and aVF"}


def assess_st_segment(signals: np.ndarray, lead_names: list[str], fs: float, qrs: np.ndarray | None = None) -> dict:
    if signals.ndim == 1:
        return {"status": "unavailable", "max_elevation_mv": None, "max_depression_mv": None, "method": "requires named leads"}
    lead_results = []
    for idx, name in enumerate(lead_names):
        lead = signals[:, idx].astype(float)
        local_qrs = qrs if qrs is not None else _detect_qrs(lead, fs)
        values = []
        centered = lead - np.nanmedian(lead)
        for peak in local_qrs[: min(len(local_qrs), 12)]:
            baseline_start = max(0, peak - int(0.20 * fs))
            baseline_end = max(0, peak - int(0.08 * fs))
            st_index = min(len(centered) - 1, peak + int(0.08 * fs))
            if baseline_end > baseline_start and st_index > 0:
                baseline = float(np.nanmedian(centered[baseline_start:baseline_end]))
                values.append(float(centered[st_index] - baseline))
        if values:
            lead_results.append({"lead": name, "st_level_mv": round(float(np.mean(values)), 3)})
    if not lead_results:
        return {"status": "unavailable", "max_elevation_mv": None, "max_depression_mv": None, "method": "J+80 ms unavailable"}
    max_elevation = max(item["st_level_mv"] for item in lead_results)
    max_depression = min(item["st_level_mv"] for item in lead_results)
    if max_elevation >= 0.1:
        status = "possible ST elevation - research/experimental"
    elif max_depression <= -0.1:
        status = "possible ST depression - research/experimental"
    else:
        status = "no major ST deviation flag - research/experimental"
    return {
        "status": status,
        "max_elevation_mv": round(max_elevation, 3),
        "max_depression_mv": round(max_depression, 3),
        "lead_measurements": lead_results,
        "method": "ST level at estimated J point +80 ms; research/experimental",
    }


def assess_lvh(signals: np.ndarray, lead_names: list[str], sex: str | None = None) -> dict:
    if signals.ndim == 1:
        return {"status": "unavailable", "sokolow_lyon_mv": None, "cornell_mv": None}

    def amplitude(name: str) -> float | None:
        lead = _lead_signal(signals, lead_names, name)
        if lead is None:
            return None
        centered = lead - np.nanmedian(lead)
        return float(np.nanpercentile(centered, 98) - np.nanpercentile(centered, 2))

    v1 = _lead_signal(signals, lead_names, "V1")
    v3 = _lead_signal(signals, lead_names, "V3")
    avl_amp = amplitude("aVL")
    v5_amp = amplitude("V5")
    v6_amp = amplitude("V6")
    sokolow = None
    cornell = None
    if v1 is not None and (v5_amp is not None or v6_amp is not None):
        centered_v1 = v1 - np.nanmedian(v1)
        s_v1 = abs(float(np.nanpercentile(centered_v1, 2)))
        sokolow = s_v1 + max(v5_amp or 0.0, v6_amp or 0.0)
    if avl_amp is not None and v3 is not None:
        centered_v3 = v3 - np.nanmedian(v3)
        s_v3 = abs(float(np.nanpercentile(centered_v3, 2)))
        cornell = avl_amp + s_v3
    sex_value = (sex or "").strip().lower()
    cornell_threshold = 2.0 if sex_value in {"female", "f", "0"} else 2.8
    met = (sokolow is not None and sokolow >= 3.5) or (cornell is not None and cornell >= cornell_threshold)
    status = "LVH criteria met" if met else "LVH criteria not met" if sokolow is not None or cornell is not None else "unavailable"
    return {
        "status": status,
        "sokolow_lyon_mv": round(sokolow, 2) if sokolow is not None else None,
        "cornell_mv": round(cornell, 2) if cornell is not None else None,
        "cornell_threshold_mv": cornell_threshold,
    }


def assess_image_quality(image) -> dict:
    """Backend placeholder for future validated scanned ECG digitization quality checks."""

    width = getattr(image, "width", None)
    height = getattr(image, "height", None)
    megapixels = (width * height / 1_000_000.0) if width and height else None
    resolution_score = min(100.0, megapixels / 2.0 * 100.0) if megapixels is not None else None
    result = {
        "image_resolution": {"width": width, "height": height, "megapixels": round(megapixels, 2) if megapixels is not None else None},
        "rotation_angle_deg": None,
        "grid_detection": None,
        "calibration_marker_detection": None,
        "lead_label_detection": None,
        "crop_quality": None,
        "signal_extraction_confidence": round(resolution_score, 1) if resolution_score is not None else None,
        "status": "requires validated image digitization backend",
    }
    logger.info("Image ECG quality assessment placeholder: %s", result)
    return result


def _assess_bbb(signals: np.ndarray, lead_names: list[str], qrs_duration_ms: float | None) -> dict:
    if qrs_duration_ms is None:
        return {"status": "unavailable", "qrs_duration_ms": None}
    if qrs_duration_ms < 120.0:
        return {"status": "No wide QRS flag", "qrs_duration_ms": qrs_duration_ms}
    if signals.ndim == 1 or not {"V1", "V6"}.issubset(set(lead_names)):
        return {"status": "Wide QRS flag; BBB morphology unavailable", "qrs_duration_ms": qrs_duration_ms}
    v1 = _lead_signal(signals, lead_names, "V1")
    v6 = _lead_signal(signals, lead_names, "V6")
    v1_net = float(np.nanpercentile(v1, 95) + np.nanpercentile(v1, 5)) if v1 is not None else 0.0
    v6_net = float(np.nanpercentile(v6, 95) + np.nanpercentile(v6, 5)) if v6 is not None else 0.0
    if v1_net > 0 and v6_net < 0:
        status = "RBBB-like morphology flag - research"
    elif v1_net < 0 and v6_net > 0:
        status = "LBBB-like morphology flag - research"
    else:
        status = "Wide QRS flag; nonspecific morphology"
    return {"status": status, "qrs_duration_ms": qrs_duration_ms}


def extract_basic_ecg_measurements(signals: np.ndarray, fs: float, lead_names: list[str], sex: str | None = None) -> dict:
    array = np.asarray(signals, dtype=float)
    lead, selected_lead, _usable = _pick_lead(array, lead_names)
    qrs = _detect_qrs(lead, fs)
    rr_ms = np.diff(qrs) / fs * 1000.0 if len(qrs) > 1 else np.array([])
    rhythm = assess_rhythm(rr_ms)
    p_features = _p_wave_features(lead, qrs, fs)
    qrs_duration = _qrs_duration_ms(lead, qrs, fs)
    qt = calculate_qt_qtc(lead, fs, qrs=qrs, rr_mean_ms=rhythm.get("mean_rr_ms"), sex=sex)
    axis = estimate_qrs_axis(array, lead_names, fs, qrs=qrs)
    st = assess_st_segment(array, lead_names, fs, qrs=qrs)
    lvh = assess_lvh(array, lead_names, sex=sex)
    bbb = _assess_bbb(array, lead_names, qrs_duration)
    fib_power, dominant_f = _fibrillatory_power(lead, fs)
    rr_irregularity = min(
        100.0,
        (rhythm.get("rr_cv") or 0.0) * 155.0
        + (rhythm.get("rmssd_ms") or 0.0) / 3.2
        + (100.0 - p_features["p_wave_presence_ratio"]) * 0.2,
    )
    measurements = {
        "label": "Research ECG measurement output",
        "selected_lead": selected_lead,
        "heart_rate": {
            "heart_rate_bpm": rhythm["heart_rate_bpm"],
            "mean_rr_ms": rhythm["mean_rr_ms"],
            "r_peak_count": int(len(qrs)),
        },
        "rhythm_regularity": rhythm,
        "p_wave_pr": {
            "pr_interval_ms": p_features.get("pr_mean_ms"),
            "pr_sd_ms": p_features.get("pr_sd_ms"),
            "p_wave_presence_ratio": p_features.get("p_wave_presence_ratio"),
            "missing_p_wave_percent": p_features.get("missing_p_wave_percent"),
            "status": "missing P waves flagged" if p_features.get("missing_p_wave_percent", 100.0) > 50.0 else "P waves usually detected",
        },
        "qrs": {
            "qrs_duration_ms": qrs_duration,
            "wide_qrs": bool(qrs_duration is not None and qrs_duration >= 120.0),
            "status": "wide QRS flag" if qrs_duration is not None and qrs_duration >= 120.0 else "No wide QRS flag" if qrs_duration is not None else "unavailable",
        },
        "qt_qtc": qt,
        "axis": axis,
        "st_segment": st,
        "lvh": lvh,
        "bbb": bbb,
        "af_rhythm_markers": {
            "rr_irregularity_index": round(rr_irregularity, 1),
            "p_wave_absence_percent": round(100.0 - p_features.get("p_wave_presence_ratio", 0.0), 1),
            "fibrillatory_baseline_power": fib_power,
            "dominant_f_wave_hz": dominant_f,
        },
        "disclaimer": "Research ECG measurement output. Requires physician confirmation.",
    }
    logger.info("Basic ECG measurements: %s", measurements)
    return measurements


def _wave_area_axis(signals: np.ndarray, lead_names: list[str], lead_a: str, lead_b: str, fs: float, qrs: np.ndarray, start_offset: float, end_offset: float) -> dict:
    signal_a = _lead_signal(signals, lead_names, lead_a)
    signal_b = _lead_signal(signals, lead_names, lead_b)
    if signal_a is None or signal_b is None or len(qrs) == 0:
        return {"axis_deg": None, "classification": "unavailable", "method": f"requires {lead_a} and {lead_b}"}

    def window_area(signal: np.ndarray) -> float:
        centered = signal - np.nanmedian(signal)
        areas = []
        for peak in qrs[: min(len(qrs), 12)]:
            start = max(0, peak + int(start_offset * fs))
            end = min(len(centered), peak + int(end_offset * fs))
            if end > start:
                areas.append(float(np.sum(centered[start:end])))
        return float(np.mean(areas)) if areas else 0.0

    area_a = window_area(signal_a)
    area_b = window_area(signal_b)
    axis = math.degrees(math.atan2(area_b, area_a))
    if -30.0 <= axis <= 90.0:
        classification = "normal"
    elif -90.0 <= axis < -30.0:
        classification = "left axis deviation"
    elif 90.0 < axis <= 180.0:
        classification = "right axis deviation"
    else:
        classification = "extreme axis deviation"
    return {"axis_deg": round(axis, 1), "classification": classification, "method": f"net area in {lead_a}/{lead_b}"}


def _lead_qrs_polarity(signals: np.ndarray, lead_names: list[str], lead_name: str, qrs: np.ndarray, fs: float) -> dict:
    lead = _lead_signal(signals, lead_names, lead_name)
    if lead is None or len(qrs) == 0:
        return {"r_mv": None, "s_mv": None, "net_mv": None}
    centered = lead - np.nanmedian(lead)
    r_values = []
    s_values = []
    for peak in qrs[: min(len(qrs), 12)]:
        start = max(0, peak - int(0.05 * fs))
        end = min(len(centered), peak + int(0.07 * fs))
        if end > start:
            segment = centered[start:end]
            r_values.append(float(np.nanmax(segment)))
            s_values.append(abs(float(np.nanmin(segment))))
    if not r_values:
        return {"r_mv": None, "s_mv": None, "net_mv": None}
    r_mv = float(np.mean(r_values))
    s_mv = float(np.mean(s_values))
    return {"r_mv": round(r_mv, 3), "s_mv": round(s_mv, 3), "net_mv": round(r_mv - s_mv, 3)}


def _analyze_t_waves(signals: np.ndarray, lead_names: list[str], fs: float, qrs: np.ndarray) -> dict:
    if signals.ndim == 1 or len(qrs) == 0:
        return {"summary": "unavailable", "lead_findings": []}
    findings = []
    for idx, name in enumerate(lead_names):
        lead = signals[:, idx].astype(float)
        centered = lead - np.nanmedian(lead)
        amps = []
        signs = []
        biphasic_count = 0
        for peak in qrs[: min(len(qrs), 10)]:
            start = min(len(centered), peak + int(0.14 * fs))
            end = min(len(centered), peak + int(0.42 * fs))
            if end <= start + 5:
                continue
            segment = centered[start:end]
            t_max = float(np.nanmax(segment))
            t_min = float(np.nanmin(segment))
            amp = t_max if abs(t_max) >= abs(t_min) else t_min
            amps.append(amp)
            signs.append(1 if amp >= 0 else -1)
            if t_max > 0.12 and t_min < -0.12:
                biphasic_count += 1
        if not amps:
            continue
        mean_amp = float(np.mean(amps))
        inverted = float(np.mean([sign < 0 for sign in signs])) > 0.6
        tall_threshold = 1.0 if name.startswith("V") else 0.5
        status = "normal/undetermined"
        if inverted:
            status = "T-wave inversion"
        elif abs(mean_amp) >= tall_threshold:
            status = "tall T waves"
        elif biphasic_count >= max(2, len(amps) // 2):
            status = "biphasic T waves"
        findings.append({"lead": name, "t_amplitude_mv": round(mean_amp, 3), "status": status})
    abnormal = [item for item in findings if item["status"] != "normal/undetermined"]
    return {"summary": "ST-T abnormality flags present" if abnormal else "no major T-wave flag", "lead_findings": findings}


def _detect_stemi(st_segment: dict, age: float | None, sex: str | None) -> dict:
    lead_values = {item["lead"]: float(item["st_level_mv"]) for item in st_segment.get("lead_measurements", [])}
    if not lead_values:
        return {"status": "unavailable", "confidence": 0.0, "culprit_vessel": "unavailable", "reasons": ["ST measurements unavailable."]}

    sex_value = (sex or "").strip().lower()
    male = sex_value in {"male", "m", "1"}
    female = sex_value in {"female", "f", "0"}

    def threshold(lead: str) -> float:
        if lead in {"V2", "V3"}:
            if female:
                return 0.15
            if male and age is not None and age < 40:
                return 0.25
            if male:
                return 0.20
        return 0.10

    territories = {
        "septal": ["V1", "V2"],
        "anterior": ["V3", "V4"],
        "lateral": ["I", "aVL", "V5", "V6"],
        "inferior": ["II", "III", "aVF"],
        "posterior": ["V1", "V2", "V3"],
    }
    elevated_groups = []
    reasons = []
    for territory, leads in territories.items():
        positive = [lead for lead in leads if lead_values.get(lead, 0.0) >= threshold(lead)]
        if len(positive) >= 2:
            elevated_groups.append(territory)
            reasons.append(f"ST elevation meets threshold in contiguous {territory} leads: {', '.join(positive)}.")
    reciprocal_inferior = any(lead_values.get(lead, 0.0) <= -0.10 for lead in ["II", "III", "aVF"])
    reciprocal_lateral = any(lead_values.get(lead, 0.0) <= -0.10 for lead in ["I", "aVL", "V5", "V6"])
    if reciprocal_inferior:
        reasons.append("Reciprocal inferior ST depression flag present.")
    if reciprocal_lateral:
        reasons.append("Reciprocal lateral ST depression flag present.")

    if not elevated_groups:
        return {"status": "No STEMI criteria met by research rules", "confidence": 35.0, "culprit_vessel": "none suggested", "reasons": ["No contiguous lead group meets ST-elevation thresholds."]}

    if "anterior" in elevated_groups or "septal" in elevated_groups:
        culprit = "LAD"
    elif "inferior" in elevated_groups and reciprocal_lateral:
        culprit = "RCA"
    elif "lateral" in elevated_groups:
        culprit = "LCX"
    else:
        culprit = "uncertain"
    confidence = min(96.0, 72.0 + len(elevated_groups) * 8.0 + (8.0 if reciprocal_inferior or reciprocal_lateral else 0.0))
    return {"status": "possible STEMI pattern - research criteria", "confidence": round(confidence, 1), "culprit_vessel": culprit, "territories": elevated_groups, "reasons": reasons}


def _detect_ischemia_and_infarction(signals: np.ndarray, lead_names: list[str], fs: float, qrs: np.ndarray, st_segment: dict) -> dict:
    lead_values = {item["lead"]: float(item["st_level_mv"]) for item in st_segment.get("lead_measurements", [])}
    territories = {
        "anterior ischemia": ["V2", "V3", "V4"],
        "inferior ischemia": ["II", "III", "aVF"],
        "lateral ischemia": ["I", "aVL", "V5", "V6"],
        "posterior ischemia": ["V1", "V2", "V3"],
    }
    ischemia = []
    for label, leads in territories.items():
        depressed = [lead for lead in leads if lead_values.get(lead, 0.0) <= -0.10]
        if len(depressed) >= 2:
            ischemia.append({"territory": label, "leads": depressed, "basis": "ST depression >=0.1 mV in contiguous leads"})

    infarct_groups = {
        "septal MI pattern": ["V1", "V2"],
        "anterior MI pattern": ["V3", "V4"],
        "inferior MI pattern": ["II", "III", "aVF"],
        "lateral MI pattern": ["I", "aVL", "V5", "V6"],
    }
    infarction = []
    for label, leads in infarct_groups.items():
        q_like = []
        for lead_name in leads:
            lead = _lead_signal(signals, lead_names, lead_name)
            if lead is None:
                continue
            centered = lead - np.nanmedian(lead)
            q_depths = []
            r_heights = []
            for peak in qrs[: min(len(qrs), 10)]:
                start = max(0, peak - int(0.05 * fs))
                q_end = max(0, peak - int(0.01 * fs))
                r_end = min(len(centered), peak + int(0.04 * fs))
                if q_end > start and r_end > peak:
                    q_depths.append(abs(float(np.nanmin(centered[start:q_end]))))
                    r_heights.append(abs(float(np.nanmax(centered[peak:r_end]))))
            if q_depths and r_heights and float(np.mean(q_depths)) >= max(0.10, float(np.mean(r_heights)) * 0.25):
                q_like.append(lead_name)
        if len(q_like) >= 2:
            infarction.append({"territory": label, "leads": q_like, "basis": "pathologic Q-wave morphology flag - research"})
    return {"ischemia": ischemia, "infarction": infarction}


def _detect_chamber_enlargement(signals: np.ndarray, lead_names: list[str], p_features: dict, ptfv1_mv_ms: float | None, axis: dict) -> dict:
    lead_ii = _lead_signal(signals, lead_names, "II")
    p_amp_ii = None
    if lead_ii is not None:
        centered = lead_ii - np.nanmedian(lead_ii)
        p_amp_ii = float(np.nanpercentile(centered, 92) - np.nanmedian(centered))
    rae = p_amp_ii is not None and p_amp_ii >= 0.25
    lae = (p_features.get("p_duration_ms") is not None and p_features["p_duration_ms"] >= 120.0) or (ptfv1_mv_ms is not None and ptfv1_mv_ms <= -0.04)
    lvh_info = assess_lvh(signals, lead_names)
    v1 = _lead_qrs_polarity(signals, lead_names, "V1", _detect_qrs(_pick_lead(signals, lead_names)[0], 500.0), 500.0) if False else None
    rvh = axis.get("classification") == "right axis deviation"
    status = []
    if rae:
        status.append("right atrial enlargement criteria")
    if lae:
        status.append("left atrial enlargement criteria")
    if rae and lae:
        status.append("biatrial enlargement criteria")
    if lvh_info.get("status") == "LVH criteria met":
        status.append("LVH criteria")
    if rvh:
        status.append("RVH screening flag")
    return {
        "right_atrial_enlargement": "criteria met" if rae else "not met/unavailable",
        "left_atrial_enlargement": "criteria met" if lae else "not met/unavailable",
        "biatrial_enlargement": "criteria met" if rae and lae else "not met",
        "lvh": lvh_info,
        "rvh": "screening flag" if rvh else "not met/unavailable",
        "summary": status or ["No chamber enlargement criteria met by available rules."],
    }


def _classify_rhythm(measurements: dict, p_features: dict, fib_power: float, qrs_duration_ms: float | None) -> dict:
    heart_rate = measurements["heart_rate"].get("heart_rate_bpm")
    rr_cv = measurements["rhythm_regularity"].get("rr_cv") or 0.0
    p_presence = p_features.get("p_wave_presence_ratio", 0.0)
    pr_ms = p_features.get("pr_mean_ms")
    qrs_wide = qrs_duration_ms is not None and qrs_duration_ms >= 120.0
    reasons = []
    label = "undetermined rhythm"
    confidence = 35.0
    candidates = []

    if p_presence >= 70.0 and rr_cv < 0.08 and heart_rate is not None and 50 <= heart_rate <= 100:
        label = "sinus rhythm"
        confidence = 88.0
        reasons.append("P waves are present before most QRS complexes with regular RR intervals and rate 50-100 bpm.")
    elif p_presence >= 70.0 and rr_cv >= 0.08:
        label = "sinus arrhythmia"
        confidence = 74.0
        reasons.append("P waves are present but RR variability is increased.")
    elif rr_cv >= 0.16 and p_presence < 55.0 and fib_power >= 0.45:
        label = "atrial fibrillation pattern"
        confidence = min(95.0, 72.0 + rr_cv * 60.0 + fib_power * 10.0)
        reasons.append("Irregular RR intervals, low P-wave presence, and fibrillatory baseline power support AF pattern.")
    elif p_presence < 55.0 and heart_rate is not None and 240 <= heart_rate <= 340:
        label = "atrial flutter pattern"
        confidence = 58.0
        reasons.append("Very rapid atrial-rate surrogate pattern; flutter-wave confirmation requires better atrial delineation.")
    elif heart_rate is not None and heart_rate > 150 and rr_cv < 0.10 and not qrs_wide:
        label = "SVT pattern"
        confidence = 66.0
        reasons.append("Regular narrow-complex tachycardia pattern.")
    elif p_presence < 45.0 and heart_rate is not None and 40 <= heart_rate <= 100 and not qrs_wide:
        label = "junctional rhythm pattern"
        confidence = 52.0
        reasons.append("P waves are often absent with a narrow QRS and non-tachycardic rate.")
    elif qrs_wide and heart_rate is not None and heart_rate >= 100:
        label = "ventricular rhythm pattern"
        confidence = 55.0
        reasons.append("Wide-complex rhythm pattern; ventricular rhythm requires expert confirmation.")
    else:
        reasons.append("Available features do not meet a specific rhythm rule with high confidence.")

    candidates.append({"rhythm": label, "confidence": round(confidence, 1), "reasons": reasons})
    if pr_ms is not None and pr_ms > 200.0:
        candidates.append({"rhythm": "first-degree AV block pattern", "confidence": 70.0, "reasons": [f"PR interval is prolonged at {pr_ms} ms."]})
    candidates.append({"rhythm": "pacemaker rhythm", "confidence": 0.0, "reasons": ["Pacemaker spike detection is not yet validated in this prototype."]})
    return {"primary": label, "confidence": round(confidence, 1), "candidates": candidates, "reasons": reasons}


def interpret_ecg_ensemble(
    signals: np.ndarray,
    fs: float,
    lead_names: list[str],
    measurements: dict,
    p_features: dict,
    qrs: np.ndarray,
    qrs_duration_ms: float | None,
    ptfv1_mv_ms: float | None,
    fib_power: float,
    age: float | None,
    sex: str | None,
    atrial_remodeling_score: float,
    af_detection_score: float,
) -> dict:
    axis_qrs = measurements.get("axis", {})
    p_axis = _wave_area_axis(signals, lead_names, "I", "aVF", fs, qrs, -0.25, -0.12)
    t_axis = _wave_area_axis(signals, lead_names, "I", "aVF", fs, qrs, 0.14, 0.42)
    rhythm = _classify_rhythm(measurements, p_features, fib_power, qrs_duration_ms)
    chamber = _detect_chamber_enlargement(signals, lead_names, p_features, ptfv1_mv_ms, axis_qrs)
    bbb = _assess_bbb(signals, lead_names, qrs_duration_ms)
    st_segment = measurements.get("st_segment", {})
    stemi = _detect_stemi(st_segment, age, sex)
    ischemia_infarction = _detect_ischemia_and_infarction(signals, lead_names, fs, qrs, st_segment)
    t_waves = _analyze_t_waves(signals, lead_names, fs, qrs)
    qt = measurements.get("qt_qtc", {})
    pr_ms = measurements.get("p_wave_pr", {}).get("pr_interval_ms")
    intervals = {
        "pr_ms": pr_ms,
        "qrs_ms": qrs_duration_ms,
        "qt_ms": qt.get("qt_ms"),
        "qtc_bazett_ms": qt.get("qtc_bazett_ms"),
        "qtc_fridericia_ms": qt.get("qtc_fridericia_ms"),
        "flags": [
            flag
            for flag in [
                "prolonged QTc" if qt.get("prolonged_qtc") == "flagged" else None,
                "short QT" if qt.get("qtc_fridericia_ms") is not None and qt["qtc_fridericia_ms"] < 340.0 else None,
                "first-degree AV block" if pr_ms is not None and pr_ms > 200.0 else None,
                "wide QRS" if qrs_duration_ms is not None and qrs_duration_ms >= 120.0 else None,
            ]
            if flag
        ],
    }
    hf_points = 0
    hf_reasons = []
    if qrs_duration_ms is not None and qrs_duration_ms >= 120.0:
        hf_points += 2
        hf_reasons.append("QRS duration is prolonged.")
    if qt.get("qtc_fridericia_ms") is not None and qt["qtc_fridericia_ms"] >= 460.0:
        hf_points += 1
        hf_reasons.append("QTc is prolonged.")
    if measurements["heart_rate"].get("heart_rate_bpm") is not None and measurements["heart_rate"]["heart_rate_bpm"] > 100.0:
        hf_points += 1
        hf_reasons.append("Heart rate is elevated.")
    if chamber["lvh"].get("status") == "LVH criteria met":
        hf_points += 2
        hf_reasons.append("LVH criteria are met.")
    if atrial_remodeling_score >= 70.0:
        hf_points += 1
        hf_reasons.append("PTB-XL atrial remodeling probability is high.")
    hf_probability = "low" if hf_points <= 1 else "intermediate" if hf_points <= 3 else "high"
    mortality = {
        "30_day": "unavailable - requires validated outcome model",
        "1_year": "unavailable - requires validated outcome model",
        "5_year": "unavailable - requires validated outcome model",
        "required_future_inputs": ["validated ECG deep model", "clinical variables", "STELA registry or external outcome cohort"],
    }
    final_lines = [
        f"{rhythm['primary'].capitalize()}.",
        f"Heart rate {measurements['heart_rate'].get('heart_rate_bpm') or 'unavailable'} bpm.",
        f"QRS axis: {axis_qrs.get('classification', 'unavailable')}.",
        "No STEMI criteria met by research rules." if stemi["status"].startswith("No STEMI") else stemi["status"],
        f"AF probability: {af_detection_score}%.",
        f"Heart failure probability: {hf_probability}.",
    ]
    if intervals["flags"]:
        final_lines.append("Interval flags: " + ", ".join(intervals["flags"]) + ".")
    if chamber["summary"]:
        final_lines.append("Chamber findings: " + "; ".join(chamber["summary"]) + ".")
    report = "FINAL ECG INTERPRETATION\n" + "\n".join(final_lines) + "\nResearch interpretation only. Requires physician confirmation."
    interpretation = {
        "module_version": "research-grade-rule-ensemble-v1",
        "rhythm": rhythm,
        "heart_rate": measurements.get("heart_rate"),
        "axes": {"p_axis": p_axis, "qrs_axis": axis_qrs, "t_axis": t_axis},
        "intervals": intervals,
        "chamber_enlargement": chamber,
        "bundle_branch_block": bbb,
        "st_t_analysis": {"st_segment": st_segment, "t_waves": t_waves},
        "stemi": stemi,
        "ischemia": ischemia_infarction["ischemia"],
        "infarction": ischemia_infarction["infarction"],
        "af_analysis": {
            "rr_irregularity_index": measurements["af_rhythm_markers"]["rr_irregularity_index"],
            "p_wave_absence_percent": measurements["af_rhythm_markers"]["p_wave_absence_percent"],
            "f_wave_likelihood": measurements["af_rhythm_markers"]["fibrillatory_baseline_power"],
            "atrial_remodeling_score": atrial_remodeling_score,
            "ptfv1_mv_ms": ptfv1_mv_ms,
            "p_wave_duration_ms": p_features.get("p_duration_ms"),
            "p_wave_dispersion": "unavailable - requires multi-lead P-wave delineation",
            "calibrated_af_probability": "unavailable - calibration model not fitted",
            "current_rule_af_probability": af_detection_score,
        },
        "heart_failure_risk": {"category": hf_probability, "score_points": hf_points, "reasons": hf_reasons or ["No major ECG HF-risk flags in available features."]},
        "mortality_risk": mortality,
        "explainability": {
            "top_reasons": rhythm["reasons"] + stemi.get("reasons", [])[:3] + hf_reasons,
            "model_blending": ["PTB-XL atrial remodeling model preserved", "rule-based ECG interpretation", "digital signal processing measurements", "future deep learning modules can be added independently"],
        },
        "physician_report": report,
        "safety": "Research interpretation only. This system does not diagnose ECG conditions and requires physician confirmation.",
    }
    logger.info("Advanced ECG interpretation: %s", interpretation)
    return interpretation


def _ptfv1(signals: np.ndarray, lead_names: list[str], qrs: np.ndarray, fs: float) -> float | None:
    if signals.ndim == 1 or "V1" not in lead_names or len(qrs) == 0:
        return None
    v1 = signals[:, lead_names.index("V1")].astype(float)
    centered = v1 - np.nanmedian(v1)
    values: list[float] = []
    for peak in qrs[: min(len(qrs), 20)]:
        start = max(0, peak - int(0.25 * fs))
        end = max(0, peak - int(0.12 * fs))
        if end <= start:
            continue
        segment = centered[start:end]
        negative = segment[segment < 0]
        if negative.size:
            amplitude_mv = float(np.min(negative))
            duration_ms = negative.size / fs * 1000.0
            values.append(amplitude_mv * duration_ms)
    return round(float(np.mean(values)), 3) if values else None


def _p_axis_deg(lead_names: list[str], p_amplitude_mv: float | None) -> float | None:
    if p_amplitude_mv is None:
        return None
    # Placeholder until multi-lead P-axis vector calculation is implemented.
    return 45.0 if "II" in lead_names else 0.0


def _model_feature_vector(
    *,
    fields: dict,
    age: float | None,
    sex: str | None,
    p_features: dict,
    qrs_duration_ms: float | None,
    qtc_ms: float | None,
    ptfv1_mv_ms: float | None,
    lead_names: list[str],
) -> tuple[dict, list[str]]:
    metadata_age, metadata_sex = _parse_demographics_from_fields(fields)
    final_age = age if age is not None else metadata_age
    final_sex = sex if sex is not None else metadata_sex
    limitations: list[str] = []

    artifacts = _load_model_artifacts()
    defaults = _artifact_training_defaults(artifacts)
    feature_columns = artifacts["feature_columns"]

    sex_value = _encode_sex(final_sex)
    extracted_features = {
        "age": final_age,
        "sex": sex_value,
        "p_duration_ms": p_features.get("p_duration_ms"),
        "p_amplitude_mv": p_features.get("p_amplitude_mv"),
        "p_axis_deg": _p_axis_deg(lead_names, p_features.get("p_amplitude_mv")),
        "pr_interval_ms": p_features.get("pr_mean_ms"),
        "qrs_duration_ms": qrs_duration_ms,
        "qtc_ms": qtc_ms,
        "ptfv1_mv_ms": ptfv1_mv_ms,
    }
    extracted_features.update({key: value for key, value in p_features.items() if value is not None})

    features: dict[str, float] = {}
    for key in feature_columns:
        value = _feature_alias_value(extracted_features, key)
        if _feature_is_missing(value):
            fallback_source = "training fallback"
            if key in defaults:
                value = defaults[key]
            else:
                value = 0.0
                fallback_source = "last-resort zero fallback"
            if key == "ptfv1_mv_ms":
                limitations.append(f"PTFV1 unavailable — imputed using {fallback_source}; confidence reduced.")
            else:
                limitations.append(f"{key} unavailable — imputed using {fallback_source}; confidence reduced.")
        features[key] = float(value)

    return features, limitations


def _run_ptbxl_model(features: dict) -> dict:
    artifacts = _load_model_artifacts()
    columns = artifacts["feature_columns"]
    missing_columns = [column for column in columns if column not in features]
    if missing_columns:
        raise ModelInferenceError(f"Required feature columns missing: {missing_columns}")

    frame = pd.DataFrame([{column: features[column] for column in columns}], columns=columns)
    scaled = artifacts["scaler"].transform(frame)
    logistic_probability = float(artifacts["logistic_model"].predict_proba(scaled)[0, 1])

    gb_model = artifacts["gradient_boosting_model"]
    gb_probability = float(gb_model.predict_proba(frame)[0, 1]) if gb_model is not None else None
    metadata = artifacts["metadata"]
    main_probability = gb_probability if gb_probability is not None else logistic_probability

    logistic_model = artifacts["logistic_model"]
    coefficients = getattr(logistic_model, "coef_", None)
    contributions = []
    if coefficients is not None:
        for column, value, coefficient in zip(columns, frame.iloc[0].to_list(), coefficients[0]):
            contributions.append(
                {
                    "feature": column,
                    "value": float(value),
                    "direction": "increases" if coefficient * value >= 0 else "decreases",
                    "contribution": float(coefficient * value),
                }
            )
        contributions.sort(key=lambda item: abs(item["contribution"]), reverse=True)

    abnormal_features = [
        {"feature": key, "value": value}
        for key, value in features.items()
        if key in {"p_duration_ms", "pr_interval_ms", "qrs_duration_ms", "qtc_ms", "ptfv1_mv_ms"}
    ]

    return {
        "atrial_remodeling_score_logistic": round(logistic_probability * 100.0, 1),
        "atrial_remodeling_score_gradient_boosting": round(gb_probability * 100.0, 1) if gb_probability is not None else None,
        "main_atrial_remodeling_score": round(main_probability * 100.0, 1),
        "model_used": "PTB-XL Gradient Boosting" if gb_probability is not None else "PTB-XL Logistic Regression",
        "model_target": metadata.get("model_target", MODEL_TARGET),
        "model_auc": metadata.get("gradient_boosting_auc" if gb_probability is not None else "logistic_auc"),
        "model_metadata": metadata,
        "logistic_feature_contributions": contributions,
        "top_abnormal_features": abnormal_features,
    }


def _analyze_signals(signals, fields: dict, age: float | None = None, sex: str | None = None) -> dict:
    array = np.asarray(signals, dtype=float)
    fs = float(fields["fs"])
    lead_names = list(fields.get("sig_name", []))
    metadata_age, metadata_sex = _parse_demographics_from_fields(fields)
    measurement_sex = sex if sex is not None else metadata_sex
    lead, selected_lead, usable_leads = _pick_lead(array, lead_names)
    qrs = _detect_qrs(lead, fs)
    rr_ms = np.diff(qrs) / fs * 1000.0 if len(qrs) > 1 else np.array([])

    rr_mean = float(np.mean(rr_ms)) if rr_ms.size else 0.0
    rr_sd = float(np.std(rr_ms)) if rr_ms.size else 0.0
    rr_cv = float(rr_sd / rr_mean) if rr_mean else 0.0
    rmssd = float(math.sqrt(np.mean(np.diff(rr_ms) ** 2))) if rr_ms.size > 1 else 0.0
    pnn50 = float(np.mean(np.abs(np.diff(rr_ms)) > 50.0) * 100.0) if rr_ms.size > 1 else 0.0
    sampen = _sample_entropy(rr_ms)
    shannon = _shannon_entropy(rr_ms)
    sd1, sd2 = _poincare(rr_ms)
    tpr = _turning_point_ratio(rr_ms)
    p_features = _p_wave_features(lead, qrs, fs)
    qrs_duration = _qrs_duration_ms(lead, qrs, fs)
    qtc = _qtc_ms(rr_mean, qrs_duration, p_features.get("pr_mean_ms"))
    ptfv1_value = _ptfv1(array, lead_names, qrs, fs)
    basic_measurements = extract_basic_ecg_measurements(array, fs, lead_names, sex=measurement_sex)
    lead_count = int(array.shape[1]) if array.ndim > 1 else 1
    quality = _signal_quality(lead, fs, len(qrs), usable_leads, lead_count)
    fib_power, dominant_f = _fibrillatory_power(lead, fs)

    rr_irregularity = min(
        100.0,
        rr_cv * 155.0 + rmssd / 3.2 + pnn50 * 0.55 + sampen * 13.0 + shannon * 5.0 + tpr * 18.0,
    )
    low_quality = quality["signal_quality_index"] < 50.0
    moderate_quality = 50.0 <= quality["signal_quality_index"] <= 70.0
    acceptable_signal = quality["signal_quality_index"] > 70.0
    high_rr_irregularity = rr_cv >= 0.18 or rr_irregularity >= 62.0
    p_absence = p_features["p_wave_presence_ratio"] < 55.0
    p_unreliable = p_features["p_wave_presence_ratio"] == 0.0 and len(qrs) < 5
    fibrillatory_activity = fib_power >= 0.55
    af_gate_passed = high_rr_irregularity and p_absence and fibrillatory_activity and not low_quality

    p_presence = float(p_features["p_wave_presence_ratio"])
    missing_p_percent = float(p_features["missing_p_wave_percent"])
    pr_consistency = float(p_features["pr_consistency"])
    af_score_raw = (
        rr_irregularity * 0.28
        + min(30.0, rr_cv * 110.0)
        + min(18.0, rmssd / 5.0)
        + min(14.0, pnn50 * 0.35)
        + max(0.0, 70.0 - p_presence) * 0.28
        + missing_p_percent * 0.18
        + fib_power * 22.0
        - max(0.0, p_presence - 70.0) * 0.45
        - max(0.0, pr_consistency - 70.0) * 0.18
        - (14.0 if rr_cv < 0.12 else 0.0)
        - (10.0 if low_quality else 0.0)
    )
    if p_presence < 40.0 and high_rr_irregularity:
        af_score_raw += 14.0
    if af_gate_passed:
        af_score_raw += 10.0

    af_score = round(max(0.0, min(100.0, af_score_raw)), 1)
    rhythm_score_cap_reasons: list[str] = []
    if p_presence > 70.0 and rr_cv < 0.12:
        af_score = min(af_score, 39.0)
        rhythm_score_cap_reasons.append("Sinus rhythm pattern likely: P-wave presence is >70% and RR coefficient of variation is <0.12.")
    if low_quality:
        af_score = min(af_score, 50.0)
        rhythm_score_cap_reasons.append("Low confidence due to signal quality: signal quality index is <50.")
    elif moderate_quality and not af_gate_passed:
        af_score = min(af_score, 69.0)
        rhythm_score_cap_reasons.append("Moderate signal quality and incomplete AF gate limit high-confidence rhythm labeling.")
    if af_score >= 70.0 and not af_gate_passed:
        af_score = 69.0
        rhythm_score_cap_reasons.append("High AF likelihood requires RR irregularity, P-wave absence, fibrillatory activity, and acceptable signal quality.")

    features_used, demographic_limitations = _model_feature_vector(
        fields=fields,
        age=age,
        sex=sex,
        p_features=p_features,
        qrs_duration_ms=qrs_duration,
        qtc_ms=qtc,
        ptfv1_mv_ms=ptfv1_value,
        lead_names=lead_names,
    )
    model_result = _run_ptbxl_model(features_used)
    imputed_feature_count = sum(1 for limitation in demographic_limitations if "imputed using" in limitation)
    advanced_interpretation = interpret_ecg_ensemble(
        array,
        fs,
        lead_names,
        basic_measurements,
        p_features,
        qrs,
        qrs_duration,
        ptfv1_value,
        fib_power,
        metadata_age,
        measurement_sex,
        float(model_result["main_atrial_remodeling_score"]),
        float(af_score),
    )

    if af_score >= 70.0 and af_gate_passed:
        rhythm = "Pattern compatible with AF or irregular atrial rhythm"
    elif af_score >= 40.0:
        rhythm = "Indeterminate atrial rhythm"
    else:
        rhythm = "AF unlikely / sinus rhythm pattern likely"

    reasons: list[str] = []
    if af_gate_passed:
        reasons.append("AF gate passed: RR irregularity, P-wave absence, fibrillatory activity, and acceptable SQI are present.")
    reasons.extend(rhythm_score_cap_reasons)
    if p_features["p_wave_presence_ratio"] > 70.0:
        reasons.append("Visible P waves before most QRS complexes reduce AF probability.")
    if rr_cv < 0.12 and p_features["p_wave_presence_ratio"] > 70.0:
        reasons.append("Regular RR intervals with visible P waves are more compatible with sinus rhythm.")
    if not acceptable_signal:
        reasons.append("Signal quality limits confidence; high-confidence AF labeling is blocked.")
    if p_unreliable:
        reasons.append("P-wave detection is unreliable; confidence was lowered instead of forcing AF.")
    if imputed_feature_count:
        reasons.append("One or more PTB-XL model inputs were unavailable and imputed; model confidence was lowered.")
    if not reasons:
        reasons.append("Digital WFDB waveform was parsed and analyzed with conservative AF gating.")
    reasons.append("This is a research prototype and does not diagnose AF. Physician confirmation is required.")

    metadata = wfdb_metadata(array, fields)
    duration = metadata["duration_seconds"]
    preview_count = min(600, len(lead))
    preview_indices = np.linspace(0, len(lead) - 1, preview_count).astype(int) if len(lead) else np.array([])
    preview_values = lead[preview_indices] if preview_indices.size else np.array([])
    if preview_values.size:
        scale = float(np.nanmax(np.abs(preview_values - np.nanmedian(preview_values)))) or 1.0
        preview = [round(float((value - np.nanmedian(preview_values)) / scale), 4) for value in preview_values]
    else:
        preview = []

    extracted_feature_count = len(features_used) - imputed_feature_count
    expected_feature_count = max(1, len(features_used))
    feature_completeness = extracted_feature_count / expected_feature_count * 100.0
    remodeling_score = float(model_result["main_atrial_remodeling_score"])
    rhythm_remodeling_agreement = 100.0 - abs(af_score - remodeling_score)
    distance_from_threshold = min(abs(af_score - 40.0), abs(af_score - 70.0))
    confidence_score = round(
        max(
            5.0,
            min(
                96.0,
                quality["signal_quality_index"] * 0.36
                + feature_completeness * 0.22
                + rhythm_remodeling_agreement * 0.16
                + min(distance_from_threshold, 30.0) * 0.42
                - imputed_feature_count * 6.0
                - (15.0 if p_unreliable else 0.0),
            ),
        ),
        1,
    )

    result = {
        "source": "wfdb",
        "input_type": "Digital WFDB",
        "wfdb_loaded": True,
        "analysis_label": "Digital ECG signal analyzed",
        "metadata": metadata,
        "sampling_frequency": metadata["sampling_frequency"],
        "number_of_leads": metadata["number_of_leads"],
        "lead_names": metadata["lead_names"],
        "signal_duration_sec": metadata["duration_seconds"],
        "signal_quality_index": quality["signal_quality_index"],
        "basic_ecg_measurements": basic_measurements,
        "advanced_ecg_interpretation": advanced_interpretation,
        "qrs_count": int(len(qrs)),
        "selected_lead": selected_lead,
        "af_detection_score": round(af_score, 1),
        "af_probability": round(af_score, 1),
        "atrial_remodeling_score": model_result["main_atrial_remodeling_score"],
        "atrial_remodeling_score_logistic": model_result["atrial_remodeling_score_logistic"],
        "atrial_remodeling_score_gradient_boosting": model_result["atrial_remodeling_score_gradient_boosting"],
        "main_atrial_remodeling_score": model_result["main_atrial_remodeling_score"],
        "model_used": model_result["model_used"],
        "model_target": model_result["model_target"],
        "model_auc": model_result["model_auc"],
        "features_used": features_used,
        "logistic_feature_contributions": model_result["logistic_feature_contributions"],
        "top_abnormal_features": model_result["top_abnormal_features"],
        "calibrated": False,
        "calibration_note": "Research output is not clinically calibrated. Fit Platt or isotonic calibration before clinical use.",
        "confidence_score": confidence_score,
        "rhythm": rhythm,
        "signal_quality": quality,
        "rr_features": {
            "rr_mean_ms": round(rr_mean, 1),
            "rr_sd_ms": round(rr_sd, 1),
            "heart_rate_bpm": round(60000.0 / rr_mean, 1) if rr_mean else 0.0,
            "rr_cv": round(rr_cv, 3),
            "sdnn_ms": round(rr_sd, 1),
            "rmssd_ms": round(rmssd, 1),
            "pnn50_percent": round(pnn50, 1),
            "sample_entropy": round(sampen, 3),
            "shannon_entropy": round(shannon, 3),
            "poincare_sd1_ms": round(sd1, 1),
            "poincare_sd2_ms": round(sd2, 1),
            "turning_point_ratio": round(tpr, 3),
            "rr_irregularity_index": round(rr_irregularity, 1),
        },
        "p_wave_features": p_features,
        "morphology_features": {
            "fibrillatory_power": fib_power,
            "dominant_f_wave_hz": dominant_f,
            "beat_morphology_similarity": None,
            "p_duration_ms": features_used["p_duration_ms"],
            "p_amplitude_mv": features_used["p_amplitude_mv"],
            "p_axis_deg": features_used["p_axis_deg"],
            "pr_interval_ms": features_used["pr_interval_ms"],
            "qrs_duration_ms": features_used["qrs_duration_ms"],
            "qtc_ms": features_used["qtc_ms"],
            "ptfv1_mv_ms": features_used["ptfv1_mv_ms"],
        },
        "af_gate_passed": af_gate_passed,
        "reasons": reasons,
        "imputed_features": [
            limitation.split(" unavailable", 1)[0]
            for limitation in demographic_limitations
            if "imputed using" in limitation
        ],
        "warnings": ([] if not low_quality else ["Signal quality index is <50; analysis is limited and repeat ECG is recommended."])
        + demographic_limitations,
        "limitations": [
            "This model detects current atrial abnormality/remodeling.",
            "It does not predict future AF without longitudinal follow-up data.",
            "This is a research prototype and does not diagnose AF. Physician confirmation is required.",
        ]
        + demographic_limitations,
        "waveform_preview": {
            "lead": selected_lead,
            "duration_seconds": round(duration, 2),
            "values": preview,
        },
    }
    logger.info(
        "Cardio MIRAI WFDB result: af_detection_score=%s main_atrial_remodeling_score=%s "
        "logistic_probability=%s gradient_boosting_probability=%s confidence=%s imputed_features=%s",
        result["af_detection_score"],
        result["main_atrial_remodeling_score"],
        result["atrial_remodeling_score_logistic"],
        result["atrial_remodeling_score_gradient_boosting"],
        result["confidence_score"],
        result["imputed_features"],
    )
    return result


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/analyze-wfdb")
async def analyze_wfdb(
    files: list[UploadFile] = File(...),
    age: float | None = Form(None),
    sex: str | None = Form(None),
) -> dict:
    with TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        saved = await _save_uploads(files, temp_dir)
        paths = _extract_zip_files(saved, temp_dir)
        pairs = find_wfdb_pairs(paths)
        if not pairs:
            raise HTTPException(status_code=400, detail="No complete WFDB .hea/.dat record found.")

        try:
            signals, fields = load_wfdb_pair(pairs[0].record_path_without_extension)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Analysis not performed because the digital ECG record could not be read: {exc}",
            ) from exc
        try:
            result = _analyze_signals(signals, fields, age=age, sex=sex)
        except ModelArtifactsMissing as exc:
            raise HTTPException(
                status_code=424,
                detail=f"Model inference not performed. {exc}",
            ) from exc
        except ModelInferenceError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Model inference not performed. {exc}",
            ) from exc
        result["record"] = pairs[0].record_path_without_extension.name
        result["records_found"] = [pair.record_path_without_extension.name for pair in pairs]
        return result
