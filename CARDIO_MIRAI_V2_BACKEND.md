# Cardio MIRAI Version 2 Backend Design

## Purpose

This backend scaffold separates research ECG modeling from the static website.

The static website remains useful for:

- Patient-facing prototype flow.
- ECG image/PDF upload.
- Dashboard demonstration.

The backend becomes responsible for:

- WFDB/PTB-XL waveform ingestion.
- Unified public dataset preprocessing.
- QRS detection.
- P-wave detection.
- RR and morphology feature extraction.
- Raw 12-lead ECG model training.
- Probability calibration.
- External validation.
- SHAP explanations.
- Future longitudinal AF prediction.
- PDF report export.

## Local Backend Launch

Install dependencies:

```powershell
py -3 -m pip install -r requirements.txt
```

Run the WFDB API:

```powershell
py -3 -m uvicorn cardiomirai.api:app --reload --host 127.0.0.1 --port 8000
```

The static prototype calls:

```text
POST http://127.0.0.1:8000/api/analyze-wfdb
```

## Module Map

| Module | Responsibility |
| --- | --- |
| `cardiomirai.datasets` | Dataset registry and adapter contract for PTB-XL, Chapman, Georgia, CPSC2018, PTB Diagnostic, AFDB, and MIT-BIH Arrhythmia. |
| `cardiomirai.preprocessing` | Resampling, filtering, lead normalization, signal quality estimation. |
| `cardiomirai.features` | QRS detection, RR features, beat segmentation, P-wave features, morphology and spectral features. |
| `cardiomirai.models` | Feature bundle, model protocols, raw waveform model interface, AF decision safety layer. |
| `cardiomirai.calibration` | Isotonic calibration, Platt scaling, calibration curve, Brier score. |
| `cardiomirai.validation` | External validation metrics by dataset. |
| `cardiomirai.interpretability` | SHAP feature attributions. |
| `cardiomirai.survival` | Future AF prediction architecture for 1-, 3-, and 5-year risk. |
| `cardiomirai.reporting` | Dashboard report schema and PDF export contract. |
| `cardiomirai.pipeline` | End-to-end AF detection orchestration. |

## Training Flow

1. Register dataset adapter.
2. Load raw WFDB waveforms.
3. Normalize sampling rate and lead order.
4. Estimate signal quality.
5. Detect QRS complexes.
6. Compute RR biomarkers.
7. Segment beats.
8. Detect P waves in the 120-250 ms pre-QRS window.
9. Compute P-wave and PR variability biomarkers.
10. Compute fibrillatory baseline and morphology similarity.
11. Train baseline Gradient Boosting or XGBoost model on extracted biomarkers.
12. Train raw 12-lead ECG model separately.
13. Calibrate probability with isotonic or Platt scaling.
14. Validate externally by dataset.
15. Save model, preprocessing config, calibration model, and validation report together.

## AF Decision Principle

AF probability must not depend on RR irregularity alone.

AF likely requires:

- High RR irregularity.
- Low P-wave presence ratio or inconsistent P waves.
- Fibrillatory baseline evidence when available.
- Acceptable signal quality.

If signal quality is insufficient:

- Return low confidence.
- Recommend repeat ECG.
- Do not issue a high-confidence AF label.

## Image Upload Policy

Image upload remains inference-only.

Image pipeline responsibilities:

- Detect paper grid.
- Deskew.
- Denoise.
- Digitize waveform.
- Estimate signal quality.
- Pass digitized waveform into the same backend pipeline.

Images must not be used as the primary training source while WFDB waveform records are available.

## WFDB Upload Policy

WFDB records must be uploaded as a complete pair:

- `record_name.hea`
- `record_name.dat`

A `.dat` file alone is invalid because the header stores sampling frequency, gain, baseline, number of leads, and lead names.

Backend workflow:

```python
from pathlib import Path
import wfdb

record_path = Path(temp_dir) / "record_name"
signals, fields = wfdb.rdsamp(str(record_path))
```

ZIP workflow:

1. Extract ZIP into a temporary folder.
2. Search recursively for `.hea` files.
3. For each `.hea`, find a matching `.dat` with the same basename.
4. If one pair is found, call `wfdb.rdsamp(record_path_without_extension)`.
5. If multiple pairs are found, analyze the first record or return a selector to the UI.

After loading WFDB:

- Display sampling frequency.
- Display number of leads.
- Display lead names.
- Display signal duration.
- Render waveform preview.
- Run the same digital ECG pipeline used for model inference.

## External Validation Protocol

Report every metric separately for:

- PTB-XL.
- Chapman.
- CPSC2018.
- MIT-BIH AFDB.

Minimum metrics:

- AUC.
- Sensitivity.
- Specificity.
- F1.
- PPV.
- NPV.
- Brier score.
- Calibration curve.

## Publication Tables

Recommended manuscript tables:

1. Dataset characteristics.
2. Feature set definitions.
3. Internal validation performance.
4. External validation performance.
5. Calibration performance.
6. Ablation study:
   - RR only.
   - P-wave only.
   - Morphology only.
   - RR + P wave.
   - RR + P wave + morphology.
   - Raw waveform model.
7. Failure analysis by signal quality.
