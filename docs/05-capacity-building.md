# 05. Capacity Building

**Status: entirely PROPOSED DESIGN.** No training has been delivered, no field officer has used this system, and no SOP below has been tested with a real user. This document exists to show what a real implementation plan would need to address — not that any of it has happened.

## Intended field workflow (proposed, untested)

```
1. Field officer identifies a district/crop/season of interest
2. Officer checks data-quality status shown by the tool (real vs. synthetic, data recency)
3. Officer reviews model output: predicted yield, its real conformal prediction interval, aggregate evaluation error context, and top contributing factors
4. Officer applies local knowledge the model doesn't have (soil condition, local pest pressure, etc.)
5. Officer makes the actual recommendation to farmers — the tool never does this directly
6. Officer records what happened (outcome feedback) — not implemented in this prototype, flagged as needed for any real pilot
```

## Training objectives (proposed)

A field officer using this tool would need to understand, at minimum:
- The difference between DEMONSTRATION MODE and REAL-DATA MODE (see `data/README.md`) and what each implies about how much to trust an output
- How to read a prediction interval in plain terms — and the difference between that (a per-prediction range) and the model's aggregate MAE/RMSE (an average error across many evaluation predictions, not specific to any one field) — without a statistics lecture
- That "human_review" on every output is not a formality — it's the point

## Low-connectivity and low-digital-literacy considerations (design principles, not implemented features)

- **ASSUMPTION, stated explicitly:** any real deployment should not assume continuous internet access at the point of use — a field officer may need an offline-capable or SMS-based summary rather than a live dashboard. This prototype's dashboard (`dashboard/app.py`) requires a live Streamlit session and does **not** currently have an offline or SMS mode — this is a real, stated gap, not a hidden one.
- Bangla-language interface: **not implemented** in this prototype's dashboard (currently English-only). Flagged as a requirement for any real deployment serving Bangladesh field officers, given the companion `rai-govtoolkit-bd` project's existing Bangla-first design work.

## Troubleshooting guidance (proposed, for a future real pilot)

| Symptom | Likely cause | What this project's code would actually tell you |
|---|---|---|
| Dashboard shows "DEMONSTRATION MODE" unexpectedly | Real data wasn't fetched/loaded, or `--source synthetic` was used | Check `data/README.md` mode-switching instructions |
| Pipeline fails with `DataSourceError` | Missing required schema columns, or `source_type` not specified | Error message names the exact missing column(s) — see `src/data/ingestion.py` |
| Governance check fails on `synthetic_label_present` | A result from synthetic data is being reported without the required label | This is enforced deliberately — fix the output label, not the check |

## Escalation (proposed)

In a real pilot: unresolved data-quality issues or model concerns would route to a named data steward (role currently unfilled — see `docs/04-governance-framework.md`). Not applicable to this prototype as it stands.

## Feedback workflow (proposed, not implemented)

A real pilot would need a mechanism for field officers to report whether a prediction matched reality, feeding back into `outputs/reports/experiment-registry.csv` as an actual-outcome column. This project's current registry only records model evaluation metrics against held-out training data — it does not yet have any field-outcome feedback loop, because there is no field deployment.
