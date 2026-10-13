"""
Real-data pipeline (jute & wheat, sajidahmed12 files) — source_type="real".
Upstream repository licence: MIT; dataset-specific redistribution rights of the underlying
observations are unresolved (the data is not asserted to be MIT-licensed).

Never falls back to synthetic data: if the raw files are absent it exits
with an error. Results are REAL-DATA, UNVALIDATED (no field validation,
exact upstream provenance unresolved) and are never mixed
with the synthetic demonstration results.

Design choices (documented, not tuned for results):
  * chronological split by year (60/20/20 of unique years) — a temporal
    split is the honest choice for yearly records;
  * reduced feature set: area_ha, rainfall_mm, rainfall_per_area, district,
    crop (no temperature/humidity exist in these files);
  * production_t is NEVER a predictor (yield = production / area).
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import sklearn

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from src.data.adapters import adapt_sajidahmed12_crop_csv
from src.data.ingestion import assert_not_real_claim
from src.data.validation import validate
from src.data.cleaning import clean
from src.features.engineering import engineer_features, get_raw_xy
from src.models.train import run_model_comparison, three_way_temporal_split
from src.models.preprocessing import get_output_feature_names
from src.models.explain import random_forest_importance, ridge_coefficients
from src.governance.checks import run_all_checks
from src.product.schemas import build_recommendation

RAW_DIR = os.path.join(REPO_ROOT, "data", "raw", "sajidahmed12_crop_data")
REPORTS = os.path.join(REPO_ROOT, "outputs", "reports")
REGISTRY = os.path.join(REPORTS, "experiment-registry.csv")
REAL_LOG = os.path.join(REPORTS, "real_run_log.md")
REAL_DQ = os.path.join(REPORTS, "real-data-quality-report.md")

REAL_NUMERIC_FEATURES = ["area_ha", "rainfall_mm", "rainfall_per_area"]
REAL_CATEGORICAL_FEATURES = ["district", "crop"]
MIN_SUBGROUP_N = 30
SOURCE_NAME = "sajidahmed12_crop_data"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--coverage", type=float, default=0.9)
    args = ap.parse_args()

    paths = {"jute": os.path.join(RAW_DIR, "jute.csv"), "wheat": os.path.join(RAW_DIR, "wheat.csv")}
    for p in paths.values():
        if not os.path.exists(p):
            sys.exit(f"ERROR: real data file missing: {p}. Real mode never falls back to synthetic data.")

    now = datetime.now(timezone.utc)
    log = ["# Real-data run log (jute & wheat) — REAL DATA, UNVALIDATED\n",
           f"- Run timestamp (UTC): {now.isoformat()}",
           f"- source_type: real | source: {SOURCE_NAME} (upstream repo MIT; dataset-specific rights and lineage unresolved)",
           f"- environment: python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}, scikit-learn {sklearn.__version__}",
           f"- random_seed: {args.seed} | conformal coverage target: {args.coverage}",
           "- Framing: retrospective yield estimation from historical records; not forecasting, "
           "not a crop recommendation tool. Associations only — no causal claims.\n"]

    df, ad = adapt_sajidahmed12_crop_csv(paths)
    log.append("## Adapter (status OBSERVED)\n```\n" + json.dumps(
        {k: v for k, v in ad.items() if k not in ("canonical_columns_present",)}, indent=2, default=str) + "\n```\n")

    val = validate(df)
    df_clean, cl = clean(df)
    df_clean.attrs.update(df.attrs)
    assert_not_real_claim(df_clean)
    log.append(f"## Validation (pre-clean)\n```\n{json.dumps(val.to_dict(), indent=2, default=str)}\n```\n")
    log.append(f"## Cleaning\n```\n{cl}\n```\n")

    dq = ["# Real-data quality report (jute & wheat) — REAL DATA, UNVALIDATED\n",
          f"Generated {now.date().isoformat()} by scripts/run_real_pipeline.py.\n",
          f"- Raw rows (jute+wheat): {ad['raw_rows']}",
          f"- Aggregate rows dropped (Region/Division/H.T.): {ad['region_aggregate_rows_dropped']}",
          f"- Zero-area/zero-production rows dropped: {ad['zero_area_zero_production_rows_dropped']}",
          f"- Zero-area with non-zero production dropped (inconsistent): {ad['zero_area_inconsistent_rows_dropped']}",
          f"- Rows after adapter: {ad['rows_after_adapter']}",
          f"- Rows removed by cleaning (duplicates {cl['duplicates_dropped']}, out-of-range "
          f"{cl['out_of_range_dropped']}, missing required {cl['missing_required_dropped']}): final {cl['final_n_rows']}",
          f"- Distinct district names after title-casing: {df_clean['district'].nunique()} "
          "(spelling variants NOT harmonised — a known limitation)",
          f"- Years: {int(df_clean['year'].min())}–{int(df_clean['year'].max())}",
          f"- Crops: {df_clean['crop'].value_counts().to_dict()}",
          "- Rows removed by the yield > 50 t/ha rule (suspicious outliers): "
          + "; ".join(f"{r.district} {r.crop} {int(r.year)} yield={r.yield_t_per_ha:.2f} t/ha "
                      f"(area={r.area_ha:.2f} ha, production={r.production_t:.0f})"
                      for r in df[df['yield_t_per_ha'] > 50].itertuples()) ,
          "- temp_c / humidity_pct: not present in source (NaN, not invented); not used as features",
          "- Unit assumptions: acres->ha x0.404686; 'Tons' treated as metric tonnes (unverified)",
          f"- Yield (t/ha) summary: {df_clean['yield_t_per_ha'].describe().round(3).to_dict()}"]
    os.makedirs(REPORTS, exist_ok=True)
    open(REAL_DQ, "w").write("\n".join(dq) + "\n")

    df_feat = engineer_features(df_clean)
    X, y = get_raw_xy(df_feat, REAL_NUMERIC_FEATURES, REAL_CATEGORICAL_FEATURES)
    years = df_feat["year"]
    Xf, yf, Xc, yc, Xt, yt, info = three_way_temporal_split(X, y, years)
    # chronology guard
    assert years[Xf.index].max() < years[Xc.index].min() <= years[Xc.index].max() < years[Xt.index].min()
    log.append(f"## Temporal split\nfit {info['fit_years']} n={len(Xf)} | calibrate {info['calib_years']} "
               f"n={len(Xc)} | test {info['test_years']} n={len(Xt)}\n")

    results, models, pre, sd = run_model_comparison(
        X, y, df_clean["district"], random_seed=args.seed, coverage_target=args.coverage,
        numeric_features=REAL_NUMERIC_FEATURES, categorical_features=REAL_CATEGORICAL_FEATURES,
        split_data_override=(Xf, yf, Xc, yc, Xt, yt))
    log.append("## Model evaluation (REAL DATA, temporal hold-out; preprocessing fit on `fit` only)\n")
    log.append("| model | n_fit | n_calib | n_test | MAE | RMSE | R2 | conformal halfwidth | target cov | empirical cov |")
    log.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        log.append(f"| {r.model_name} | {r.n_fit} | {r.n_calibrate} | {r.n_test} | {r.mae} | {r.rmse} | "
                   f"{r.r2} | {r.conformal_interval_halfwidth} | {r.conformal_coverage_target} | "
                   f"{r.conformal_empirical_coverage} |")
    log.append("")

    best = min((r for r in results if r.model_name != "naive_mean_baseline"), key=lambda r: r.mae)
    model, hw = models[best.model_name]
    names = get_output_feature_names(pre)
    imp = (random_forest_importance(model, names) if best.model_name == "random_forest"
           else ridge_coefficients(model, names))
    log.append(f"## Top 5 features/coefficients ({best.model_name}; associations, not causes)\n")
    log.append(imp.head(5).to_markdown(index=False) + "\n")

    # by-crop error analysis on the test split (best model + naive)
    Xt_t = sd["X_test_t"]
    pred_best = model.predict(Xt_t)
    naive = np.full(len(yt), yf.mean())
    log.append("## Error by crop (test split)\n")
    log.append("| crop | n_test | MAE best | MAE naive |\n|---|---|---|---|")
    for crop in sorted(Xt["crop"].unique()):
        m = (Xt["crop"] == crop).values
        if m.sum() < MIN_SUBGROUP_N:
            log.append(f"| {crop} | {int(m.sum())} | INSUFFICIENT SAMPLE | INSUFFICIENT SAMPLE |")
        else:
            log.append(f"| {crop} | {int(m.sum())} | {np.mean(np.abs(yt.values[m]-pred_best[m])):.3f} | "
                       f"{np.mean(np.abs(yt.values[m]-naive[m])):.3f} |")
    log.append("")

    gov = run_all_checks(df_clean, results, source_type="real", output_label=None, source_path=RAW_DIR)
    log.append("## Governance checks\n")
    for c in gov:
        log.append(f"- [{'PASS' if c['passed'] else 'FAIL'}] {c['check']}: {c['details']}")
    log.append("")

    meta = Xt.iloc[0]
    top = imp.head(3)["feature"].tolist()
    rec = build_recommendation(
        district=str(meta["district"]), crop=str(meta["crop"]), season="annual_aggregate",
        predicted_yield=float(model.predict(Xt_t[0:1])[0]), observed_yield=float(yt.iloc[0]),
        mae=best.mae, rmse=best.rmse, conformal_halfwidth=hw, coverage_target=args.coverage,
        empirical_coverage=best.conformal_empirical_coverage, top_factors=top,
        model_version="sonardesh-ai-v0.1.0", is_synthetic=False)
    log.append("## Example decision-support output (real held-out test row, human review required)\n```json")
    log.append(json.dumps(rec.to_dict(), indent=2) + "\n```\n")

    write_header = not os.path.exists(REGISTRY)
    with open(REGISTRY, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["experiment_id", "date", "source_type", "dataset_name", "model", "n_fit", "n_calibrate",
                        "n_test", "MAE", "RMSE", "R2", "conformal_halfwidth", "coverage_target",
                        "empirical_coverage", "random_seed", "status"])
        base = now.strftime("EXP-REAL-%Y%m%d%H%M%S")
        for i, r in enumerate(results):
            w.writerow([f"{base}-{i}", now.date().isoformat(), "real", SOURCE_NAME, r.model_name, r.n_fit,
                        r.n_calibrate, r.n_test, r.mae, r.rmse, r.r2, r.conformal_interval_halfwidth,
                        r.conformal_coverage_target, r.conformal_empirical_coverage, r.random_seed,
                        "real_unvalidated"])
    open(REAL_LOG, "w").write("\n".join(log))
    print("\n".join(log))


if __name__ == "__main__":
    main()
