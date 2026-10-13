# 03. Analytics Pipeline

This document describes the pipeline as it actually exists in `src/`, and reports the actual results of the most recent executions of `scripts/run_pipeline.py --source synthetic` (§§1–9, SYNTHETIC) and `scripts/run_real_pipeline.py` (§10, REAL-DATA EXPLORATORY). See `outputs/reports/run_log.md` and `outputs/reports/experiment-registry.csv` for the unedited machine-generated output this document summarizes.

**Sections 1–9 report SYNTHETIC results: they verify the pipeline's mechanics, not any finding about real Bangladesh agriculture. Section 10 reports a separate real-data exploratory run (unvalidated, provenance unresolved) and is never mixed with them.** See `docs/data-provenance/provenance-register.md`.

## Framing: what this pipeline actually estimates

This is **retrospective/seasonal yield-estimation research**, not a pre-season forecasting or crop-recommendation tool. For the synthetic demonstration, inputs include generated same-period rainfall, temperature and humidity. The real jute/wheat experiment instead uses the source-reported `Rainfall in MM` field (aggregation unverified) and has no temperature/humidity inputs. These are retrospective analyses of periods already observed; the model is not a pre-season forecast. A genuinely forward-looking advisory tool would need different, truly predictive inputs (e.g. seasonal forecasts, not observed totals), which this prototype does not implement.

## 1–4. Ingestion, validation, cleaning, feature engineering

Unchanged in purpose from earlier drafts, with one structural fix: **`engineer_features()` now performs only deterministic, row-wise transforms** (two derived features: `rainfall_per_area`, `temp_humidity_index`). It does **not** impute missing values or one-hot encode categoricals — those require dataset-level statistics (a median, a category list) that must be fit only on training data, so they were moved into `src/models/preprocessing.py`, fit after the split. This was a **real leakage bug** in an earlier version, caught in pre-release review: the previous code computed a median-fill value and a category-dummy matrix from the *entire* dataset before splitting, meaning test-set rows could influence training-time preprocessing. Fixed and covered by a direct regression test (`test_preprocessor_imputation_uses_only_fit_split_statistics`).

## 5. Evaluation methodology — three-way split (synthetic: district-held-out; real run: chronological, see §10)

**Fit / calibrate / test**, not a two-way split — for the synthetic demonstration, by district (`GroupShuffleSplit`), so no district appears in more than one set. The real-data experiment uses a separate chronological split by year (see §10):

- **Fit** — used to train the preprocessor and the model.
- **Calibrate** — a second, genuinely held-out set used only to compute conformal calibration residuals. Never touched during model fitting.
- **Test** — touched only for final evaluation and empirical coverage measurement.

This matters specifically because the earlier implementation only had fit/test, and used MAE/RMSE computed on test as if they were an "uncertainty range" — which is a different statistical claim than what MAE/RMSE actually measure (aggregate evaluation error, not a per-prediction interval). The calibration split exists specifically to support the real interval described below.

## 6. Models and actual results — SYNTHETIC DEMONSTRATION (DEMONSTRATION ONLY — NOT EMPIRICAL EVIDENCE)

| Model | n_fit | n_calib | n_test | MAE (t/ha) | RMSE (t/ha) | R² | Conformal halfwidth | Target coverage | Empirical coverage |
|---|---|---|---|---|---|---|---|---|---|
| Naive mean baseline | 293 | 131 | 176 | 0.5409 | 0.7114 | −0.0100 | 1.063 | 0.90 | 0.892 |
| Ridge regression | 293 | 131 | 176 | 0.4410 | 0.5843 | 0.3185 | 0.980 | 0.90 | 0.926 |
| Random Forest | 293 | 131 | 176 | 0.3928 | 0.5123 | 0.4761 | 0.842 | 0.90 | 0.898 |

Random seed 42, fixed for reproducibility. **MAE and RMSE are aggregate evaluation-set error metrics — not an individual-prediction uncertainty bound.** The conformal halfwidth and its empirical coverage (computed by actually checking what fraction of test predictions fell within the interval) are the real per-prediction uncertainty quantification. All three models' empirical coverage landed close to the 90% target — a genuine, if small-sample, confirmation the conformal procedure behaves as intended, not a planted result.

## 7. A real held-out example (not a hardcoded or copied value)

```
District: Chattogram, Crop: Jute, Season: Aman
Observed yield:   3.911 t/ha
Predicted yield:  3.732 t/ha   (from random_forest.predict(), genuinely held out)
Residual:         0.179 t/ha
90% prediction interval: [2.889, 4.574] t/ha
```

An earlier version of this pipeline had a real bug here: the example decision-support record used the row's own *observed* target value, mislabelled as `predicted_yield`. Fixed, and covered by `test_held_out_prediction_is_model_generated_not_copied`, which explicitly asserts the predicted and observed values are not identical and that changing the model changes the prediction.

## 8. Explainability

Random Forest importances (impurity-based, against the preprocessor's actual output feature names, e.g. `numeric__rainfall_mm`) rank rainfall and temperature highest on this run — **exactly matching the synthetic generator's planted formula**. This confirms the pipeline correctly recovers a known signal (a mechanics check), and is explicitly not a finding about real crop yield drivers.

## 9. Governance checks (actual run output)

```
[PASS] no_personal_data
[PASS] district_coverage: 10 distinct districts (minimum expected: 3)
[PASS] error_metrics_present: MAE and RMSE present for every model
[PASS] prediction_interval_present: conformal interval + empirical coverage present for every model
[PASS] synthetic_label_present
[PASS] source_type_plausible: no path/source_type mismatch detected
```

`check_uncertainty_present()` was renamed to `check_error_metrics_present()` — its old name implied it verified uncertainty quantification, when it only checked that MAE/RMSE existed. A new `check_prediction_interval_present()` was added to actually verify the conformal-interval fields.

## 10. Real-data run (jute & wheat) — REAL DATA, UNVALIDATED

Source: `data/raw/sajidahmed12_crop_data/{jute,wheat}.csv` (upstream repository MIT-licensed, dataset-specific rights unresolved, see `ATTRIBUTION.md`; adapter status **OBSERVED**; upstream provenance **REQUIRES PROVENANCE REVIEW**). Run with `python scripts/run_real_pipeline.py` (seed 42, 90% conformal target). Full log: `outputs/reports/real_run_log.md`; data-quality report: `outputs/reports/real-data-quality-report.md`.

**Data flow (actual counts from the run):** 2,421 raw rows -> 373 aggregate rows dropped (names containing Region / Division / H.T.) -> 147 zero-area/zero-production rows and 1 zero-area/non-zero-production (inconsistent) row dropped -> 1,900 rows after the adapter -> 2 rows with yield > 50 t/ha dropped by the range rule -> **1,898 modelled rows**, 1970-2014, 68 district-name strings (spelling variants not harmonised).

**Split:** chronological by year, 60/20/20 of unique years. Fit 1970-1996 (n=868), calibrate 1997-2005 (n=430), test 2006-2014 (n=600). Preprocessing fit on the fit split only. Features: `area_ha`, `rainfall_mm`, `rainfall_per_area`, `district`, `crop` (no temperature or humidity exist in these files; `production_t` is never a predictor).

| Model | n_fit | n_calib | n_test | MAE (t/ha) | RMSE (t/ha) | R² | Conformal halfwidth | Target | Empirical coverage |
|---|---|---|---|---|---|---|---|---|---|
| Naive mean baseline | 868 | 430 | 600 | 2.4328 | 3.1432 | -0.0285 | 6.801 | 0.90 | 0.928 |
| Ridge regression | 868 | 430 | 600 | 1.5818 | 3.2343 | -0.0890 | 7.211 | 0.90 | 0.900 |
| Random Forest | 868 | 430 | 600 | 1.2335 | 1.7565 | 0.6788 | 3.268 | 0.90 | 0.923 |

**Reading these numbers honestly (the comparison is exploratory; no conclusive ranking is claimed):**
- All three models were evaluated on the same test years, and the model used for the example/importances is chosen by lowest *test* MAE — post-hoc selection on the test set. One split, one seed.
- Random Forest has the lowest MAE/RMSE; Ridge has a lower MAE than the naive baseline but a *higher* RMSE and a negative R² (not diagnosed further; no change was made to chase a better number).
- The naive baseline is a single pooled mean across both crops. Random Forest's top importances are the crop indicators (Jute 0.383, Wheat 0.353), followed by `area_ha` (0.127) and `rainfall_mm` (0.047). Much of its advantage over the pooled-mean baseline is therefore plausibly crop identity (jute and wheat yields differ), not rainfall. A per-crop-mean baseline was not evaluated, so how much beyond crop identity the model learns is **not established**. These are associations in an impurity-based importance, not causes.
- Error by crop on the test split (best model vs pooled naive; the naive column is not a per-crop baseline): Jute n=81 MAE 3.604 vs 6.969; Wheat n=519 MAE 0.863 vs 1.725. Jute's test sample is small.
- Conformal intervals are wide (Random Forest halfwidth 3.27 t/ha) relative to typical yields. The reported coverage (0.900-0.928) is empirical coverage on the held-out temporal test set (2006-2014) for this one split; it is not a future-coverage guarantee, and conformal guarantees do not carry over under temporal distribution shift.
- No field validation; no separate climate dataset (the model uses the source's own `Rainfall in MM` field, whose aggregation is unverified; no temperature/humidity); units are assumed (acres->ha; "Tons" as metric tonnes); district names unharmonised; rainfall definition undocumented upstream.

## What a further real-data iteration would require (not done in v0.1.0)

1. Tracing each CSV value to the references the upstream README lists (BBS "45 years Major Crops"; data.gov.bd daily rainfall), and confirming units and what the rainfall column aggregates.
2. District-name harmonisation, then a district-level join with a verified climate source (e.g. NASA POWER district series) — not performed; NASA POWER remained unreachable from the build environment.
3. A per-crop baseline and per-crop models, to separate crop identity from other signal.
4. Domain/agronomic review (see `docs/04-governance-framework.md`) before any real-world claim.
