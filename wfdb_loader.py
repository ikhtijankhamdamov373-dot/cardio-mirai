"""WFDB record loading helpers for Cardio MIRAI.

WFDB digital ECG records require at least two files with the same basename:

- rec_1.hea: header containing sampling rate, gain, lead names, baseline, units.
- rec_1.dat: binary signal samples.

The record path passed to wfdb.rdsamp must omit the file extension:

    signals, fields = wfdb.rdsamp(str(temp_dir / "rec_1"))
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, Sequence
from zipfile import ZipFile


@dataclass(frozen=True)
class WFDBRecordInfo:
    record_path_without_extension: Path
    header_path: Path
    signal_path: Path


def find_wfdb_pairs(paths: Iterable[Path]) -> list[WFDBRecordInfo]:
    """Find matching .hea/.dat pairs by basename."""

    headers = {path.with_suffix("").name: path for path in paths if path.suffix.lower() == ".hea"}
    signals = {path.with_suffix("").name: path for path in paths if path.suffix.lower() == ".dat"}
    pairs: list[WFDBRecordInfo] = []

    for basename, header_path in headers.items():
        signal_path = signals.get(basename)
        if signal_path is not None:
            pairs.append(
                WFDBRecordInfo(
                    record_path_without_extension=header_path.with_suffix(""),
                    header_path=header_path,
                    signal_path=signal_path,
                )
            )

    return pairs


def load_wfdb_pair(record_path_without_extension: Path):
    """Load a complete WFDB record using wfdb.rdsamp."""

    import wfdb

    return wfdb.rdsamp(str(record_path_without_extension))


def load_first_record_from_zip(zip_path: Path):
    """Extract a ZIP and load the first complete WFDB .hea/.dat pair found recursively."""

    with TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        with ZipFile(zip_path) as archive:
            archive.extractall(temp_dir)

        paths = [path for path in temp_dir.rglob("*") if path.is_file()]
        pairs = find_wfdb_pairs(paths)
        if not pairs:
            raise ValueError("No complete WFDB .hea/.dat record found in ZIP.")

        return load_wfdb_pair(pairs[0].record_path_without_extension)


def wfdb_metadata(signals, fields: dict) -> dict:
    """Return metadata needed by the dashboard after wfdb.rdsamp."""

    sample_count = len(signals)
    sampling_frequency = float(fields["fs"])
    duration_seconds = sample_count / sampling_frequency if sampling_frequency else 0.0
    lead_names: Sequence[str] = fields.get("sig_name", [])

    return {
        "sampling_frequency": sampling_frequency,
        "number_of_leads": len(lead_names),
        "lead_names": list(lead_names),
        "duration_seconds": duration_seconds,
    }

