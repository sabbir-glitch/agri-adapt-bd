# Changelog

## 0.1.0 — 2026-10-12 (first release; not pushed to GitHub by the build process)

### Added
- Synthetic demonstration pipeline (ingestion with mandatory `source_type`, validation, cleaning, row-wise feature engineering, leakage-safe preprocessing fit on the fit split only, naive/Ridge/Random Forest models, split-conformal prediction intervals, explainability, governance checks, decision-support output with hardcoded `human_review`).
- Real-data exploratory pipeline for jute & wheat (`scripts/run_real_pipeline.py`): observed-schema adapter (excludes Region/Division/H.T. aggregate rows, handles zero-area rows, acres→ha), chronological 60/20/20 split by year, by-crop error analysis, experiment registry rows tagged `real_unvalidated`.
- `scripts/fetch_real_data.py --source sajidahmed12`: SHA-256-verified retrieval with source URLs and access date; raw data is not bundled.
- Streamlit dashboard (synthetic mode; upload-only real mode).
- 66 automated tests; GitHub Actions workflows — default (synthetic, no external data) and manual real-data (checksum-verified fetch) — not yet run on GitHub.
- `docs/data-card.md` and `docs/model-card.md`.
- Documentation: problem definition, stakeholder map, pipeline, governance, capacity building, policy brief, data-provenance register, source audit, product docs.

### Post-review corrections (before publication)
- Split-conformal halfwidth now uses the k-th smallest calibration residual, k = ceil((n+1)·coverage), without interpolation; coverage and residual inputs are validated and k > n raises an error (previously an interpolated quantile with clipping). Regression tests added. MAE/RMSE/R² are unchanged; interval halfwidths changed slightly and all interval figures were regenerated (e.g. real-data Random Forest halfwidth 3.2734 → 3.2681 t/ha).
- Provenance register evidence statuses made internally consistent; jute/wheat remain OBSERVED, not VERIFIED, with lineage, units, rainfall aggregation and dataset-level rights unresolved.
- Synthetic Random Forest metrics: documentation now quotes the values reproduced by repeated actual runs (MAE 0.3928, RMSE 0.5123, R² 0.4761). An earlier draft quoted 0.3926/0.5120/0.4768; the run or environment that produced those could not be identified or reproduced, and the difference is plausibly (not demonstrably) due to library-version differences. Run logs now record Python/numpy/pandas/scikit-learn versions.
- Split-conformal rank now computed exactly with Decimal arithmetic (replacing an approximate rounding guard that mis-ranked e.g. n=2, coverage=0.6666666668); halfwidths for the reported 90% runs are unchanged.
- `data/metadata/data_dictionary.csv` now separates canonical intended semantics from observed jute/wheat source semantics (rainfall aggregation unknown; temperature/humidity not present); licence metadata clarified (upstream repository MIT; dataset-specific rights unresolved; Kaggle licences reported by metadata, not independently confirmed).

### Fixed during development (each with a regression test)
- Predicted yield was the observed value → now `model.predict()` on a held-out row.
- Preprocessing statistics computed before the split → fit on the fit split only.
- MAE/RMSE described as uncertainty → replaced by split-conformal intervals.
- `rainfall_per_area` object dtype crash; `clean()` deleting all rows when optional columns were all NaN.
- Aggregate-row filter missed "Division"/"H.T." rows (205 → 373 rows excluded); earlier real metrics were discarded and regenerated.

### Known limitations
- Real data: exact provenance unresolved (upstream lists BBS and data.gov.bd references; lineage to each value unestablished); units assumed; unharmonised district names; no field validation.
- No separate climate dataset integrated; the real model uses the source's own `Rainfall in MM` field (aggregation unverified) and has no temperature/humidity.
- Dashboard real mode is not connected to the jute/wheat experiment; no browser testing.
- Not production-ready; not field-validated.
