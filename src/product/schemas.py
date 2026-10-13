"""
Decision-support output contract. Every model output that would reach a
human user must pass through build_recommendation() — there is no path
in this codebase that hands a raw model prediction to a user without
an evaluation-error context, a real conformal prediction interval,
data-quality status, evidence sources, and a human-review flag attached.

Pre-release review found two real bugs here, both fixed:
1. The example output previously used an OBSERVED target value
   (y.iloc[0]) mislabelled as "predicted_yield" — it is now an actual
   model.predict() output on a genuinely held-out test row, with the
   observed value, prediction, and residual all reported separately
   so the distinction is visible, not just correct internally.
2. "uncertainty_note" built from bare MAE/RMSE has been replaced with
   an actual split-conformal prediction interval plus its empirically
   measured coverage — MAE/RMSE are now reported separately as
   "evaluation_error_context", not described as an uncertainty range.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class DecisionSupportOutput:
    district: str
    crop: str
    season: str
    analysis_date: str
    observed_yield_t_per_ha: float | None
    predicted_yield_t_per_ha: float
    residual_t_per_ha: float | None
    prediction_interval: dict  # {low, high, coverage_target, empirical_coverage}
    evaluation_error_context: str
    data_quality_label: str
    top_factors: list
    recommended_action_type: str  # always "human_review" in this prototype
    model_version: str
    evidence_sources: list
    limitations: list
    demonstration_only: bool

    def to_dict(self) -> dict:
        return asdict(self)


def build_recommendation(
    district: str, crop: str, season: str,
    predicted_yield: float,
    observed_yield: float | None,
    mae: float, rmse: float,
    conformal_halfwidth: float, coverage_target: float, empirical_coverage: float,
    top_factors: list,
    model_version: str,
    is_synthetic: bool,
) -> DecisionSupportOutput:
    residual = (observed_yield - predicted_yield) if observed_yield is not None else None

    evaluation_error_context = (
        f"On the held-out test set, this model's aggregate error was "
        f"MAE={mae:.3f} t/ha, RMSE={rmse:.3f} t/ha. These are evaluation-set "
        f"averages, not a per-prediction uncertainty bound — see "
        f"prediction_interval for that."
    )

    prediction_interval = {
        "low": round(predicted_yield - conformal_halfwidth, 3),
        "high": round(predicted_yield + conformal_halfwidth, 3),
        "coverage_target": coverage_target,
        "empirical_coverage_on_test": empirical_coverage,
        "method": "split-conformal (absolute-residual, finite-sample corrected)",
    }

    limitations = [
        "RETROSPECTIVE YIELD ESTIMATION, NOT A PRE-SEASON FORECAST: the model uses source-provided "
        "same-period inputs. In the real jute/wheat experiment these are the source-reported "
        "rainfall field (aggregation unverified); temperature and humidity are absent. The "
        "synthetic demonstration uses generated temperature/humidity. It is not a crop-"
        "recommendation or pre-planting forecasting tool.",
        "Interval coverage is empirical coverage on a held-out evaluation set; it is not a "
        "guarantee of future coverage, especially under temporal distribution shift.",
        "Not validated against real-world field outcomes.",
        "District-level resolution only; does not capture farm-level variation.",
        "No causal claim is made between any input variable and yield.",
    ]
    if is_synthetic:
        limitations.insert(0, "UNDERLYING DATA IS SYNTHETIC — see data/processed/synthetic_demo/README.md.")

    return DecisionSupportOutput(
        district=district, crop=crop, season=season,
        analysis_date=datetime.now(timezone.utc).date().isoformat(),
        observed_yield_t_per_ha=round(observed_yield, 3) if observed_yield is not None else None,
        predicted_yield_t_per_ha=round(predicted_yield, 3),
        residual_t_per_ha=round(residual, 3) if residual is not None else None,
        prediction_interval=prediction_interval,
        evaluation_error_context=evaluation_error_context,
        data_quality_label="synthetic_demonstration" if is_synthetic else "real_unvalidated",
        top_factors=top_factors,
        recommended_action_type="human_review",
        model_version=model_version,
        evidence_sources=["See docs/data-provenance/provenance-register.md"],
        limitations=limitations,
        demonstration_only=is_synthetic,
    )
