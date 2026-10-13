# SonarDesh AI (`agri-adapt-bd`)
### Historical Agricultural Yield Analytics for Bangladesh — a governed, evidence-honest prototype

> **Independent open-source portfolio/research project.** Not affiliated with, reviewed by, or submitted on behalf of any government body or organization. No institutional endorsement of any kind is claimed or implied.

## What this is

A working data-analytics and decision-support pipeline — ingestion, validation, cleaning, feature engineering, modelling, explainability, and automated governance checks — built around a Bangladesh agricultural/climate use case, with one organizing principle above all others: **never present a stronger evidentiary claim than what was actually verified.**

That principle is enforced in code, not just stated in prose. See `src/data/ingestion.py`'s mandatory `source_type` flag and `src/governance/checks.py`'s automated label checks.

## The problem

Bangladesh's agricultural and climate data already exists — spread across the Bangladesh Bureau of Statistics (crop statistics), DAE/BAMIS (agro-meteorological advisories), BARC (crop zoning, drought monitoring), and research datasets combining these with satellite climate data — but not combined into a single, interpretable, field-usable analytical resource. See `docs/01-problem-definition.md` for the full evidence basis, with every claim labelled FACT / EVIDENCE / ASSUMPTION / HYPOTHESIS / PROPOSED DESIGN.

## Two kinds of results — kept separate

**A. SYNTHETIC DEMONSTRATION** — randomly generated data that proves the pipeline mechanics work. Labelled `DEMONSTRATION ONLY — NOT EMPIRICAL EVIDENCE` everywhere, enforced by an automated governance check.

**B. REAL-DATA EXPLORATORY** — one real dataset (jute & wheat records, 1970–2014) was downloaded from a public GitHub repository, its actual files inspected, and modelled. The upstream repository contains an MIT LICENSE, but dataset-specific rights and exact provenance are not independently established. **Its exact provenance is unresolved:** the upstream repository's README lists two references — a Bangladesh Bureau of Statistics "45 years Major Crops" report and the data.gov.bd daily rainfall dataset — but the exact lineage from those references to each CSV value and transformation is unresolved. Units are assumed, and nothing has been field-validated. These results are exploratory, labelled `real_unvalidated`, and must **not** be described as official or verified Bangladesh government statistics.

Real mode never silently falls back to synthetic data.

## Architecture

```
Data source (synthetic OR real, never mixed)
        │
        ▼
Ingestion (mandatory source_type tag) ──► Validation (schema, missingness, range checks)
        │
        ▼
Cleaning (dedupe, range-filter, drop missing required fields)
        │
        ▼
Feature engineering (interpretable derived features only)
        │
        ▼
Preprocessing (imputation + encoding, fit ONLY on the fit-split — leakage fix)
        │
        ▼
Modelling: naive baseline → Ridge regression → Random Forest
        │   (synthetic: 3-way group split by district; real: 3-way chronological
        │    split by year — fit / calibrate / test, never overlapping)
        ▼
Split-conformal prediction interval (calibrated on the calibrate split,
        │   empirical coverage measured on test — separate from MAE/RMSE)
        ▼
Explainability (feature importance, with bias caveats stated)
        │
        ▼
Governance checks (no personal data / error-metrics present / real conformal prediction interval present / synthetic label enforced / source-type plausibility)
        │
        ▼
Decision-support output (always: aggregate error context + a real conformal prediction interval + limitations + human_review flag)
        │
        ▼
Dashboard (always shows data mode, prominently)
```

## Results (from the most recent runs; reproduced by the commands under "Running it")

### A. SYNTHETIC DEMONSTRATION — DEMONSTRATION ONLY, NOT EMPIRICAL EVIDENCE
**Canonical synthetic result = the table below**, reproduced across repeated runs in the release environment (Python 3.13, numpy 2.5.3, pandas 3.0.5, scikit-learn 1.9.1; versions are also written to each run log). Different library versions can change Random Forest results slightly; an earlier draft of the docs quoted Random Forest MAE 0.3926 / RMSE 0.5120 / R² 0.4768, which these runs do not reproduce.
District-held-out split (fit 293 / calibrate 131 / test 176), seed 42, 90% split-conformal target.

| Model | MAE | RMSE | R² | Conformal halfwidth | Empirical coverage |
|---|---|---|---|---|---|
| Naive mean | 0.5409 | 0.7114 | −0.0100 | 1.063 | 0.892 |
| Ridge | 0.4410 | 0.5843 | 0.3185 | 0.980 | 0.926 |
| Random Forest | 0.3928 | 0.5123 | 0.4761 | 0.842 | 0.898 |

### B. REAL-DATA EXPLORATORY (jute & wheat) — real, unvalidated; provenance unresolved
2,421 raw rows → 373 aggregate rows (Region/Division/H.T.), 148 zero-area rows and 2 yield>50 t/ha rows removed → **1,898 modelled rows**. Chronological split: fit 1970–1996 (n=868), calibrate 1997–2005 (n=430), test 2006–2014 (n=600). Features: area, rainfall, rainfall-per-area, district, crop. **No temperature or humidity are used (not present in these files).**

| Model | MAE (t/ha) | RMSE (t/ha) | R² | Conformal halfwidth | Empirical coverage (target 0.90) |
|---|---|---|---|---|---|
| Naive mean (pooled, both crops) | 2.4328 | 3.1432 | −0.0285 | 6.801 | 0.928 |
| Ridge | 1.5818 | 3.2343 | −0.0890 | 7.211 | 0.900 |
| Random Forest | 1.2335 | 1.7565 | 0.6788 | 3.268 | 0.923 |

How to read this (the comparison is **exploratory**, not a conclusive ranking):
- Random Forest has the lowest test error, but there was no pre-registered model choice: all three models were evaluated on the same test years, and the model shown in examples/importances is chosen by lowest test MAE (post-hoc selection on the test set). Results come from one split and one seed.
- The naive baseline is a single pooled mean across jute and wheat, which may understate what a crop-specific baseline would achieve; a per-crop baseline was **not** evaluated. Crop indicators dominate the Random Forest importances, so much of its edge is plausibly crop identity, not rainfall. Importances are associations, not causes.
- Ridge's RMSE is worse than the naive baseline (not diagnosed). Prediction intervals are wide.
- Reported coverage is **empirical coverage on the held-out temporal test set (2006–2014)**. It is not a guarantee of future coverage: under temporal distribution shift, conformal coverage guarantees do not carry over. Full details: `docs/03-analytics-pipeline.md` §10, `outputs/reports/real_run_log.md`, `outputs/reports/real-data-quality-report.md`.

## Verification status (what was actually run)

- **Tests:** `pytest tests/` — 66 tests, all passing at release (see `CHANGELOG.md`). Includes regression tests for: predicted≠observed; leakage-safe preprocessing; unseen categories; disjoint splits; conformal structure; governance checks; adapter behaviour (aggregate-row exclusion, zero-area handling, unit conversion, no invented climate); cleaning of all-NaN optional columns; chronological split; real mode refusing to fall back to synthetic; download checksum verification; split-conformal order-statistic correctness and input validation.
- **Both pipelines executed:** `scripts/run_pipeline.py --source synthetic` and `scripts/run_real_pipeline.py`.
- **Dashboard (programmatic only):** Streamlit's `AppTest` ran the app without exceptions; synthetic mode's *Run analysis* output matched the pipeline's synthetic numbers; real mode with no upload shows an error and does not fall back to synthetic. **No browser/UI testing was performed.**
- **CI:** `.github/workflows/tests.yml` (default; no external data: install, generate synthetic data, test, synthetic pipeline) and `.github/workflows/real-data-manual.yml` (manual only: checksum-verified download + real pipeline) are valid YAML but have **not yet run on GitHub**.

## Dashboard limitations
- Synthetic mode shows synthetic results only. Real mode is **upload-only**: it expects a CSV already in the canonical schema and uses the generic district-group split. It is **not connected** to the jute/wheat experiment — those real results live in `outputs/reports/`, not in the dashboard.
- Real-mode upload with an actual file was not exercised.

## Climate data status
**No separate climate dataset has been integrated.** The real-data model does use the agricultural source's own reported `Rainfall in MM` field (as `rainfall_mm`) and the derived `rainfall_per_area`. What that field aggregates (a monthly, seasonal or annual figure; a mean or a total; which station or district) is **unverified** — no annual or seasonal rainfall total is claimed. Temperature and humidity are not present in the observed agricultural files and are not used by the real-data model. The synthetic demonstration includes synthetic temperature/humidity only. NASA POWER and other climate sources were not integrated; no district/year climate join was performed or validated. `adapt_nasa_power_monthly_csv` is a documented placeholder that raises `NotImplementedError`.

## Repository structure

| Path | Contents |
|---|---|
| `docs/01-problem-definition.md` → `06-policy-brief.md` | Problem, stakeholders, pipeline design, governance, capacity building, policy brief — every claim evidence-labelled |
| `docs/data-card.md`, `docs/model-card.md` | Concise data card and model card for the real-data (jute & wheat) run |
| `docs/data-provenance/provenance-register.md` | Every dataset considered, with DOCUMENTED/EXPECTED/OBSERVED/VERIFIED status and exact access-attempt results |
| `docs/research/source-audit.md` | Self-audit of this repository's own documentation for overclaiming |
| `src/` | The actual pipeline: `data/`, `features/`, `models/`, `governance/`, `product/` |
| `scripts/generate_synthetic_demo.py` | Generates the labelled synthetic dataset |
| `scripts/run_pipeline.py` | Runs the full pipeline, writes real output logs |
| `scripts/fetch_real_data.py` | Retrieval helper; `--source sajidahmed12` downloads the jute/wheat files with SHA-256 verification and fails explicitly on any error |
| `scripts/run_real_pipeline.py` | Real-data (jute & wheat) pipeline: adapter → clean → temporal split → models → conformal → reports → registry |
| `CHANGELOG.md` | Release history |
| `dashboard/app.py` | Streamlit dashboard with an explicit, prominent data-mode indicator |
| `tests/` | 66 automated tests, covering ingestion guardrails, validation, cleaning, leakage-safety, 3-way splitting, conformal intervals, model-generated predictions, governance checks, and source adapters |
| `.github/workflows/tests.yml` | CI — runs tests and the synthetic pipeline on every push |
| `docs/product/` | Product requirements, user journeys, service blueprint, accessibility, pitch-deck outline — each labelled CURRENT PROTOTYPE / PROPOSED EXTENSION / REQUIRES FIELD VALIDATION |
| `src/data/adapters.py` | Real-data source adapter interface — honestly scoped: an adapter built against the observed jute/wheat files (tested), a generic long-format mapper, and a documented NASA POWER placeholder that raises rather than guesses |

## Running it

```bash
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

python scripts/generate_synthetic_demo.py
pytest tests/ -v
python scripts/run_pipeline.py --source synthetic
streamlit run dashboard/app.py
```

For the real-data (jute & wheat) run — the raw files are **not bundled** in this repository (the upstream data's primary provenance is unresolved); the script downloads them and verifies checksums:

```bash
python scripts/fetch_real_data.py --source sajidahmed12
python scripts/run_real_pipeline.py
```

Outputs go to `outputs/reports/` (`real_run_log.md`, `real-data-quality-report.md`, `experiment-registry.csv`). The upstream repository carries an MIT LICENSE (© 2021 Sajid Ahmed); the dataset-specific redistribution rights of the underlying observations are unresolved, so the data is not asserted to be MIT-licensed (`data/raw/sajidahmed12_crop_data/ATTRIBUTION.md`).

## Technology stack

Python, pandas, scikit-learn, Streamlit, pytest, GitHub Actions. Chosen for being widely understood and runnable by one developer locally — no cloud infrastructure, no unnecessary dependencies.

## Limitations (stated plainly, not buried)

- English-only dashboard; no Bangla-language support yet (a real gap, given the intended field-officer audience).
- No offline or low-bandwidth delivery mode.
- Impurity-based feature importance is known to be biased toward high-cardinality features — stated in `src/models/explain.py`, not hidden.
- GitHub Actions workflows are written and valid YAML but have not been triggered on GitHub yet.
- Real data: provenance unresolved; units assumed (acres→ha, "Tons" as metric tonnes); 68 district-name strings, spelling variants not harmonised; two historical yield outliers (655.8 and 73.96 t/ha, 1988 jute) removed by the >50 t/ha rule; no field validation.
- Not implemented: separate climate-data integration, per-crop models, Bangla/offline delivery.

## Relationship to `rai-govtoolkit-bd`

Same author, same evidence-honesty discipline, different domain: [`rai-govtoolkit-bd`](https://github.com/sabbir-glitch/rai-govtoolkit-bd) applies problem definition → stakeholder mapping → data governance → AI risk → policy brief to an AI-assisted citizen-service chatbot. This project applies the same discipline to a climate-adaptation analytics pipeline, adding real modelling and a decision-support product layer.

## Author

**Sabbir Ahammed** — [github.com/sabbir-glitch](https://github.com/sabbir-glitch)

## Disclaimer

This is an independent open-source prototype. It is not an official system of any government or organization, not a validated agronomic advisory tool, and not a substitute for qualified agricultural professionals. Any real-world use would require institutional data-sharing agreements, domain/agronomic validation, legal and privacy review, and field testing — none of which has occurred.
