"""
Source adapters: map a source-specific file onto the canonical schema
(src/data/ingestion.py's REQUIRED_COLUMNS). Three adapters, with
different statuses:

1. adapt_sajidahmed12_crop_csv — OBSERVED and EXECUTED. Written against
   the actual jute.csv / wheat.csv files (github.com/sajidahmed12/
   Agricultural-Crop-Yield-Prediction, whose repository contains an MIT LICENSE), which were opened, and it is
   run by scripts/run_real_pipeline.py and covered by tests. Its unit
   assumptions (acres -> ha; "Tons" as metric tonnes) and the meaning of
   the "Rainfall in MM" column remain unverified, and the exact lineage
   of the values from the upstream's cited references is unresolved.
2. adapt_generic_wide_csv — a generic renamer. It requires the caller to
   supply a column_mapping written after inspecting the real file; it has
   been exercised only in tests on small synthetic frames, not on any
   other real source.
3. adapt_nasa_power_monthly_csv — a documented PLACEHOLDER that raises
   NotImplementedError. No NASA POWER file has been integrated.

Other candidate sources (Kaggle, Mendeley, data.gov.bd) were not
retrievable from the development sandbox; no adapter exists for them
beyond the generic one. See docs/data-provenance/provenance-register.md.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from src.data.ingestion import REQUIRED_COLUMNS


class AdapterStatus:
    REQUIRES_LOCAL_VALIDATION = "REQUIRES_LOCAL_VALIDATION"
    OBSERVED = "OBSERVED"  # set only after a maintainer confirms the mapping against a real file


def validate_canonical_output(df: pd.DataFrame, adapter_name: str) -> dict:
    """Checks an adapter's output against the canonical schema — does NOT
    check correctness of values, only that the expected columns exist."""
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    return {
        "adapter": adapter_name,
        "canonical_columns_present": sorted(set(REQUIRED_COLUMNS) & set(df.columns)),
        "canonical_columns_missing": sorted(missing),
        "fully_canonical": len(missing) == 0,
    }


def adapt_nasa_power_monthly_csv(path: str) -> tuple[pd.DataFrame, dict]:
    """
    Status: REQUIRES LOCAL VALIDATION — never run against a real downloaded
    file in this project.

    NASA POWER's documented monthly point-API CSV format (per NASA's own
    API documentation, confirmed directly in this session) returns a
    header block followed by rows keyed by YEAR, with one column per
    requested parameter per month (e.g. columns named JAN, FEB, ... for
    each parameter block). This does NOT match the canonical schema's
    long format (one row per district/crop/season/year).

    IMPORTANT, STATED EXPLICITLY: NASA POWER provides climate variables
    ONLY (temperature, precipitation, humidity). It has no concept of
    district, crop, area, or production — those are agricultural fields
    this adapter cannot populate. Using NASA POWER data in the canonical
    pipeline REQUIRES joining it with a real agricultural-outcome source
    (e.g. BBS statistics or AgriClimateBD) on a shared key (district +
    year, or similar) — a join this project has not performed, because
    no agricultural-outcome file has been accessible either.

    This function is therefore a documented placeholder, not a working
    adapter: it defines the intended reshaping logic but raises
    NotImplementedError rather than guessing at a join it cannot verify.
    """
    raise NotImplementedError(
        "NASA POWER provides climate variables only, not agricultural "
        "outcomes (district/crop/area/production/yield). This adapter "
        "cannot alone populate the canonical schema — it would need a "
        "verified join with a real agricultural-outcome source, which "
        "has not been performed in this project. See this function's "
        "docstring. Fetch the raw file with "
        "scripts/fetch_real_data.py --source nasa_power, inspect it "
        "yourself, and extend this function once you've confirmed the "
        "actual column layout and an appropriate agricultural dataset "
        "to join it against."
    )


def adapt_generic_wide_csv(path: str, column_mapping: dict) -> tuple[pd.DataFrame, dict]:
    """
    Status: REQUIRES LOCAL VALIDATION for any specific mapping passed in.

    Generic helper for a source whose file already has one row per
    district/crop/season/year (a "long" format like the canonical
    schema) but different column names — e.g. AgriClimateBD or
    SPAS-Dataset-BD, per their DOCUMENTED (not OBSERVED) field
    descriptions in docs/data-provenance/provenance-register.md.

    column_mapping: {source_column_name: canonical_column_name}
    This function does NOT guess the mapping — the caller must supply
    it after actually inspecting the real downloaded file's columns.
    Passing a guessed mapping here would reintroduce exactly the
    "invented schema" risk this module exists to avoid.
    """
    df = pd.read_csv(path)
    missing_source_cols = set(column_mapping.keys()) - set(df.columns)
    if missing_source_cols:
        raise ValueError(
            f"column_mapping references source columns not found in {path}: "
            f"{missing_source_cols}. The actual file's columns are: {list(df.columns)}. "
            "This confirms the mapping was guessed rather than observed — "
            "inspect the file and correct column_mapping before proceeding."
        )
    df = df.rename(columns=column_mapping)
    report = validate_canonical_output(df, adapter_name="generic_wide_csv")
    df.attrs["source_type"] = "real"
    df.attrs["adapter_status"] = AdapterStatus.REQUIRES_LOCAL_VALIDATION
    return df, report


SAJID_EXPECTED_COLUMNS = ["Crop Name", "Area Name", "Area of Land in acres",
                          "Amount of Production in Tons", "Rainfall in MM", "Year"]
ACRE_TO_HA = 0.404686


def adapt_sajidahmed12_crop_csv(paths: dict) -> tuple[pd.DataFrame, dict]:
    """
    Status: OBSERVED — mapping written against the actual files
    (jute.csv, wheat.csv from github.com/sajidahmed12/Agricultural-Crop-Yield-Prediction,
    whose repository carries an MIT LICENSE; dataset-specific rights unresolved) opened in this project. Provenance of the underlying figures:
    REQUIRES PROVENANCE REVIEW.

    paths: {"jute": "<path>", "wheat": "<path>"} (any non-empty subset).

    Documented assumptions (not verified against a primary source):
      * "Amount of Production in Tons" is treated as metric tonnes.
      * Area is in acres (column name) -> hectares x 0.404686.
      * The files contain aggregate rows (names containing "Region",
        "Division", or "H.T.") mixed with district rows; these are dropped
        because they would double-count districts.
      * Rows with zero area are dropped (yield undefined); zero-area rows
        with non-zero production are counted separately as inconsistent.
      * No temperature or humidity exists in these files -> NaN (not invented).
      * No season exists -> "annual_aggregate".
    """
    frames = []
    for crop_key, path in paths.items():
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        raw = pd.read_csv(path)
        missing = [c for c in SAJID_EXPECTED_COLUMNS if c not in raw.columns]
        if missing:
            raise ValueError(f"{path}: expected observed columns missing: {missing}; "
                             f"actual columns: {list(raw.columns)}")
        frames.append(raw[SAJID_EXPECTED_COLUMNS].copy())
    raw = pd.concat(frames, ignore_index=True)
    report = {"adapter": "sajidahmed12_crop_csv", "status": AdapterStatus.OBSERVED,
              "raw_rows": int(len(raw))}

    raw["Area Name"] = raw["Area Name"].astype(str).str.strip()
    aggregate_pattern = r"Region|Division|H\.?T\.?"
    is_agg = raw["Area Name"].str.contains(aggregate_pattern, case=False, regex=True, na=False)
    is_blank = raw["Area Name"].isin(["", "nan", "None"])
    report["region_aggregate_rows_dropped"] = int(is_agg.sum())
    report["blank_name_rows_dropped"] = int((is_blank & ~is_agg).sum())
    df = raw[~is_agg & ~is_blank].copy()

    area_ac = pd.to_numeric(df["Area of Land in acres"], errors="coerce")
    prod = pd.to_numeric(df["Amount of Production in Tons"], errors="coerce")
    zero_area = area_ac == 0
    zz = zero_area & (prod == 0)
    inconsistent = zero_area & (prod != 0)
    report["zero_area_zero_production_rows_dropped"] = int(zz.sum())
    report["zero_area_inconsistent_rows_dropped"] = int(inconsistent.sum())
    df = df[~zero_area].copy()
    area_ac, prod = area_ac[df.index], prod[df.index]

    out = pd.DataFrame({
        "district": df["Area Name"].values,
        "crop": df["Crop Name"].astype(str).str.strip().values,
        "season": "annual_aggregate",
        "year": pd.to_numeric(df["Year"], errors="coerce").values,
        "area_ha": (area_ac * ACRE_TO_HA).values,
        "production_t": prod.values,
        "rainfall_mm": pd.to_numeric(df["Rainfall in MM"], errors="coerce").values,
        "temp_c": np.nan,
        "humidity_pct": np.nan,
    })
    out["yield_t_per_ha"] = out["production_t"] / out["area_ha"]
    out = out[["district", "crop", "season", "year", "area_ha", "production_t",
               "yield_t_per_ha", "rainfall_mm", "temp_c", "humidity_pct"]].reset_index(drop=True)
    report["rows_after_adapter"] = int(len(out))
    report["distinct_district_names"] = int(out["district"].str.title().nunique())
    report["climate_variables_available"] = False
    report.update(validate_canonical_output(out, "sajidahmed12_crop_csv"))
    out.attrs["source_type"] = "real"
    out.attrs["source_name"] = "sajidahmed12_crop_data"
    out.attrs["adapter_status"] = AdapterStatus.OBSERVED
    return out, report
