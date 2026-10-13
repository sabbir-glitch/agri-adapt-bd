"""
SonarDesh AI dashboard. Always shows data mode prominently, and shows
model error metrics (MAE/RMSE) separately from the actual conformal
prediction interval — the two were previously conflated, fixed in
pre-release review.

Run: streamlit run dashboard/app.py
"""

import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data.ingestion import load_dataset, DataSourceError
from src.data.validation import validate
from src.data.cleaning import clean
from src.features.engineering import engineer_features, get_raw_xy
from src.models.train import run_model_comparison
from src.models.explain import random_forest_importance, ridge_coefficients
from src.models.preprocessing import get_output_feature_names
from src.governance.checks import run_all_checks

SYNTHETIC_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "processed", "synthetic_demo",
    "synthetic_agroclimate_demo.csv"
)

st.set_page_config(page_title="SonarDesh AI — Decision Support (Prototype)", layout="wide")

st.title("SonarDesh AI — Retrospective Agricultural Yield Analytics")
st.caption(
    "Independent open-source portfolio/research prototype. Not affiliated with or "
    "endorsed by any government or institutional body. This is RETROSPECTIVE / "
    "SEASONAL estimation research, not a pre-season crop-recommendation tool — "
    "inputs like seasonal rainfall are not fully known before a season ends."
)

mode = st.sidebar.radio("Data mode", ["🟡 SYNTHETIC DEMONSTRATION DATA", "🟢 REAL DATA (upload your own)"])

if mode.startswith("🟡"):
    st.sidebar.warning(
        "SYNTHETIC DEMONSTRATION DATA\n\n"
        "All data is randomly generated. Results are NOT empirical evidence "
        "about Bangladesh agriculture, climate, or yield."
    )
    source_type, source_name, data_path, uploaded = "synthetic", "synthetic_demo_v1", SYNTHETIC_PATH, None
else:
    st.sidebar.info(
        "REAL DATA MODE\n\nUpload a CSV matching the canonical schema (see "
        "src/data/ingestion.py). This does not by itself make any model output "
        "field-validated — see docs/04-governance-framework.md."
    )
    source_type = "real"
    uploaded = st.sidebar.file_uploader("Upload CSV", type="csv")
    source_name = uploaded.name if uploaded else "unnamed_upload"
    data_path = None

run_clicked = st.sidebar.button("Run analysis")

if run_clicked:
    try:
        if source_type == "synthetic":
            df = load_dataset(data_path, source_type="synthetic", source_name=source_name)
        else:
            if uploaded is None:
                st.error("Please upload a CSV file first.")
                st.stop()
            df = pd.read_csv(uploaded)
            required = {"district", "crop", "season", "year", "area_ha", "production_t",
                        "yield_t_per_ha", "rainfall_mm", "temp_c", "humidity_pct"}
            missing = required - set(df.columns)
            if missing:
                st.error(f"Uploaded file is missing required canonical-schema columns: {sorted(missing)}. "
                        f"If your file comes from an external source, it needs a source adapter first "
                        f"— see src/data/adapters.py.")
                st.stop()
            df.attrs["source_type"] = "real"
            df.attrs["source_name"] = source_name

        if source_type == "synthetic":
            st.error("🟡 SYNTHETIC DEMONSTRATION DATA — NOT EMPIRICAL EVIDENCE\n\n"
                     "Every number below comes from randomly generated data.")
        else:
            st.success(f"🟢 REAL DATA MODE — source: {source_name}, {len(df)} rows loaded. "
                       "Real data alone does not imply field-validated results.")

        col1, col2, col3 = st.columns(3)
        col1.metric("Records", len(df))
        col2.metric("Districts", df["district"].nunique())
        col3.metric("Crops", df["crop"].nunique())

        val_report = validate(df)
        st.subheader("Data quality")
        st.json(val_report.to_dict())

        df_clean, clean_report = clean(df)
        df_clean.attrs.update(df.attrs)
        st.write("Cleaning report:", clean_report)

        df_feat = engineer_features(df_clean)
        X, y = get_raw_xy(df_feat)
        groups = df_clean["district"]

        if df_clean["district"].nunique() < 4:
            st.warning("Not enough distinct districts for a fit/calibrate/test group split "
                       "(need at least 4). Governance check 'district_coverage' would also flag this.")
            st.stop()

        results, fitted_models, preprocessor, split_data = run_model_comparison(X, y, groups, random_seed=42)

        st.subheader("Model evaluation error metrics (aggregate, NOT a per-prediction interval)")
        results_df = pd.DataFrame([r.__dict__ for r in results])
        st.dataframe(results_df[["model_name", "n_fit", "n_calibrate", "n_test", "mae", "rmse", "r2"]])

        st.subheader("Split-conformal prediction interval (actual per-prediction uncertainty)")
        st.caption("Calibrated on a genuinely held-out calibration set, distinct from both fit and test data.")
        st.dataframe(results_df[["model_name", "conformal_coverage_target",
                                 "conformal_interval_halfwidth", "conformal_empirical_coverage"]])

        best_name = min((r for r in results if r.model_name != "naive_mean_baseline"),
                        key=lambda r: r.mae).model_name
        best_model, best_halfwidth = fitted_models[best_name]
        output_feature_names = get_output_feature_names(preprocessor)

        st.subheader(f"Held-out example: observed vs. predicted ({best_name})")
        X_test_t = split_data["X_test_t"]
        y_test = split_data["y_test"]
        X_test = split_data["X_test"]
        pred0 = float(best_model.predict(X_test_t[0:1])[0])
        obs0 = float(y_test.iloc[0])
        c1, c2, c3 = st.columns(3)
        c1.metric("Observed yield (t/ha)", round(obs0, 3))
        c2.metric("Predicted yield (t/ha)", round(pred0, 3))
        c3.metric("Residual (t/ha)", round(obs0 - pred0, 3))
        st.caption(f"District: {X_test.iloc[0]['district']}, crop: {X_test.iloc[0]['crop']}, "
                  f"season: {X_test.iloc[0]['season']}. Prediction interval: "
                  f"[{pred0 - best_halfwidth:.3f}, {pred0 + best_halfwidth:.3f}] t/ha "
                  f"(90% nominal coverage).")

        st.subheader(f"Feature importance ({best_name})")
        st.caption("Impurity/coefficient-based — biased toward high-cardinality features for Random Forest. See src/models/explain.py.")
        if best_name == "random_forest":
            importance_df = random_forest_importance(best_model, output_feature_names)
        else:
            importance_df = ridge_coefficients(best_model, output_feature_names).rename(columns={"coefficient": "importance"})
        st.bar_chart(importance_df.set_index("feature").head(10))

        st.subheader("Governance checks")
        output_label = "DEMONSTRATION ONLY — NOT EMPIRICAL EVIDENCE" if source_type == "synthetic" else None
        checks = run_all_checks(df_clean, results, source_type=source_type,
                                output_label=output_label, source_path=data_path)
        for c in checks:
            (st.success if c["passed"] else st.error)(f"{'✅' if c['passed'] else '❌'} {c['check']}: {c['details']}")

        st.caption(
            "Every output above is decision support for a human reviewer, not an instruction. "
            "This is retrospective/seasonal estimation, not a pre-planting forecast. "
            "See docs/04-governance-framework.md."
        )

    except DataSourceError as e:
        st.error(f"Data error: {e}")
else:
    st.info("Select a data mode in the sidebar and click **Run analysis**.")
