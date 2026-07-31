"""Feature extraction contracts for AF detection and atrial morphology."""

from dataclasses import dataclass
from typing import Sequence

from .schemas import ECGRecord, MorphologyFeatures, PWaveFeatures, RhythmFeatures


@dataclass(frozen=True)
class QRSDetectionResult:
    qrs_sample_indices: Sequence[int]
    method: str


@dataclass(frozen=True)
class BeatSegmentationResult:
    beat_windows: Sequence[tuple[int, int]]
    aligned_qrs_indices: Sequence[int]


class QRSDetector:
    """Detect QRS complexes using NeuroKit2 or Pan-Tompkins."""

    def detect(self, record: ECGRecord) -> QRSDetectionResult:
        raise NotImplementedError("Use NeuroKit2 ecg_peaks or Pan-Tompkins implementation.")


class RhythmFeatureExtractor:
    """Compute RR interval features validated for AF detection."""

    def extract(self, record: ECGRecord, qrs: QRSDetectionResult) -> RhythmFeatures:
        raise NotImplementedError("Compute RR mean, SDNN, RMSSD, pNN50, entropy, TPR, SD1, and SD2.")


class BeatSegmenter:
    """Segment beats around detected QRS complexes."""

    def segment(self, record: ECGRecord, qrs: QRSDetectionResult) -> BeatSegmentationResult:
        raise NotImplementedError("Implement lead-aware beat segmentation around QRS complexes.")


class PWaveDetector:
    """Detect P waves in the 120-250 ms pre-QRS search window."""

    def extract(self, record: ECGRecord, qrs: QRSDetectionResult) -> PWaveFeatures:
        raise NotImplementedError("Detect P waves, PR interval consistency, PTFV1, and missing P-wave ratio.")


class MorphologyFeatureExtractor:
    """Compute morphology similarity and fibrillatory baseline biomarkers."""

    def extract(
        self,
        record: ECGRecord,
        qrs: QRSDetectionResult,
        beats: BeatSegmentationResult,
    ) -> MorphologyFeatures:
        raise NotImplementedError("Compute f-wave spectral power, beat similarity, clusters, and lead features.")

