"""End-to-end AF detection pipeline orchestration."""

from .features import BeatSegmenter, MorphologyFeatureExtractor, PWaveDetector, QRSDetector, RhythmFeatureExtractor
from .models import AFDecisionLayer, ProbabilityModel
from .preprocessing import SignalQualityEstimator, WaveformPreprocessor
from .schemas import AFPrediction, ECGRecord


class AFDetectionPipeline:
    """Waveform-first AF detection pipeline.

    Pipeline stages:
    1. Preprocess raw 12-lead ECG waveform.
    2. Estimate signal quality.
    3. Detect QRS complexes.
    4. Compute RR/rhythm features.
    5. Segment beats.
    6. Detect P waves before QRS complexes.
    7. Compute morphology and fibrillatory baseline features.
    8. Run model inference.
    9. Calibrate probability.
    10. Apply AF decision safety layer.
    """

    def __init__(
        self,
        preprocessor: WaveformPreprocessor,
        quality_estimator: SignalQualityEstimator,
        qrs_detector: QRSDetector,
        rhythm_extractor: RhythmFeatureExtractor,
        beat_segmenter: BeatSegmenter,
        p_wave_detector: PWaveDetector,
        morphology_extractor: MorphologyFeatureExtractor,
        model: ProbabilityModel,
        decision_layer: AFDecisionLayer,
    ) -> None:
        self.preprocessor = preprocessor
        self.quality_estimator = quality_estimator
        self.qrs_detector = qrs_detector
        self.rhythm_extractor = rhythm_extractor
        self.beat_segmenter = beat_segmenter
        self.p_wave_detector = p_wave_detector
        self.morphology_extractor = morphology_extractor
        self.model = model
        self.decision_layer = decision_layer

    def predict(self, record: ECGRecord) -> AFPrediction:
        """Run the full AF detection pipeline on one waveform record."""

        raise NotImplementedError("Wire concrete implementations after dependencies and model artifacts are added.")

