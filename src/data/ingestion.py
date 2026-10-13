"""
Data ingestion for the SonarDesh AI analytics pipeline.

Schema status: DOCUMENTED / EXPECTED — this schema is written to match
field names and types *described* by AgriClimateBD / SPAS-Dataset-BD /
BBS source pages (see docs/data-provenance/provenance-register.md). No
real file from any of those sources has been opened or inspected in
this project — file access was BLOCKED from the sandbox this code was
originally written in (see provenance register for the specific tested
reasons). This schema becomes OBSERVED only once a real file is
actually loaded through this module with source_type="real", and
VERIFIED only once that real data's provenance has also been checked
against its source. Do not describe this schema as "verified" anywhere
in this repository's documentation until that has actually happened.

    district        str   - Bangladesh district name
    crop            str   - crop type
    season          str   - growing season (e.g. Boro, Aman, Aus)
    year            int   - harvest year
    area_ha         float - cultivated area, hectares
    production_t    float - total production, tonnes
    yield_t_per_ha  float - yield, tonnes per hectare (target variable)
    rainfall_mm     float - rainfall, millimetres (aggregation depends on the source;
                    UNVERIFIED for the real jute/wheat files)
    temp_c          float - mean seasonal temperature, Celsius
    humidity_pct    float - mean seasonal relative humidity, percent

This module does NOT fabricate data. It loads whatever CSV is handed to
it and tags every row with where it came from. If no real file is
available, use scripts/generate_synthetic_demo.py to create a clearly
labelled synthetic file for pipeline-testing purposes only — this
module will refuse to load a file that isn't explicitly flagged as
either real or synthetic (see `source_type` requirement below).
"""

from __future__ import annotations

import os
import pandas as pd

REQUIRED_COLUMNS = [
    "district", "crop", "season", "year",
    "area_ha", "production_t", "yield_t_per_ha",
    "rainfall_mm", "temp_c", "humidity_pct",
]


class DataSourceError(Exception):
    pass


def load_dataset(path: str, source_type: str, source_name: str) -> pd.DataFrame:
    """
    Load a CSV and tag it with explicit provenance.

    source_type: must be exactly "real" or "synthetic" — this is a
    deliberate guardrail. There is no default, because a silent default
    is exactly how synthetic data quietly becomes "real" data in a
    careless pipeline.
    source_name: a short identifier matching an entry in
    docs/data-provenance/provenance-register.md (e.g. "agriclimatebd",
    "synthetic_demo_v1").
    """
    if source_type not in ("real", "synthetic"):
        raise DataSourceError(
            f"source_type must be 'real' or 'synthetic', got {source_type!r}. "
            "This is intentionally not optional — see module docstring."
        )
    if not os.path.exists(path):
        raise DataSourceError(f"File not found: {path}")

    df = pd.read_csv(path)
    missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_cols:
        raise DataSourceError(
            f"Dataset at {path} is missing required columns: {sorted(missing_cols)}. "
            f"Expected schema: {REQUIRED_COLUMNS}"
        )

    df = df.copy()
    df.attrs["source_type"] = source_type
    df.attrs["source_name"] = source_name
    df.attrs["source_path"] = path
    return df


def assert_not_real_claim(df: pd.DataFrame) -> None:
    """
    Call this before computing or reporting any metric intended to be
    presented as empirical evidence. Raises if the dataframe is
    synthetic, so a synthetic-data metric can never accidentally be
    reported as real-world evidence by a later script that forgot to
    check.
    """
    if df.attrs.get("source_type") != "real":
        raise DataSourceError(
            "Refusing to treat this result as empirical evidence: "
            f"the underlying data is tagged source_type="
            f"{df.attrs.get('source_type')!r}, not 'real'. "
            "Label any output from this data as "
            "'DEMONSTRATION ONLY — NOT EMPIRICAL EVIDENCE'."
        )
