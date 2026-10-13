"""
Models: a naive baseline, Ridge, and Random Forest, with leakage-safe
preprocessing and real split-conformal prediction intervals.

Three-way group split (by district, not row), not two-way:
    fit        — model training
    calibrate  — conformal interval calibration (NEVER used in training)
    test       — final evaluation, untouched until the very end

This replaces an earlier version that (a) imputed/encoded on the full
dataset before splitting — a real leakage bug fixed here by fitting
src/models/preprocessing.py's transformer on the fit split only, and
(b) called MAE/RMSE an "uncertainty range," which is a technically
incorrect description of an aggregate error metric. Split-conformal
prediction intervals, calibrated on a genuinely held-out calibration
set and evaluated for empirical coverage on test, are what an
uncertainty claim actually requires — implemented below.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit

from src.models.preprocessing import build_preprocessor


@dataclass
class EvalResult:
    model_name: str
    n_fit: int
    n_calibrate: int
    n_test: int
    mae: float
    rmse: float
    r2: float
    conformal_coverage_target: float
    conformal_interval_halfwidth: float
    conformal_empirical_coverage: float
    random_seed: int


def naive_baseline_predict(y_fit: pd.Series, n: int) -> np.ndarray:
    return np.full(n, y_fit.mean())


def three_way_group_split(X: pd.DataFrame, y: pd.Series, groups: pd.Series,
                           test_size: float = 0.25, calib_size: float = 0.20,
                           random_seed: int = 42):
    """
    Splits by group (district) twice: first carving off `test`, then
    carving `calibrate` out of what remains, leaving `fit`. No group
    (district) ever appears in more than one of the three splits.
    """
    splitter1 = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_seed)
    trainval_idx, test_idx = next(splitter1.split(X, y, groups=groups))

    X_trainval, y_trainval = X.iloc[trainval_idx], y.iloc[trainval_idx]
    groups_trainval = groups.iloc[trainval_idx]

    splitter2 = GroupShuffleSplit(n_splits=1, test_size=calib_size, random_state=random_seed)
    fit_idx, calib_idx = next(splitter2.split(X_trainval, y_trainval, groups=groups_trainval))

    X_fit, y_fit = X_trainval.iloc[fit_idx], y_trainval.iloc[fit_idx]
    X_calib, y_calib = X_trainval.iloc[calib_idx], y_trainval.iloc[calib_idx]
    X_test, y_test = X.iloc[test_idx], y.iloc[test_idx]

    return X_fit, y_fit, X_calib, y_calib, X_test, y_test


def three_way_temporal_split(X: pd.DataFrame, y: pd.Series, year_col: pd.Series,
                              fit_frac: float = 0.6, calib_frac: float = 0.2):
    """
    Chronological split by unique year: earliest `fit_frac` of years -> fit,
    next `calib_frac` -> calibrate, remainder -> test. No year appears in
    more than one split, and every test year is later than every fit /
    calibration year. Returns (..., split_info) with the year ranges.
    """
    years = np.array(sorted(pd.Series(year_col).dropna().unique()))
    n = len(years)
    n_fit = max(int(round(n * fit_frac)), 1)
    n_cal = max(int(round(n * calib_frac)), 1)
    if n_fit + n_cal >= n:
        raise ValueError("Not enough distinct years for a 3-way temporal split.")
    fit_years, cal_years, test_years = years[:n_fit], years[n_fit:n_fit + n_cal], years[n_fit + n_cal:]
    yr = pd.Series(year_col).values
    m_fit, m_cal, m_test = np.isin(yr, fit_years), np.isin(yr, cal_years), np.isin(yr, test_years)
    info = {"fit_years": (int(fit_years[0]), int(fit_years[-1])),
            "calib_years": (int(cal_years[0]), int(cal_years[-1])),
            "test_years": (int(test_years[0]), int(test_years[-1]))}
    return (X[m_fit], y[m_fit], X[m_cal], y[m_cal], X[m_test], y[m_test], info)


def split_conformal_halfwidth(residuals_abs: np.ndarray, coverage: float = 0.9) -> float:
    """
    Split-conformal interval halfwidth: the k-th smallest absolute
    calibration residual, with k = ceil((n + 1) * coverage), computed exactly with Decimal. This is an
    actual order statistic (no interpolation), which is what the standard
    finite-sample split-conformal argument requires.

    Exactness: the rank uses Decimal arithmetic on the decimal (shortest round-trip)
    representation of `coverage`, with no approximate rounding rule, so e.g.
    n=2, coverage=0.6666666668 gives k=3 > n and raises.

    Validation (raises ValueError rather than returning a misleading value):
      * coverage must be a real number with 0 < coverage < 1;
      * residuals_abs must be a non-empty 1-D array of finite, non-negative values;
      * if k > n the calibration set is too small for the requested coverage
        (a finite interval with that guarantee does not exist) — raised, not
        silently clipped to the maximum residual.

    The coverage guarantee (>= coverage, marginally) holds under
    exchangeability of calibration and test points; it is not a guarantee
    under temporal distribution shift.
    """
    if isinstance(coverage, bool) or not isinstance(coverage, (int, float, np.floating, np.integer)):
        raise ValueError(f"coverage must be a real number in (0, 1), got {coverage!r}")
    coverage = float(coverage)
    if not np.isfinite(coverage) or not (0.0 < coverage < 1.0):
        raise ValueError(f"coverage must satisfy 0 < coverage < 1, got {coverage!r}")
    r = np.asarray(residuals_abs, dtype=float)
    if r.ndim != 1 or r.size == 0:
        raise ValueError("residuals_abs must be a non-empty 1-D array")
    if not np.all(np.isfinite(r)) or np.any(r < 0):
        raise ValueError("residuals_abs must contain only finite, non-negative values")
    n = r.size
    # Exact rank: k = ceil((n + 1) * coverage), computed in Decimal arithmetic on the
    # decimal representation of `coverage` (Python's shortest round-trip repr, so the
    # float 0.9 is treated as exactly 0.9). No approximate rounding rule is applied:
    #   (99 + 1) * 0.9            -> 90            (binary floats would give 90.00000000000001)
    #   (2 + 1) * 0.6666666668    -> 2.0000000004  -> k = 3 > n
    k = int(((n + 1) * Decimal(repr(coverage))).to_integral_value(rounding="ROUND_CEILING"))
    if k > n:
        raise ValueError(
            f"Calibration set too small: n={n} residuals cannot support coverage={coverage} "
            f"(needs k=ceil((n+1)*coverage)={k} <= n). Use more calibration data or a lower coverage."
        )
    return float(np.sort(r)[k - 1])


def evaluate_test_metrics(y_true, y_pred, model_name: str, n_fit: int,
                           n_calib: int, conformal_halfwidth: float,
                           coverage_target: float, random_seed: int) -> EvalResult:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    r2 = r2_score(y_true, y_pred) if len(set(y_true)) > 1 else float("nan")

    within_interval = np.abs(np.asarray(y_true) - np.asarray(y_pred)) <= conformal_halfwidth
    empirical_coverage = float(np.mean(within_interval))

    return EvalResult(
        model_name=model_name, n_fit=n_fit, n_calibrate=n_calib, n_test=len(y_true),
        mae=round(float(mae), 4), rmse=round(float(rmse), 4),
        r2=round(float(r2), 4) if not np.isnan(r2) else None,
        conformal_coverage_target=coverage_target,
        conformal_interval_halfwidth=round(conformal_halfwidth, 4),
        conformal_empirical_coverage=round(empirical_coverage, 4),
        random_seed=random_seed,
    )


def run_model_comparison(X: pd.DataFrame, y: pd.Series, groups: pd.Series,
                          random_seed: int = 42, coverage_target: float = 0.9,
                          numeric_features=None, categorical_features=None,
                          split_data_override=None):
    """groups is used for the district-group split unless split_data_override
    (a 6-tuple X_fit,y_fit,X_calib,y_calib,X_test,y_test, e.g. temporal) is given."""
    if split_data_override is not None:
        X_fit, y_fit, X_calib, y_calib, X_test, y_test = split_data_override
    else:
        X_fit, y_fit, X_calib, y_calib, X_test, y_test = three_way_group_split(
            X, y, groups, random_seed=random_seed)

    preprocessor = build_preprocessor(numeric_features, categorical_features)
    preprocessor.fit(X_fit)  # fit ONLY on the fit split — this is the leakage fix
    X_fit_t = preprocessor.transform(X_fit)
    X_calib_t = preprocessor.transform(X_calib)
    X_test_t = preprocessor.transform(X_test)

    results = []
    fitted_models = {}

    # 1. Naive baseline — same conformal procedure applied for a fair comparison
    pred_calib = naive_baseline_predict(y_fit, len(y_calib))
    halfwidth = split_conformal_halfwidth(np.abs(y_calib.values - pred_calib), coverage_target)
    pred_test = naive_baseline_predict(y_fit, len(y_test))
    results.append(evaluate_test_metrics(y_test, pred_test, "naive_mean_baseline",
                                          len(y_fit), len(y_calib), halfwidth,
                                          coverage_target, random_seed))

    # 2. Ridge
    ridge = Ridge(random_state=random_seed)
    ridge.fit(X_fit_t, y_fit)
    pred_calib = ridge.predict(X_calib_t)
    halfwidth = split_conformal_halfwidth(np.abs(y_calib.values - pred_calib), coverage_target)
    pred_test = ridge.predict(X_test_t)
    results.append(evaluate_test_metrics(y_test, pred_test, "ridge_regression",
                                          len(y_fit), len(y_calib), halfwidth,
                                          coverage_target, random_seed))
    fitted_models["ridge_regression"] = (ridge, halfwidth)

    # 3. Random Forest
    rf = RandomForestRegressor(n_estimators=200, max_depth=6, random_state=random_seed)
    rf.fit(X_fit_t, y_fit)
    pred_calib = rf.predict(X_calib_t)
    halfwidth = split_conformal_halfwidth(np.abs(y_calib.values - pred_calib), coverage_target)
    pred_test = rf.predict(X_test_t)
    results.append(evaluate_test_metrics(y_test, pred_test, "random_forest",
                                          len(y_fit), len(y_calib), halfwidth,
                                          coverage_target, random_seed))
    fitted_models["random_forest"] = (rf, halfwidth)

    split_data = {
        "X_fit": X_fit, "y_fit": y_fit, "X_calib": X_calib, "y_calib": y_calib,
        "X_test": X_test, "y_test": y_test,
        "X_test_t": X_test_t,
    }
    return results, fitted_models, preprocessor, split_data
