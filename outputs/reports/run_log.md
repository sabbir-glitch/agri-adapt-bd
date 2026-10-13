# Pipeline run log

- Run timestamp (UTC): 2026-10-13T04:30:05.292022+00:00
- source: synthetic
- path: /home/claude/work/scripts/../data/processed/synthetic_demo/synthetic_agroclimate_demo.csv
- name: synthetic_demo_v1
- environment: python 3.13.16, numpy 2.5.3, pandas 3.0.5, scikit-learn 1.9.1
- random_seed: 42
- conformal coverage target: 0.9

**Framing note:** this pipeline estimates yield retrospectively from seasonal rainfall/temperature/humidity. These inputs are not fully known before a season ends, so this is retrospective/seasonal estimation research, not a pre-season forecasting or crop-recommendation tool.

## Ingestion
Loaded 600 rows, 10 columns from /home/claude/work/scripts/../data/processed/synthetic_demo/synthetic_agroclimate_demo.csv

## Validation
```
{'n_rows': 600, 'n_duplicate_rows': 0, 'missingness_by_column': {'district': 0.0, 'crop': 0.0, 'season': 0.0, 'year': 0.0, 'area_ha': 0.0, 'production_t': 0.0, 'yield_t_per_ha': 0.0, 'rainfall_mm': 0.0, 'temp_c': 0.0, 'humidity_pct': 0.0}, 'out_of_range_flags': {}, 'passed': True, 'issues': []}
```

## Cleaning
```
{'duplicates_dropped': 0, 'out_of_range_dropped': 0, 'missing_required_dropped': 0, 'final_n_rows': 600}
```

## Feature engineering
Raw feature matrix shape: (600, 9) (unimputed, unencoded — preprocessing is fit after the split, see below)

## Model evaluation (district-held-out: fit / calibrate / test, preprocessing fit on `fit` split only)

| model | n_fit | n_calib | n_test | MAE | RMSE | R2 | conformal halfwidth | target coverage | empirical coverage |
|---|---|---|---|---|---|---|---|---|---|
| naive_mean_baseline | 293 | 131 | 176 | 0.5409 | 0.7114 | -0.01 | 1.0626 | 0.9 | 0.892 |
| ridge_regression | 293 | 131 | 176 | 0.441 | 0.5843 | 0.3185 | 0.9797 | 0.9 | 0.9261 |
| random_forest | 293 | 131 | 176 | 0.3928 | 0.5123 | 0.4761 | 0.8424 | 0.9 | 0.8977 |

## Top 5 feature importances (random_forest)

| feature                      |   importance |
|:-----------------------------|-------------:|
| numeric__rainfall_mm         |    0.566187  |
| numeric__temp_c              |    0.247493  |
| numeric__temp_humidity_index |    0.0789105 |
| numeric__humidity_pct        |    0.0227066 |
| numeric__rainfall_per_area   |    0.0198688 |

## Governance checks

- [PASS] no_personal_data: None found.
- [PASS] district_coverage: 10 distinct districts present (minimum expected: 3).
- [PASS] error_metrics_present: Every model result includes both MAE and RMSE.
- [PASS] prediction_interval_present: Every model result includes a conformal prediction interval and its empirical coverage.
- [PASS] synthetic_label_present: Synthetic-data label correctly present.
- [PASS] source_type_plausible: No obvious path/source_type mismatch.

## Example decision-support output (real held-out test-row prediction)
```json

{
  "district": "Chattogram",
  "crop": "Jute",
  "season": "Aman",
  "analysis_date": "2026-10-13",
  "observed_yield_t_per_ha": 3.911,
  "predicted_yield_t_per_ha": 3.732,
  "residual_t_per_ha": 0.179,
  "prediction_interval": {
    "low": 2.889,
    "high": 4.574,
    "coverage_target": 0.9,
    "empirical_coverage_on_test": 0.8977,
    "method": "split-conformal (absolute-residual, finite-sample corrected)"
  },
  "evaluation_error_context": "On the held-out test set, this model's aggregate error was MAE=0.393 t/ha, RMSE=0.512 t/ha. These are evaluation-set averages, not a per-prediction uncertainty bound \u2014 see prediction_interval for that.",
  "data_quality_label": "synthetic_demonstration",
  "top_factors": [
    "numeric__rainfall_mm",
    "numeric__temp_c",
    "numeric__temp_humidity_index"
  ],
  "recommended_action_type": "human_review",
  "model_version": "sonardesh-ai-v0.1",
  "evidence_sources": [
    "See docs/data-provenance/provenance-register.md"
  ],
  "limitations": [
    "UNDERLYING DATA IS SYNTHETIC \u2014 see data/processed/synthetic_demo/README.md.",
    "RETROSPECTIVE YIELD ESTIMATION, NOT A PRE-SEASON FORECAST: the model uses source-provided same-period inputs. In the real jute/wheat experiment these are the source-reported rainfall field (aggregation unverified); temperature and humidity are absent. The synthetic demonstration uses generated temperature/humidity. It is not a crop-recommendation or pre-planting forecasting tool.",
    "Interval coverage is empirical coverage on a held-out evaluation set; it is not a guarantee of future coverage, especially under temporal distribution shift.",
    "Not validated against real-world field outcomes.",
    "District-level resolution only; does not capture farm-level variation.",
    "No causal claim is made between any input variable and yield."
  ],
  "demonstration_only": true
}

```
