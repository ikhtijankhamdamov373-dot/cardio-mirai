# Cardio MIRAI PTB-XL Model Artifacts

This folder is reserved for real trained PTB-XL atrial remodeling models.

Do not place dummy models here.

## Required Files

The backend expects exactly:

- `atrial_logistic_model.pkl`
- `atrial_gradient_boosting_model.pkl`
- `feature_scaler.pkl`
- `feature_columns.json`
- `model_metadata.json`

## Dataset

Training source:

- PTB-XL-derived `features_table.csv`
- Target: current atrial abnormality / atrial electrical remodeling
- Not a future AF prediction target

## Required Feature List

The production feature order is:

1. `age`
2. `sex`
3. `p_duration_ms`
4. `p_amplitude_mv`
5. `p_axis_deg`
6. `pr_interval_ms`
7. `qrs_duration_ms`
8. `qtc_ms`
9. `ptfv1_mv_ms`

This order is saved in `feature_columns.json` and must match the backend inference pipeline.

## Training

Run from the project root after placing `features_table.csv` in the project folder:

```powershell
py -3 scripts/train_ptbxl_production_models.py --features-table features_table.csv
```

If your target column has a non-default name:

```powershell
py -3 scripts/train_ptbxl_production_models.py --features-table features_table.csv --target-column atrial_abnormality
```

The script performs:

- Stratified train/test split
- Median imputation fitted only on the training split
- StandardScaler fitted only on the training split for logistic regression
- Logistic Regression training
- XGBoost training if available, otherwise `HistGradientBoostingClassifier`
- Metrics calculation
- Calibration curve points
- Artifact saving
- Reload identity verification

## Saved Metrics

`model_metadata.json` stores:

- dataset
- records used
- target column
- model target
- AUC
- accuracy
- sensitivity
- specificity
- precision
- recall
- F1
- PPV
- NPV
- confusion matrix
- Brier score
- calibration curve points

## Smoke Test

After training:

```powershell
py -3 scripts/test_saved_models.py --features-table features_table.csv
```

The script reloads the saved artifacts and prints:

- predicted probability
- predicted class
- true class

## Replacing Models

Future models can replace these artifacts if they preserve:

- the expected artifact filenames, or
- backend loading code is updated intentionally

For future AF prediction models, do not reuse this target label. The current model detects current atrial abnormality/remodeling only.

