"""Dataset registry and dataset adapter contracts."""

from dataclasses import dataclass
from typing import Dict, Iterable, Protocol

from .schemas import ECGRecord


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    modality: str
    native_format: str
    primary_task: str
    external_validation_group: str
    notes: str


DATASET_REGISTRY: Dict[str, DatasetSpec] = {
    "ptbxl": DatasetSpec(
        name="PTB-XL",
        modality="12-lead ECG",
        native_format="WFDB",
        primary_task="morphology and diagnostic labels",
        external_validation_group="PTB-XL",
        notes="Primary Version 1 source. Use direct waveform loading for Version 2.",
    ),
    "chapman": DatasetSpec(
        name="Chapman ECG",
        modality="12-lead ECG",
        native_format="WFDB or CSV depending mirror",
        primary_task="rhythm and diagnostic classes",
        external_validation_group="Chapman",
        notes="Useful for AF rhythm detection and domain-shift testing.",
    ),
    "georgia": DatasetSpec(
        name="Georgia 12-lead",
        modality="12-lead ECG",
        native_format="WFDB",
        primary_task="rhythm and diagnostic classes",
        external_validation_group="Georgia",
        notes="Useful for PhysioNet challenge-style multi-label training.",
    ),
    "cpsc2018": DatasetSpec(
        name="CPSC2018",
        modality="12-lead ECG",
        native_format="MAT/WFDB-convertible",
        primary_task="arrhythmia classification",
        external_validation_group="CPSC",
        notes="External validation target for arrhythmia and AF detection.",
    ),
    "ptb_diagnostic": DatasetSpec(
        name="PTB Diagnostic ECG",
        modality="12-lead ECG",
        native_format="WFDB",
        primary_task="diagnostic ECG classification",
        external_validation_group="PTB Diagnostic",
        notes="Useful for diagnostic confounders and ischemia/cardiomyopathy labels.",
    ),
    "mitbih_afdb": DatasetSpec(
        name="MIT-BIH AFDB",
        modality="rhythm ECG",
        native_format="WFDB",
        primary_task="AF rhythm detection",
        external_validation_group="MIT-BIH AFDB",
        notes="Rhythm-focused AF validation dataset.",
    ),
    "mitbih_arrhythmia": DatasetSpec(
        name="MIT-BIH Arrhythmia Database",
        modality="rhythm ECG",
        native_format="WFDB",
        primary_task="arrhythmia beat/rhythm classification",
        external_validation_group="MIT-BIH Arrhythmia",
        notes="Useful for rhythm confounders and beat-level validation.",
    ),
}


class DatasetAdapter(Protocol):
    """Adapter interface for dataset-specific loading and label normalization."""

    dataset_key: str

    def records(self) -> Iterable[ECGRecord]:
        """Yield normalized ECG records with dataset provenance."""

    def label_for_record(self, record: ECGRecord) -> Dict[str, int]:
        """Return normalized task labels for a record."""


def get_dataset_spec(dataset_key: str) -> DatasetSpec:
    """Return the registered dataset specification."""

    return DATASET_REGISTRY[dataset_key]

