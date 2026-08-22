"""RR-interval-derived statistics, computed once from the final validated beat sequence.

The original codebase computed "rr_irregularity" two different ways in two
different places (extract_basic_ecg_measurements vs _analyze_signals), with
different weights and no shared source of truth. This module is that single
source of truth. Every RR-derived number (HR, SDNN, RMSSD, pNN50, CV,
entropy, Poincare, turning-point ratio, and the renamed "RR Irregularity
Index") is computed here, from the beat sequence produced by
qrs_detection.detect_qrs AFTER missed-beat recovery -- never from the raw
base-detector output alone.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


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


@dataclass
class RrAnalysis:
    beat_count: int
    mean_rr_ms: float | None
    median_rr_ms: float | None
    min_rr_ms: float | None
    max_rr_ms: float | None
    rr_sd_ms: float | None
    rr_cv: float | None
    sdnn_ms: float | None
    rmssd_ms: float | None
    pnn50_percent: float | None
    sample_entropy: float
    shannon_entropy: float
    poincare_sd1: float
    poincare_sd2: float
    turning_point_ratio: float
    heart_rate_bpm: float | None
    median_heart_rate_bpm: float | None
    instantaneous_hr_min: float | None
    instantaneous_hr_max: float | None
    regularity: str
    rr_irregularity_index: float | None  # renamed, advanced-measurements-only metric

    def to_dict(self) -> dict:
        return {
            "beat_count": self.beat_count,
            "mean_rr_ms": self.mean_rr_ms,
            "median_rr_ms": self.median_rr_ms,
            "min_rr_ms": self.min_rr_ms,
            "max_rr_ms": self.max_rr_ms,
            "rr_sd_ms": self.rr_sd_ms,
            "rr_cv": self.rr_cv,
            "sdnn_ms": self.sdnn_ms,
            "rmssd_ms": self.rmssd_ms,
            "pnn50_percent": self.pnn50_percent,
            "sample_entropy": self.sample_entropy,
            "shannon_entropy": self.shannon_entropy,
            "poincare_sd1": self.poincare_sd1,
            "poincare_sd2": self.poincare_sd2,
            "turning_point_ratio": self.turning_point_ratio,
            "heart_rate_bpm": self.heart_rate_bpm,
            "median_heart_rate_bpm": self.median_heart_rate_bpm,
            "instantaneous_hr_range": [self.instantaneous_hr_min, self.instantaneous_hr_max],
            "regularity": self.regularity,
            "rr_irregularity_index": self.rr_irregularity_index,
        }


def analyze_rr(peak_samples: np.ndarray, fs: float) -> RrAnalysis:
    peak_samples = np.asarray(peak_samples, dtype=float)
    if peak_samples.size < 2:
        return RrAnalysis(
            beat_count=int(peak_samples.size),
            mean_rr_ms=None, median_rr_ms=None, min_rr_ms=None, max_rr_ms=None,
            rr_sd_ms=None, rr_cv=None, sdnn_ms=None, rmssd_ms=None, pnn50_percent=None,
            sample_entropy=0.0, shannon_entropy=0.0, poincare_sd1=0.0, poincare_sd2=0.0,
            turning_point_ratio=0.0, heart_rate_bpm=None, median_heart_rate_bpm=None,
            instantaneous_hr_min=None, instantaneous_hr_max=None, regularity="unavailable",
            rr_irregularity_index=None,
        )

    rr_ms = np.diff(peak_samples) / fs * 1000.0
    mean_rr = float(np.mean(rr_ms))
    median_rr = float(np.median(rr_ms))
    sd_rr = float(np.std(rr_ms))
    cv_rr = float(sd_rr / mean_rr) if mean_rr else 0.0
    rmssd = float(math.sqrt(np.mean(np.diff(rr_ms) ** 2))) if rr_ms.size > 1 else 0.0
    pnn50 = float(np.mean(np.abs(np.diff(rr_ms)) > 50.0) * 100.0) if rr_ms.size > 1 else 0.0
    sampen = _sample_entropy(rr_ms)
    shannon = _shannon_entropy(rr_ms)
    sd1, sd2 = _poincare(rr_ms)
    tpr = _turning_point_ratio(rr_ms)

    instantaneous_hr = 60000.0 / rr_ms
    p_features_presence = None  # populated by caller if needed; kept out of this module deliberately

    if cv_rr < 0.08:
        regularity = "regular"
    elif cv_rr < 0.16:
        regularity = "mildly irregular"
    else:
        regularity = "irregular"

    # Single, shared irregularity formula (replaces the two divergent ones).
    # Bounded 0-100, intended ONLY as an advanced/research metric -- NOT as
    # an AF probability. See af_evidence.py for the actual AF evidence logic,
    # which treats this as one input among several rather than the primary
    # signal.
    irregularity = min(
        100.0,
        cv_rr * 120.0 + rmssd / 6.0 + pnn50 * 0.35 + sampen * 8.0 + shannon * 3.0 + tpr * 10.0,
    )

    return RrAnalysis(
        beat_count=int(peak_samples.size),
        mean_rr_ms=round(mean_rr, 1),
        median_rr_ms=round(median_rr, 1),
        min_rr_ms=round(float(np.min(rr_ms)), 1),
        max_rr_ms=round(float(np.max(rr_ms)), 1),
        rr_sd_ms=round(sd_rr, 1),
        rr_cv=round(cv_rr, 3),
        sdnn_ms=round(sd_rr, 1),  # SDNN == SD of NN(RR) intervals for a single short recording
        rmssd_ms=round(rmssd, 1),
        pnn50_percent=round(pnn50, 1),
        sample_entropy=round(sampen, 3),
        shannon_entropy=round(shannon, 3),
        poincare_sd1=round(sd1, 2),
        poincare_sd2=round(sd2, 2),
        turning_point_ratio=round(tpr, 3),
        heart_rate_bpm=round(60000.0 / mean_rr, 1) if mean_rr else None,
        median_heart_rate_bpm=round(60000.0 / median_rr, 1) if median_rr else None,
        instantaneous_hr_min=round(float(np.min(instantaneous_hr)), 1) if instantaneous_hr.size else None,
        instantaneous_hr_max=round(float(np.max(instantaneous_hr)), 1) if instantaneous_hr.size else None,
        regularity=regularity,
        rr_irregularity_index=round(irregularity, 1),
    )
