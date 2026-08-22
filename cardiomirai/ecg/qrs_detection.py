"""QRS/R-peak detection: base energy detector + evidence-gated missed-beat recovery.

Design rationale (see ECG_CORE_V1_1_REPORT.md for the full writeup):

Validated against Patient 2's manually-annotated segment, the existing
global-threshold energy detector achieves 10/10 matches within ~4ms -- it
is NOT broadly inaccurate. The problem is specifically *local*
underdetection: a single threshold computed once over an entire recording
cannot adapt to a stretch where beat energy is locally lower, so a real
beat there never crosses the global threshold at all.

Rather than replace the base detector (which would risk the precision it
already has), this module keeps it completely unchanged and adds a
separate, conservative recovery pass that:
  1. Only looks inside RR gaps that are anomalously long relative to the
     recording's *local* rhythm (not a fixed absolute value).
  2. Computes a threshold *local* to that gap's neighboring beats, not the
     global one.
  3. Requires morphological evidence (energy concentrated in a narrow
     window, like a real QRS, not spread out like a T-wave) before
     accepting a candidate.
  4. Never inserts a beat from RR-interval length alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    window = max(1, int(window))
    kernel = np.ones(window) / window
    return np.convolve(values, kernel, mode="same")


def _energy_trace(signal: np.ndarray, fs: float) -> np.ndarray:
    centered = signal - np.nanmedian(signal)
    derivative = np.diff(centered, prepend=centered[0])
    return _moving_average(derivative * derivative, int(0.12 * fs))


@dataclass
class Beat:
    sample: int
    amplitude: float
    confidence: float
    source: str  # "base" | "recovered"


@dataclass
class QrsDetectionResult:
    beats: list[Beat] = field(default_factory=list)
    base_threshold: float = 0.0
    recovery_attempts: int = 0
    recovery_accepted: int = 0
    recovery_rejected: list[dict] = field(default_factory=list)

    @property
    def peak_samples(self) -> np.ndarray:
        return np.array([b.sample for b in self.beats], dtype=int)


def _detect_qrs_base(signal: np.ndarray, fs: float) -> tuple[np.ndarray, float]:
    """Unchanged base detector (identical behavior to the original _detect_qrs).

    Kept bit-for-bit equivalent so the 10/10, ~4ms-precision result already
    validated against Patient 2's annotations is never put at risk by the
    recovery pass below.
    """

    centered = signal - np.nanmedian(signal)
    energy = _energy_trace(signal, fs)
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

    return np.array(sorted(set(peaks)), dtype=int), float(threshold)


def _sharpness_ratio(centered: np.ndarray, fs: float, sample: int) -> float:
    """How concentrated the energy is around `sample`: high for QRS, low for T-waves.

    QRS complexes are narrow (~80-120ms) with a sharp derivative spike;
    T-waves are broad (~150-250ms) and comparatively slow-rising. Comparing
    energy in a narrow window against a wider window separates the two.
    """

    narrow_half = int(0.05 * fs)
    wide_half = int(0.20 * fs)
    n_start, n_end = max(0, sample - narrow_half), min(len(centered), sample + narrow_half)
    w_start, w_end = max(0, sample - wide_half), min(len(centered), sample + wide_half)
    if n_end <= n_start or w_end <= w_start:
        return 0.0
    narrow_energy = float(np.sum(np.diff(centered[n_start:n_end]) ** 2))
    wide_energy = float(np.sum(np.diff(centered[w_start:w_end]) ** 2)) or 1e-12
    return narrow_energy / wide_energy


def _local_median_rr(rr_ms: np.ndarray, idx: int, span: int = 5) -> float:
    start = max(0, idx - span)
    end = min(len(rr_ms), idx + span + 1)
    window = rr_ms[start:end]
    window = window[np.isfinite(window)]
    return float(np.median(window)) if window.size else float(np.median(rr_ms)) if rr_ms.size else 0.0


def _attempt_recovery(
    centered: np.ndarray,
    energy: np.ndarray,
    fs: float,
    left_beat: int,
    right_beat: int,
    left_amp: float,
    right_amp: float,
    refractory: int,
    left_sharpness: float,
    right_sharpness: float,
) -> dict | None:
    """Search a single suspicious gap for one recoverable beat.

    Returns a dict describing the outcome (accepted candidate or rejection
    reason) for transparency/debugging -- never silently drops information.
    """

    search_start = left_beat + refractory
    search_end = right_beat - refractory
    if search_end <= search_start:
        return {"accepted": False, "reason": "gap too short after refractory margin"}

    # Local threshold: a fraction of the neighboring beats' own energy at
    # their peaks, NOT the global recording-wide threshold. This is what
    # lets a locally-lower-amplitude beat be found without lowering
    # sensitivity (and false-positive risk) everywhere else.
    neighbor_scale = max(
        float(np.max(energy[max(0, left_beat - int(0.05 * fs)):min(len(energy), left_beat + int(0.05 * fs))]) if left_beat < len(energy) else 0.0),
        float(np.max(energy[max(0, right_beat - int(0.05 * fs)):min(len(energy), right_beat + int(0.05 * fs))]) if right_beat < len(energy) else 0.0),
    )
    if neighbor_scale <= 0:
        return {"accepted": False, "reason": "neighboring beats have no measurable energy reference"}
    local_threshold = 0.35 * neighbor_scale

    window_energy = energy[search_start:search_end]
    if window_energy.size == 0:
        return {"accepted": False, "reason": "empty search window"}
    above = np.flatnonzero(window_energy > local_threshold)
    if above.size == 0:
        return {"accepted": False, "reason": "no candidate exceeds local (neighbor-relative) threshold"}

    # Group contiguous runs, evaluate the strongest one.
    runs = np.split(above, np.where(np.diff(above) > 1)[0] + 1)
    best = None
    for run in runs:
        idx_in_window = run[int(np.argmax(window_energy[run]))]
        candidate_sample = search_start + int(idx_in_window)
        sharpness = _sharpness_ratio(centered, fs, candidate_sample)
        candidate_amp = abs(float(centered[candidate_sample]))
        neighbor_amp_avg = (abs(left_amp) + abs(right_amp)) / 2.0 or 1e-9
        amp_ratio = candidate_amp / neighbor_amp_avg
        if best is None or window_energy[idx_in_window] > best["energy"]:
            best = {
                "sample": candidate_sample,
                "energy": float(window_energy[idx_in_window]),
                "sharpness": sharpness,
                "amp_ratio": amp_ratio,
                "amplitude": candidate_amp if centered[candidate_sample] >= 0 else -candidate_amp,
            }

    if best is None:
        return {"accepted": False, "reason": "no candidate run found"}

    # Morphology gate: require QRS-like sharpness (narrow energy concentration),
    # calibrated against THIS gap's own neighboring beats rather than a fixed
    # constant -- what counts as "sharp enough" varies by recording and even
    # by lead, so the neighbors (known-real QRS complexes moments away) are
    # a better reference than any single global number. A floor still applies
    # so a recording with unusually soft neighbors can't make the gate trivial.
    neighbor_sharpness_avg = (left_sharpness + right_sharpness) / 2.0 or 1e-9
    min_sharpness = max(0.40, 0.78 * neighbor_sharpness_avg)
    MIN_AMP_RATIO = 0.25
    if best["sharpness"] < min_sharpness:
        return {
            "accepted": False,
            "reason": f"candidate too broad/slow relative to neighboring QRS complexes (sharpness {best['sharpness']:.2f} vs required {min_sharpness:.2f}, neighbors averaged {neighbor_sharpness_avg:.2f})",
            "candidate_sample": best["sample"],
        }
    if best["amp_ratio"] < MIN_AMP_RATIO:
        return {"accepted": False, "reason": f"candidate amplitude too small relative to neighboring beats (ratio {best['amp_ratio']:.2f} < {MIN_AMP_RATIO})", "candidate_sample": best["sample"]}
    if best["sample"] - left_beat < refractory or right_beat - best["sample"] < refractory:
        return {"accepted": False, "reason": "candidate violates refractory spacing from a neighbor"}

    confidence = float(max(0.0, min(1.0, 0.5 * min(1.0, best["sharpness"]) + 0.5 * min(1.0, best["amp_ratio"]))))
    return {
        "accepted": True,
        "sample": best["sample"],
        "amplitude": best["amplitude"],
        "confidence": confidence,
        "sharpness": best["sharpness"],
        "amp_ratio": best["amp_ratio"],
    }


def detect_qrs(signal: np.ndarray, fs: float, max_recoveries_per_gap: int = 1) -> QrsDetectionResult:
    """Base detection + conservative, evidence-gated missed-beat recovery."""

    centered = signal - np.nanmedian(signal)
    base_peaks, threshold = _detect_qrs_base(signal, fs)
    energy = _energy_trace(signal, fs)
    refractory = max(1, int(0.25 * fs))

    result = QrsDetectionResult(base_threshold=threshold)
    if base_peaks.size == 0:
        return result

    beats: list[Beat] = [Beat(sample=int(p), amplitude=float(centered[p]), confidence=1.0, source="base") for p in base_peaks]

    if base_peaks.size < 2:
        result.beats = beats
        return result

    rr = np.diff(base_peaks).astype(float)
    rr_ms = rr / fs * 1000.0

    recovered: list[Beat] = []
    for i in range(len(base_peaks) - 1):
        local_median = _local_median_rr(rr_ms, i)
        if local_median <= 0:
            continue
        ratio = rr_ms[i] / local_median
        # Only investigate genuinely suspicious gaps -- a real single missed
        # beat roughly doubles the RR, so anything well short of that is
        # left alone (more likely genuine rate variability, e.g. sinus
        # arrhythmia, which must NOT trigger synthetic beat insertion).
        if ratio < 1.7:
            continue

        result.recovery_attempts += 1
        outcome = _attempt_recovery(
            centered,
            energy,
            fs,
            left_beat=int(base_peaks[i]),
            right_beat=int(base_peaks[i + 1]),
            left_amp=float(centered[base_peaks[i]]),
            right_amp=float(centered[base_peaks[i + 1]]),
            refractory=refractory,
            left_sharpness=_sharpness_ratio(centered, fs, int(base_peaks[i])),
            right_sharpness=_sharpness_ratio(centered, fs, int(base_peaks[i + 1])),
        )
        if outcome.get("accepted"):
            result.recovery_accepted += 1
            recovered.append(
                Beat(
                    sample=int(outcome["sample"]),
                    amplitude=float(outcome["amplitude"]),
                    confidence=float(outcome["confidence"]),
                    source="recovered",
                )
            )
        else:
            result.recovery_rejected.append({"gap_index": i, "left": int(base_peaks[i]), "right": int(base_peaks[i + 1]), "rr_ms": float(rr_ms[i]), **outcome})

    beats.extend(recovered)
    beats.sort(key=lambda b: b.sample)
    result.beats = beats
    return result
