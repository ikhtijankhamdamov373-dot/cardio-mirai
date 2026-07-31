"""Waveform-first ECG preprocessing contracts."""

from dataclasses import dataclass
from typing import Sequence

from .schemas import ECGRecord, SignalQuality


@dataclass(frozen=True)
class PreprocessingConfig:
    target_sampling_rate: float = 500.0
    bandpass_low_hz: float = 0.5
    bandpass_high_hz: float = 40.0
    notch_hz: float = 50.0
    required_leads: Sequence[str] = (
        "I",
        "II",
        "III",
        "aVR",
        "aVL",
        "aVF",
        "V1",
        "V2",
        "V3",
        "V4",
        "V5",
        "V6",
    )


class WaveformPreprocessor:
    """Normalize raw ECG records before feature extraction or model training."""

    def __init__(self, config: PreprocessingConfig | None = None) -> None:
        self.config = config or PreprocessingConfig()

    def transform(self, record: ECGRecord) -> ECGRecord:
        """Return a filtered, resampled, lead-normalized ECG record.

        Production implementation should use WFDB, scipy, numpy, and robust
        lead mapping. This scaffold intentionally leaves algorithmic code out
        until dependencies and data paths are fixed.
        """

        raise NotImplementedError("Implement waveform filtering, resampling, and lead normalization.")


class SignalQualityEstimator:
    """Estimate ECG signal quality before diagnosis."""

    def estimate(self, record: ECGRecord) -> SignalQuality:
        """Return signal quality index and warnings."""

        raise NotImplementedError("Implement SQI, noise, baseline wander, and missing-lead assessment.")

