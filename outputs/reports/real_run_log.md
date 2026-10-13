# Real-data run log (jute & wheat) — REAL DATA, UNVALIDATED

- Run timestamp (UTC): 2026-10-13T04:30:07.356866+00:00
- source_type: real | source: sajidahmed12_crop_data (upstream repo MIT; dataset-specific rights and lineage unresolved)
- environment: python 3.13.16, numpy 2.5.3, pandas 3.0.5, scikit-learn 1.9.1
- random_seed: 42 | conformal coverage target: 0.9
- Framing: retrospective yield estimation from historical records; not forecasting, not a crop recommendation tool. Associations only — no causal claims.

## Adapter (status OBSERVED)
```
{
  "adapter": "sajidahmed12_crop_csv",
  "status": "OBSERVED",
  "raw_rows": 2421,
  "region_aggregate_rows_dropped": 373,
  "blank_name_rows_dropped": 0,
  "zero_area_zero_production_rows_dropped": 147,
  "zero_area_inconsistent_rows_dropped": 1,
  "rows_after_adapter": 1900,
  "distinct_district_names": 68,
  "climate_variables_available": false,
  "canonical_columns_missing": [],
  "fully_canonical": true
}
```

## Validation (pre-clean)
```
{
  "n_rows": 1900,
  "n_duplicate_rows": 0,
  "missingness_by_column": {
    "district": 0.0,
    "crop": 0.0,
    "season": 0.0,
    "year": 0.0,
    "area_ha": 0.0,
    "production_t": 0.0,
    "yield_t_per_ha": 0.0,
    "rainfall_mm": 0.0,
    "temp_c": 1.0,
    "humidity_pct": 1.0
  },
  "out_of_range_flags": {
    "yield_t_per_ha": 2
  },
  "passed": false,
  "issues": [
    "Columns with >20% missing values: {'temp_c': 1.0, 'humidity_pct': 1.0}",
    "2 rows with yield_t_per_ha outside plausible range [0, 50]"
  ]
}
```

## Cleaning
```
{'duplicates_dropped': 0, 'out_of_range_dropped': 2, 'missing_required_dropped': 0, 'final_n_rows': 1898}
```

## Temporal split
fit (1970, 1996) n=868 | calibrate (1997, 2005) n=430 | test (2006, 2014) n=600

## Model evaluation (REAL DATA, temporal hold-out; preprocessing fit on `fit` only)

| model | n_fit | n_calib | n_test | MAE | RMSE | R2 | conformal halfwidth | target cov | empirical cov |
|---|---|---|---|---|---|---|---|---|---|
| naive_mean_baseline | 868 | 430 | 600 | 2.4328 | 3.1432 | -0.0285 | 6.8006 | 0.9 | 0.9283 |
| ridge_regression | 868 | 430 | 600 | 1.5818 | 3.2343 | -0.089 | 7.2114 | 0.9 | 0.9 |
| random_forest | 868 | 430 | 600 | 1.2335 | 1.7565 | 0.6788 | 3.2681 | 0.9 | 0.9233 |

## Top 5 features/coefficients (random_forest; associations, not causes)

| feature                    |   importance |
|:---------------------------|-------------:|
| categorical__crop_Jute     |    0.383354  |
| categorical__crop_Wheat    |    0.353363  |
| numeric__area_ha           |    0.126855  |
| numeric__rainfall_mm       |    0.0470377 |
| numeric__rainfall_per_area |    0.0412041 |

## Error by crop (test split)

| crop | n_test | MAE best | MAE naive |
|---|---|---|---|
| Jute | 81 | 3.604 | 6.969 |
| Wheat | 519 | 0.863 | 1.725 |

## Governance checks

- [PASS] no_personal_data: None found.
- [PASS] district_coverage: 68 distinct districts present (minimum expected: 3).
- [PASS] error_metrics_present: Every model result includes both MAE and RMSE.
- [PASS] prediction_interval_present: Every model result includes a conformal prediction interval and its empirical coverage.
- [PASS] synthetic_label_present: Not applicable — data is not synthetic.
- [PASS] source_type_plausible: No obvious path/source_type mismatch.

## Example decision-support output (real held-out test row, human review required)
```json
{
  "district": "Barisal",
  "crop": "Jute",
  "season": "annual_aggregate",
  "analysis_date": "2026-10-13",
  "observed_yield_t_per_ha": 7.636,
  "predicted_yield_t_per_ha": 6.986,
  "residual_t_per_ha": 0.65,
  "prediction_interval": {
    "low": 3.718,
    "high": 10.254,
    "coverage_target": 0.9,
    "empirical_coverage_on_test": 0.9233,
    "method": "split-conformal (absolute-residual, finite-sample corrected)"
  },
  "evaluation_error_context": "On the held-out test set, this model's aggregate error was MAE=1.234 t/ha, RMSE=1.756 t/ha. These are evaluation-set averages, not a per-prediction uncertainty bound \u2014 see prediction_interval for that.",
  "data_quality_label": "real_unvalidated",
  "top_factors": [
    "categorical__crop_Jute",
    "categorical__crop_Wheat",
    "numeric__area_ha"
  ],
  "recommended_action_type": "human_review",
  "model_version": "sonardesh-ai-v0.1.0",
  "evidence_sources": [
    "See docs/data-provenance/provenance-register.md"
  ],
  "limitations": [
    "RETROSPECTIVE YIELD ESTIMATION, NOT A PRE-SEASON FORECAST: the model uses source-provided same-period inputs. In the real jute/wheat experiment these are the source-reported rainfall field (aggregation unverified); temperature and humidity are absent. The synthetic demonstration uses generated temperature/humidity. It is not a crop-recommendation or pre-planting forecasting tool.",
    "Interval coverage is empirical coverage on a held-out evaluation set; it is not a guarantee of future coverage, especially under temporal distribution shift.",
    "Not validated against real-world field outcomes.",
    "District-level resolution only; does not capture farm-level variation.",
    "No causal claim is made between any input variable and yield."
  ],
  "demonstration_only": false
}
```
