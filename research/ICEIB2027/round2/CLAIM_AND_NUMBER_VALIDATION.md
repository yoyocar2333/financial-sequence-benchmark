# Claim and Number Validation — Round 2

## Scope and calculation definitions

All empirical claims refer to frozen original experiments. This revision adds deterministic interpretation arithmetic, not a new financial evaluation or hypothesis test. The [locked calculation plan](audits/REVISION2_CALCULATION_PLAN.json) was recorded before calculation. Evidence is reproduced by [the validator](../../../scripts/iceib2027_r2_validate.py).

- Absolute benefit: ΔBS = Brier(reference) − Brier(candidate); positive is better for the candidate.
- Relative benefit (%) = 100 × ΔBS / unrounded Brier(reference), **within the same row/cohort**.
- Source paired differences are retained; they agree with subtraction of source score means within 2×10⁻¹² rounding tolerance.
- Main-table gain/CI units are explicitly ×10³. Thus +0.980 in that column means +0.000980 Brier, not +0.980.
- Percentages are descriptive. There are no new relative-effect confidence intervals, p-values, causal information shares or investment-return conversions.
- Existing pointwise confidence intervals and original adjusted p-values may come from different stated block analyses; they are not recombined into a new test.

## Principal numerical checks

| Claim in revised paper | Source and qualification | Interpretation |
| --- | --- | --- |
| Eight technical comparisons show no corrected positive benefit | [Original eight rows](../../E9a/tables/E5_technical_increments.csv); original bootstrap/HAC Holm8, block20 | No established improvement under the tested models; not universal ineffectiveness |
| TSLA XGBoost +0.000235, +0.094%; CI [−0.000378,0.000837] | Same table, unrounded reference 0.250206… | Positive point change is small and unresolved |
| RSI rank correlations 0.890/0.880; forward R² 0.755/−0.948 | [All 13 reconstruction targets](../../E9b/tables/technical_representation_joint.csv) | Association differs from stable out-of-time linear transfer; neither proves conditional redundancy |
| All ten raw fusion comparisons are negative | [Raw/calibrated summary](../../E9b/tables/fusion_probability_summary.csv), [existing intervals](../../E9b/tables/fusion_pointwise_intervals.csv) | Raw accounting expert does not beat same-weight constant contraction in these settings |
| AAPL LSTM/Mamba −0.002834/−0.002919 raw → +0.000980/+0.001198 calibrated | Same original point differences; relative gains +0.395%/+0.482% | Separate calibrators alter complete probability pipelines; not identified information effects |
| Calibrated neural block60 CIs span zero; all four displayed original family p=1 | CI source above; original [E6 fusion family](../../E6/results/information_and_fusion_gains.csv) | CI is E9b pointwise block60; p is original E6 block20 Holm20, not a newly tested family |
| Price/fusion/constant SD 0.086/0.020/0.022; differing REL/RES/grouping | [Probability summaries](../../E9b/tables/fusion_probability_summary.csv), [decomposition](../../E9b/tables/fusion_decomposition.csv) | Binning remainder retained; lower reliability penalty alone does not determine total continuous Brier |
| AAPL secondary direct-up 0.315318→0.251362; p=0.0024/0.004; weight1; constant0.251469 | [E6 paired tests](../../E6/results/paired_tests.csv), [original E6 report](../../E6/E6_SUMMARY.md) | Directional12 and directional20 families, separate from reversal; F-only replacement, not two-expert complementarity |
| All six tree matched contrasts adjusted p≥0.4032 | [All12 development contrasts](../../E9b/tables/development_all12_contrasts.csv) | No corrected numerical-content advantage; LR unfavorable results also retained |
| Initialization benefit +0.005726 (+2.257%); CI [0.001548,0.009306]; p=.0240/.0480 | Same source, LR C6 block60; exact equal-stock score reference | Holm6 and combined Holm12 are alternative source families, not pooled evidence |
| Block120 p=.0744, all C6 change in 2017–2018 | Same source; [fold allocation](../../E9b/tables/development_prequential_weights.csv) | Later strategies are identical; no persistent diversification claim |
| Density +.021825 (6.857%); extra tone +.000744 (.251%); full news +.022569 (7.091%) | [All eight event predictors](../../E9a/tables/E4c_event_models.csv), [original paired tests](../../E4c/results/paired_tests.csv) | Each percentage has its own reference, not a common denominator |
| Primary news p=.1512, CI [−.002035,.047736]; extra-tone p=.8564 | Same sources, primary_LR_news2 vs secondary_density_sentiment2 | Separate two-comparison families; no pooled conclusion |
| Hierarchical gain .006702, secondary p=.028; delays p=.1894/.3714 | [Original timing sensitivity](../../E9b/tables/news_original_timing_tests.csv) | Local secondary result, sensitive to availability assumptions |
| Historical prior .256489 vs hierarchical news .259011; relative benefit −.983% | Original event-model table; arithmetic only | Candidate worse than prior on point Brier; no new test |
| Within-state AUC .5532, unadjusted p=.5721; strata6/30/29 | Timing source, [support](../../E9b/tables/news_density_support.csv), [stratified contrasts](../../E9b/tables/news_attention_sentiment_contrasts.csv) | Sparse descriptive support; zero retained windows do not establish no-news observations |

## Cohorts, dependence and methods

Market/technical and archived accounting comparisons have 482 common evaluation dates per stock, seeds42–46, 2012–2022 training/2023 stopping-calibration/2024–2025 already-explored evaluation. Development controls cover 1,450 dates/stock in2017–2022; their equal-stock means are reproduced before calculating percentages. News has a distinct 2023/2024/2025 design, 224/232/230 eligible dates, 28/36/65 extreme events and42 positive evaluation events. These absolute scores are never pooled or cross-ranked.

Original E5/E6/E4c Brier bootstrap uses9,999 resamples; E9b development and pointwise block60 diagnostics use4,999. Main text distinguishes them. Seeds are not independent market paths; repeated daily accounting values are not independent quarterly releases.

Market Platt fitting uses C=1 L2-regularized logistic regression on clipped probability logits in2023H2, with unconstrained slope. A negative slope can reverse rankings. News retains its distinct identity-regularized monotone mapping and2024 selection/calibration reuse. The compact F expert is logistic; archived LSTM/genuine Mamba are price experts in late fusion, not newly trained accounting encoders.

## Machine-verifiable evidence and conservation

[Exact evidence ledger](audits/R2_SOURCE_EVIDENCE.csv):596 original rows with source file, selector, original record index, fields and SHA256. [Interpretation CSV](tables/R2_SCORE_INTERPRETATION.csv):73 complete descriptive comparisons (8technical +20raw/calibrated fusion +36development +9news). Decimal arithmetic preserves sign and unrounded denominators; replay regenerates the Markdown and full supplementary tables byte for byte.

[237 protected source hashes](audits/PROTECTED_SCIENTIFIC_SOURCE_HASHES.json) include original E3c protocol, E4c/E5/E6/E9a/E9b material. They remain unchanged. The twelve conference references and DOI mapping are inherited from the verified current conference bibliography; see [original citation audit](../../E9a/LITERATURE_AND_CITATION_AUDIT.md) and [reference mapping](../audits/REFERENCE_MAPPING.csv). No new citation or empirical p-value is invented.

Engineering validation establishes source consistency, not independent statistical replication, human document QA or historical PIT certification. Full test results: [EVIDENCE_VALIDATION.json](audits/EVIDENCE_VALIDATION.json). DOCX/PDF consistency is separately recorded in [format validation](FORMAT_AND_PAGE_VALIDATION.md).
