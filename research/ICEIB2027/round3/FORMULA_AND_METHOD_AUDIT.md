# Formula and Method Audit

## 1. Raw fusion versus constant contraction

For price probability p, logistic-accounting probability f, training Beta(1,1) constant c=(Σy_train+1)/(n_train+2) and a development-chosen weight w:

q=(1−w)p+wf; q₀=(1−w)p+wc; e=q−q₀=w(f−c).

With L(q,y)=(q−y)², expansion gives

L(q₀,y)−L(q₀+e,y)=2e(y−q₀)−e²=2w(f−c)(y−q₀)−w²(f−c)².

Alignment is positive when the additional deviation aligns with the constant-control residual; the deviation penalty is nonnegative and subtracted. This algebra describes raw linear mixtures. Separate Platt maps do not preserve the same raw linear identity. No causal information share follows from its empirical average.

The actual code is [e9b_fusion.py](../../../scripts/e9b_fusion.py), and all ten stock/expert identities are in [fusion_raw_identities.csv](../../E9b/tables/fusion_raw_identities.csv). Float64 reconstructed mixtures satisfy the exact identity within1e−12; the archived float32 intermediates are compared under the recorded four-float32-epsilon tolerance. We retain archived score effects/intervals rather than overwrite them with recomputed rounded quantities. The conference equations use the same sign convention: positive reference loss minus candidate loss.

## 2. Continuous Brier and the signed grouping remainder

Use k_i=min(floor(Kp_i),K−1), K=10 (K=5 sensitivity). In bin k, v_k=n_k/N, μ_k=mean(p), o_k=mean(y), o=overall mean(y). Empty bins contribute zero.

REL=Σv_k(μ_k−o_k)²; RES=Σv_k(o_k−o)²; UNC=o(1−o).

G=Σv_k mean_k[(p−μ_k)²−2(p−μ_k)(y−o_k)].

Thus BS_continuous=REL−RES+UNC+G; replacing every p_i by its bin mean gives BS_binned=REL−RES+UNC. G can have either sign. It is neither an omitted nonnegative error term nor an unbiased population-information contribution. Components depend on fixed bins and sample outcomes; decompositions are computed per seed before averaging.

The implementation [e9b_core.py: decomposition](../../../scripts/e9b_core.py) and120 current audit rows agree with [archived per-seed components](../../E9b/tables/fusion_decomposition_per_seed.csv). In the AAPL LSTM calibrated comparison, the constant has a smaller reliability penalty even though the fusion point score is lower; resolution and G also differ. Therefore reliability alone cannot explain total Brier ordering.

## 3. Calibrators and AUC

Historical fitting is [e3b_protocol.py: calibrate](../../../scripts/e3b_protocol.py): C=1, lbfgs, max_iter500 on clipped logits,2023H2 only, independent per pipeline/seed. Saved coefficients now replay without fitting. All thirty single-seed rank relations and six summaries are checked in [CALIBRATION_AUDIT.md](CALIBRATION_AUDIT.md). News uses its separate identity-prior monotone calibration; no replacement method is chosen in this revision.

## 4. Spearman and forward Ridge reconstruction

The [locked E9b plan](../../E9b/ANALYSIS_PLAN_LOCKED.json) and [e9b_technical.py](../../../scripts/e9b_technical.py) are authoritative. The frozen adjusted snapshots are filtered before any post2025 numerical use; this auxiliary analysis is cut at2022-12-31.

Spearman correlations use2768 finite-feature dates per stock,2012-01-03–2022-12-30. They concern same-date ranks among all51 features, including the13 additions. Reconstruction maps the38 available price features to all13 added features (including centered Wilder14 RSI), not only favorable targets. Per-fold price-feature construction/thresholds use the training cutoff, followed by StandardScaler for inputs and targets fitted within that fold's training rows. Ridge(alpha=10) fits standardized targets; predictions are inverse-scaled before scoring.

Three expanding fits end2016/2018/2020-06-30. The following half-year is the inherited model-stopping gap; outer evaluation covers2017–2018,2019–2020,2021–2022. The common index rule requires60 finite-history sessions, exact nonzero preceding direction and end20 inside the block. This inherited purging/filtering also applies to auxiliary reconstruction despite its same-date target. Full sample sizes are below.

R²=1−Σ(y−ŷ)²/Σ(y−ȳ_eval)² within each outer fold/feature, matching sklearn r2_score. The reported mean is the arithmetic unweighted mean over three folds, not pooled-row R². Target-train-SD normalized RMSE is separately retained. Negative R² values are preserved. “Forward” refers to forward time splits of contemporaneous features; no next-day RSI target or future feature is used. High Spearman and poor linear transfer are compatible and do not establish conditional label information.

| ticker | fold | n_fit | n_eval | R2 | alpha |
| --- | --- | --- | --- | --- | --- |
| AAPL | 2016 | 1109 | 482 | 0.801889087 | 10 |
| AAPL | 2018 | 1612 | 485 | 0.632351685 | 10 |
| AAPL | 2020 | 2115 | 483 | 0.829339986 | 10 |
| TSLA | 2016 | 1110 | 482 | 0.873486698 | 10 |
| TSLA | 2018 | 1611 | 485 | -0.156161484 | 10 |
| TSLA | 2020 | 2114 | 483 | -3.561752012 | 10 |

Six archived multivariate coefficient/scaler artifacts support no-refit reconstruction replay; no Ridge fitting is executed in this conference revision. [All13 target summaries](../../E9b/tables/technical_reconstruction_summary.csv) and [all78 fold/feature rows](../../E9b/tables/technical_forward_reconstruction.csv) remain authoritative. AAPL/TSLA RSI mean R²=0.754526919/−0.948142266; individual folds, including−3.561752012, are retained rather than clipped.

## 5. Exact flat-direction exclusions

The pipeline defines past5=100×(log(Close)−log(Close.shift(5))) and reference_sign=np.sign(past5). The index mask requires reference_sign!=0, with **exact floating equality**, not an epsilon tolerance. A zero has no preceding up/down direction for a reversal label. The frozen E6 market snapshot is checked before label use; no2026 prices are numerically read.

| ticker | partition | calendar_rows | exact_zero_past5_calendar | eligible_before_direction | excluded_exact_zero_after_other_filters | retained |
| --- | --- | --- | --- | --- | --- | --- |
| AAPL | train | 2768 | 2 | 2748 | 2 | 2746 |
| AAPL | stop | 124 | 0 | 104 | 0 | 104 |
| AAPL | cal | 126 | 0 | 106 | 0 | 106 |
| AAPL | test | 502 | 0 | 482 | 0 | 482 |
| TSLA | train | 2768 | 3 | 2748 | 3 | 2745 |
| TSLA | stop | 124 | 0 | 104 | 0 | 104 |
| TSLA | cal | 126 | 0 | 106 | 0 | 106 |
| TSLA | test | 502 | 0 | 482 | 0 | 482 |

Training excludes2 AAPL/3 TSLA otherwise-eligible dates for exactly zero past direction; stopping, calibration and evaluation exclude0. Test482 dates per stock, after the shared end20 purge, match the archived forecasts. Spearman's2768-date feature calendar and classifier/Ridge filtered samples differ intentionally; their counts are not conflated. Main text states the definition; this table preserves exclusions.
