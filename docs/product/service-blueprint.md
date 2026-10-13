# Service Blueprint

A single blueprint for the CURRENT PROTOTYPE's one real journey (field officer running an analysis), showing what's visible to the user vs. what happens "backstage" in code.

```
FRONTSTAGE (what the user sees)
────────────────────────────────────────────────────────────
Select data mode (🟡 synthetic / 🟢 real)
        │
Click "Run analysis"
        │
See: data-mode banner, record/district/crop counts
        │
See: data quality report (missingness, duplicates, range flags)
        │
See: model comparison table (MAE/RMSE/R² — labelled as
     aggregate error, not uncertainty)
        │
See: conformal prediction-interval table (separate, labelled
     as the actual per-prediction uncertainty)
        │
See: one held-out example — observed vs. predicted vs. residual
        │
See: feature importance chart
        │
See: governance check results (pass/fail per check)
────────────────────────────────────────────────────────────
BACKSTAGE (code, invisible to the user)
────────────────────────────────────────────────────────────
load_dataset() → tags source_type, refuses silent defaults
        │
validate() → missingness/duplicate/range report
        │
clean() → dedupe, range-filter, drop missing-required rows
        │
engineer_features() → row-wise derived features only
        │
three_way_group_split() → fit/calibrate/test, no district overlap
        │
build_preprocessor().fit(X_fit) → imputation + encoding, TRAIN ONLY
        │
Ridge.fit(), RandomForest.fit() → on transformed fit split
        │
split_conformal_halfwidth() → calibrated on the calibrate split
        │
evaluate_test_metrics() → MAE/RMSE/R² + empirical coverage on test
        │
run_all_checks() → governance checks, all logged
        │
build_recommendation() → the decision-support contract, with
     mandatory human_review flag
────────────────────────────────────────────────────────────
```

## Failure points and what currently happens (not proposed — actual code behavior)

| Failure | Current behavior |
|---|---|
| Fewer than 4 districts | Dashboard shows a warning and stops before the split |
| Uploaded CSV missing required columns | Clear error naming exactly which columns are missing |
| `source_type` declared inconsistently with file path | `check_source_type_plausible()` flags it (a heuristic, not a guarantee) |
| Real data access fails (`fetch_real_data.py`) | Fails explicitly with an error — never silently substitutes synthetic data |
