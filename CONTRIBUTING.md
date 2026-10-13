# Contributing

This is an independent portfolio/research project. Contributions, issues, and forks are welcome.

## Ground rules (non-negotiable, matching this project's own standard)

1. **No fabricated data or results.** Any dataset must be logged in `docs/data-provenance/provenance-register.md` with its real source, licence, and evidence status (DOCUMENTED/EXPECTED/OBSERVED/VERIFIED — see that file's legend) before being used in `src/` or referenced in `docs/`.
2. **Synthetic stays labelled synthetic.** Any result from `data/processed/synthetic_demo/` must carry `"DEMONSTRATION ONLY — NOT EMPIRICAL EVIDENCE"` wherever it's reported.
3. **Run before claiming.** If you add or change pipeline code, run `pytest` and `python scripts/run_pipeline.py` and confirm they pass before opening a PR.
4. **Documentation must match implementation.** If a doc describes a feature, that feature must exist in `src/` or be explicitly marked PROPOSED DESIGN / PLANNED.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
pytest
```
