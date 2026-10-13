# Accessibility

**Honest status: largely PROPOSED EXTENSION.** The current prototype is a Streamlit dashboard in English, built for a technical reviewer to inspect — not yet built for a Bangladesh field officer to use day-to-day. Listed here so the gap is explicit, not discovered later.

| Consideration | Status |
|---|---|
| Bangla-language interface | **PROPOSED EXTENSION** — not implemented. All current labels, errors, and governance messages are English-only. |
| Low literacy / simplified terminology | **PROPOSED EXTENSION** — current output includes technical terms (MAE, RMSE, conformal interval) aimed at a reviewer, not simplified for a field audience. `docs/05-capacity-building.md` proposes training to bridge this, which is a workaround, not a fix to the interface itself. |
| Low bandwidth / offline use | **PROPOSED EXTENSION** — Streamlit requires a live session; no offline-capable or SMS-based output currently exists. |
| Colour-independent interpretation | **PARTIALLY IMPLEMENTED** — the dashboard uses 🟡/🟢 emoji plus text labels for data mode (not colour alone), but pass/fail governance checks currently rely on ✅/❌ plus Streamlit's built-in success/error colour styling, which is not independently verified against colour-blind-safe contrast standards. |
| Mobile usability | **Not tested.** Streamlit has some responsive behavior by default, but this has not been verified on a mobile device in this project. |
| Screen-reader support | **Not tested.** No specific ARIA/accessibility work has been done beyond Streamlit's defaults. |
| Human-assisted workflow as a first-class path | **PARTIALLY IMPLEMENTED in design, not in interface** — the governance framework assumes a field officer mediates between the tool and a farmer (`docs/02-stakeholder-map.md`), but the interface itself doesn't yet support a distinct "officer mode" vs. "farmer mode."|

## What would be required for a genuine accessibility pass

User testing with actual Bangladeshi field officers and, ideally, farmers — not a developer's assumptions about what's accessible. None of that testing has occurred. This document is a gap list, not a compliance claim.
