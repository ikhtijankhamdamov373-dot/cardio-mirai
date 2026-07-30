"""Build the full Cardio MIRAI PTB-XL morphology feature table.

This replacement script is intentionally strict about saving:

- It does not merely print the output path.
- It creates the output directory.
- It executes DataFrame.to_csv().
- It verifies os.path.exists(output_csv).
- It prints the final file size in bytes.
- It raises an explicit exception if the CSV is missing or empty.

Example:

    py -3 scripts/stage3_build_table_full.py ^
      --ptbxl-root "C:\\path\\to\\ptb-xl-a-large-publicly-available-electrocardiography-dataset-1.0.3" ^
      --output-csv features_table.csv

For a quick smoke test:

    py -3 scripts/stage3_build_table_full.py --ptbxl-root C:\\ptb-xl --limit 25
"""

from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path
from typing import Any

import neurokit2 as nk
import numpy as np
import pandas as pd
import wfdb


LEADS = ["I", "II", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6"]
ATRIAL_ABNORMALITY_CODES = {
    "LAO/LAE",
    "RAO/RAE",
    "LAE",
    "RAE",
    "BAE",
    "ABQRS",
    "LAFB",
}


def lead_index(name: str) -> int:
    return LEADS.index(name)


def safe_mean(values: list[float]) -> float:
    clean = [value for value in values if value is not None and not np.isnan(value)]
    return float(np.mean(clean)) if clean else float("nan")


def interval_ms(start_values: list[Any], end_values: list[Any], fs: float) -> float:
    values = []
    for start, end in zip(start_values, end_values):
        if start is None or end is None:
            continue
        if np.isnan(start) or np.isnan(end):
            continue
        values.append((end - start) / fs * 1000.0)
    return safe_mean(values)


def parse_scp_codes(value: str) -> dict:
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def current_atrial_abnormality_label(scp_codes: dict) -> int:
    return int(any(code in ATRIAL_ABNORMALITY_CODES for code in scp_codes.keys()))


def extract_morphology(signal: np.ndarray, fs: float) -> dict:
    lead_ii = signal[:, lead_index("II")]
    cleaned = nk.ecg_clean(lead_ii, sampling_rate=fs)
    _, rpeaks = nk.ecg_peaks(cleaned, sampling_rate=fs)
    r = rpeaks["ECG_R_Peaks"]

    output = {
        "p_duration_ms": np.nan,
        "p_amplitude_mv": np.nan,
        "p_axis_deg": np.nan,
        "pr_interval_ms": np.nan,
        "qrs_duration_ms": np.nan,
        "qtc_ms": np.nan,
        "ptfv1_mv_ms": np.nan,
    }
    if len(r) < 3:
        return output

    _, waves = nk.ecg_delineate(cleaned, rpeaks, sampling_rate=fs, method="dwt")
    p_on = waves.get("ECG_P_Onsets", [])
    p_off = waves.get("ECG_P_Offsets", [])
    p_peak = waves.get("ECG_P_Peaks", [])
    q_on = waves.get("ECG_R_Onsets", [])
    s_off = waves.get("ECG_R_Offsets", [])
    t_off = waves.get("ECG_T_Offsets", [])

    output["p_duration_ms"] = interval_ms(p_on, p_off, fs)
    output["pr_interval_ms"] = interval_ms(p_on, q_on, fs)
    output["qrs_duration_ms"] = interval_ms(q_on, s_off, fs)
    output["p_amplitude_mv"] = safe_mean(
        [lead_ii[int(index)] for index in p_peak if index is not None and not np.isnan(index)]
    )

    qt_ms = interval_ms(q_on, t_off, fs)
    rr_seconds = safe_mean([(r[index + 1] - r[index]) / fs for index in range(len(r) - 1)])
    if not np.isnan(qt_ms) and rr_seconds and not np.isnan(rr_seconds) and rr_seconds > 0:
        output["qtc_ms"] = qt_ms / np.sqrt(rr_seconds)

    v1 = signal[:, lead_index("V1")]
    ptfv1_values = []
    for onset, offset in zip(p_on, p_off):
        if onset is None or offset is None or np.isnan(onset) or np.isnan(offset):
            continue
        segment = v1[int(onset):int(offset)]
        negative = segment[segment < 0]
        if len(negative):
            ptfv1_values.append(abs(np.min(negative)) * (len(negative) / fs * 1000.0))
    output["ptfv1_mv_ms"] = safe_mean(ptfv1_values)

    def p_amp(lead: str) -> float:
        samples = signal[:, lead_index(lead)]
        return safe_mean([samples[int(index)] for index in p_peak if index is not None and not np.isnan(index)])

    p_i = p_amp("I")
    p_avf = p_amp("AVF")
    if not np.isnan(p_i) and not np.isnan(p_avf):
        output["p_axis_deg"] = float(np.degrees(np.arctan2(p_avf, p_i)))

    return output


def build_table(ptbxl_root: Path, limit: int | None = None) -> pd.DataFrame:
    db_path = ptbxl_root / "ptbxl_database.csv"
    if not db_path.exists():
        raise FileNotFoundError(f"PTB-XL database CSV not found: {db_path}")

    database = pd.read_csv(db_path)
    if limit is not None:
        database = database.head(limit)

    rows = []
    for row_index, row in database.iterrows():
        record_relative = row.get("filename_lr")
        if not isinstance(record_relative, str) or not record_relative:
            continue
        record_path = ptbxl_root / record_relative
        record_without_extension = str(record_path.with_suffix(""))

        try:
            signal, fields = wfdb.rdsamp(record_without_extension)
            features = extract_morphology(signal, float(fields["fs"]))
        except Exception as exc:
            print(f"Skipping {record_relative}: {exc}")
            continue

        scp_codes = parse_scp_codes(str(row.get("scp_codes", "{}")))
        features.update(
            {
                "ecg_id": row.get("ecg_id"),
                "age": row.get("age", np.nan),
                "sex": row.get("sex", np.nan),
                "current_atrial_abnormality": current_atrial_abnormality_label(scp_codes),
            }
        )
        rows.append(features)

        if len(rows) % 250 == 0:
            print(f"Processed {len(rows)} records...")

    table = pd.DataFrame(rows)
    if table.empty:
        raise RuntimeError("No feature rows were extracted; refusing to save an empty table.")
    return table


def save_feature_table(table: pd.DataFrame, output_csv: Path) -> None:
    output_csv = output_csv.resolve()
    output_dir = output_csv.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    if not output_dir.exists():
        raise RuntimeError(f"Output directory was not created: {output_dir}")
    if table.empty:
        raise RuntimeError("Feature table is empty; refusing to save.")

    try:
        table.to_csv(output_csv, index=False)
    except Exception as exc:
        raise RuntimeError(f"DataFrame.to_csv() failed for {output_csv}: {exc}") from exc

    if not os.path.exists(output_csv):
        raise RuntimeError(f"Feature table save failed; file does not exist: {output_csv}")

    size_bytes = os.path.getsize(output_csv)
    if size_bytes <= 0:
        raise RuntimeError(f"Feature table save failed; file is empty: {output_csv}")

    print(f"Feature table saved to: {output_csv}")
    print(f"Verified feature table exists: {os.path.exists(output_csv)}")
    print(f"Feature table size: {size_bytes} bytes")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ptbxl-root", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, default=Path("features_table.csv"))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    table = build_table(args.ptbxl_root.resolve(), limit=args.limit)
    save_feature_table(table, args.output_csv)


if __name__ == "__main__":
    main()

