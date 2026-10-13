# Pitch Deck Outline (11 slides)

An outline, not rendered slides — for anyone who wants to present this project. Content pulled from this repository's actual docs/code; no new claims introduced here.

1. **Title** — SonarDesh AI: retrospective agricultural yield-estimation research for Bangladesh. Independent open-source prototype.
2. **The problem** — Agricultural/climate data exists across BBS, DAE/BAMIS, BARC, and research datasets, but not combined into field-usable decision support (`docs/01-problem-definition.md`).
3. **What this is, precisely** — Retrospective/seasonal yield estimation, not pre-season forecasting or crop recommendation. State this plainly, up front, not as a caveat buried later.
4. **Architecture** — Data → validation → leakage-safe preprocessing → 3-way split (fit/calibrate/test) → models → conformal interval → governance → decision support (`README.md` diagram).
5. **The evidence-honesty discipline** — Every result traced to DOCUMENTED/EXPECTED/OBSERVED/VERIFIED status; synthetic vs. real data structurally separated, never silently mixed.
6. **Two real bugs, found and fixed** — predicted-vs-observed value confusion; preprocessing leakage before the split. Shown with their regression tests. (A stronger credibility signal than claiming nothing ever went wrong.)
7. **Actual results** — MAE/RMSE/R² table + conformal empirical coverage, explicitly labelled synthetic/demonstration.
8. **Responsible AI by construction** — `recommended_action_type` hardcoded to `human_review`; no code path bypasses it.
9. **What's NOT done yet** — Real-data results exist for one dataset only (jute & wheat, provenance unresolved, unvalidated); no separate climate dataset integrated (the model uses the source's own rainfall field; no temperature/humidity). No field officer has used this. Bangla/offline/accessibility work is proposed, not built. State this as plainly as the results.
10. **What real-data validation requires** — fetch → inspect actual columns → build/confirm an adapter → re-run the identical pipeline → still requires domain review before any real-world claim.
11. **Contact / repository** — Link to the GitHub repository.
