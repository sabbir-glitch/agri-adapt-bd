# User Journeys

**REQUIRES FIELD VALIDATION in full** — none of these journeys have been tested with a real user. They describe intended design, built against the actual current prototype's capabilities (not aspirational features).

## 1. Field officer (primary intended user) — CURRENT PROTOTYPE capability

| Step | Detail |
|---|---|
| Goal | Get an interpretable yield estimate with honest uncertainty for a district/crop/season |
| Task | Open dashboard, select/upload data, click "Run analysis" |
| Input | A CSV matching the canonical schema (synthetic demo provided; real data requires an adapter) |
| Output | Observed vs. predicted yield for a held-out example, a 90%-target prediction interval, MAE/RMSE context, top factors, governance-check results |
| Constraint | Requires a machine that can run Streamlit — no offline mode currently |
| Accessibility need | English literacy currently required — Bangla not yet implemented |
| Failure mode | Fewer than 4 districts in the data → dashboard warns and stops rather than running an unreliable split |
| Human escalation | Every output says `recommended_action_type: human_review` — by design, this journey never ends in an automated decision |

## 2. Programme/policy user — CURRENT PROTOTYPE capability

| Step | Detail |
|---|---|
| Goal | Understand whether this analytical approach is worth investing further in |
| Task | Read `docs/06-policy-brief.md`, inspect `outputs/reports/experiment-registry.csv` |
| Output | An honest account of what's proven (pipeline mechanics) vs. not (real-world validity) |
| Failure mode | Misreading synthetic results as real findings — actively guarded against by the labelling throughout |

## 3. Technical/data administrator — CURRENT PROTOTYPE capability

| Step | Detail |
|---|---|
| Goal | Add a new real data source |
| Task | Fetch raw file (`scripts/fetch_real_data.py` or manually), inspect actual columns, write a `column_mapping`, use `src/data/adapters.py::adapt_generic_wide_csv()`, update the provenance register's status from DOCUMENTED to OBSERVED |
| Constraint | Must not guess column names — the adapter raises an error naming exactly which mapped columns weren't found |
| Failure mode | A real file whose structure doesn't fit the generic long-format adapter (e.g. NASA POWER's wide monthly format) needs a dedicated adapter — `adapt_nasa_power_monthly_csv()` is a documented placeholder, not a working one |

## 4. Smallholder farmer — PROPOSED EXTENSION, not current capability

**This project does not currently reach a farmer directly at all.** A real pathway would route through the field officer journey above, in the farmer's own language, likely via a channel other than a web dashboard (SMS, voice, or in-person). This is named explicitly as a gap, not glossed over — see `docs/05-capacity-building.md`.
