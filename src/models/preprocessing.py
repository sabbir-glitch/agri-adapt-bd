"""
Preprocessing, fit ONLY on training data. This module exists specifically
to fix a real leakage bug found in pre-release review: an earlier
version computed median-imputation values and categorical dummy columns
from the FULL dataset before splitting, meaning test-set rows could
influence training-time preprocessing statistics. Here, `fit_preprocessor`
is only ever called on a training subset; `transform` is then applied,
unchanged, to calibration and test subsets.

OneHotEncoder(handle_unknown="ignore") also means a district that
appears only in the test split (expected under the group-held-out
split in src/models/train.py, by design) produces an all-zero
indicator rather than crashing — the model simply can't use that
district's identity, which is the correct behavior for testing
generalization to an unseen district.
"""

from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.features.engineering import NUMERIC_FEATURES, CATEGORICAL_FEATURES


def build_preprocessor(numeric_features=None, categorical_features=None) -> ColumnTransformer:
    num = NUMERIC_FEATURES if numeric_features is None else list(numeric_features)
    cat = CATEGORICAL_FEATURES if categorical_features is None else list(categorical_features)
    numeric_pipeline = Pipeline(steps=[("impute_median", SimpleImputer(strategy="median"))])
    categorical_pipeline = Pipeline(steps=[
        ("impute_missing", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer(transformers=[
        ("numeric", numeric_pipeline, num),
        ("categorical", categorical_pipeline, cat),
    ])


def get_output_feature_names(preprocessor: ColumnTransformer) -> list[str]:
    """Human-readable names for the transformed matrix's columns, for explainability."""
    return list(preprocessor.get_feature_names_out())
