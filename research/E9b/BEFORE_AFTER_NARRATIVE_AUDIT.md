# E9b：論述修訂前後對照


## 可重算的文字計數

固定規則辨識的防禦句：**38 → 0**，減少 **38** 句。not／cannot／never token：**124 → 0**。此為明示規則的文字指標；負面實驗結論仍保留，不能把所有否定詞一律當作缺點。

範圍與逐句匹配見 `audits/narrative_counts.json`。排除中摘、表格、圖像、標題、References及附錄，以免新增引用或移動工程紀錄扭曲對照。


## 1. 以三項完成的比較與診斷取代方法發明的否定聲明；新穎性範圍留在相關研究定位

**E9a 原段落**

> Three contributions are currently supportable. First, the paper provides an auditable cross-experiment account of apparent incremental gains and negative results, including locally significant exceptions. Second, it organizes controls that distinguish price representation, metadata, calibration and constant shrinkage from complementary information. Third, it connects those comparisons to explicit historical-version and data-access requirements. These are empirical and methodological audit contributions. We do not claim to invent technical indicators, probability shrinkage, forecast combination, PIT analysis, or multiple-testing correction, and we do not claim a demonstrated general impossibility of stock prediction.

**E9b 修訂段落**

> The study makes three contributions. First, it connects technical-feature comparisons to training redundancy and forward representation diagnostics, showing why strong contemporaneous correlations alone are an incomplete explanation of forecasting performance. Second, it evaluates fundamental fusion against constant shrinkage, separately examining raw forecasts, recalibrated forecasts, matched input formats and sequential expert allocation. Third, it separates publication density from sentiment and event features, and relates the resulting estimates to historical content-version evidence. These comparisons bring forecast-evaluation controls into a common financial research setting.


## 2. Methods直接說明凍結價格預測與F來源；神經樣本gate及擬合紀錄移至補充方法

**E9a 原段落**

> Early fusion appends the accounting-related columns to the existing price sequence. Late fusion combines frozen P predictions with the F logistic expert. F weights in {0, .25, .5, .75, 1} are selected with existing forward development predictions, followed by stage-specific calibration. Matched-weight P-plus-training-constant mixtures provide a shrinkage control. The metadata-only expert is low-dimensional; it is not the complete capacity-matched P-plus-metadata control required for attribution. No new neural early-fusion model is claimed: each stock had only 45 distinct training vintages, below the study's fixed gate.

**E9b 修訂段落**

> The accounting study fixes T51 as P. Its compact F expert contains seven accounting measures, release age, seven missingness flags and the shared past-direction indicator. Early fusion has sixty-by-sixty-six inputs; late fusion uses the frozen price predictions and a common F logistic expert. Source weights are chosen from {0,.25,.5,.75,1} on development folds. Two strictly later trading sessions align date-only releases, with a five-session sensitivity. Each stock has forty-five training vintages and nine carried/updated test vintages, including eight new test-period updates. Analyst-consensus vintages were unavailable, so the accounting task uses realized financial measures.


## 3. 保留QQQ對照及完整效果；因果與容量限制整合至Limitations

**E9a 原段落**

> The TSLA XGBoost comparison against C is approximately −0.000000510 Brier benefit, with adjusted bootstrap p=1. The small gain over B is thus almost reproduced by adding QQQ alone. This does not causally quantify the contribution of technical indicators, because representations and selected configurations can interact. Training-only RSI/z20 rank correlations are high, consistent with redundancy, but high correlation does not prove conditional redundancy. Likewise, a calibrated trading rule whose learned calibration slope reverses its literal interpretation is not proof that the original investor rule worked.

**E9b 修訂段落**

> The original technical-feature comparison shows small or adverse changes across architectures (Table 2). AAPL deteriorates in all four primary architectures; only TSLA XGBoost has a positive point benefit. Its QQQ-only control almost reproduces the result: the T-versus-C benefit is approximately −0.000000510, with adjusted bootstrap p=1.


## 4. 結果以寬度與穩定性為主；seed的統計單位在Methods集中解釋

**E9a 原段落**

> T increases the AAPL Mamba seed SD from approximately 0.000700 to 0.004474. This is algorithmic variability conditional on one sample, not the standard error of a market effect. The project also reports no corrected within-state ranking advantage in E5. Taken together, these controls do not identify a winning architecture or a stable technical-information channel.

**E9b 修訂段落**

> Complexity changes also matter. Flattening increases the input from 2,280 to 3,060 columns. The AAPL Mamba calibrated seed SD rises from .000700 to .004474. Archived configuration, parameter-count and stopping metadata show the representation and optimization changes alongside these stability measures, supporting an interpretation in terms of finite-model estimation as well as information content.


## 5. 以可核對的損失恆等式、raw/calibrated對照及分箱餘項補足機制分析

**E9a 原段落**

> For AAPL LSTM, late fusion reaches 0.246922 versus P at 0.251127; the matched-weight constant mixture reaches 0.247902. For Mamba, late fusion reaches 0.247623 versus P at 0.252111, while the constant control reaches 0.248822. The remaining advantages over the constant mixtures are about 0.000980 and 0.001198, and neither is statistically reliable under the source H3 family. The original total-gain intervals also cross zero. Describing how much of the point gain is reproduced by a constant control is arithmetic, not a causal decomposition into shrinkage and genuine information. All twenty primary H3 comparisons fail the source joint criterion; TSLA supplies no consistent replication.

**E9b 修訂段落**

> For price forecast p, fundamental forecast f, training constant c and fixed weight w, define q=(1-w)p+wf and q₀=(1-w)p+wc. Their realized loss difference is


## 6. 直接方向顯著差異保留數字、家族與F-only端點，改用實際比較的解釋

**E9a 原段落**

> A significant exception must be retained. In the secondary AAPL direct-up task, logistic Late decreases Brier from 0.315318 to 0.251362, with source bootstrap Holm12 p=0.0024 and all-twenty adjustment p=0.004. However, F weight is one: Late equals F alone. The calibrated constant has Brier 0.251469, and a fixed probability of 0.5 has Brier exactly 0.25 for a binary outcome. This is evidence against that weak direct-up P pipeline, not evidence of complementary fusion or superiority to simple probability baselines. Its task, hyperparameter procedure and correction family are separate from primary reversal inference.

**E9b 修訂段落**

> Ranking supplies complementary evidence. LSTM fusion's overall AUC is .583474, compared with .520047 within the frozen market cells; Mamba's corresponding values are .549749 and .523325. A secondary direct-up example illustrates component replacement: AAPL Logistic drops from .315318 to .251362, with source bootstrap Holm12 p=.0024 and all-twenty p=.004, but F weight is one. The calibration-period constant scores .251469. This contrast measures the replacement of a weak directional price pipeline by the compact expert.


## 7. 完整保留次要p=.028、延遲敏感度與同狀態排序；刪除反覆的寫作防衛

**E9a 原段落**

> The secondary hierarchical S-versus-P benefit of 0.006702 is significant within its own family: HAC Holm2 p=0.013587 and bootstrap Holm2 p=0.028. It must not be suppressed because the primary contrast is nonsignificant. It also must not rescue the primary hypothesis. With one- and two-session additional information delays, its bootstrap Holm2 p-values become 0.1894 and 0.3714. The hierarchical S event Brier remains above the global historical-probability baseline in the main alignment.

**E9b 修訂段落**

> The secondary hierarchical S-versus-P benefit remains .006702, with HAC Holm2 p=.013587 and bootstrap Holm2 p=.028. Additional one-/two-session delays raise the latter to .1894/.3714. Hierarchical S has within-state AUC .5532 with unadjusted p=.5721; Logistic S/T have .5887/.6383, with Holm5 p=.8726/.8544. These results place the local probability improvement alongside its timing and within-state discrimination evidence.


## 8. 以明確標籤與cohort表統一可比性；執行沿革移至S1

**E9a 原段落**

> These earlier stages motivate the audit rather than add independent replications to E4–E6. All-stage selection correction is unavailable: local frozen plans and complete tables improve transparency but cannot turn repeatedly viewed 2024–2025 observations into preregistered holdouts. No cross-stage aggregate p-value or combined effect is reported.

**E9b 修訂段落**

> The principal label compares the past-five-session direction s_t with the next executable five-session return:


## 9. 正文呈現實際歷史證據缺口；E8b行政閘門狀態留在Gap Register

**E9a 原段落**

> E8a and E8a.1 report zero qualified L3 and L4 records; the latter acquired zero real pilot samples and completed zero independent human QA. The offline provenance and collector tests check engineering behavior with clearly separated synthetic responses. They are not data certification, actual historical observations, or human review. E8b remains NOT_READY under the unchanged gates.

**E9b 修訂段落**

> The financial prototype covers twenty companies in four research groups, with twenty-one readable filing indexes and seventeen rendered pages. Original XBRL instance bytes and strictly qualified company quarters remain absent from the acquired evidence. Identity, split/dividend units and historical exits also require explicit handling before expanding the panel. The news/social audits reproduce existing feature joins but contain zero qualified historical source-version or arrival records under their strict contract. These are measured evidence gaps that bound the retrospective information set.


## 10. 技術文件與人工／同儕審查紀錄移至補充檢查，正文僅保留推論限制

**E9a 原段落**

> This draft has been checked computationally for source consistency and visually for document rendering. It has not undergone independent human scientific replication, institutional legal review or peer review. Citation metadata verification does not certify every inference in a cited paper. Faculty review, author confirmation and venue-specific formatting remain necessary.

**E9b 修訂段落**

> The market population consists of two prominent stocks, and 2024–2025 has been repeatedly inspected. Local correction families address their stated contrasts rather than the full research history. The supplementary controls use fixed candidate settings, including high-dimensional Logistic and the two original tree architectures; results are conditional on those model classes and budgets. Five seeds quantify computational stability, while quarterly updates and overlapping returns limit independent information. The displayed intervals leave relevant effects unresolved. Larger historical populations, matched stronger price baselines and true unseen validation are needed for broader predictive claims.


## 11. 凍結／登錄行政沿革移S6；正文提出由結果支持的具體比較

**E9a 原段落**

> The E7a document is a frozen candidate protocol, not an externally registered or executed confirmation study. Its six H1/H3 controls include strong P, matched metadata and redundant-price inputs, and late fusion against same-weight shrinkage, independently tuned shrinkage and the best single branch. Nondegenerate weights are required for a complementarity claim. These controls should be retained and audited before a future test, rather than selected for their already-viewed performance.

**E9b 修訂段落**

> For future work, the most informative comparison is a modest, fixed price/metadata/accounting design combined with separately tuned constant shrinkage and a prior-selected component benchmark. New sources should enter through a versioned information contract. Sample planning must reflect repeated quarterly updates and shared market shocks; the development variance diagnostics provide an initial scale, while broader dependence and power require a larger historical universe [R24, R31]. Preregistration then turns these exploratory mechanism checks into a focused unseen-sample assessment [R25].


## 12. 結論改為回答表示、收縮、初始化與新聞訊號的實際結果

**E9a 原段落**

> Adding information sources and model complexity to financial prediction can improve a reported probability score without establishing incremental predictive information. We audit an existing sequence of exploratory studies of AAPL and TSLA, distinguishing next-day return magnitude from five-session reversal prediction and separating three noninterchangeable cohorts. In the technical-indicator study, none of eight primary feature contrasts satisfies both source-stage multiplicity-adjusted inference procedures. In the fundamentals study, none of eight information contrasts or twenty fusion contrasts satisfies that joint standard. Apparent improvements in two AAPL neural-price late-fusion pipelines are substantially reproduced by matched-weight constant-probability controls, without reliable remaining complementarity. In a separate, retrospectively reconstructed Apple Newsroom cohort, sentiment augmentation improves event Brier score by 0.022569, but its primary adjusted bootstrap p-value is 0.1512. A significant secondary hierarchical-probability contrast is sensitive to timing assumptions and does not establish within-state event ranking. We retain a significant secondary direct-up result whose fusion weight discards the price expert, rather than treating it as complementary fusion. Finally, financial-document and news/social provenance audits distinguish downloadable artifacts from qualified historical versions and delivery evidence; the latter remain unavailable under the project's strict gates. The contribution is an evidence-linked audit and validation design, not a new forecasting architecture, a causal decomposition, or an independently confirmed rejection of non-price information. Licensed version evidence, matched information controls, dependence-aware power assessment, and genuinely unseen validation remain necessary.

**E9b 修訂段落**

> The experiments show why the source of a financial prediction gain matters. Technical-feature overlap is substantial but its forward reconstruction is unstable. Fundamental fusion changes concentration and calibration, and its raw advantage over constant shrinkage is negative in all ten archived settings. The new matched-input and sequential-allocation controls distinguish numerical content from representation and initialization. In the news study, publication density reproduces most of the total point change, while the smaller sentiment contribution varies with source density and timing.


## 保留而非刪除的必要限制

2024–2025重複探索、兩股及季度更新依賴、原H1/H3校正結果、新聞次要顯著與時間敏感度、原直接方向F-only結果、PIT歷史版本缺口及2026誠信揭露均保留。新增C6的正向結果、冷啟動位置與block120敏感性一併呈現。原始效果量、p-value及CI無改寫。
