"""
Automated governance checks — turning parts of docs/04-governance-framework.md
into code that actually runs, rather than a document nobody re-verifies.

check_uncertainty_present() was renamed to check_error_metrics_present()
and a separate check_prediction_interval_present() was added, following
pre-release review: MAE/RMSE are aggregate evaluation error metrics, not
an individual-prediction uncertainty interval, and the old name
conflated the two. A real prediction-interval check now verifies the
conformal-interval fields (src/models/train.py) are actually present.
"""

from __future__ import annotations

import pandas as pd

FORBIDDEN_PERSONAL_FIELDS = {
    "farmer_name", "phone_number", "nid", "national_id", "address",
    "farmer_id", "email", "gps_exact", "household_id",
}


def check_no_personal_data(df: pd.DataFrame) -> dict:
    present = FORBIDDEN_PERSONAL_FIELDS & set(c.lower() for c in df.columns)
    return {
        "check": "no_personal_data",
        "passed": len(present) == 0,
        "details": f"Forbidden personal-data columns found: {present}" if present else "None found.",
    }


def check_district_coverage(df: pd.DataFrame, min_districts: int = 3) -> dict:
    n_districts = df["district"].nunique() if "district" in df.columns else 0
    return {
        "check": "district_coverage",
        "passed": n_districts >= min_districts,
        "details": f"{n_districts} distinct districts present (minimum expected: {min_districts}).",
    }


def check_error_metrics_present(eval_results: list) -> dict:
    """
    Every reported model result must include both MAE and RMSE — an
    aggregate error-metric completeness check. This does NOT check for
    an individual-prediction uncertainty interval; see
    check_prediction_interval_present() for that.
    """
    ok = all(hasattr(r, "mae") and hasattr(r, "rmse") for r in eval_results)
    return {
        "check": "error_metrics_present",
        "passed": ok,
        "details": "Every model result includes both MAE and RMSE." if ok
                   else "At least one model result is missing a required error metric.",
    }


def check_prediction_interval_present(eval_results: list) -> dict:
    """
    Every reported model result must include an actual split-conformal
    prediction interval (halfwidth + empirical coverage), not just an
    aggregate error metric mislabelled as "uncertainty."
    """
    required_attrs = ("conformal_coverage_target", "conformal_interval_halfwidth",
                       "conformal_empirical_coverage")
    ok = all(all(hasattr(r, a) for a in required_attrs) for r in eval_results)
    return {
        "check": "prediction_interval_present",
        "passed": ok,
        "details": "Every model result includes a conformal prediction interval and its empirical coverage."
                   if ok else "At least one model result is missing conformal-interval fields.",
    }


def check_synthetic_label_present(source_type: str, output_label: str | None) -> dict:
    if source_type != "synthetic":
        return {"check": "synthetic_label_present", "passed": True,
                "details": "Not applicable — data is not synthetic."}
    required = "DEMONSTRATION ONLY"
    ok = bool(output_label) and required in output_label
    return {
        "check": "synthetic_label_present",
        "passed": ok,
        "details": "Synthetic-data label correctly present." if ok
                  else f"Synthetic data in use but output is not labelled with '{required}'.",
    }


def check_source_type_plausible(source_type: str, source_path: str | None) -> dict:
    """
    Lightweight guardrail (NOT a guarantee): flags an obvious
    mismatch if a path containing 'synthetic' is declared source_type
    'real', or vice versa. This cannot detect every mislabeling —
    source_type is fundamentally a developer declaration, not something
    inferred from file content — but it catches the most likely
    copy-paste mistake.
    """
    if not source_path:
        return {"check": "source_type_plausible", "passed": True, "details": "No path to check (e.g. uploaded data)."}
    path_lower = source_path.lower()
    mismatch = (
        ("synthetic" in path_lower and source_type == "real") or
        ("synthetic" not in path_lower and source_type == "synthetic" and "demo" not in path_lower)
    )
    return {
        "check": "source_type_plausible",
        "passed": not mismatch,
        "details": "No obvious path/source_type mismatch." if not mismatch
                   else f"Path {source_path!r} looks inconsistent with declared source_type={source_type!r} — verify this wasn't a mistake.",
    }


def run_all_checks(df: pd.DataFrame, eval_results: list, source_type: str,
                    output_label: str | None, source_path: str | None = None) -> list[dict]:
    return [
        check_no_personal_data(df),
        check_district_coverage(df),
        check_error_metrics_present(eval_results),
        check_prediction_interval_present(eval_results),
        check_synthetic_label_present(source_type, output_label),
        check_source_type_plausible(source_type, source_path),
    ]
