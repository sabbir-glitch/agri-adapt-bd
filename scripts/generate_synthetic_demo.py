"""
Generates a SYNTHETIC demonstration dataset matching the real, documented
schema (see src/data/ingestion.py docstring) so the pipeline can be
proven to run correctly end-to-end without any real Bangladesh data.

THIS IS NOT REAL DATA. Every value is randomly generated. The yield
column has a deliberately simple synthetic relationship to rainfall and
temperature baked in (so the models have *something* non-trivial to
fit and the pipeline's mechanics can be verified against a known
pattern) — this is a software test fixture, not a simulation intended
to resemble real Bangladesh agriculture.
"""

from __future__ import annotations

import os
import numpy as np
import pandas as pd

OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "processed", "synthetic_demo",
    "synthetic_agroclimate_demo.csv"
)

# Real Bangladesh district names (names only — no other real data attached;
# using real place names keeps the schema realistic without claiming any
# real observation).
DISTRICTS = ["Dhaka", "Rajshahi", "Khulna", "Sylhet", "Barisal", "Rangpur",
             "Mymensingh", "Chattogram", "Comilla", "Jessore"]
CROPS = ["Rice", "Wheat", "Potato", "Jute", "Maize"]
SEASONS = ["Boro", "Aman", "Aus", "Rabi"]


def generate(n_rows: int = 600, random_seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(random_seed)

    district = rng.choice(DISTRICTS, n_rows)
    crop = rng.choice(CROPS, n_rows)
    season = rng.choice(SEASONS, n_rows)
    year = rng.integers(2015, 2024, n_rows)

    area_ha = rng.uniform(50, 5000, n_rows)
    rainfall_mm = rng.normal(1800, 400, n_rows).clip(200, 4000)
    temp_c = rng.normal(27, 2.5, n_rows).clip(15, 38)
    humidity_pct = rng.normal(78, 8, n_rows).clip(40, 100)

    # Deliberately simple synthetic signal: yield responds positively to
    # rainfall up to a point, negatively to extreme heat, plus noise.
    # This is a toy function for testing pipeline mechanics ONLY.
    base_yield = (
        2.0
        + 0.0009 * rainfall_mm
        - 0.04 * (temp_c - 27) ** 2
        + 0.01 * humidity_pct
        + rng.normal(0, 0.4, n_rows)
    ).clip(0.3, 8.0)

    production_t = base_yield * area_ha

    df = pd.DataFrame({
        "district": district,
        "crop": crop,
        "season": season,
        "year": year,
        "area_ha": area_ha.round(1),
        "production_t": production_t.round(1),
        "yield_t_per_ha": base_yield.round(3),
        "rainfall_mm": rainfall_mm.round(1),
        "temp_c": temp_c.round(2),
        "humidity_pct": humidity_pct.round(1),
    })
    return df


if __name__ == "__main__":
    df = generate()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(df)} SYNTHETIC rows to {OUTPUT_PATH}")
