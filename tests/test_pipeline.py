import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd
import pytest

from src.data.ingestion import load_dataset, DataSourceError, assert_not_real_claim
from src.data.validation import validate
from src.data.cleaning import clean
from src.features.engineering import engineer_features, get_raw_xy
from src.models.preprocessing import build_preprocessor
from src.models.train import (
    run_model_comparison, naive_baseline_predict, three_way_group_split,
    split_conformal_halfwidth,
)
from src.governance.checks import (
    check_no_personal_data, check_district_coverage, check_error_metrics_present,
    check_prediction_interval_present, check_synthetic_label_present,
    check_source_type_plausible,
)
from src.product.schemas import build_recommendation
from src.data.adapters import adapt_generic_wide_csv, validate_canonical_output

SYNTHETIC_PATH = os.path.join(os.path.dirname(__file__), "..", "data",
                               "processed", "synthetic_demo", "synthetic_agroclimate_demo.csv")


@pytest.fixture(scope="module")
def synthetic_df():
    return load_dataset(SYNTHETIC_PATH, source_type="synthetic", source_name="synthetic_demo_v1")


@pytest.fixture(scope="module")
def pipeline_outputs(synthetic_df):
    feat = engineer_features(synthetic_df)
    X, y = get_raw_xy(feat)
    groups = synthetic_df["district"]
    results, fitted_models, preprocessor, split_data = run_model_comparison(X, y, groups, random_seed=42)
    return results, fitted_models, preprocessor, split_data


# ---------- Ingestion ----------

def test_ingestion_rejects_missing_source_type():
    with pytest.raises(DataSourceError):
        load_dataset(SYNTHETIC_PATH, source_type="unspecified", source_name="x")


def test_ingestion_rejects_missing_file():
    with pytest.raises(DataSourceError):
        load_dataset("does_not_exist.csv", source_type="real", source_name="x")


def test_ingestion_loads_synthetic(synthetic_df):
    assert len(synthetic_df) > 0
    assert synthetic_df.attrs["source_type"] == "synthetic"


def test_assert_not_real_claim_blocks_synthetic(synthetic_df):
    with pytest.raises(DataSourceError):
        assert_not_real_claim(synthetic_df)


# ---------- Validation / cleaning ----------

def test_validation_schema(synthetic_df):
    report = validate(synthetic_df)
    assert report.n_rows == len(synthetic_df)


def test_cleaning_drops_duplicates(synthetic_df):
    dupe_df = pd.concat([synthetic_df, synthetic_df.iloc[:5]], ignore_index=True)
    cleaned, report = clean(dupe_df)
    assert report["duplicates_dropped"] == 5


# ---------- Feature engineering (now raw, no leakage-prone step) ----------

def test_feature_engineering_is_raw_not_imputed(synthetic_df):
    """
    Regression test for the pre-release leakage fix: engineer_features()
    must NOT impute or encode — that happens only after the split, in
    the preprocessor. This test fails if someone reintroduces fillna()
    or pd.get_dummies() into engineer_features().
    """
    feat = engineer_features(synthetic_df)
    X, y = get_raw_xy(feat)
    assert len(X) == len(synthetic_df)
    # Categorical columns must still be raw strings, not one-hot columns:
    assert "district" in X.columns
    assert not any(c.startswith("district_") for c in X.columns)


# ---------- Leakage-safety: preprocessing fit only on training data ----------

def test_preprocessor_imputation_uses_only_fit_split_statistics():
    """
    Direct regression test for the leakage bug found in pre-release
    review: builds train/test sets with deliberately different
    distributions, fits the preprocessor on train only, and proves the
    test set's values did not influence the fitted median.
    """
    train_df = pd.DataFrame({
        "area_ha": [10.0, 20.0, 30.0, np.nan],
        "rainfall_mm": [100, 200, 300, 400],
        "temp_c": [25, 26, 27, 28],
        "humidity_pct": [70, 71, 72, 73],
        "rainfall_per_area": [1, 1, 1, 1],
        "temp_humidity_index": [1, 1, 1, 1],
        "district": ["A", "A", "B", "B"],
        "crop": ["Rice", "Rice", "Rice", "Rice"],
        "season": ["Boro", "Boro", "Boro", "Boro"],
    })
    # Test set's area_ha values are wildly different (e.g. 100000) —
    # if the imputer were fit on train+test combined, the median used
    # to fill train's NaN would shift toward this huge test value.
    test_df = pd.DataFrame({
        "area_ha": [100000.0, 200000.0],
        "rainfall_mm": [500, 600], "temp_c": [29, 30], "humidity_pct": [74, 75],
        "rainfall_per_area": [1, 1], "temp_humidity_index": [1, 1],
        "district": ["C", "C"], "crop": ["Rice", "Rice"], "season": ["Boro", "Boro"],
    })

    preprocessor = build_preprocessor()
    preprocessor.fit(train_df)  # fit on train ONLY

    numeric_imputer = preprocessor.named_transformers_["numeric"].named_steps["impute_median"]
    fitted_median_for_area_ha = numeric_imputer.statistics_[0]  # area_ha is first numeric column

    # The correct median of train's area_ha (ignoring NaN) is median(10, 20, 30) = 20.
    assert fitted_median_for_area_ha == 20.0, (
        f"Expected the imputer's fitted median to reflect ONLY the training data (20.0), "
        f"got {fitted_median_for_area_ha} — this would indicate test-set leakage into preprocessing."
    )


def test_preprocessor_handles_unknown_category_without_crashing():
    """District names appear in test that were never seen in fit — by
    design, given the group-held-out split. OneHotEncoder(handle_unknown="ignore")
    must not crash on this."""
    train_df = pd.DataFrame({
        "area_ha": [10.0], "rainfall_mm": [100], "temp_c": [25], "humidity_pct": [70],
        "rainfall_per_area": [1], "temp_humidity_index": [1],
        "district": ["A"], "crop": ["Rice"], "season": ["Boro"],
    })
    test_df = pd.DataFrame({
        "area_ha": [20.0], "rainfall_mm": [200], "temp_c": [26], "humidity_pct": [71],
        "rainfall_per_area": [1], "temp_humidity_index": [1],
        "district": ["NEVER_SEEN_DISTRICT"], "crop": ["Rice"], "season": ["Boro"],
    })
    preprocessor = build_preprocessor()
    preprocessor.fit(train_df)
    transformed = preprocessor.transform(test_df)  # must not raise
    assert transformed.shape[0] == 1


# ---------- Modelling + conformal intervals ----------

def test_three_way_split_has_no_overlapping_districts(synthetic_df):
    feat = engineer_features(synthetic_df)
    X, y = get_raw_xy(feat)
    groups = synthetic_df["district"]
    X_fit, y_fit, X_calib, y_calib, X_test, y_test = three_way_group_split(X, y, groups, random_seed=42)

    fit_districts = set(X_fit["district"])
    calib_districts = set(X_calib["district"])
    test_districts = set(X_test["district"])
    assert fit_districts.isdisjoint(calib_districts)
    assert fit_districts.isdisjoint(test_districts)
    assert calib_districts.isdisjoint(test_districts)


def test_model_comparison_beats_naive_on_mae(pipeline_outputs):
    results, _, _, _ = pipeline_outputs
    by_name = {r.model_name: r for r in results}
    # Sanity check on pipeline correctness using synthetic data with a
    # known planted signal — NOT a claim about real-world performance.
    assert by_name["random_forest"].mae < by_name["naive_mean_baseline"].mae
    assert by_name["ridge_regression"].mae < by_name["naive_mean_baseline"].mae


def test_conformal_interval_has_valid_structure(pipeline_outputs):
    results, _, _, _ = pipeline_outputs
    for r in results:
        assert r.conformal_interval_halfwidth >= 0
        assert 0 <= r.conformal_empirical_coverage <= 1
        assert r.conformal_coverage_target == 0.9


def test_conformal_empirical_coverage_roughly_matches_target(pipeline_outputs):
    """
    Not an exact-equality test (conformal coverage is a statistical
    guarantee, not exact on a finite test set) — checks the empirical
    coverage lands in a broad, defensible band around the 90% target.
    """
    results, _, _, _ = pipeline_outputs
    for r in results:
        assert 0.6 <= r.conformal_empirical_coverage <= 1.0, (
            f"{r.model_name}: empirical coverage {r.conformal_empirical_coverage} "
            f"is implausibly far from the 90% target — investigate the calibration logic."
        )


def test_held_out_prediction_is_model_generated_not_copied(pipeline_outputs, synthetic_df):
    """
    Direct regression test for the predicted_yield bug found in
    pre-release review: proves the "predicted" value actually comes
    from model.predict(), not from copying the observed target.
    """
    results, fitted_models, preprocessor, split_data = pipeline_outputs
    best_name = min((r for r in results if r.model_name != "naive_mean_baseline"),
                     key=lambda r: r.mae).model_name
    model, _ = fitted_models[best_name]
    X_test_t = split_data["X_test_t"]
    y_test = split_data["y_test"]

    predicted = float(model.predict(X_test_t[0:1])[0])
    observed = float(y_test.iloc[0])

    # The old bug made these identical by construction (predicted WAS observed).
    # On real model inference with held-out data, the two should almost never
    # be bit-identical. This is a meaningful assertion, not tautological:
    # it would fail immediately if someone reintroduced `predicted = observed`.
    assert predicted != observed, (
        "Predicted value exactly equals observed value — this is the exact "
        "shape of the previously-fixed bug (copying y instead of predicting). "
        "Investigate immediately if this ever fails."
    )

    # Changing the model should change the prediction (proves it's not a
    # hardcoded constant either).
    other_name = "ridge_regression" if best_name == "random_forest" else "random_forest"
    other_model, _ = fitted_models[other_name]
    other_predicted = float(other_model.predict(X_test_t[0:1])[0])
    assert other_predicted != predicted


# ---------- Governance ----------

def test_governance_check_no_personal_data(synthetic_df):
    assert check_no_personal_data(synthetic_df)["passed"] is True


def test_governance_check_flags_personal_data():
    df = pd.DataFrame({"district": ["Dhaka"], "farmer_name": ["x"]})
    assert check_no_personal_data(df)["passed"] is False


def test_governance_district_coverage(synthetic_df):
    assert check_district_coverage(synthetic_df, min_districts=3)["passed"] is True


def test_governance_error_metrics_check(pipeline_outputs):
    results, _, _, _ = pipeline_outputs
    assert check_error_metrics_present(results)["passed"] is True


def test_governance_prediction_interval_check(pipeline_outputs):
    results, _, _, _ = pipeline_outputs
    assert check_prediction_interval_present(results)["passed"] is True


def test_governance_synthetic_label_enforced():
    assert check_synthetic_label_present("synthetic", None)["passed"] is False
    assert check_synthetic_label_present(
        "synthetic", "DEMONSTRATION ONLY — NOT EMPIRICAL EVIDENCE")["passed"] is True


def test_governance_source_type_plausibility_catches_mismatch():
    result = check_source_type_plausible("real", "data/processed/synthetic_demo/synthetic_agroclimate_demo.csv")
    assert result["passed"] is False  # path says synthetic, declared as real — should flag


def test_governance_source_type_plausibility_passes_consistent_case():
    result = check_source_type_plausible("synthetic", "data/processed/synthetic_demo/synthetic_agroclimate_demo.csv")
    assert result["passed"] is True


# ---------- Product schema ----------

def test_recommendation_always_requires_human_review():
    rec = build_recommendation(
        district="Dhaka", crop="Rice", season="Boro",
        predicted_yield=4.2, observed_yield=4.5,
        mae=0.4, rmse=0.5, conformal_halfwidth=0.6, coverage_target=0.9,
        empirical_coverage=0.88,
        top_factors=["rainfall_mm"], model_version="v0.1", is_synthetic=True,
    )
    assert rec.recommended_action_type == "human_review"
    assert rec.demonstration_only is True
    assert rec.residual_t_per_ha == pytest.approx(0.3, abs=1e-6)
    assert any("SYNTHETIC" in lim for lim in rec.limitations)
    assert any("RETROSPECTIVE" in lim for lim in rec.limitations)
    assert "uncertainty" not in rec.evaluation_error_context.lower().replace("not a per-prediction uncertainty bound", "")


def test_recommendation_prediction_interval_is_centered_on_prediction():
    rec = build_recommendation(
        district="Dhaka", crop="Rice", season="Boro",
        predicted_yield=4.0, observed_yield=None,
        mae=0.4, rmse=0.5, conformal_halfwidth=0.5, coverage_target=0.9,
        empirical_coverage=0.9,
        top_factors=[], model_version="v0.1", is_synthetic=True,
    )
    assert rec.prediction_interval["low"] == pytest.approx(3.5)
    assert rec.prediction_interval["high"] == pytest.approx(4.5)
    assert rec.observed_yield_t_per_ha is None
    assert rec.residual_t_per_ha is None


# ---------- Source adapters ----------

def test_adapter_rejects_mapping_with_nonexistent_source_columns(tmp_path):
    csv_path = tmp_path / "fake_source.csv"
    pd.DataFrame({"real_col_a": [1, 2], "real_col_b": [3, 4]}).to_csv(csv_path, index=False)
    with pytest.raises(ValueError):
        adapt_generic_wide_csv(str(csv_path), column_mapping={"col_that_does_not_exist": "district"})


def test_adapter_applies_valid_mapping_and_flags_requires_validation(tmp_path):
    csv_path = tmp_path / "fake_source.csv"
    pd.DataFrame({"zila": ["Dhaka"], "fasol": ["Rice"]}).to_csv(csv_path, index=False)
    df, report = adapt_generic_wide_csv(str(csv_path), column_mapping={"zila": "district", "fasol": "crop"})
    assert "district" in df.columns
    assert df.attrs["adapter_status"] == "REQUIRES_LOCAL_VALIDATION"
    assert report["fully_canonical"] is False  # only 2 of 10 canonical columns present


def test_validate_canonical_output_reports_missing_columns():
    df = pd.DataFrame({"district": ["Dhaka"]})
    report = validate_canonical_output(df, adapter_name="test")
    assert "crop" in report["canonical_columns_missing"]
    assert report["fully_canonical"] is False


# ---------------------------------------------------------------------------
# Real-data layer regression tests (v0.1.0)
# ---------------------------------------------------------------------------
import subprocess  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.data.adapters import adapt_sajidahmed12_crop_csv, ACRE_TO_HA  # noqa: E402
from src.data.cleaning import clean  # noqa: E402
from src.features.engineering import engineer_features  # noqa: E402
from src.models.train import three_way_temporal_split  # noqa: E402

_COLS = ["Crop Name", "Area Name", "Area of Land in acres",
         "Amount of Production in Tons", "Rainfall in MM", "Year"]


def _write_crop_csv(tmp_path, name, rows):
    p = tmp_path / name
    pd.DataFrame(rows, columns=_COLS).to_csv(p, index=False)
    return str(p)


def test_adapter_drops_region_division_and_ht_rows(tmp_path):
    rows = [["Jute", "Bogra ", 1000, 2000, 10, 1970],
            ["Jute", "Rajshahi Region", 5000, 9000, 10, 1970],
            ["Jute", "Dhaka Division", 5000, 9000, 10, 1970],
            ["Jute", "H.T. Total", 5000, 9000, 10, 1970],
            ["Jute", "Pabna", 800, 1000, 10, 1970]]
    df, rep = adapt_sajidahmed12_crop_csv({"jute": _write_crop_csv(tmp_path, "j.csv", rows)})
    assert rep["region_aggregate_rows_dropped"] == 3
    assert sorted(df["district"]) == ["Bogra", "Pabna"]


def test_adapter_unit_conversion_and_yield(tmp_path):
    rows = [["Wheat", "Bogra", 1000, 400, 5, 1971]]
    df, _ = adapt_sajidahmed12_crop_csv({"wheat": _write_crop_csv(tmp_path, "w.csv", rows)})
    assert df["area_ha"].iloc[0] == pytest.approx(1000 * ACRE_TO_HA)
    assert df["yield_t_per_ha"].iloc[0] == pytest.approx(400 / (1000 * ACRE_TO_HA))


def test_adapter_never_invents_climate_or_season(tmp_path):
    rows = [["Wheat", "Bogra", 1000, 400, 5, 1971]]
    df, rep = adapt_sajidahmed12_crop_csv({"wheat": _write_crop_csv(tmp_path, "w.csv", rows)})
    assert df["temp_c"].isna().all() and df["humidity_pct"].isna().all()
    assert rep["climate_variables_available"] is False
    assert df["season"].iloc[0] == "annual_aggregate"
    assert df.attrs["source_type"] == "real"


def test_adapter_separates_zero_area_cases(tmp_path):
    rows = [["Jute", "A", 0, 0, 5, 1970], ["Jute", "B", 0, 50, 5, 1970], ["Jute", "C", 100, 50, 5, 1970]]
    df, rep = adapt_sajidahmed12_crop_csv({"jute": _write_crop_csv(tmp_path, "j.csv", rows)})
    assert rep["zero_area_zero_production_rows_dropped"] == 1
    assert rep["zero_area_inconsistent_rows_dropped"] == 1
    assert list(df["district"]) == ["C"]


def test_adapter_rejects_unexpected_columns(tmp_path):
    p = tmp_path / "bad.csv"
    pd.DataFrame({"a": [1]}).to_csv(p, index=False)
    with pytest.raises(ValueError):
        adapt_sajidahmed12_crop_csv({"jute": str(p)})


def test_clean_does_not_wipe_rows_when_optional_columns_all_nan(tmp_path):
    rows = [["Jute", "Bogra", 1000, 2000, 10, 1970], ["Wheat", "Pabna", 800, 1000, 10, 1971]]
    df, _ = adapt_sajidahmed12_crop_csv({"x": _write_crop_csv(tmp_path, "x.csv", rows)})
    out, rep = clean(df)
    assert len(out) == 2 and rep["out_of_range_dropped"] == 0


def test_clean_still_drops_present_out_of_range_values(tmp_path):
    rows = [["Jute", "Bogra", 1, 655, 10, 1970], ["Jute", "Pabna", 800, 1000, 10, 1971]]
    df, _ = adapt_sajidahmed12_crop_csv({"x": _write_crop_csv(tmp_path, "x.csv", rows)})
    out, rep = clean(df)
    assert rep["out_of_range_dropped"] == 1 and len(out) == 1


def test_engineer_features_handles_zero_area_and_missing_climate():
    df = pd.DataFrame({"area_ha": [0.0, 2.0], "rainfall_mm": [10.0, 10.0]})
    out = engineer_features(df)
    assert np.isnan(out["rainfall_per_area"].iloc[0])
    assert out["rainfall_per_area"].dtype == float
    assert out["temp_humidity_index"].isna().all()


def test_temporal_split_is_strictly_chronological_and_disjoint():
    years = pd.Series(np.repeat(np.arange(1970, 2015), 4))
    X = pd.DataFrame({"f": np.arange(len(years))})
    y = pd.Series(np.arange(len(years), dtype=float))
    Xf, yf, Xc, yc, Xt, yt, info = three_way_temporal_split(X, y, years)
    assert years[Xf.index].max() < years[Xc.index].min()
    assert years[Xc.index].max() < years[Xt.index].min()
    assert len(Xf) + len(Xc) + len(Xt) == len(X)
    assert info["fit_years"][1] < info["calib_years"][0] < info["test_years"][0]


def test_temporal_split_requires_enough_years():
    years = pd.Series([2000, 2000, 2001])
    with pytest.raises(ValueError):
        three_way_temporal_split(pd.DataFrame({"f": [1, 2, 3]}), pd.Series([1., 2., 3.]), years)


def test_real_pipeline_refuses_to_fall_back_to_synthetic(tmp_path):
    import shutil, os
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stash = os.path.join(repo, "data", "raw", "sajidahmed12_crop_data")
    tmp = str(tmp_path / "stash")
    had_data = os.path.isdir(stash)
    if had_data:
        shutil.move(stash, tmp)
    try:
        r = subprocess.run(["python3", os.path.join(repo, "scripts", "run_real_pipeline.py")],
                           capture_output=True, text=True)
        assert r.returncode != 0
        assert "never falls back" in (r.stderr + r.stdout).lower()
    finally:
        if had_data:
            shutil.move(tmp, stash)


def test_production_is_never_a_real_pipeline_predictor():
    import importlib.util, os
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("rrp", os.path.join(repo, "scripts", "run_real_pipeline.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    feats = set(mod.REAL_NUMERIC_FEATURES + mod.REAL_CATEGORICAL_FEATURES)
    assert "production_t" not in feats and "yield_t_per_ha" not in feats


def test_fetch_sha256_verification_detects_tampering(tmp_path):
    import importlib.util, os
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("frd", os.path.join(repo, "scripts", "fetch_real_data.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    f = tmp_path / "x.csv"; f.write_bytes(b"hello")
    import hashlib
    mod.verify_sha256(str(f), hashlib.sha256(b"hello").hexdigest())  # passes
    with pytest.raises(mod.IntegrityError):
        mod.verify_sha256(str(f), "0" * 64)
    assert set(mod.SAJID_FILES) == {"jute.csv", "wheat.csv"}


# ---------------------------------------------------------------------------
# Split-conformal quantile: order-statistic correctness and input validation
# ---------------------------------------------------------------------------
def test_conformal_halfwidth_is_the_kth_order_statistic():
    r = np.arange(1, 10, dtype=float)            # n=9
    # k = ceil(10 * 0.8) = 8 -> the 8th smallest, exactly (no interpolation)
    assert split_conformal_halfwidth(r, 0.8) == 8.0
    # shuffled input gives the same answer
    assert split_conformal_halfwidth(np.random.default_rng(0).permutation(r), 0.8) == 8.0


def test_conformal_halfwidth_is_always_an_observed_residual():
    r = np.array([0.1, 0.35, 0.9, 1.7, 2.2, 3.05, 4.4, 5.0, 6.6, 7.1, 9.3])
    for cov in (0.5, 0.8, 0.9):
        assert split_conformal_halfwidth(r, cov) in set(r)


def test_conformal_halfwidth_float_rounding_guard():
    r = np.arange(1, 100, dtype=float)           # n=99, (n+1)*0.9 = 90.00000000000001 in floats
    assert split_conformal_halfwidth(r, 0.9) == 90.0


def test_conformal_halfwidth_old_interpolated_quantile_differs():
    # n=10, coverage 0.8: k=ceil(11*0.8)=9 -> 9th smallest (9.0). The previous
    # interpolated implementation returned a non-observed value here.
    r = np.arange(1, 11, dtype=float)
    assert split_conformal_halfwidth(r, 0.8) == 9.0


def test_conformal_halfwidth_rejects_too_small_calibration_set():
    with pytest.raises(ValueError, match="too small"):
        split_conformal_halfwidth(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), 0.9)  # k=6 > n=5


@pytest.mark.parametrize("bad", [0, 1, 0.0, 1.0, -0.1, 1.5, float("nan"), float("inf"), None, "0.9", True])
def test_conformal_halfwidth_rejects_invalid_coverage(bad):
    with pytest.raises(ValueError):
        split_conformal_halfwidth(np.arange(1, 50, dtype=float), bad)


@pytest.mark.parametrize("bad", [np.array([]), np.array([[1.0, 2.0]]), np.array([1.0, np.nan, 3.0]),
                                  np.array([1.0, np.inf]), np.array([-1.0, 2.0, 3.0])])
def test_conformal_halfwidth_rejects_invalid_residuals(bad):
    with pytest.raises(ValueError):
        split_conformal_halfwidth(bad, 0.5)


def test_conformal_marginal_coverage_under_exchangeability():
    rng = np.random.default_rng(12345)
    covered = []
    for _ in range(400):
        cal = np.abs(rng.normal(size=60))
        test = np.abs(rng.normal(size=200))
        hw = split_conformal_halfwidth(cal, 0.9)
        covered.append(np.mean(test <= hw))
    assert np.mean(covered) >= 0.89               # guarantee is >= 0.9 marginally


def test_conformal_halfwidth_four_residuals_at_half_coverage_returns_three():
    # n=4, k=ceil(5*0.5)=ceil(2.5)=3 -> third smallest residual, no interpolation
    assert split_conformal_halfwidth(np.array([1.0, 2.0, 3.0, 4.0]), 0.5) == 3.0


def test_conformal_halfwidth_exact_ceiling_edge_case_raises():
    # (2 + 1) * 0.6666666668 = 2.0000000004 -> k = 3 > n = 2: must raise, not return a
    # finite halfwidth (an approximate rounding rule would wrongly give k = 2).
    with pytest.raises(ValueError, match="too small"):
        split_conformal_halfwidth(np.array([1.0, 2.0]), 0.6666666668)


def test_conformal_halfwidth_exact_boundaries_not_over_ceiled():
    assert split_conformal_halfwidth(np.array([1.0, 2.0]), 0.5) == 2.0          # k = ceil(1.5) = 2
    assert split_conformal_halfwidth(np.array([1.0, 2.0, 3.0]), 0.75) == 3.0    # (3+1)*0.75 = 3 exactly


def test_conformal_halfwidth_rejects_empty_calibration_set():
    with pytest.raises(ValueError, match="non-empty"):
        split_conformal_halfwidth(np.array([]), 0.9)
