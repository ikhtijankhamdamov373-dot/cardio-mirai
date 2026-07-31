"""Model interfaces for AF detection and atrial abnormality classification."""

from dataclasses import dataclass
from typing import Dict, Protocol

from .schemas import AFPrediction, MorphologyFeatures, PWaveFeatures, RhythmFeatures, SignalQuality


@dataclass(frozen=True)
class FeatureBundle:
    """Combined features passed to a model."""

    rhythm: RhythmFeatures
    p_wave: PWaveFeatures
    morphology: MorphologyFeatures
    signal_quality: SignalQuality
    extra: Dict[str, float]


class ProbabilityModel(Protocol):
    """Common model interface for Gradient Boosting, XGBoost, or deep models."""

    model_name: str
    model_version: str

    def predict_proba(self, features: FeatureBundle) -> float:
        """Return uncalibrated AF probability."""


class AFDecisionLayer:
    """Safety layer requiring both RR irregularity and P-wave absence."""

    def apply(self, probability: float, features: FeatureBundle) -> AFPrediction:
        """Apply conservative clinical decision rules after model inference."""

        raise NotImplementedError("Implement gated AF probability and clinical warnings.")


class RawWaveformModel(Protocol):
    """Interface for raw 12-lead ECG AI models."""

    model_name: str
    model_version: str

    def predict_proba_from_waveform(self, signal: object, sampling_rate: float) -> float:
        """Return AF probability from raw waveform tensor."""

