# Real-data quality report (jute & wheat) — REAL DATA, UNVALIDATED

Generated 2026-10-13 by scripts/run_real_pipeline.py.

- Raw rows (jute+wheat): 2421
- Aggregate rows dropped (Region/Division/H.T.): 373
- Zero-area/zero-production rows dropped: 147
- Zero-area with non-zero production dropped (inconsistent): 1
- Rows after adapter: 1900
- Rows removed by cleaning (duplicates 0, out-of-range 2, missing required 0): final 1898
- Distinct district names after title-casing: 68 (spelling variants NOT harmonised — a known limitation)
- Years: 1970–2014
- Crops: {'Wheat': 1354, 'Jute': 544}
- Rows removed by the yield > 50 t/ha rule (suspicious outliers): Barisal Jute 1988 yield=73.96 t/ha (area=3221.30 ha, production=238250); Patuakhali Jute 1988 yield=655.80 t/ha (area=455.27 ha, production=298565)
- temp_c / humidity_pct: not present in source (NaN, not invented); not used as features
- Unit assumptions: acres->ha x0.404686; 'Tons' treated as metric tonnes (unverified)
- Yield (t/ha) summary: {'count': 1898.0, 'mean': 3.821, 'std': 3.574, 'min': 0.0, '25%': 1.69, '50%': 2.147, '75%': 5.778, 'max': 42.479}
