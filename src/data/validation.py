"""
Data quality validation: schema, missingness, duplicates, basic range
checks. Returns a structured report rather than silently passing or
failing, because "the pipeline ran" and "the data is trustworthy" are
different claims — this module exists to keep the documentation honest
about which one actually holds for any given run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import pandas as pd


@dataclass
class ValidationReport:
    n_rows: int
    n_duplicate_rows: int
    missingness_by_column: dict
    out_of_range_flags: dict = field(default_factory=dict)
    passed: bool = True
    issues: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "n_rows": self.n_rows,
            "n_duplicate_rows": self.n_duplicate_rows,
            "missingness_by_column": self.missingness_by_column,
            "out_of_range_flags": self.out_of_range_flags,
            "passed": self.passed,
            "issues": self.issues,
        }


# Plausible physical ranges — used only to flag obviously broken rows
# (e.g. negative rainfall), not to assert these are the "correct"
# ranges for Bangladesh specifically.
RANGE_CHECKS = {
    "area_ha": (0, None),
    "production_t": (0, None),
    "yield_t_per_ha": (0, 50),       # generous upper bound, flags data-entry errors
    "rainfall_mm": (0, 5000),        # broad sanity bound only; source unit/aggregation may be unknown
    "temp_c": (-5, 50),
    "humidity_pct": (0, 100),
}


def validate(df: pd.DataFrame) -> ValidationReport:
    issues = []

    missingness = {col: float(df[col].isna().mean()) for col in df.columns}
    high_missing = {c: v for c, v in missingness.items() if v > 0.2}
    if high_missing:
        issues.append(f"Columns with >20% missing values: {high_missing}")

    n_dupes = int(df.duplicated().sum())
    if n_dupes > 0:
        issues.append(f"{n_dupes} fully duplicate rows found")

    out_of_range = {}
    for col, (lo, hi) in RANGE_CHECKS.items():
        if col not in df.columns:
            continue
        mask = pd.Series(False, index=df.index)
        if lo is not None:
            mask |= df[col] < lo
        if hi is not None:
            mask |= df[col] > hi
        n_bad = int(mask.sum())
        if n_bad > 0:
            out_of_range[col] = n_bad
            issues.append(f"{n_bad} rows with {col} outside plausible range [{lo}, {hi}]")

    passed = len(issues) == 0

    return ValidationReport(
        n_rows=len(df),
        n_duplicate_rows=n_dupes,
        missingness_by_column=missingness,
        out_of_range_flags=out_of_range,
        passed=passed,
        issues=issues,
    )
