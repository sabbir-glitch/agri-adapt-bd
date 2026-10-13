"""
Orchestrates the full pipeline end to end and writes REAL outputs from
an ACTUAL run. No number in outputs/reports/ is hand-typed — every one
is written by this script after the corresponding computation actually
executed, including the example decision-support record, which now
uses a genuine model.predict() on a held-out test row (pre-release
review caught an earlier version that used the row's own observed
target value instead — fixed here, with a regression test in
tests/test_pipeline.py proving it can't regress silently).

Usage:
    python scripts/run_pipeline.py --source synthetic
    python scripts/run_pipeline.py --source real --path path/to/real_data.csv --name agriclimatebd
"""

from __future__ import annotations

import argparse
import platform
import csv
import json
import os
import sys

import numpy as np
import pandas as pd
import sklearn
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data.ingestion import load_dataset, DataSourceError
from src.data.validation import validate
from src.data.cleaning import clean
from src.features.engineering import engineer_features, get_raw_xy
from src.models.train import run_model_comparison
from src.models.explain import random_forest_importance, ridge_coefficients
from src.models.preprocessing import get_output_feature_names
from src.governance.checks import run_all_checks
from src.product.schemas import build_recommendation

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
SYNTHETIC_PATH = os.path.join(REPO_ROOT, "data", "processed", "synthetic_demo",
                               "synthetic_agroclimate_demo.csv")
EXPERIMENT_REGISTRY = os.path.join(REPO_ROOT, "outputs", "reports", "experiment-registry.csv")
RUN_LOG = os.path.join(REPO_ROOT, "outputs", "reports", "run_log.md")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["real", "synthetic"], default="synthetic")
    parser.add_argument("--path", default=SYNTHETIC_PATH)
    parser.add_argument("--name", default="synthetic_demo_v1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--coverage", type=float, default=0.9)
    args = parser.parse_args()

    log = []
    log.append("# Pipeline run log\n")
    log.append(f"- Run timestamp (UTC): {datetime.now(timezone.utc).isoformat()}")
    log.append(f"- source: {args.source}\n- path: {args.path}\n- name: {args.name}")
    log.append(f"- environment: python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}, scikit-learn {sklearn.__version__}")
    log.append(f"- random_seed: {args.seed}\n- conformal coverage target: {args.coverage}\n")
    log.append(
        "**Framing note:** this pipeline estimates yield retrospectively from "
        "seasonal rainfall/temperature/humidity. These inputs are not fully known "
        "before a season ends, so this is retrospective/seasonal estimation "
        "research, not a pre-season forecasting or crop-recommendation tool.\n"
    )

    # 1. Ingest
    df = load_dataset(args.path, source_type=args.source, source_name=args.name)
    log.append(f"## Ingestion\nLoaded {len(df)} rows, {len(df.columns)} columns from {args.path}\n")

    # 2. Validate
    val_report = validate(df)
    log.append(f"## Validation\n```\n{val_report.to_dict()}\n```\n")

    # 3. Clean
    df_clean, clean_report = clean(df)
    df_clean.attrs.update(df.attrs)
    log.append(f"## Cleaning\n```\n{clean_report}\n```\n")

    # 4. Feature engineering (row-wise only — no leakage-prone step here)
    df_feat = engineer_features(df_clean)
    X, y = get_raw_xy(df_feat)
    groups = df_clean["district"]
    log.append(f"## Feature engineering\nRaw feature matrix shape: {X.shape} (unimputed, unencoded — "
               f"preprocessing is fit after the split, see below)\n")

    # 5. Model comparison: 3-way group split, preprocessing fit on fit-split only,
    #    split-conformal prediction intervals calibrated on a genuinely held-out set.
    results, fitted_models, preprocessor, split_data = run_model_comparison(
        X, y, groups, random_seed=args.seed, coverage_target=args.coverage)

    log.append("## Model evaluation (district-held-out: fit / calibrate / test, "
               "preprocessing fit on `fit` split only)\n")
    log.append("| model | n_fit | n_calib | n_test | MAE | RMSE | R2 | conformal halfwidth | "
               "target coverage | empirical coverage |")
    log.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        log.append(f"| {r.model_name} | {r.n_fit} | {r.n_calibrate} | {r.n_test} | {r.mae} | "
                   f"{r.rmse} | {r.r2} | {r.conformal_interval_halfwidth} | "
                   f"{r.conformal_coverage_target} | {r.conformal_empirical_coverage} |")
    log.append("")

    # 6. Explainability — against the preprocessor's actual output feature names
    best_name = min((r for r in results if r.model_name != "naive_mean_baseline"),
                     key=lambda r: r.mae).model_name
    best_model, best_halfwidth = fitted_models[best_name]
    output_feature_names = get_output_feature_names(preprocessor)

    if best_name == "random_forest":
        importance_df = random_forest_importance(best_model, output_feature_names)
        log.append(f"## Top 5 feature importances ({best_name})\n")
        log.append(importance_df.head(5).to_markdown(index=False))
    else:
        coef_df = ridge_coefficients(best_model, output_feature_names)
        log.append(f"## Top 5 coefficients by magnitude ({best_name})\n")
        log.append(coef_df.head(5).to_markdown(index=False))
    log.append("")

    # 7. Governance checks
    gov_checks = run_all_checks(
        df_clean, results, source_type=args.source,
        output_label="DEMONSTRATION ONLY — NOT EMPIRICAL EVIDENCE" if args.source == "synthetic" else None,
        source_path=args.path,
    )
    log.append("## Governance checks\n")
    for c in gov_checks:
        status = "PASS" if c["passed"] else "FAIL"
        log.append(f"- [{status}] {c['check']}: {c['details']}")
    log.append("")

    # 8. Example decision-support output — REAL held-out prediction, not a copied observed value.
    X_test = split_data["X_test"]
    y_test = split_data["y_test"]
    X_test_t = split_data["X_test_t"]
    example_row_pos = 0
    example_pred = float(best_model.predict(X_test_t[example_row_pos:example_row_pos + 1])[0])
    example_observed = float(y_test.iloc[example_row_pos])
    example_meta = X_test.iloc[example_row_pos]

    if best_name == "random_forest":
        top_factors = random_forest_importance(best_model, output_feature_names).head(3)["feature"].tolist()
    else:
        top_factors = ridge_coefficients(best_model, output_feature_names).head(3)["feature"].tolist()

    best_result = next(r for r in results if r.model_name == best_name)
    example_rec = build_recommendation(
        district=str(example_meta["district"]), crop=str(example_meta["crop"]),
        season=str(example_meta["season"]),
        predicted_yield=example_pred, observed_yield=example_observed,
        mae=best_result.mae, rmse=best_result.rmse,
        conformal_halfwidth=best_halfwidth, coverage_target=args.coverage,
        empirical_coverage=best_result.conformal_empirical_coverage,
        top_factors=top_factors, model_version="sonardesh-ai-v0.1",
        is_synthetic=(args.source == "synthetic"),
    )
    log.append("## Example decision-support output (real held-out test-row prediction)\n```json\n")
    log.append(json.dumps(example_rec.to_dict(), indent=2))
    log.append("\n```\n")

    # Write experiment registry
    os.makedirs(os.path.dirname(EXPERIMENT_REGISTRY), exist_ok=True)
    write_header = not os.path.exists(EXPERIMENT_REGISTRY)
    with open(EXPERIMENT_REGISTRY, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["experiment_id", "date", "source_type", "dataset_name", "model",
                              "n_fit", "n_calibrate", "n_test", "MAE", "RMSE", "R2",
                              "conformal_halfwidth", "coverage_target", "empirical_coverage",
                              "random_seed", "status"])
        exp_id_base = datetime.now(timezone.utc).strftime("EXP-%Y%m%d%H%M%S")
        for i, r in enumerate(results):
            status = "demonstration_only" if args.source == "synthetic" else "real_unvalidated"
            writer.writerow([f"{exp_id_base}-{i}", datetime.now(timezone.utc).date().isoformat(),
                              args.source, args.name, r.model_name, r.n_fit, r.n_calibrate, r.n_test,
                              r.mae, r.rmse, r.r2, r.conformal_interval_halfwidth,
                              r.conformal_coverage_target, r.conformal_empirical_coverage,
                              r.random_seed, status])

    os.makedirs(os.path.dirname(RUN_LOG), exist_ok=True)
    with open(RUN_LOG, "w") as f:
        f.write("\n".join(log))

    print("\n".join(log))
    print(f"\nExperiment registry updated: {EXPERIMENT_REGISTRY}")
    print(f"Run log written: {RUN_LOG}")


if __name__ == "__main__":
    main()
