"""
Feature engineering — deliberately limited to deterministic, row-wise
transforms only (no aggregate statistic, like a median or a category
list, is computed here). That split is the point: anything requiring a
dataset-level statistic (imputation values, the set of known
categories) must be fit AFTER the train/test split, inside
src/models/preprocessing.py — never here. See docs/03-analytics-pipeline.md
"Leakage-safe preprocessing" for why this module was restructured.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

NUMERIC_FEATURES = ["area_ha", "rainfall_mm", "temp_c", "humidity_pct",
                     "rainfall_per_area", "temp_humidity_index"]
CATEGORICAL_FEATURES = ["district", "crop", "season"]
TARGET_COLUMN = "yield_t_per_ha"


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Adds row-wise derived features only. No fillna, no encoding."""
    df = df.copy()
    area = df["area_ha"].astype(float).replace(0, np.nan)
    df["rainfall_per_area"] = df["rainfall_mm"].astype(float) / area
    if "temp_c" in df.columns and "humidity_pct" in df.columns:
        df["temp_humidity_index"] = (df["temp_c"].astype(float)
                                     * df["humidity_pct"].astype(float) / 100.0)
    else:
        df["temp_humidity_index"] = np.nan
    return df


def get_raw_xy(df: pd.DataFrame, numeric_features=None,
               categorical_features=None) -> tuple[pd.DataFrame, pd.Series]:
    """
    Returns the RAW feature matrix (numeric + categorical columns,
    possibly containing NaN) and target. Imputation and categorical
    encoding happen later, in src/models/preprocessing.py, fit only on
    the training split.
    """
    num = NUMERIC_FEATURES if numeric_features is None else numeric_features
    cat = CATEGORICAL_FEATURES if categorical_features is None else categorical_features
    X = df[list(num) + list(cat)].copy()
    y = df[TARGET_COLUMN]
    return X, y
