"""
Cleaning: drop exact duplicates, clip obviously-impossible values flagged
by validation, standardize text columns. Deliberately conservative —
this module does not impute missing values silently; it drops rows
with missing required fields and reports how many, because silent
imputation on a small dataset can manufacture signal that isn't there.
"""

from __future__ import annotations

import pandas as pd

from .validation import RANGE_CHECKS


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report = {}
    start_n = len(df)

    df = df.drop_duplicates().copy()
    report["duplicates_dropped"] = start_n - len(df)

    for col in ("district", "crop", "season"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()

    before_range = len(df)
    for col, (lo, hi) in RANGE_CHECKS.items():
        if col not in df.columns:
            continue
        # Only reject a row when the value is PRESENT and out of range;
        # a missing optional value (NaN) is not an out-of-range value.
        if lo is not None:
            df = df[~(df[col].notna() & (df[col] < lo))]
        if hi is not None:
            df = df[~(df[col].notna() & (df[col] > hi))]
    report["out_of_range_dropped"] = before_range - len(df)

    before_na = len(df)
    df = df.dropna(subset=[c for c in df.columns if c in
                            ("district", "crop", "season", "year", "yield_t_per_ha")])
    report["missing_required_dropped"] = before_na - len(df)

    report["final_n_rows"] = len(df)
    df.attrs["cleaning_report"] = report
    return df, report
