# Claim and Number Validation — Third Round

## Fixed evidence and estimators

All inherited scores, effects, p-values and confidence intervals remain the frozen experiment values. The [R2 full596-row evidence ledger](../round2/audits/R2_SOURCE_EVIDENCE.csv) and [73 descriptive interpretations](../round2/tables/R2_SCORE_INTERPRETATION.csv) remain unchanged. New work applies saved calibration coefficients and checks descriptive scores, rather than selecting a better model or generating new inference.

Positive gain = reference Brier − candidate Brier. Relative gain =100×gain / the corresponding unrounded reference. Main gain/CI columns are explicitly10⁻³ Brier units. Percentages are loss reductions, not AUC, accuracy or returns. Different cohorts and multiplicity families are never pooled or ranked.

## Source index for the main paper

| Main claim | Authoritative source | Check |
| --- | --- | --- |
| Price task,60 histories, three-candidate/fold budget, batch64,24-epoch/patience4 | [E5 plan](../../E5/config/evaluation_plan.json), [E3b protocol code](../../../scripts/e3b_protocol.py) | Classification settings; do not conflate with earlier amplitude batch8 |
| Eight technical primary contrasts | [Exact source eight rows](../../E9a/tables/E5_technical_increments.csv) | All four actual primary architectures×two stocks in mainTable1; bootstrap Holm8, negative gains preserved |
| TSLA XGBoost reference0.2502074685851789, gain0.00023532936963814 | Same source | +0.094% descriptive; CI[−0.0003781492,+0.0008369810], p=1 |
| Spearman and forward RSI R² | [Joint13 targets](../../E9b/tables/technical_representation_joint.csv), [fold rows](../../E9b/tables/technical_forward_reconstruction.csv) | Spearman0.890/0.880; unweighted meanR²0.755/−0.948; no clipping |
| Raw/calibrated fusion gains and all ten settings | [Summary](../../E9b/tables/fusion_probability_summary.csv), [pointwise intervals](../../E9b/tables/fusion_pointwise_intervals.csv) | AAPL−0.002834/−0.002919 raw→+.000980/+.001198 calibrated; all ten raw gains negative |
| AAPL+0.395%/+0.482%; TSLA−.000506/−.000530 | R2 exact interpretation CSV | MainTable2 four rows retained; block60 intervals distinct from primary block20 Holm20 p=1 |
| Six pipelines,30 saved a,b and their raw/calibrated scores | [CALIBRATION_PER_SEED.csv](tables/CALIBRATION_PER_SEED.csv), [source E6 coefficients](../../E6/results/calibration_parameters.csv) | Direct archived-map replay to2.22e−16; no fitting |
| LSTM fusion AUC.583474→.583474; Mamba.573053→.549749 | [Per-seed source](../../E9b/tables/fusion_probability_per_seed.csv), [six summaries](tables/CALIBRATION_SUMMARY.csv) | Arithmetic mean of five per-seed AUCs; not probability-ensemble AUC |
| Negative Mamba seed46; AUC.558262→.441738 for fusion | Saved coefficients and same-seed frozen probabilities | Direct slope proof; positivity/negativity maps AUC to itself/1−AUC |
| REL/RES/UNC/signedG | [Archived per-seed decomposition](../../E9b/tables/fusion_decomposition_per_seed.csv), [120 audit rows](tables/CALIBRATION_DECOMPOSITION.csv) | All components/identities reconcile to1e−12 |
| Initialization+.005726; p=.0240/.0480; block120p=.0744 | [All12 development controls](../../E9b/tables/development_all12_contrasts.csv), [fold allocations](../../E9b/tables/development_prequential_weights.csv) | All gain confined2017–2018; same-weight/tuned gains.001931,p=.152 |
| Secondary direct-up.315318→.251362,p=.0024/.004 | [E6 results](../../E6/results/paired_tests.csv), [report](../../E6/E6_SUMMARY.md) | Weight1 is a single-expert replacement; constant.251469; separate directional families |
| News density+.021825, extra tone+.000744, total+.022569,p=.1512 | [News models](../../E9a/tables/E4c_event_models.csv), [paired tests](../../E4c/results/paired_tests.csv) | Separate primary2 and diagnostic2 families; extra-tone adjustedp=.8564 |
| Hierarchical+.006702,p=.028; delays.1894/.3714 | [Timing tests](../../E9b/tables/news_original_timing_tests.csv) | Secondary, delay-sensitive; prior.256489 beats hierarchical.259011 on point loss |
| Within-state newsAUC.5532,p=.5721; strata6/30/29 | [Density support](../../E9b/tables/news_density_support.csv), timing source | Sparse descriptive strata, not a fully observed no-news regime |
| Flat directions2AAPL/3TSLA in training;0later | [Exact-mask audit](tables/FLAT_DIRECTION_COUNTS.csv) | No epsilon; before/after other filters distinguished |
| Strict newsL3/L4 counts0 | [E8a source contract](../../E8a/DATA_CONTRACT_AND_PIT.md), [E8a1 provenance audit](../../E8a1/HISTORICAL_PIT_PROVENANCE_AUDIT.md) | Source versions and vendor-arrival are separate; engineering tests do not confer eligibility |

A transcription in the R2 supporting audit described the TSLA XGBoost reference as0.250206…; the actual source is0.2502074685851789. R2's manuscript rounding0.250207, effect, percentage and source CSV were already correct. This R3 audit corrects that supporting-prose typo explicitly without changing the protected R2 files or any scientific result.

## Additional checks

[CALIBRATION_AUDIT.md](CALIBRATION_AUDIT.md) supplies full coefficients, SD, calibrated/raw overall and within-state estimators. [FORMULA_AND_METHOD_AUDIT.md](FORMULA_AND_METHOD_AUDIT.md) supplies exact grouping and Ridge definitions. The [public validator](../../../scripts/iceib2027_r3_validate.py) checks264 protected source files, coefficient rows against frozen E6 tables, scores/components against E9b, primary family conservation and byte-reproduced main text. Formula identities and paper numbers are not new p-values.

[Source version index](SOURCE_VERSION_INDEX.md) distinguishes the immutable evidence commit from manuscript rendering/manifests. Twelve verified conference references are inherited without new DOI claims. Current audits establish consistency, not independent human review, authenticated historical PIT or genuinely unseen testing.
