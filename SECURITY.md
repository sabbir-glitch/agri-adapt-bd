# Security

## No personal data

This prototype does not require, collect, or process personal farmer data. `src/governance/checks.py::check_no_personal_data()` runs on every pipeline execution and fails loudly if a forbidden personal-data field (name, phone, NID, address, etc.) is ever introduced.

## No committed secrets

No API keys, tokens, or credentials are committed to this repository. `scripts/fetch_real_data.py` expects the user to configure their own Kaggle credentials locally (`kaggle.json`, per Kaggle's own documentation) — this file is explicitly gitignored.

## Dependency hygiene

Dependencies are pinned to minimum versions in `requirements.txt`. No dependency was added without a concrete use in this codebase — there is no unused library pulled in "for appearance."

## Input validation

`src/data/ingestion.py` and `src/data/validation.py` reject malformed input (missing columns, wrong `source_type`) with explicit errors rather than attempting to silently proceed with bad data.

## Reporting a concern

This is an independent portfolio project without a formal disclosure programme. Open a GitHub issue on this repository for any concern.
