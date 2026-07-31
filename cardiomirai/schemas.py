"""Shared data structures for Cardio MIRAI Version 2."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


LeadName = str


@dataclass(frozen=True)
class ECGRecord:
    """A normalized 12-lead ECG record with provenance."""

    record_id: str
    dataset: str
    signal: object
    sampling_rate: float
    lead_names: Sequence[LeadName]
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SignalQuality:
    """Signal quality assessment used before diagnosis."""

    signal_quality_index: float
    noise_score: float
    baseline_wander_score: float
    missing_lead_names: Sequence[LeadName]
    warnings: Sequence[str] = field(default_factory=list)


@dataclass(frozen=True)
class RhythmFeatures:
    """Validated RR-interval and rhythm irregularity biomarkers."""

    qrs_count: int
    rr_mean_ms: float
    rr_sd_ms: float
    rr_cv: float
    sdnn_ms: float
    rmssd_ms: float
    pnn50_percent: float
    sample_entropy: float
    shannon_entropy: float
    turning_point_ratio: float
    poincare_sd1_ms: float
    poincare_sd2_ms: float


@dataclass(frozen=True)
class PWaveFeatures:
    """Atrial depolarization features measured before QRS complexes."""

    p_wave_presence_ratio: float
    pr_mean_ms: Optional[float]
    pr_sd_ms: Optional[float]
    pr_variability: Optional[float]
    p_wave_duration_ms: Optional[float]
    p_wave_amplitude_mv: Optional[float]
    p_axis_degrees: Optional[float]
    ptfv1: Optional[float]
    missing_p_wave_percent: float


@dataclass(frozen=True)
class MorphologyFeatures:
    """Beat morphology, fibrillatory baseline, and morphology-similarity features."""

    fibrillatory_power: float
    dominant_f_wave_hz: Optional[float]
    beat_morphology_similarity: float
    beat_cluster_count: int
    lead_feature_values: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class AFPrediction:
    """Patient-level AF detection output."""

    af_probability: float
    confidence_score: float
    signal_quality: SignalQuality
    rhythm_label: str
    reasons: Sequence[str]
    top_features: Sequence[Tuple[str, float]]
    warnings: Sequence[str] = field(default_factory=list)
    calibration_model: Optional[str] = None


@dataclass(frozen=True)
class ValidationMetrics:
    """Dataset-level validation metrics."""

    dataset: str
    auc: float
    sensitivity: float
    specificity: float
    f1: float
    ppv: float
    npv: float
    brier_score: Optional[float] = None
    calibration_slope: Optional[float] = None
    calibration_intercept: Optional[float] = None

