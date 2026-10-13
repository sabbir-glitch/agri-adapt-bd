"""
Explainability: feature importance for the Random Forest and coefficients
for Ridge, read against the preprocessor's actual output feature names
(not the pre-encoding names) since models now train on the
ColumnTransformer's transformed matrix, not a hand-built dummy matrix.
"""

from __future__ import annotations

import pandas as pd


def random_forest_importance(rf_model, feature_names: list[str]) -> pd.DataFrame:
    """
    Impurity-based feature importances. NOTE: this measure is biased
    toward high-cardinality / high-variance features (a documented
    scikit-learn limitation) — it indicates what the model relied on,
    not a causal or unbiased ranking of true agronomic importance.
    """
    importances = rf_model.feature_importances_
    df = pd.DataFrame({"feature": feature_names, "importance": importances})
    return df.sort_values("importance", ascending=False).reset_index(drop=True)


def ridge_coefficients(ridge_model, feature_names: list[str]) -> pd.DataFrame:
    df = pd.DataFrame({"feature": feature_names, "coefficient": ridge_model.coef_})
    return df.sort_values("coefficient", key=abs, ascending=False).reset_index(drop=True)
