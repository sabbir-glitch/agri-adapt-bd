# Data folder — two modes, never mixed

This project runs in exactly one of two modes, and the two are never mixed in the same folder or the same output.

## 🟡 DEMONSTRATION MODE (synthetic)

- **Location:** `data/processed/synthetic_demo/`
- **What it is:** Randomly generated data matching the DOCUMENTED/EXPECTED schema of real Bangladesh agricultural+climate datasets (see `docs/data-provenance/provenance-register.md`), with real Bangladesh district names but entirely synthetic values.
- **Purpose:** Prove the pipeline (`src/`) runs correctly end to end, with no network access required.
- **Status of any result from this mode:** labelled `DEMONSTRATION ONLY — NOT EMPIRICAL EVIDENCE` everywhere, enforced in code by `src/governance/checks.py::check_synthetic_label_present`.
- **Generate it:** `python scripts/generate_synthetic_demo.py`
- **Run the pipeline on it:** `python scripts/run_pipeline.py --source synthetic`

## 🟢 REAL-DATA MODE

- **Location:** `data/raw/sajidahmed12_crop_data/` (fetched, not bundled) — kept structurally separate from `synthetic_demo/`.
- **What it is:** `jute.csv` and `wheat.csv` from github.com/sajidahmed12/Agricultural-Crop-Yield-Prediction (the upstream repository carries an MIT LICENSE, © 2021 Sajid Ahmed; dataset-specific rights are unresolved — see `ATTRIBUTION.md`). Files were opened and inspected (status OBSERVED). **Primary statistical provenance is unresolved**; units are assumed.
- **Status of results:** real, **unvalidated** exploratory results — not field-validated, not official statistics.
- **Fetch (checksum-verified; fails explicitly on error):** `python scripts/fetch_real_data.py --source sajidahmed12`
- **Run:** `python scripts/run_real_pipeline.py`
- Other candidate sources in the provenance register (Kaggle, Mendeley, NASA POWER, data.gov.bd) were not retrieved in this release; `fetch_real_data.py` has helpers for them, unverified.
