# Product Requirements

Status labels used throughout: **CURRENT PROTOTYPE** (exists and runs), **PROPOSED EXTENSION** (designed, not built), **REQUIRES FIELD VALIDATION** (needs real-world testing before it could be trusted).

## What the product is (CURRENT PROTOTYPE)

A Streamlit dashboard + CLI pipelines (`dashboard/app.py`, `scripts/run_pipeline.py`, `scripts/run_real_pipeline.py`). Synthetic mode evaluates the full demo schema; the real jute/wheat experiment runs through the CLI. Dashboard real mode is upload-only and expects a canonical-schema CSV; it is not connected to the saved jute/wheat experiment outputs. Outputs include: a held-out model prediction with observed value and residual shown, a real split-conformal prediction interval, aggregate MAE/RMSE error context, feature importance, and automated governance checks — always with a mandatory human-review flag.

## What it explicitly does not do (CURRENT PROTOTYPE boundary)

- Does not forecast ahead of a season (inputs are same-period observations — for the real run, a source-reported rainfall field whose aggregation is unverified — not pre-season forecasts — see `docs/03-analytics-pipeline.md`'s framing note).
- Does not make a farmer-facing recommendation directly (`recommended_action_type` is hardcoded to `"human_review"`).
- Does not collect or require any personal/farmer-level data.
- Does not claim any real-world validated accuracy. The repository contains a separate real-data exploratory run; its results remain unvalidated because source lineage and units are unresolved.

## Functional requirements (CURRENT PROTOTYPE)

| Requirement | Status |
|---|---|
| Load data with explicit real/synthetic declaration | Implemented — `src/data/ingestion.py` |
| Validate schema, missingness, implausible ranges | Implemented — `src/data/validation.py` |
| Leakage-safe preprocessing (fit on fit-split only) | Implemented — `src/models/preprocessing.py` |
| 3-way split (fit/calibrate/test) | Implemented — district-held-out for synthetic mode; chronological by year for the real-data pipeline |
| Real split-conformal prediction interval | Implemented — `src/models/train.py` |
| Governance checks (privacy, coverage, interval presence, synthetic labelling) | Implemented — `src/governance/checks.py` |
| Decision-support output contract | Implemented — `src/product/schemas.py` |
| Dashboard with explicit data-mode banner | Implemented — `dashboard/app.py` |
| Real-data source adapters | **PARTIALLY IMPLEMENTED** — the jute/wheat adapter is observed and executed; the generic mapper is tested on synthetic fixtures only; NASA POWER remains a placeholder |

## Non-functional requirements

| Requirement | Status |
|---|---|
| Reproducibility (fixed random seed) | Implemented |
| Runs on one developer's machine, no cloud infra | Implemented |
| Bangla-language interface | **PROPOSED EXTENSION** — not built |
| Offline/low-bandwidth delivery | **PROPOSED EXTENSION** — not built |
| Accessibility for low-literacy users | **PROPOSED EXTENSION**, see `accessibility.md` |

## Out of scope for this version

Deep learning, mobile app, SMS gateway, multi-user accounts, real-time data ingestion, cloud deployment — none of these are needed to demonstrate the core evidence-honesty and governance discipline this project is built around, and adding them would be scope inflation, not depth.
