# Supplementary Results — complete comparisons

All rows retain original cohorts, signs, intervals and correction families. Gain = reference Brier minus candidate Brier; ×10³ changes display units only. Relative gain (%) = 100 × gain / unrounded reference. Interval endpoints remain absolute source differences (displayed ×10³); no new inference is attached to percentages. Raw fusion rows have no newly calculated p-value. These descriptive additions do not replace the frozen E9b tables.

## Table S1. All eight technical additions

| Stock/model | Reference | Candidate | Gain ×10³ | Gain % | 95% CI ×10³ | Original bootstrap Holm8 p |
| --- | --- | --- | --- | --- | --- | --- |
| AAPL xgboost | 0.249847 | 0.250267 | -0.420 | -0.168 | [-0.942, +0.143] | 0.9952 |
| AAPL lightgbm | 0.249707 | 0.249727 | -0.020 | -0.008 | [-0.190, +0.148] | 1.0000 |
| AAPL lstm | 0.249484 | 0.251127 | -1.643 | -0.659 | [-10.325, +7.534] | 1.0000 |
| AAPL mamba | 0.248494 | 0.252111 | -3.616 | -1.455 | [-9.143, +2.335] | 1.0000 |
| TSLA xgboost | 0.250207 | 0.249972 | +0.235 | 0.094 | [-0.378, +0.837] | 1.0000 |
| TSLA lightgbm | 0.249855 | 0.249888 | -0.033 | -0.013 | [-1.017, +0.911] | 1.0000 |
| TSLA lstm | 0.250556 | 0.250565 | -0.009 | -0.004 | [-1.664, +1.517] | 1.0000 |
| TSLA mamba | 0.250284 | 0.250790 | -0.506 | -0.202 | [-2.202, +1.278] | 1.0000 |

Intervals and tests above use the original block20 analysis. All 13 reconstruction targets and complete rank correlations remain in [technical representation diagnostics](../../E9b/tables/technical_representation_joint.csv) and [the original matrix](../../E9b/tables/technical_spearman_matrix.csv). No high correlation is treated as proof of conditional redundancy.

## Table S2. All ten accounting-fusion settings before/after calibration

| Stock/model | Stage | Constant reference | Fusion | Gain ×10³ | Gain % | Existing block60 CI ×10³ | Original calibrated Holm20 p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL logistic | raw | 0.254604 | 0.259323 | -4.719 | -1.854 | [-14.156, +3.890] | Not retested |
| AAPL logistic | calibrated | 0.249260 | 0.249761 | -0.502 | -0.201 | [-1.046, +0.053] | 1.0000 |
| AAPL xgboost | raw | 0.252727 | 0.254506 | -1.779 | -0.704 | [-6.489, +2.572] | Not retested |
| AAPL xgboost | calibrated | 0.249598 | 0.250073 | -0.476 | -0.191 | [-0.980, +0.042] | 1.0000 |
| AAPL lightgbm | raw | 0.253235 | 0.254834 | -1.598 | -0.631 | [-6.309, +2.731] | Not retested |
| AAPL lightgbm | calibrated | 0.249429 | 0.249739 | -0.311 | -0.124 | [-0.632, +0.016] | 1.0000 |
| AAPL lstm | raw | 0.253387 | 0.256221 | -2.834 | -1.119 | [-9.967, +3.904] | Not retested |
| AAPL lstm | calibrated | 0.247902 | 0.246922 | +0.980 | 0.395 | [-1.351, +3.419] | 1.0000 |
| AAPL mamba | raw | 0.254174 | 0.257093 | -2.919 | -1.148 | [-10.109, +3.790] | Not retested |
| AAPL mamba | calibrated | 0.248822 | 0.247623 | +1.198 | 0.482 | [-0.735, +3.321] | 1.0000 |
| TSLA logistic | raw | 0.250368 | 0.253711 | -3.343 | -1.335 | [-9.347, +2.789] | Not retested |
| TSLA logistic | calibrated | 0.250121 | 0.250651 | -0.530 | -0.212 | [-2.440, +1.464] | 1.0000 |
| TSLA xgboost | raw | 0.249870 | 0.252120 | -2.250 | -0.901 | [-6.636, +2.232] | Not retested |
| TSLA xgboost | calibrated | 0.250092 | 0.250562 | -0.470 | -0.188 | [-1.750, +0.847] | 1.0000 |
| TSLA lightgbm | raw | 0.250368 | 0.253711 | -3.343 | -1.335 | [-9.347, +2.789] | Not retested |
| TSLA lightgbm | calibrated | 0.250121 | 0.250651 | -0.530 | -0.212 | [-2.440, +1.464] | 1.0000 |
| TSLA lstm | raw | 0.250784 | 0.253370 | -2.586 | -1.031 | [-7.044, +1.920] | Not retested |
| TSLA lstm | calibrated | 0.250159 | 0.250665 | -0.506 | -0.202 | [-2.026, +0.964] | 1.0000 |
| TSLA mamba | raw | 0.250368 | 0.253711 | -3.343 | -1.335 | [-9.347, +2.789] | Not retested |
| TSLA mamba | calibrated | 0.250121 | 0.250651 | -0.530 | -0.212 | [-2.440, +1.464] | 1.0000 |

The CI block60 is an existing pointwise E9b diagnostic; the adjusted p column is the original E6 calibrated block20 fusion family of20. They are not a new joint test. Complete [raw/calibrated distribution summaries](../../E9b/tables/fusion_probability_summary.csv), [ten-bin decompositions including grouping remainder](../../E9b/tables/fusion_decomposition.csv), [raw identities](../../E9b/tables/fusion_raw_identities.csv) and [per-seed records](../../E9b/tables/fusion_probability_per_seed.csv) are unchanged.

## Table S3. All six logistic and six tree matched controls

| Readable contrast (source code) | Model / block | Reference | Candidate | Gain ×10³ | Gain % | 95% CI ×10³ | Original Holm6 p | Original Holm12 p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Accounting values vs. zero-value control (C1) | logistic / 60 | 0.333162 | 0.340817 | -7.655 | -2.298 | [-21.292, +7.731] | 0.5972 | 1.0000 |
| Accounting values vs. duplicated-price control (C2) | logistic / 60 | 0.334499 | 0.340817 | -6.319 | -1.889 | [-20.165, +9.262] | 0.5972 | 1.0000 |
| Accounting values vs. price-only (C3) | logistic / 60 | 0.317734 | 0.340817 | -23.083 | -7.265 | [-42.023, -3.594] | 0.1050 | 0.2310 |
| Sequential fusion vs. same-weight shrinkage (C4) | logistic / 60 | 0.249918 | 0.247987 | +1.931 | 0.773 | [+0.110, +3.728] | 0.1520 | 0.3800 |
| Sequential fusion vs. independently tuned shrinkage (C5) | logistic / 60 | 0.249918 | 0.247987 | +1.931 | 0.773 | [+0.110, +3.728] | 0.1520 | 0.3800 |
| Sequential fusion vs. prior-selected single expert (C6) | logistic / 60 | 0.253713 | 0.247987 | +5.726 | 2.257 | [+1.548, +9.306] | 0.0240 | 0.0480 |
| Accounting values vs. zero-value control (C1) | logistic / 20 | 0.333162 | 0.340817 | -7.655 | -2.298 | [-19.277, +4.399] | 0.3936 | 1.0000 |
| Accounting values vs. duplicated-price control (C2) | logistic / 20 | 0.334499 | 0.340817 | -6.319 | -1.889 | [-18.245, +5.957] | 0.3936 | 1.0000 |
| Accounting values vs. price-only (C3) | logistic / 20 | 0.317734 | 0.340817 | -23.083 | -7.265 | [-39.739, -5.959] | 0.0380 | 0.0836 |
| Sequential fusion vs. same-weight shrinkage (C4) | logistic / 20 | 0.249918 | 0.247987 | +1.931 | 0.773 | [+0.033, +3.909] | 0.2096 | 0.5240 |
| Sequential fusion vs. independently tuned shrinkage (C5) | logistic / 20 | 0.249918 | 0.247987 | +1.931 | 0.773 | [+0.033, +3.909] | 0.2096 | 0.5240 |
| Sequential fusion vs. prior-selected single expert (C6) | logistic / 20 | 0.253713 | 0.247987 | +5.726 | 2.257 | [+2.506, +8.558] | 0.0060 | 0.0120 |
| Accounting values vs. zero-value control (C1) | logistic / 120 | 0.333162 | 0.340817 | -7.655 | -2.298 | [-19.831, +8.072] | 0.5988 | 1.0000 |
| Accounting values vs. duplicated-price control (C2) | logistic / 120 | 0.334499 | 0.340817 | -6.319 | -1.889 | [-18.886, +9.804] | 0.5988 | 1.0000 |
| Accounting values vs. price-only (C3) | logistic / 120 | 0.317734 | 0.340817 | -23.083 | -7.265 | [-40.198, -4.435] | 0.0744 | 0.1488 |
| Sequential fusion vs. same-weight shrinkage (C4) | logistic / 120 | 0.249918 | 0.247987 | +1.931 | 0.773 | [+0.127, +3.698] | 0.1400 | 0.3500 |
| Sequential fusion vs. independently tuned shrinkage (C5) | logistic / 120 | 0.249918 | 0.247987 | +1.931 | 0.773 | [+0.127, +3.698] | 0.1400 | 0.3500 |
| Sequential fusion vs. prior-selected single expert (C6) | logistic / 120 | 0.253713 | 0.247987 | +5.726 | 2.257 | [+0.880, +9.984] | 0.0744 | 0.1540 |
| Accounting values vs. zero-value control (C1) | xgboost / 60 | 0.247255 | 0.247587 | -0.332 | -0.134 | [-1.031, +0.418] | 1.0000 | 1.0000 |
| Accounting values vs. duplicated-price control (C2) | xgboost / 60 | 0.247682 | 0.247587 | +0.095 | 0.038 | [-0.830, +1.026] | 1.0000 | 1.0000 |
| Accounting values vs. price-only (C3) | xgboost / 60 | 0.247744 | 0.247587 | +0.157 | 0.064 | [-1.504, +2.003] | 1.0000 | 1.0000 |
| Accounting values vs. zero-value control (C1) | lightgbm / 60 | 0.248492 | 0.248343 | +0.149 | 0.060 | [-1.250, +1.436] | 1.0000 | 1.0000 |
| Accounting values vs. duplicated-price control (C2) | lightgbm / 60 | 0.247316 | 0.248343 | -1.027 | -0.415 | [-2.104, +0.077] | 0.4032 | 0.5376 |
| Accounting values vs. price-only (C3) | lightgbm / 60 | 0.248035 | 0.248343 | -0.308 | -0.124 | [-1.705, +1.039] | 1.0000 | 1.0000 |
| Accounting values vs. zero-value control (C1) | xgboost / 20 | 0.247255 | 0.247587 | -0.332 | -0.134 | [-1.127, +0.448] | 1.0000 | 1.0000 |
| Accounting values vs. duplicated-price control (C2) | xgboost / 20 | 0.247682 | 0.247587 | +0.095 | 0.038 | [-0.883, +1.021] | 1.0000 | 1.0000 |
| Accounting values vs. price-only (C3) | xgboost / 20 | 0.247744 | 0.247587 | +0.157 | 0.064 | [-1.339, +1.750] | 1.0000 | 1.0000 |
| Accounting values vs. zero-value control (C1) | lightgbm / 20 | 0.248492 | 0.248343 | +0.149 | 0.060 | [-1.204, +1.454] | 1.0000 | 1.0000 |
| Accounting values vs. duplicated-price control (C2) | lightgbm / 20 | 0.247316 | 0.248343 | -1.027 | -0.415 | [-2.128, +0.108] | 0.4392 | 0.5856 |
| Accounting values vs. price-only (C3) | lightgbm / 20 | 0.248035 | 0.248343 | -0.308 | -0.124 | [-1.686, +1.005] | 1.0000 | 1.0000 |
| Accounting values vs. zero-value control (C1) | xgboost / 120 | 0.247255 | 0.247587 | -0.332 | -0.134 | [-1.074, +0.444] | 1.0000 | 1.0000 |
| Accounting values vs. duplicated-price control (C2) | xgboost / 120 | 0.247682 | 0.247587 | +0.095 | 0.038 | [-0.933, +1.122] | 1.0000 | 1.0000 |
| Accounting values vs. price-only (C3) | xgboost / 120 | 0.247744 | 0.247587 | +0.157 | 0.064 | [-1.500, +2.095] | 1.0000 | 1.0000 |
| Accounting values vs. zero-value control (C1) | lightgbm / 120 | 0.248492 | 0.248343 | +0.149 | 0.060 | [-1.257, +1.476] | 1.0000 | 1.0000 |
| Accounting values vs. duplicated-price control (C2) | lightgbm / 120 | 0.247316 | 0.248343 | -1.027 | -0.415 | [-2.182, +0.254] | 0.5556 | 0.7408 |
| Accounting values vs. price-only (C3) | lightgbm / 120 | 0.248035 | 0.248343 | -0.308 | -0.124 | [-1.663, +0.999] | 1.0000 | 1.0000 |

References/candidates above are exact equal-stock means of each source score (2017–2022;1,450 dates/stock), not averages of daily independent earnings events. Six LR and six tree families stay separate; the combined12 sensitivity is reported additionally. Block20/60/120 rows remain complete. Initialization is documented in [foldwise choices](../../E9b/tables/development_prequential_weights.csv); actual/zero/duplicated controls share metadata and width, without a claim of equal effective capacity.

## Table S4. All news predictors and nested contrasts

| method | n | Brier | Log_loss | AUC | claim_id |
| --- | --- | --- | --- | --- | --- |
| lr_P | 65 | 0.3182755044380514 | 0.8417486974346028 | 0.3944099378881987 | E4C_lr_P |
| lr_D | 65 | 0.29645020896092655 | 0.7900066810114286 | 0.4761904761904762 | E4C_lr_D |
| lr_S | 65 | 0.2957062823406152 | 0.788906113992409 | 0.5341614906832299 | E4C_lr_S |
| lr_T | 65 | 0.2969545038214456 | 0.7914714285733971 | 0.5320910973084887 | E4C_lr_T |
| hier_P | 65 | 0.26571344400835545 | 0.7251239194480523 | 0.522256728778468 | E4C_hier_P |
| hier_S | 65 | 0.25901140829045133 | 0.7115999353504392 | 0.5869565217391305 | E4C_hier_S |
| hier_T | 65 | 0.2571486965009206 | 0.7077563908847064 | 0.5755693581780538 | E4C_hier_T |
| global | 65 | 0.25648915134367156 | 0.7061331734883063 | 0.5 | E4C_global |

| Candidate vs. reference | Reference Brier | Candidate Brier | Gain ×10³ | Gain % | Original CI ×10³ | Original adjusted p | Family |
| --- | --- | --- | --- | --- | --- | --- | --- |
| lr_D vs. lr_P | 0.318276 | 0.296450 | +21.825 | 6.857 | [-1.903, +48.796] | 0.1928 | secondary_density_sentiment2 |
| lr_S vs. lr_D | 0.296450 | 0.295706 | +0.744 | 0.251 | [-6.932, +8.301] | 0.8564 | secondary_density_sentiment2 |
| lr_S vs. lr_P | 0.318276 | 0.295706 | +22.569 | 7.091 | [-2.035, +47.736] | 0.1512 | primary_LR_news2 |
| lr_T vs. lr_S | 0.295706 | 0.296955 | -1.248 | -0.422 | [-3.561, +1.717] | 0.3445 | primary_LR_news2 |
| hier_S vs. hier_P | 0.265713 | 0.259011 | +6.702 | 2.522 | [+2.417, +12.570] | 0.0280 | secondary_hier_news2 |
| hier_T vs. hier_S | 0.259011 | 0.257149 | +1.863 | 0.719 | [-0.273, +4.184] | 0.1022 | secondary_hier_news2 |
| lr_S vs. global | 0.256489 | 0.295706 | -39.217 | -15.290 | No new interval | Descriptive only | DESCRIPTIVE_ONLY_NO_NEW_TEST |
| hier_S vs. global | 0.256489 | 0.259011 | -2.522 | -0.983 | No new interval | Descriptive only | DESCRIPTIVE_ONLY_NO_NEW_TEST |
| hier_T vs. global | 0.256489 | 0.257149 | -0.660 | -0.257 | No new interval | Descriptive only | DESCRIPTIVE_ONLY_NO_NEW_TEST |

P = prices; D = prices+density/existence; S = D+tone/interaction; T = S+four event-type proportions; hier = hierarchical shrinkage; global = original historical prior. These original codes are confined to the complete source tables. Same65 extreme events; these scores are never ranked against market-wide or development cohorts. Full [timing/delay/sensitivity tests](../../E9b/tables/news_original_timing_tests.csv), [density support](../../E9b/tables/news_density_support.csv), [stratified metrics](../../E9b/tables/news_density_conditioned_metrics.csv) and [density/sentiment contrasts](../../E9b/tables/news_attention_sentiment_contrasts.csv) retain sparse and negative results.

## Complete settings and inference

The frozen [market/technical study](../../E5/README.md), [accounting study](../../E6/E6_SUMMARY.md), [news study](../../E4c/README.md), [E9b methods and integrity](../../E9b/SUPPLEMENTARY_METHODS_AND_INTEGRITY.md) and original machine-readable tables are the authoritative settings. Brier, log loss, AUC, calibration and ranking refer to different properties. No revised model, threshold, p-value, confidence interval or financial evaluation was generated for this editorial revision.
