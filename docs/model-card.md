# Model card — real-data exploratory run (jute & wheat)

Status: **exploratory, real-data, unvalidated.** Numbers are from `outputs/reports/real_run_log.md` and `experiment-registry.csv` (seed 42), reproduced on a second run.

## Task and target
Retrospective estimation of crop yield (`yield_t_per_ha` = production / area) for an area-crop-year record. Not forecasting, not crop recommendation.

## Models
Naive pooled-mean baseline (one mean across both crops), Ridge regression, Random Forest (200 trees, max depth 6).

## Features
`area_ha`, `rainfall_mm` (the source's reported "Rainfall in MM" field — aggregation unverified), `rainfall_per_area`, `district`, `crop`. **Not used:** temperature, humidity (absent from the files), `production_t` (would leak the target), year, season. No separate climate dataset is integrated. Imputation and one-hot encoding are fit on the fit split only (unknown categories ignored).

## Split (chronological, by unique year, 60/20/20)
| Split | Years | n |
|---|---|---|
| Fit | 1970–1996 | 868 |
| Calibrate (conformal) | 1997–2005 | 430 |
| Test | 2006–2014 | 600 (Wheat 519, Jute 81) |

## Reported metrics (test years)
| Model | MAE (t/ha) | RMSE (t/ha) | R² | Interval halfwidth (t/ha) | Empirical coverage (target 0.90) |
|---|---|---|---|---|---|
| Naive pooled mean | 2.4328 | 3.1432 | −0.0285 | 6.8006 | 0.9283 |
| Ridge | 1.5818 | 3.2343 | −0.0890 | 7.2114 | 0.9000 |
| Random Forest | 1.2335 | 1.7565 | 0.6788 | 3.2681 | 0.9233 |

Random Forest top importances (impurity-based; associations only): crop_Jute 0.383, crop_Wheat 0.353, area_ha 0.127, rainfall_mm 0.047, rainfall_per_area 0.041. By-crop test MAE (Random Forest vs *pooled* naive): Jute 3.604 vs 6.969; Wheat 0.863 vs 1.725.

## Prediction-interval method
Split-conformal with absolute residuals: the halfwidth is the k-th smallest absolute calibration residual, k = ceil((n+1)·coverage) (n = 430 calibration rows, so k = 388 at 90%), taken as an actual order statistic with no interpolation; the interval is symmetric around each prediction. Invalid coverage, empty or non-finite residuals, or a calibration set too small for the requested coverage (k > n) raise an error rather than being clipped. Reported coverage is **empirical coverage on the held-out 2006–2014 test set**. It is not a guarantee of future coverage; conformal guarantees assume exchangeability, which temporal distribution shift can violate.

## Interpreting the comparison
- Exploratory: three models, one split, one seed, no confidence intervals on the metrics. The model used in examples is selected by lowest *test* MAE (post-hoc selection on the test set), so Random Forest is not shown to be conclusively superior.
- The pooled baseline may understate a crop-specific baseline (not evaluated). Crop identity dominates the Random Forest importance, so much of its advantage is plausibly crop differences rather than rainfall.
- Ridge's RMSE exceeds the naive baseline's; not diagnosed.

## Limitations of temporal evaluation
A single chronological split tests one forward period (2006–2014) after the fit and calibration years; it says nothing about later years, other regions, or structural change. Calibration years (1997–2005) may differ from test years in distribution. Test composition is mostly wheat (519 of 600).

## Intended use
Research and demonstration of a governed, leakage-aware analytics pipeline; outputs are decision support requiring human review (`recommended_action_type = human_review`).

## Prohibited / out-of-scope uses
Operational advice to farmers; policy, subsidy, insurance or credit decisions; forecasting future seasons; crop recommendation; causal claims about rainfall or area; presenting results as official or field-validated.

## Unresolved data-quality issues
Provenance lineage unresolved; units assumed; rainfall field aggregation unknown; 68 unharmonised district-name strings; two 1988 jute outliers removed by a fixed rule and high retained yields not investigated; only two crops. No field validation, farmer feedback, or climate integration exists.
