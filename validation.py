"""External validation interfaces."""

from typing import Iterable, Sequence

from .schemas import AFPrediction, ECGRecord, ValidationMetrics


class ExternalValidator:
    """Evaluate model performance separately on each dataset."""

    def evaluate(
        self,
        dataset_name: str,
        records: Iterable[ECGRecord],
        labels: Sequence[int],
        predictions: Sequence[AFPrediction],
    ) -> ValidationMetrics:
        raise NotImplementedError("Compute AUC, sensitivity, specificity, F1, PPV, NPV, and calibration.")

