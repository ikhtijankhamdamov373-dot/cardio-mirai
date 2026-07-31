"""Dashboard and PDF report schemas."""

from dataclasses import dataclass
from typing import Sequence

from .interpretability import FeatureAttribution
from .schemas import AFPrediction


@dataclass(frozen=True)
class ClinicalRecommendation:
    priority: str
    text: str


@dataclass(frozen=True)
class DashboardReport:
    prediction: AFPrediction
    feature_attributions: Sequence[FeatureAttribution]
    recommendations: Sequence[ClinicalRecommendation]
    pdf_ready: bool


class PDFReportExporter:
    """Export clinical dashboard output to PDF."""

    def export(self, report: DashboardReport, output_path: str) -> str:
        raise NotImplementedError("Implement PDF export after dashboard schema stabilizes.")

