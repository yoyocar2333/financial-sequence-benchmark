# Diagnosing apparent predictive gains in financial machine learning

Hsieh Hao-Hsuan and Jian-Jiun Ding *

Graduate Institute of Communication Engineering, National Taiwan University, Taipei 106319, Taiwan;

* correspondence: jjding@ntu.edu.tw; Tel.: +886-3-33669652

† 7th International Conference on Electronic Communications, Internet of Things and Big Data 2027 (ICEIB 2027). April 23-25, 2027, Tamkang University

## Abstract

Financial machine-learning models combine prices with technical, accounting and textual features, but lower probability loss need not demonstrate new predictive information. We present an integrated evaluation workflow for five-day stock reversals that separates feature representation, probability shrinkage, calibration and news coverage. AAPL and TSLA market experiments use 2012–2022 training, 2023 development and exploratory 2024–2025 evaluation; a separate Apple news cohort evaluates 2025. Logistic regression, XGBoost, LightGBM, long short-term memory and Mamba are assessed with matched inputs, same-weight constant shrinkage, news-density controls and temporally paired inference. None of eight primary technical-feature comparisons establishes improvement after multiplicity correction. All ten raw accounting-fusion settings underperform matched shrinkage; calibrated tree-model gains remain negative for both stocks. Calibrated AAPL neural gains are 0.000980 and 0.001198 Brier units, below 0.5% of their references, with confidence intervals crossing zero. A development-stage fusion advantage is confined to initialization. News density accounts for most improvement over the price comparator, while the primary price-to-sentiment comparison is inconclusive and a historical prior remains competitive. These findings support source-specific controls before attributing apparent gains to additional information. The reproducible workflow provides an interpretable assessment of exploratory financial forecasts without conflating probability accuracy, ranking and investment performance.

Keywords: financial machine learning; incremental information; probability calibration; forecast combination; news density; reversal prediction

## 1. Introduction and Related Work

Financial forecasting combines market histories with technical indicators, accounting reports and text. Lower loss may reflect new information, a more convenient price representation, or moderated probabilities. For short-horizon reversals, calibration improvement need not identify when an event will reverse. We study this attribution problem across forecasting architectures.

Gu et al. [1] identify nonlinear interactions as an important source of machine-learning gains in empirical asset pricing. Lo et al. [2] develop computational tests of technical patterns. These studies motivate nonlinear models and engineered representations, but their targets and populations differ from five-day reversals in two stocks. Xu and Cohen [3] jointly model tweets and historical prices; textual signals therefore warrant comparison with market information, not an assumption that sentiment automatically predicts reversals.

Forecast combination [4] and probability pooling [5] offer a second explanation for improved scores: averaging changes dispersion and calibration. Reliability diagnostics [6,7] assess these effects. Glasserman and Lin [8] further show why text-based backtests require attention to model knowledge and historical availability. Proper scoring rules [9] help distinguish probability accuracy from ranking, but do not alone identify a source's independent information. FinBERT [10] estimates financial tone; its sentiment task differs from forecasting subsequent returns.

We integrate three source-specific controls: existing-price representations for technical indicators, equal-weight constant shrinkage and matched inputs for accounting fusion, and article density for sentiment. Logistic, boosted-tree and sequence models are compared within cohorts. Our reproducible workflow interprets gains through these controls and temporal uncertainty rather than pooling incompatible datasets.
## 2. Methods and Experimental Setup

Our contribution is a common diagnostic workflow with source-specific controls for representation, probability contraction and coverage. Matched inputs, calibration audits and the equations test alternative explanations for lower loss.

### 2.1. Tasks, Data and Models

Five-session reversal uses the known past direction sₜ=sign[log(Cₜ/Cₜ₋₅)], entry at the next open and exit at the fifth future close:

`Yₜ = 1{sₜ log(Cₜ₊₅/Oₜ₊₁) < 0}.` (1)

C/O denote close/open; exact-zero preceding directions are excluded. For N observations, the probability loss [9] and candidate benefit are

`BS = N⁻¹Σᵢ(pᵢ−yᵢ)².` (2)

`ΔBS = BS_ref−BS_cand; r(%) = 100ΔBS/BS_ref.` (3)

Positive gains favor candidates; percentages use unrounded same-cohort references, not investment returns.

AUC assesses ranking; within-state AUC pairs outcomes within past-direction/trend/volatility cells.

Market experts use 60-session histories: logistic regression is a linear log-odds baseline; XGBoost/LightGBM learn boosted-tree interactions in flattened inputs; long short-term memory (LSTM) and selective state-space Mamba process sequences. All use the same logistic-accounting fusion expert. Selection uses three candidates/three folds; neural training uses batch 64, up to 24 epochs and patience 4.

Table 1. Separate cohorts; market seeds 42–46 share evaluation dates.

| Cohort | Training | Stopping/calibration | Evaluation |
| --- | --- | --- | --- |
| Market: AAPL/TSLA | 2012–2022 | 2023 | 2024–2025; 482 dates/stock |
| Apple news | 2023: 224 dates/28 events | 2024: 232 dates/36 events | 2025: 230 dates/65 events |

Technical inputs add 12 indicators/QQQ-relative strength to 38 prices. Accounting adds seven measures/age/missingness to 51 prices after two later sessions (five-session sensitivity); each stock supplies 45 training/nine evaluation-used vintages.

The 448-article corpus adds density, FinBERT tone/direction [10] and four event proportions to eight prices; hierarchical models shrink state probabilities. Evaluation contains 42 reversals; thinning retains 22 events.

### 2.2. Fusion, Calibration and Brier Diagnostics

Let p,f denote price/logistic-accounting probabilities, c a training constant and w the development-chosen weight. The compact expert accommodates limited quarterly updates:

`q = (1−w)p + wf; q₀ = (1−w)p + wc.` (4)

For squared loss L(q,y)=(q−y)², the exact raw-mixture benefit is

`L(q₀,y)−L(q,y) = 2w(f−c)(y−q₀)−w²(f−c)².` (5)

Alignment rewards f−c matching y−q₀; the squared penalty subtracts its cost. This raw identity does not extend to separately calibrated pipelines.

For ten fixed bins, vₖ is bin weight, μₖ mean forecast, oₖ outcome rate, o overall rate and Eₖ a within-bin mean. Define REL=Σvₖ(μₖ−oₖ)² (reliability), RES=Σvₖ(oₖ−o)² (resolution), UNC=o(1−o):

`BS = REL − RES + UNC + G.` (6)

`G = ΣₖvₖEₖ[(p−μₖ)²−2(p−μₖ)(y−oₖ)].` (7)

The signed remainder reconciles continuous/bin-mean losses [6,7]; five-bin sensitivity is supplementary.

Each market pipeline uses an L2-regularized Platt map (C=1), fitted on 2023 H2 logit-transformed probabilities clipped first to [10⁻⁶,1−10⁻⁶]:

`q_cal = sigmoid[a logit(q_raw) + b].` (8)

Positive slopes preserve single-seed AUC; negative slopes reverse ranking. News uses identity-regularized monotone calibration, reusing 2024 for selection/calibration.

### 2.3. Representation Diagnostics

Spearman uses 2,768 development dates/stock in 2012–2022. Ridge(alpha=10) reconstructs 13 added features from 38 prices with training-only input/target scaling. Three expanding fits through 2016/2018/2020 H1 evaluate 2017–2018/2019–2020/2021–2022. Forward means temporal evaluation of same-date features, not tomorrow’s RSI; R² averages folds equally. Full filters/scalers are supplementary.

### 2.4. Development Controls and Statistical Evaluation

Development uses 2017–2022 (1,450 dates/stock), 24 logistic/36 tree fits, 60-session histories and 20-session purging. XGBoost/LightGBM accounting values face zero-value, duplicated-price and price-only controls; zero/duplicate arms share metadata/width. Sequential logistic fusion starts at 0.5, then selects weights, experts and constants from preceding folds.

Paired HAC [11], calendar-block bootstrap and Holm [12] retain separate technical-eight, fusion-twenty, news-two, development-six logistic/six tree families and combined-12 sensitivity. Primary studies use 9,999 resamples; development/block 60 use 4,999, with block 20/120 sensitivities.

## 3. Results and Analysis

### 3.1. Overview of Experimental Findings

The following comparisons test representation, contraction and news-coverage explanations within separate cohorts. The design diagram is supplementary.

### 3.2. Technical Indicators: Representation versus New Information

No primary technical contrast establishes corrected benefit (Table 2). TSLA XGBoost gains 0.000235 (0.094% of reference 0.250207), CI[−0.000378,0.000837]; the market-only arm almost reproduces it.

Table 2. Technical additions to the same prices: gain=reference−candidate Brier (10⁻³); primary bootstrap Holm 8 p.

| Model | AAPL gain | AAPL p | TSLA gain | TSLA p |
| --- | --- | --- | --- | --- |
| XGBoost | -0.420 | 0.9952 | +0.235 | 1.0000 |
| LightGBM | -0.020 | 1.0000 | -0.033 | 1.0000 |
| LSTM | -1.643 | 1.0000 | -0.009 | 1.0000 |
| Mamba | -3.616 | 1.0000 | -0.506 | 1.0000 |

RSI/standardized price deviation have Spearman 0.890/0.880 (AAPL/TSLA), but forward Ridge R²=0.755/−0.948. Strong same-period association can coexist with unstable linear transfer. Neither proves conditional redundancy; forecast tests establish no reliable incremental signal from these representations.

### 3.3. Fundamental Fusion: Calibration versus Information Gain

Does accounting fusion beat equal constant contraction? All ten raw settings score worse. AAPL LSTM/Mamba benefits −0.002834/−0.002919 become +0.000980/+0.001198 after calibration (0.395%/0.482%). Block 60 intervals cross zero; TSLA gains are negative (Table 3).

Table 3. Fusion vs same-weight constants: gains×10⁻³, raw→calibrated; displayed reference BS is calibrated. Primary block 20 Holm 20 p=1 for all ten.

| Price expert | AAPL ref. | AAPL raw→cal. | TSLA ref. | TSLA raw→cal. |
| --- | --- | --- | --- | --- |
| Logistic | 0.249260 | -4.719→-0.502 | 0.250121 | -3.343→-0.530 |
| XGBoost | 0.249598 | -1.779→-0.476 | 0.250092 | -2.250→-0.470 |
| LightGBM | 0.249429 | -1.598→-0.311 | 0.250121 | -3.343→-0.530 |
| LSTM | 0.247902 | -2.834→+0.980 | 0.250159 | -2.586→-0.506 |
| Mamba | 0.248822 | -2.919→+1.198 | 0.250121 | -3.343→-0.530 |

XGBoost loses 0.000476/0.000470 (AAPL/TSLA); LightGBM also stays negative. The neural sign change is therefore architecture-specific. Block 60 CIs (×10⁻³) are [−1.351,3.419]/[−0.735,3.321] for AAPL LSTM/Mamba and [−2.026,0.964]/[−2.440,1.464] for TSLA, all spanning zero.

AAPL fusion AUC stays 0.583474 for LSTM but changes 0.573053→0.549749 for Mamba: seed 46 has negative slopes in all three pipelines. Scores average seeds, not ensemble probabilities. LSTM fusion SD contracts 0.055→0.020, versus price 0.102→0.086; constants have lower reliability penalty. Full slope/decomposition audits are supplementary. These pipeline differences do not identify causal information shares.

Secondary AAPL logistic direct-up Brier improves 0.315318→0.251362 (adjusted p=0.0024 within 12, 0.004 across 20 contrasts). Accounting weight=1; a calibration-period constant scores 0.251469. The weak price expert is replaced, not complemented.

### 3.4. Matched Controls: Does Additional Accounting Information Help?

Do accounting numbers beat equally formatted inputs? Against the zero-value control, development XGBoost loses 0.000332 while LightGBM gains 0.000149; both adjusted p=1. Against duplicated prices, their gains are +0.000095/−0.001027. No corrected positive tree advantage appears across six contrasts (p≥0.4032). Matching width controls representation, not effective capacity; complete contrasts remain supplementary.

Logistic fusion gains 0.001931 versus constants (adjusted p=0.152). Versus the prior-selected expert, gain=0.005726 (2.257%), CI[0.001548,0.009306], with six-family p=0.0240/combined-12 p=0.0480. All gain is in 2017–2018 (initial 0.5 fusion versus price); later policies select accounting identically. Block 120 p=0.0744; fixed accounting scores better. This is initialization, not persistent complementarity.

### 3.5. News Density versus Sentiment

Does tone add beyond density? Across 65 Apple events, price→density gains 0.021825 (6.857%); extra tone adds 0.000744 (0.251%; secondary adjusted p=0.8564). Full price→tone gain 0.022569 (7.091%) has primary p=0.1512, CI[−0.002035,0.047736]. Most improvement precedes sentiment.

The secondary hierarchical gain 0.006702 has adjusted p=0.028, rising to 0.1894/0.3714 with one-/two-session extra delays. Its Brier 0.259011 exceeds the historical prior’s 0.256489 (-0.983% gain). Within-state AUC 0.5532 has unadjusted p=0.5721. Improving on one price comparator does not establish superiority to the prior or reliable reversal timing.

Density strata (6/30/29 events) are descriptive: zero means no matching retained article, not no market news. Full comparisons and delay sensitivities are supplementary.

### 3.6. Cross-Experiment Synthesis

Table 4. Cohort-specific findings with separate correction families.

| Question | Critical control | Cohort-specific finding |
| --- | --- | --- |
| Technical | Same prices; market-only | No corrected positive gain. |
| Accounting | Same-weight shrinkage | AAPL gains unresolved; TSLA negative. |
| Values / allocation | Matched inputs; prior expert | No tree advantage; startup-only gain. |
| News | Density; historical prior | Primary inconclusive; secondary delay-sensitive. |

Lower loss alone cannot distinguish new content from representation, estimation or coverage.

## 4. Discussion and Limitations

Technical additions fail to establish corrected improvement across all four families. Accounting fusion stays negative for both tree models; favorable AAPL neural estimates depend on calibration. Source-specific controls clarify these architecture-specific outcomes rather than establish common information gains.

Limits include two surviving stocks, repeatedly explored 2024–2025, overlapping labels, quarterly repetition, bounded searches and sparse news. Local corrections omit the wider research history. Retrospective prices and lagged accounting/news versions lack authenticated PIT: audits found zero L3 version-qualified or L4 arrival-qualified records. Calibration sensitivity and independent-validation needs remain; integrity details are supplementary.

## 5. Conclusions

Matched controls expose representation, probability-processing, initialization and news-coverage effects. In these exploratory cohorts, lower loss alone establishes neither incremental information nor investment utility.

## Back Matter

Author Contributions: Investigation and experiments, Hsieh Hao-Hsuan; supervision, Jian-Jiun Ding.

Funding: This research received no external funding.

Institutional Review Board Statement: Not applicable.

Informed Consent Statement: Not applicable.

Data Availability Statement: Code and aggregate results: https://github.com/yoyocar2333/financial-sequence-benchmark, commit 6f29a9f8375b21ac2894878aa424f12b8d6fa138. Restricted raw data/weights are not public.

Conflicts of Interest: The authors declare no conflicts of interest.

Acknowledgments: Generative AI assisted drafting/code/formatting; authors verify outputs and accept responsibility.

## References

1. Gu, S.; Kelly, B.; Xiu, D. Empirical Asset Pricing via Machine Learning. Rev. Financ. Stud. 2020, 33, 2223-2273. doi:10.1093/rfs/hhaa009

2. Lo, A.W.; Mamaysky, H.; Wang, J. Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation. J. Finance 2000, 55, 1705-1765. doi:10.1111/0022-1082.00265

3. Xu, Y.; Cohen, S.B. Stock Movement Prediction from Tweets and Historical Prices. Proc. ACL (Vol. 1: Long Papers) 2018, 1970-1979. doi:10.18653/v1/P18-1183

4. Bates, J.M.; Granger, C.W.J. The Combination of Forecasts. J. Oper. Res. Soc. 1969, 20, 451-468. doi:10.1057/jors.1969.103

5. Ranjan, R.; Gneiting, T. Combining Probability Forecasts. J. R. Stat. Soc. B 2010, 72, 71-91. doi:10.1111/j.1467-9868.2009.00726.x

6. Bröcker, J. Some Remarks on the Reliability of Categorical Probability Forecasts. Mon. Weather Rev. 2008, 136, 4488-4502. doi:10.1175/2008MWR2329.1

7. Dimitriadis, T.; Gneiting, T.; Jordan, A.I. Stable reliability diagrams for probabilistic classifiers. Proc. Natl. Acad. Sci. USA 2021, 118. doi:10.1073/pnas.2016191118

8. Glasserman, P.; Lin, C. Assessing Look-Ahead Bias in Stock Return Predictions Generated By GPT Sentiment Analysis. arXiv preprint arXiv:2309.17322 2023. doi:10.48550/arXiv.2309.17322

9. Gneiting, T.; Raftery, A.E. Strictly Proper Scoring Rules, Prediction, and Estimation. J. Am. Stat. Assoc. 2007, 102, 359-378. doi:10.1198/016214506000001437

10. Dogu Araci FinBERT: Financial Sentiment Analysis with Pre-trained Language Models. arXiv preprint arXiv:1908.10063 2019. doi:10.48550/arXiv.1908.10063

11. Newey, W.K.; West, K.D. A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix. Econometrica 1987, 55, 703. doi:10.2307/1913610

12. Holm, S. A Simple Sequentially Rejective Multiple Test Procedure. Scand. J. Stat. 1979, 6, 65–70.
