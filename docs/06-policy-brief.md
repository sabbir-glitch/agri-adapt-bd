# Policy Brief: A Governed Approach to Climate-Adaptive Agricultural Analytics for Bangladesh

**An independent open-source portfolio/research project. Not an official recommendation from any institution.**

---

## Executive summary

Bangladesh's agricultural and climate data already exists across several institutions — the Bangladesh Bureau of Statistics (crop statistics), DAE/BAMIS (agro-meteorological advisories), BARC (crop zoning and drought monitoring), and emerging research datasets combining these with climate variables. This project, SonarDesh AI, is a prototype demonstrating how such data *could* be combined into interpretable, decision support with a real, calibrated prediction interval (not just aggregate error metrics) for agricultural field officers — built with a deliberate emphasis on not overstating what has actually been validated.

**What this prototype demonstrates:** a working, tested data pipeline (ingestion → validation → cleaning → feature engineering → modelling → explainability → governance checks) that runs correctly end to end on a clearly labelled synthetic dataset, plus the infrastructure to run the same pipeline on real data once it is accessible to the developer.

**What this prototype does not demonstrate:** any empirical finding about real Bangladesh agriculture, any validated predictive accuracy on real data, or any field-tested user experience. These distinctions are maintained deliberately throughout this project's code and documentation — see `docs/data-provenance/provenance-register.md`.

## The development problem

Agricultural and climate information relevant to Bangladeshi smallholder farmers is distributed across institutionally separate systems, not absent (see `docs/01-problem-definition.md` for the full evidence basis). A field officer today likely synthesizes this manually, if at all. The opportunity is not to create new data, but to responsibly combine what already exists into a usable, honestly-uncertain decision-support format.

## Proposed intervention (design, not deployment)

A pipeline that: ingests district/crop/season-level agricultural and climate data → validates and cleans it → produces an interpretable yield-estimate with a real split-conformal prediction interval (distinct from the model's aggregate MAE/RMSE) → routes every output through a mandatory human-review flag before it could ever reach a farmer-facing recommendation.

## How it works (as actually built)

1. **Data layer** — strict separation between synthetic demonstration data and real data (see `data/README.md`); no path exists in the code for the two to be silently confused.
2. **Modelling layer** — a deliberately "boring" progression: naive baseline → Ridge regression → Random Forest, evaluated with a district-held-out split (not a random split) to avoid letting the same district leak between training and test.
3. **Governance layer** — automated checks (not just documentation) verifying no personal data is present, a real conformal prediction interval is always reported (not just an aggregate error metric), and synthetic results are always labelled as such.
4. **Product layer** — a decision-support output contract that cannot omit a human-review flag, a real prediction interval, or a limitations list, by construction.

## Governance safeguards

See `docs/04-governance-framework.md` in full. The single most load-bearing safeguard: `src/product/schemas.py` hardcodes every output's `recommended_action_type` to `"human_review"` — there is no code path that produces a bare, unqualified instruction.

## Inclusion considerations

This prototype's dashboard is currently English-only and requires live internet access — both stated as real, unresolved gaps (`docs/05-capacity-building.md`), not glossed over. A real deployment serving Bangladesh field officers would need Bangla-language support and a low-connectivity-friendly delivery mode before it could be considered genuinely inclusive.

## Implementation model (hypothetical — no implementation has occurred)

A real pilot would require: an institutional data-sharing agreement with BBS and/or DAE (none exists); a named domain/agronomic reviewer (role currently unfilled); and field testing with actual officers before any accuracy claim could be made about real-world performance.

## Monitoring indicators (proposed, not collected)

Data-quality metrics, model-performance metrics (MAE/RMSE on real held-out data — one exploratory run exists, see `docs/03-analytics-pipeline.md` §10; unvalidated), and equity-disaggregated performance by district — see `docs/04-governance-framework.md`'s Monitoring section for what's proposed versus implemented.

## Risks

The primary risk this project is designed to avoid: presenting a synthetic-data sanity check as real-world evidence. This is addressed structurally (code-enforced labelling), not just through a disclaimer that could be ignored. The secondary risk — that even real data, once accessible, would need agronomic and field validation before any claim is trustworthy — is stated throughout rather than assumed away.

## Next steps (for this project, not a commitment by any institution)

1. Run `scripts/fetch_real_data.py` from an internet-connected machine to actually test real-data ingestion.
2. Reconcile the provenance register's DOCUMENTED-level schema claims against an OBSERVED real file for the sources not yet observed (only the jute/wheat files have been opened).
3. Any further claim beyond "the pipeline runs correctly" requires the domain-review step this project has explicitly not performed.
