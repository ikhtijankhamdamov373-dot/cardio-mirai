# Cardio MIRAI / UzAF-AI Version 2 Roadmap

## Current Version 1 Status

- Prototype website completed.
- ECG upload works.
- Image preprocessing implemented.
- Rhythm extraction implemented.
- Morphology engine implemented.
- PTB-XL morphology features extracted.
- Logistic regression and Gradient Boosting models trained.
- Current PTB-XL-derived atrial abnormality classification:
  - Logistic regression AUC: 0.851
  - Gradient Boosting AUC: 0.907

## Version 2 Objective

Transform Cardio MIRAI / UzAF-AI from a prototype morphology classifier into a publication-quality AF detection and future AF prediction platform.

The central architectural change is:

> Raw 12-lead ECG waveforms become the source of truth. ECG images are used only for inference-time digitization of paper ECGs.

## Step 1: Waveform-First AI

Highest priority.

Replace hand-crafted image heuristics with waveform-based AI.

Requirements:

- Read WFDB/PTB-XL records directly.
- Train on raw 12-lead ECG waveforms.
- Preserve image upload as inference only.
- Use the image module only to digitize paper ECGs.
- Keep waveform ingestion independent from the web dashboard.
- Store extracted features and model-ready tensors with dataset provenance.

Deliverables:

- `cardiomirai.datasets` registry for PTB-XL and future public datasets.
- `cardiomirai.waveforms` loader for WFDB signal records.
- `cardiomirai.preprocessing` pipeline for sampling rate normalization, filtering, lead validation, and signal quality.
- `cardiomirai.models` interfaces for raw-signal and feature-based models.

## Step 2: AF Detection Upgrade

AF probability must depend on both:

- Irregular RR intervals.
- Absent or inconsistent P waves.

Feature requirements:

- Robust P-wave detector.
- P-wave presence ratio.
- PR variability.
- RR variability.
- RMSSD.
- pNN50.
- Sample entropy.
- Turning point ratio.
- Signal quality index.
- Confidence calibration.

Decision safety rule:

- Do not call AF likely from RR irregularity alone.
- Downgrade AF probability when RR is regular and P waves are present.
- If signal quality is insufficient, return low confidence and recommend repeat ECG.

## Step 3: Public Dataset Expansion

Support:

- PTB-XL.
- Chapman ECG.
- Georgia 12-lead.
- CPSC2018.
- PTB Diagnostic ECG.
- MIT-BIH AFDB.
- MIT-BIH Arrhythmia Database.

Requirement:

- Unified preprocessing and labeling interface.
- Dataset-specific adapters must normalize labels into a shared task vocabulary.
- Dataset identity must be retained for external validation and domain-shift analysis.

## Step 4: Probability Calibration

Implement:

- Isotonic calibration.
- Platt scaling.

Return:

- Calibrated probability.
- Confidence score.
- Calibration curve.
- Brier score.

## Step 5: External Validation

Evaluate separately on:

- PTB-XL.
- Chapman.
- CPSC.
- MIT-BIH AFDB.

Report:

- AUC.
- Sensitivity.
- Specificity.
- F1.
- PPV.
- NPV.
- Calibration.
- Brier score.
- Dataset-specific failure modes.

## Step 6: Interpretability

Implement:

- SHAP values for tabular feature models.
- Saliency or attribution maps for raw waveform models.

Show:

- Top contributing ECG features per patient.
- Direction of effect.
- Signal quality warnings.
- Explanation limitations.

## Step 7: Future AF Prediction Architecture

No implementation yet.

Prepare modular architecture for longitudinal prediction.

Inputs:

- ECG morphology.
- Clinical variables.
- Echo variables.
- Laboratory data.

Outputs:

- 1-year AF risk.
- 3-year AF risk.
- 5-year AF risk.

Candidate models:

- Cox proportional hazards model.
- XGBoost survival model.
- DeepSurv.

Design requirement:

- UK Biobank or hospital follow-up cohorts should plug into the prediction engine without changing the ECG detection pipeline.

## Step 8: Clinical Dashboard

Display:

- Signal quality.
- Detected rhythm.
- AF probability.
- Explanation.
- Feature importance.
- Recommendation.
- PDF report export.

Clinical-grade requirements:

- Strict versioning of models and preprocessing.
- Dataset provenance.
- Audit log for inference.
- Calibration status visible to clinicians.
- Research-only and clinical-use modes separated.

## Publication-Quality Milestones

1. Freeze Version 2 preprocessing specification.
2. Train waveform-first baseline on PTB-XL.
3. Add AF rhythm datasets.
4. Validate AF decision layer with RR plus P-wave criteria.
5. Calibrate probabilities.
6. Run external validation by dataset.
7. Add SHAP and patient-level explanations.
8. Prepare manuscript tables and figures.
9. Prepare clinical dashboard report export.

