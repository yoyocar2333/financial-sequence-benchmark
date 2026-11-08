"""Render E7a design documents, not a model training or registration command."""
import json
from pathlib import Path
import pandas as pd
from e7a_development_audit import OUT,dump,sha
from e7a_literature_catalog import WORKS

def write():
    contrasts=[
      ('C1','H1','Early_PMF','Early_PM_zero_padding','Numeric fundamentals beyond availability metadata'),
      ('C2','H1','Early_PMF','Early_PM_duplicate_P','Numeric fundamentals beyond duplicated representation'),
      ('C3','H1','Early_PMF','strong_P','Improvement beyond a strong price baseline'),
      ('C4','H3','Late_PF','same_weight_constant_blend','Complement beyond identical-weight shrinkage'),
      ('C5','H3','Late_PF','independently_tuned_constant_blend','Complement beyond optimized shrinkage'),
      ('C6','H3','Late_PF','development_selected_best_single','Complement beyond selecting a single expert')]
    pd.DataFrame(contrasts,columns=['comparison_id','hypothesis','candidate','reference','interpretation']).to_csv(OUT/'tables/primary_contrast_matrix.csv',index=False)
    protocol={
      'version':'E7a-design-candidate-1.0-20261106','status':'NOT_EXTERNALLY_REGISTERED_NOT_EXECUTED',
      'registration_gate':'Data, sample manifest, inference calibration and power must pass before a final timestamped external registration. No performance-dependent amendments.',
      'scope':['H1_information_increment','H3_complementarity'],'H2_primary':False,
      'seeds':[42,43,44,45,46],'selection_seed':42,'sequence_length':60,
      'information_cutoff':'17:00 America/New_York on trading session t; market finalization and each source clock must be verified; source not actually available is excluded',
      'entry':'next trading session official opening auction, with tradable corporate-action wealth accounting',
      'exit':'session t+5 official close; delisting/merger settlement follows frozen corporate-action policy',
      'target':'1{sign(log(C_t/C_t-5))*log(wealth_t+5/entry_open_t+1)<0}; past flat excluded, future flat=0',
      'secondary_target':'1{future executable wealth return >0}; no separate winning claim without secondary correction',
      'primary_population':'all eligible dates, not only price extremes; event-only results secondary',
      'features':{'P':'E5 T51 feature definitions, audited point-in-time market inputs; 60-day common information window',
        'M':['release_age_days_clipped180','7_numeric_missing_flags','4_source_quality_indicators_SEC_original_issuer_original_licensed_asreported_arrival_certified','4_predefined_industry_indicators'],
        'F_values':['revenue_yoy','eps_yoy_symmetric','gross_margin','net_margin','operating_margin','cfo_margin','cash_asset_ratio'],
        'F_expert':'M + seven numeric values + reference_sign; latest daily vector, explicitly lower-dimensional',
        'duplicate_controls':['past5','past20','past60','past120','RV5','RV20','Close'],
        'news':'Excluded from initial confirmatory module: current retrospective corpus lacks strict historical PIT; future separately registered module only',
        'analyst_expectations':'Excluded unless licensed historical received-time vintages pass a separately frozen module; never synthesize surprise'},
      'primary_architectures':['logistic','xgboost','lightgbm'],
      'primary_selection':'One common architecture and config index selected using only nested pre2023 development, lowest P-only development Brier across the fixed architecture/config grid. Same selected architecture/config for C1-C3, no test architecture winner.',
      'candidate_grid':{'logistic':[{'C':v} for v in [.001,.01,.1]],
        'xgboost':[{'max_depth':d,'min_child_weight':m,'reg_lambda':l,'learning_rate':r} for d,m,l,r in [(2,20,10,.03),(3,30,20,.03),(4,50,40,.02)]],
        'lightgbm':[{'num_leaves':d,'min_child_samples':m,'reg_lambda':l,'learning_rate':r} for d,m,l,r in [(4,40,10,.03),(8,60,20,.03),(16,80,40,.02)]]},
      'nested_development':{'outer_eval':['2017-2018','2019-2020','2021-2022'],
        'outer_fit_ends':['2016-12-31','2018-12-31','2020-12-31'],
        'inner_eval':'two calendar years immediately before each outer start; train through preceding year, last half of preceding year reserved for stopping',
        'outer_role':'Evaluate selection procedure without using that outer outcome to select its own forecast; final fixed choice uses all pre2023 forward folds only',
        'tree_round_cap':300,'tree_patience':25,'stop_min_delta':1e-5,'tie_break':'lowest architecture order then config index; no score within 1e-6 distinguishes ties'},
      'late_expert':'Logistic M+F values, three C candidates on same development dates; one common F expert for all price architectures',
      'alpha_grid':[0,.25,.5,.75,1],
      'alpha_selection':'pre2023 OOF Brier only, tie smallest alpha; tuned shrink alpha independently uses exactly same grid/budget',
      'constants':'Beta(1,1) training prior and same calibration-period prior are reported; matched and tuned blends use common training prior, not test mean',
      'conditional_prior':'Beta shrinkage to training prior, strength20, cells reference_sign x train-median VIX; thresholds train-only, no H2 regime fitting',
      'calibration':{'primary':'fixed monotone ridge Platt', 'objective':'sum binary log loss +20*((slope-1)^2+intercept^2)',
        'slope_bounds':[0,3],'intercept_bounds':[-5,5],'probability_clip':1e-6,'initial_parameters':[1,0],
        'equal_budget':'each complete pipeline calibrated independently with same dates and objective; constants use same calibration dates as comparator',
        'raw':'retained fixed secondary factorial, never choose raw vs calibrated on test'},
      'final_fit_candidate':'After final registry only: fixed config and pre2023-derived median stopping iteration refit2012-2024; fixed calibration2025 only. No new config/weight/feature selection using2024-2025. No fits in current E7a.',
      'purge':'label exit must stay in its partition; additionally exclude last20 trading dates of all development/fit/calibration/test blocks; history can precede block but not use future values',
      'primary_forecast':'mean probability of five seeds; seed-loss distribution secondary, seeds never independent observations',
      'primary_metric':'issuer-equal mean of date-paired Brier loss difference, positive=candidate better; within issuer dates equal weighted',
      'primary_contrasts':[dict(zip(['id','hypothesis','candidate','reference','meaning'],r)) for r in contrasts],
      'multiplicity':'two-sided Holm across exactly six primary contrasts, alpha .05; H1 requires C1-C3 all positive corrected; H3 requires C4-C6 all positive corrected plus interior alpha',
      'SESOI_absolute_Brier':.001,'planning_target_Brier':.0025,
      'inference_candidate':{'primary':'resample issuer histories and synchronized calendar blocks, 20000 centered studentized bootstrap replicates; validate null size before registration',
        'block_sessions':120,'sensitivity_blocks':[60,250],'seed':20261106,
        'sensitivity':'calendar cross-sectional mean HAC120 and two-way issuer/calendar-quarter cluster SE; small-time-cluster caveat',
        'gate':'Realistic development-only null/coverage simulations at nominal .05: 2000 or more replicates; reject method if type-I upper95% binomial bound >.075. If fail, revise and register before independent period, never after its scores.'},
      'secondary_metrics':['LogLoss','ROC_AUC','BalancedAccuracy_at_.5','MCC_at_.5','ECE10_fixed_bins','calibration_slope_intercept','within_existing_state_AUC'],
      'secondary_rules':'Holm within all reported secondary model-pair score contrasts; event/state and individual stock plots descriptive; no secondary finding rescues a failed H1/H3',
      'universe_candidate':{'asof':'2025-12-31','stocks':200,'strata_SIC2digit_ranges':[[10,19],[20,39],[40,59],[70,89]],'per_stratum':50,'max_per_SIC2':20,
        'eligibility':'US primary common stock, asof price>=5 USD, preceding60-session median dollar volume>=1e6, >=250 past price observations and >=4 historical reports; licensed inactive and corporate-action coverage required',
        'sampling':'sort SHA256(20261106|CIK) within strata, fill50 subject to SIC2 cap, freeze complete eligible pool before outcomes; no forced AAPL/TSLA inclusion',
        'manifest_status':'NOT_YET_OBTAINED; no claim of an existing200-stock dataset','attrition':'retain eligible exits/delistings and settlement; no replacement using future performance'},
      'independent_period_candidate':{'start':'2027-10-01','end':'2031-09-30','quarters':16,'lock_deadline':'2027-09-15',
        'warmup':'2027 pre-start price history >=180 sessions; no2026 label or price context needed',
        'predictions':'daily append-only hashes and source-receipt ledger; custodian seals outcomes until maturity/end; all fixed models evaluated once',
        'power_gate':'all six contrast variances and dependence estimated using >=100 development issuers and >=40 calendar quarters; worst plausible scenario must give joint80% power for planning target, else not ready',
        'if_gate_fails':'do not start this candidate; publish new prospective dates/design before unseen outcomes, no outcome-dependent extension'},
      'data_gates':{'PIT_eligible_used_records':'100% traceable original accession/version/timezone, no unverifiable backfill',
        'numeric_cells_coverage_per_corefield':.80,'daily_primary_availability':.90,
        'manual_stratified_document_sample':200,'critical_clock_or_revision_errors_allowed':0,
        'noncritical_numeric_agreement_min':.99,'market_action_return_reconciliation_min':.999,
        'data_missingness_policy':'train-only imputation and common missing flags; report exclusions, never encode absent data as absence of economic event'},
      'E3c_2026':'UNCHANGED_NOT_EXECUTED_NOT_EXTENDED_TO_E6_E7',
      'known_exposure':'2024-2025 repeatedly reviewed; earlier2026 news aggregates and E6 search snippets containing actual earnings headline figures incidentally seen; not zero-exposure claim',
      'current_execution':'CPU audit, old pre2023 fixedconfig predictions, synthetic controls, no new financial fit; no large search, no2026 validation'
    }
    dump(OUT/'protocol_candidate.json',protocol)

    docs={}
    docs['E7A_RESEARCH_DESIGN.md']='''# E7a：資訊增量與融合互補性的論文研究設計

日期：2026-11-06。範圍：H1與H3；H2延後。本階段完成設計、來源稽核、開發期變異量分析與合成方法控制，新增金融模型訓練數為0。

## 1. 結論先行與研究定位

目前證據支持「必須分辨資訊增量、校準、收縮與表示效果」這項研究需求，尚未支持「新聞或基本面已穩定提升反轉預測」的結論。最有機會形成論文的貢獻，是具有來源版本稽核與強控制的**增益歸因實證基準**，而非另一個融合演算法或Mamba優越性宣稱。外部未檢視樣本與跨股票PIT資料仍欠缺。

本套文件是正式預分析方案的候選版本，**尚未向外部註冊平台提交，尚未執行確認性實驗，也尚未通過資料／功效啟動門檻**。GitHub版本紀錄保存承諾，但不等於完成外部預註冊。[協定](PREREGISTERED_EVALUATION_PROTOCOL.md)與[機器可讀版本](protocol_candidate.json)一併提供。

## 2. E0–E6證據重整

|階段|核對結果|可以支持的論述／限制|
|---|---|---|
|E0|Naive記錄MAPE：AAPL 0.6766%、TSLA 2.6378%|早期單月表格，未重跑；不是後來的反轉任務|
|E1–E2|五seed MAE：AAPL .794984722→.791656808；TSLA 1.847153691→1.845582152|隔日幅度、501共同日、batch8；微幅改善未形成校正後證據|
|E3a|98個宣告主要比較中，主規格可評估48列，通過0列|稀疏事件與重疊使「普遍反轉」無法成立；不是98個獨立市場|
|E3b|5日Brier、block20：正向且兩項校正通過0/102|四架構與A/B比較；不能由單一排名推論架構優勢|
|E3c v1.1|事件Brier＋同狀態排序聯合標準0/8|整體AUC可能只反映不同狀態平均機率|
|E4a–b|52摘要、36Gemini；回溯重建448篇Apple 2023–25|來源偏向企業自有新聞；回溯全文非已證明歷史PIT|
|E4c|65個2025事件；P→S Brier改善 .022569222，Holm bootstrap p=.1512；S→T反而惡化 .001248221|未顯著；價格模型校準差與密度資訊均可能解釋表面增益|
|E5|8個主要技術特徵增益聯合檢定0/8|技術指標多為價格的確定性轉換；T另加QQQ，須拆解來源|
|E6|反轉H1 0/8、H3 0/20；同狀態排序0/112|118個財報版本均尚不具E7嚴格PIT資格；不等於證明基本面無價值|

來源、分母與限制逐列存於[證據帳本](tables/research_claims_ledger.csv)，原檔雜湊存於`audits/evidence_source_hashes.json`。E0是封存記錄；E3a有不可評估比較；E4c僅2025；E3b/E5/E6為482共同日，不能直接混合效果量或平均p值。

E6值得追查的數字：AAPL LSTM Late Brier改善 .004205（原CI −.003878至.011585），Mamba改善 .004487（−.001104至.009600）；相同權重常數控制後只剩 .000980與.001198。這是機制診斷，不是73–77%已被因果識別為收縮。直接上漲任務一項顯著比較來自捨棄弱P、F權重=1，不能當作融合互補。

## 3. 為什麼舊結果不足以辨識新資訊

新增資訊可能改變：(a)條件期望本身；(b)同資訊的有限樣本表示／正則化；(c)過度自信的校準；(d)缺失與資料覆蓋metadata；(e)選模與重複檢視偏誤。Brier變低無法單獨識別其中哪一項。

同一條季度數字被沿用60個交易日，不會變成60個獨立基本面事件。五seed共享相同標籤；多股票共享市場衝擊。2024–2025被多階段反覆檢視，即使各階段內做Holm，也不能恢復整個研究過程的獨立性。E6的227/460校準斜率為負更提醒：固定校準器可能翻轉排序，校準成績不等於原模型辨識能力。

## 4. 新控制設計與本輪實作

H1要求數值基本面同時勝過P+metadata、等維重複價格控制與強P；H3要求Late同時勝過同權重常數收縮、獨立調權重收縮及開發期選定最佳單模型。六項比較共同Holm校正；不能只選有利一項。價格技術表示不是外部新資訊，新聞／分析師資料未過PIT閘門就不進主試驗。

合成測試提供兩個反例：純收縮可把Brier約 .250876降到 .227938，完全沒有新資訊；重複價格訊號也能勝過過度收縮的常數混合。此為已知平方損失性質的教學／設計驗證，不是新定理或市場實證。[控制圖](figures/method_control_counterexamples.png)。初稿5比較因新增重複價格控制而修訂為6，舊功效表保留在`drafts/`，原因記錄於`audits/protocol_design_amendment.json`；此時未註冊、未產生新市場測試預測。

本輪功效使用既有config0、seed42、固定50/50之2017–2022前向CV預測，沒有選擇效果最好的權重。每一比較只有兩股×24個季度；288列包含模型與比較重複，並非288獨立事件。市場輸入副本實際只到2022年。[功效文件](STATISTICAL_POWER_ANALYSIS.md)顯示，目前不足以宣稱200股票即有足夠功效。

## 5. 執行順序與交付

先做20公司來源／時鐘原型；再取得至少100公司×40開發季度的真PIT面板，量測六項比較的變異與檢定尺寸；之後才凍結候選200股、16未來季度方案並外部預註冊。新獨立驗證候選為2027-10至2031-09，並非已承諾或已具功效的研究。資料閘門失敗即停止，不事後延長看成績。

E3c的2026固定協定保持不變，未執行，也不加入E6/E7。過去意外看過部分2026新聞彙總，以及E6搜尋片段中的實際財報標題數字；不能宣稱零接觸。E7另須真正未檢視的資料與存取管理。

文件索引：[文獻](LITERATURE_REVIEW.md)、[缺口與貢獻](RESEARCH_GAP_AND_CONTRIBUTIONS.md)、[資料與PIT](DATA_FEASIBILITY_AND_PIT_AUDIT.md)、[功效](STATISTICAL_POWER_ANALYSIS.md)、[協定](PREREGISTERED_EVALUATION_PROTOCOL.md)、[論文架構](PAPER_OUTLINE.md)、[重現](REPRODUCIBILITY.md)。
'''
    docs['LITERATURE_REVIEW.md']='''# 相關研究：結構化快速證據回顧

## 1. 回顧方法與可核查範圍

截至2026-11-06，以核心作者／方法為種子，透過web搜尋、出版社與作者原始頁核對，分成金融ML、基本面、技術表示、文本、融合、概率、資料探勘、推論、時間分割與研究設計。納入41個不同作品；作者稿與期刊版本只算一次。收錄方法關聯與不可外推限制，見[literature_evidence_map.csv](tables/literature_evidence_map.csv)；12組主題搜尋記錄見[literature_search_log.csv](tables/literature_search_log.csv)。

這是有結構的快速回顧，不是完整PRISMA系統性回顧或meta-analysis；沒有訂閱資料庫可匯出的完整命中集合，不虛報搜尋總數或全部全文讀完。排除投資部落格、二手未核對引述、reddit與仿冒出版社網域。FinBERT、Mamba與Frazier等的本次來源為preprint／論文稿，不能一概標示為已同儕審查。

## 2. 金融ML與強基準：效能必須限定任務

Gu、Kelly與Xiu以大規模橫斷面資產訂價展示機器學習的研究價值，但其月度風險溢酬任務、股票數量與本案兩股5日事件分類不同。Welch與Goyal提醒樣本外穩定性及歷史平均基準的重要性。兩者共同支持擴大樣本與強比較設計，並不保證本案神經模型優勢。[L01](https://doi.org/10.1093/rfs/hhaa009)、[L02](https://doi.org/10.1093/rfs/hhm014)。

技術分析可以被形式化檢驗，但已知價格的確定性轉換並非新資訊集；資訊相同仍可因表示與有限樣本正則化改變預測。大量規則搜尋會產生data snooping，故E5負面結果與規則選擇歷程都應保留。[L06](https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00265)、[L07](https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00163)。

## 3. 基本面與新聞：研究動機不等於本任務證據

Piotroski的歷史財報訊號、Bernard與Thomas的盈餘公告後漂移，以及Novy-Marx的毛利獲利能力，提供基本面有經濟意義的動機。然而價值股策略、公告反應及中長期橫斷面溢酬，不是已證實的AAPL／TSLA短期反轉。必須區分真實公告版本、首次可得時點及分析師預期；沒有歷史預期便不能把EPS年增率叫作surprise。[L03](https://www.ivey.uwo.ca/media/3775523/value_investing_the_use_of_historical_financial_statement_information.pdf)、[L04](https://doi.org/10.2307/2491062)、[L05作者稿](https://www.nber.org/papers/w15940)。

Tetlock研究媒體語調，Loughran與McDonald強調金融語境，FinBERT提供文本編碼方法。這些研究不表示企業自有Newsroom代表完整市場新聞，更不證明情緒分類器的準確率能轉為股價概率增益。回溯取回內容、現代編碼器與生成模型也可能帶入版本或預訓練污染。[L08](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2007.01232.x)、[L09](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2010.01625.x)、[L10](https://arxiv.org/abs/1908.10063)。

## 4. 融合與校準：最接近本研究的已知方法

組合預測從Bates與Granger開始，簡單平均與估計權重不確定性已有長期研究；Wang、Hyndman、Li與Kang的綜述涵蓋逾50年。Frazier等進一步指出某些組合比較的檢定可能有非標準分布／功效問題。**Early／Late Fusion與凸組合本身沒有方法新穎性**。[L11](https://doi.org/10.1057/jors.1969.103)、[L12](https://onlinelibrary.wiley.com/doi/10.1111/j.1468-0084.2008.00541.x)、[L13](https://www.sciencedirect.com/science/article/pii/S0169207022001480)、[L14 preprint](https://arxiv.org/abs/2308.05263)。

Proper scores及Brier的可靠度／解析度分解是既有理論；校準可改善概率卻不增加排序資訊。分箱分解帶有估計誤差，不能直接稱為新資訊的無偏度量。E7將raw與同預算校準結果分開，加入metadata、重複特徵及不同收縮控制；這是針對具體金融資料的識別設計，不是發明校準。[L15](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf)、[L16](https://journals.ametsoc.org/abstract/journals/apme/12/4/1520-0450_1973_012_0595_anvpot_2_0_co_2.xml)、[L17](https://icml.cc/Conferences/2005/proceedings/papers/079_GoodProbabilities_NiculescuMizilCaruana.pdf)、[L18](https://proceedings.mlr.press/v70/guo17a.html)。

## 5. 選擇偏誤、相依性與驗證

White Reality Check、Hansen SPA及Romano–Wolf處理搜尋與多重推論；Harvey等及PBO文獻提醒未記錄的研究選擇不能只靠最後一張p值表補救。E0–E6跨階段重複檢視使2024–2025仍屬探索性，即使每階段內已校正。[L19](https://onlinelibrary.wiley.com/doi/10.1111/1468-0262.00152)、[L20作者稿](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=264569)、[L21作者稿](https://users.ssc.wisc.edu/~behansen/718/RomanoWolf2005.pdf)、[L22](https://doi.org/10.1093/rfs/hhv059)、[L23作者稿](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)。

成對預測損失、HAC與區塊bootstrap具有理論基礎，但須遵守各自條件。公司內季度持續與同日市場衝擊需同時處理；增加股票數不能消除共同時間風險。一般DM常態或任意bootstrap不能保證嵌套、退化融合或少季度下有效。[L24](https://doi.org/10.1080/07350015.1995.10524599)、[L25](https://onlinelibrary.wiley.com/doi/10.1111/j.1468-0262.2006.00718.x)、L26–L29。

選模本身可以過擬合；前向nested切分、訓練期預處理、標籤purging及一次獨立驗證是不同層次的必要控制。某些純AR條件下K-fold成立的結果，不能直接套到本案重疊標籤／非平穩面板。[L30](https://www.jmlr.org/papers/v11/cawley10a.html)、[L31](https://onlinelibrary.wiley.com/doi/10.1111/ecog.02881)、[L32作者稿](https://robjhyndman.com/papers/cv-wp.pdf)。

## 6. 近年研究與真正最近鄰

Kelly、Malamud與Zhou（2024）說明同資訊下複雜表示與收縮可能有效；Jiang、Kelly與Xiu（2023）用價格圖形學習趨勢；Chen、Pelger與Zhu（2024期刊卷期，2023 online）以深度模型融合公司／總體資訊估資產訂價。這些是本案「複雜度沒有自動優勢」的重要邊界：有限兩股負面結果不能否定更廣的複雜度文獻。[L37](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13298)、[L38](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13268)、[L39](https://pubsonline.informs.org/doi/abs/10.1287/mnsc.2023.4695)。

Missing Financial Data（2025期刊卷期，2024 online）已將基本面缺失與樣本選擇當作核心問題；本案不能把missingness有資訊稱為新發現。FinMultiTime（2025作者preprint）已提出跨股票價格／新聞／財報表格／圖形的多模態資料；因此多模態benchmark本身亦非空白。本文較窄的候選貢獻是結合真PIT版本鏈與metadata、重複表示、校準及多種收縮控制的實證稽核。這不是已證明從未有人做過的組合，仍須最近鄰全文比較。[L40](https://doi.org/10.1093/rfs/hhae036)、[L41](https://arxiv.org/abs/2506.05019)。本輪沒有下載FinMultiTime，也未認證其逐筆時鐘、修訂或原始資產授權，不能將作者宣告的規模當作本專案已取得的合格PIT資料。

## 7. 功效、等效性與尚待補齊的文獻工作

樣本量需由效果大小、精確度與限制辯護；大p值不證明無效。若要主張效果小於有意義範圍，應事先定義等效界線並設計等效推論。預註冊用來區分生成假說與確認，而非回溯漂白歷史樣本。[L33](https://pure.tue.nl/ws/files/214011492/collabra_2022_8_1_33267.pdf)、[L34](https://pmc.ncbi.nlm.nih.gov/articles/PMC5502906/)、[L35](https://doi.org/10.1073/pnas.1708274114)。

投稿前仍須用學校可取得的WoS／Scopus／EconLit做可匯出的完整檢索，向前／向後追蹤最接近的「financial multimodal incremental value + metadata + shrinkage controls」實證，核對全文、2025–2026新進展與preprint出版狀態。現有回顧不支持「從未有人做過」的主張。以下為全部收錄書目；每列的閱讀深度與限制可查CSV。

'''+ '\n'.join(f'- **{i}** {c} [原始／作者來源]({u})。{lim}' for i,t,c,u,n,lim in WORKS)+'\n'
    docs['RESEARCH_GAP_AND_CONTRIBUTIONS.md']='''# 研究缺口、貢獻與主張邊界

## 1. 可以提出的問題

多模態金融預測常同時改變資訊來源、特徵維度、缺失旗標、模型容量、調參預算與校準。若只比較P與P+F的Brier，效果無法歸因。真正的缺口候選是：在可驗證的來源時點與公平預算下，對短期反轉概率增益進行**可重現、預先承諾的歸因稽核**。這是特定實證設計的定位，不宣稱融合、收縮、PIT或proper scoring是新方法。

已存在FinMultiTime多模態資料、價格圖形表示、基本面缺失與複雜度研究（文獻L37–L41）；不能以「首次融合新聞與財報」或「發現缺失有訊號」定位。具體控制組合的最近鄰全文比較仍待補齊。

## 2. 三項可形成貢獻的工作

|貢獻候選|現在具備|尚缺的證據|
|---|---|---|
|資訊／表示／metadata／校準分離的基準|E0–E6帳本、六對照、合成反例、PIT資料契約|同一跨股票真PIT面板上的實驗與獨立驗證|
|融合互補而非向平均收縮的檢驗|同權重與調好權重收縮、最佳單模型及退化權重規則|足夠季度與公司叢聚、有效檢定尺寸及正向精確CI|
|透明的負面證據及資料稽核|完整失敗／未顯著結果、來源限制、2026接觸揭露|可公開的資料生成流程、外部重現與較廣市場外推|

最有機會的主線是第一項與第二項結合的實證方法基準。即使未來結果為零，只要CI足夠精確、資訊可得與控制嚴格，也能提供有意義證據；目前的「未顯著」還不具有這種排除能力。

## 3. 現有結果允許與不允許的表述

- 可寫：在指定兩股、候選預算、已檢視期間中，主要新聞／技術／基本面增益未取得校正後穩定支持。
- 可寫：E6表面Late改善的大部分可被特定常數控制重現，顯示必須檢查收縮；不是因果分解比例。
- 可寫：某些較高整體AUC沒有同狀態排序支持；但粗分狀態也可能殘留混雜。
- 不可寫：基本面／新聞完全沒有資訊、Mamba不適合金融、模型學會因果機制，或所有投資者規則均無效。
- 不可寫：單一顯著的直接上漲弱基準比較證明了反轉任務H1或H3。
- 不可寫：目前118個回溯財報版本已嚴格PIT，或已完成E7預註冊／確認性驗證。

## 4. 原設計的主要識別問題與修正

P+F除了數值還新增age／missing flags：比較P+M+F與P+M；技術指標為價格轉換：加等維重複價格控制；Late可能捨棄壞P：加最佳單模型且要求內部權重；校準器可能反向：固定單調校準、raw並列；QTY更新很少：按公司／日曆時間處理相依，報獨立申報版本；反覆探索：使用全新未檢視樣本，不以事後Holm漂白。

這些控制仍不建立因果資訊價值。數值F可能代理遺漏的價格歷史或企業類型；「同維」也不等於「同有效自由度」。結論應限於固定可得資訊與模型類別下的增量預測證據。主張外部新資訊時還須報條件殘差診斷、metadata來源差異及重複表示敏感性。

## 5. 論文成熟度

目前適合形成透明的探索性研究／方法稽核工作論文；投稿機率不能由本次工具作業保證。完成一篇較有說服力的實證論文，至少還需：嚴格PIT與授權、跨股非存活者偏誤面板、對六比較都適用的功效設計、檢定尺寸驗證、外部註冊與真正未檢視結果，以及全文層級的最近文獻比較。先補資料及識別，不再增加架構是資源最合理的下一步。
'''
    docs['DATA_FEASIBILITY_AND_PIT_AUDIT.md']='''# 跨股票資料可行性與Point-in-Time稽核

## 1. 本地實際持有與嚴格資格

本地E6有AAPL 60、TSLA 58個季度版本，發布日範圍分別2011-01-18至2025-10-30、2011-08-03至2025-10-22。SEC acceptance、修訂時點、歷史first-seen與版本證明欄均未補齊；按新主研究契約，**0/118具嚴格PIT資格**。[實際表](tables/current_pit_readiness.csv)。這不表示118份內容都是錯的，而是未取得其當時可得版本與時鐘證明。原先+2／+5交易日只能作延遲敏感性，不能認證PIT。

AAPL早期20季部分指標來自四捨五入摘要；TSLA各項缺失不同，EPS成長與CFO尤其稀疏。各年七欄覆蓋存於[current_fundamental_field_coverage.csv](tables/current_fundamental_field_coverage.csv)。目前只兩股，不能宣稱完成跨產業資料集。E4重建448篇也不能替代市場完整新聞；FNSPID日期精度與年份缺口已稽核，不能直接塞入主比較。

## 2. 來源調查與授權判斷

|來源|合理用途與限制|目前取得狀態|
|---|---|---|
|SEC EDGAR原申報／FSDS|公開原始申報、XBRL與accession；須逐文件重建原始值及修訂鏈，API彙整值本身不認證歷史快照|本工作站先前原始API回403；本輪只核對官方方法文件，沒有繞過阻擋|
|Issuer IR|補官方原PDF／發布線索；現今頁面可能被改，date-only不足以判定盤前盤後|E6已取回；未有版本／時鐘鏈|
|CRSP US Stock／CCM|活躍與已退出股票、永久ID、公司行動／退市；正式訂閱資料較適合避免存活者偏誤|僅文件；未驗證校內權限|
|Compustat／S&P PIT|跨公司標準化財報及專門PIT產品；一般最新版fundamentals不自動等於PIT|僅文件；具體產品、欄位與修訂政策需授權確認|
|LSEG I/B/E/S PIT|歷史預期快照與時戳；須核對broker修訂／收到時間、EPS口徑與split調整|未取得授權資料，不製造surprise|
|FactSet PIT consensus|專門PIT歷史共識資料；日期級snapshot不一定足以同日17:00交易|未取得授權資料|
|Nasdaq Sharadar SF1|有datekey／dimension等篩選；as-reported、restated與lastupdated要分清楚，不能只看欄名推論版本完整|候選付費來源，未取得資料|

官方來源：[SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)、[SEC FSDS](https://www.sec.gov/files/fsds.pdf)、[CRSP](https://www.crsp.org/research/crsp-us-stock-databases-2025-layout/)、[S&P fundamentals](https://www.spglobal.com/market-intelligence/en/solutions/products/fundamental-data)、[LSEG量化資料說明](https://www.lseg.com/content/dam/data-analytics/en_us/documents/brochures/lseg-data-for-quant-research-brochure.pdf)、[FactSet PIT](https://www.factset.com/marketplace/catalog/product/factset-estimates-pointintime)、[SF1文件](https://data.nasdaq.com/databases/SF1/documentation)。以上僅證明供應商描述／可調查路線，沒有證明已購得、費率、特定股票年份完整或允許原始資料轉載。SEC是公開來源也不表示其附件中的所有第三方內容皆可任意再授權；公開以程式、雜湊、彙整結果為主。

## 3. 時間與版本資料契約

每項fact至少保留issuer永久ID、concept、期間起訖、單位、數值、accession、原文件SHA256、原申報acceptance raw字串與驗證時區、公開可得時點證據、retrieval時間、修訂連結。來源／標籤以UTC儲存並保留America/New_York與DST轉換；不能因JSON尾端Z就跳過與原header／index的時鐘交叉查核。

對原始SEC不可變文件，可建立「來源事件時點已認證」層級；這與「當時資料供應商收到時點已認證」不同。今日抓到的版本不能證明當年網站相同。新聞／分析師預期需歷史版本與provider_received時間；缺一即拒絕主比較。只知道日期者不臆測盤前盤後，移出主分析並可作另註冊的保守隔日敏感性。

as-of join只挑cutoff前已可得、同concept／period／unit的最新版本，後來修訂不可回填過往；現金流YTD轉季值、Q4年減前三季、EPS拆股與分母都要能回到同時可得資料。不可混用後來重編的分母算當年比率。價格使用當時原始價格／已生效公司行動，不用全歷史後調整絕對價格作嚴格PIT特徵。

## 4. 原型、閘門與資料不足時的處理

`e7a_pit_contract.py`實作fail-closed欄位與as-of版本邏輯；合成測試驗證修訂不回填、晚發布拒用、未知時區拒用與標籤越界拒用。這不是已建成的EDGAR下載／XBRL parser，也不能驗證供應商聲稱是否為真。未通過不能只把布林值設成True。

初步20公司×4產業原型後，至少100公司×40個開發期日曆季度估計六比較變異與依賴。啟動要求：使用的來源紀錄100%可追溯；每個核心數值至少80%原始可得覆蓋；共同日期至少90%可用；分層人工查200文件，重大時鐘／修訂錯誤0，其他數值一致≥99%，公司行動報酬對帳≥99.9%。這些是事先設定的品質閘門，未達即改為資料可行性論文，不依結果降低。

完整股票母體與抽樣manifest目前不存在。候選為as-of2025-12-31的200股、4大非金融SIC區間各50，固定雜湊排序與每SIC2最多20股；須包括後續退出、避免只用現存指數成分。金融業比率不可比，先明確排除而非宣稱全市場。新聞／預期沒過門檻不進初始確認性模組；之後新增來源需另註冊，不以缺資料當作無新聞／無預期。

## 5. 2026隔離

本輪不下載／計分2026金融資料。先前已有部分2026新聞彙總及E6搜尋片段中財報標題數字的意外接觸，完整性聲明不應寫成「從未見過2026」。E3c舊協定雜湊保持；E7需要另訂未檢視期與管理人／append-only來源、預測與存取帳本。
'''
    docs['STATISTICAL_POWER_ANALYSIS.md']='''# 統計功效、相依性與可偵測效果量

## 1. 實際輸入與估計單位

功效尺度只用既有E5 P的Logistic／XGBoost config0、E6 F Logistic config0、seed42、固定50/50之2017–2022前向CV。市場副本截到2022，未使用新的2024–2025效果選樣本量。每股票／模型有1450個CV日、24個季度；兩公司提供48個公司季度，但只有24個共同日曆季度。12個模型×比較cell合成288列不是288個獨立財報事件。季度平均損失可描述，但日曆季度不等於精確的財報發布事件；未來另以accession統計更新。

本輪量測日損失HAC lag0/5/20/60、季度lag0/1/2/4及兩股相關診斷，完整CSV在tables。兩股相關不能代表跨產業人口ICC。原CV是探索性開發資料，這裡只取變異尺度、不用其平均增益作預期效果。

## 2. 規劃模型與推導

令σ為季度成對平均Brier損失差的SD，J為股票數、Q為季度數。情境分解為共通AR(1)市場項、持久公司項及個別AR(1)項，變異占比ρm、ρi及φ皆為假設：

`g(Q,φ)=[Q+2 Σ(l=1..Q−1)(Q−l)φ^l]/Q²`

`Var(mean)=σ²[ρm*g + ρi/J + (1−ρm−ρi)*g/J]`。

獨立時回到σ²/(JQ)；共同市場項不隨J消失，公司持久項不隨Q消失。以t(Q−1)及Bonferroni6保守近似Holm6，單比較80% MDE=(critical+z.8)*SE。H1或H3三項皆成功的80%規劃以union bound令每項功效≥.93333，因此MDE=(critical+z.93333)*SE；不是把三個80%相乘或把seed當樣本。此近似沒有模擬實際估計SE的分布。

假設獨立／mild(.01,0,.3)／moderate(.05,.10,.3)／strong(.15,.15,.6)／stress(.30,.20,.6)，另σ×.5/1/2，股票20–400、季度4–40。參考σ=.0059531805226298為目前同權重收縮增量中四個cell的最大值，不是跨產業保守上界。

## 3. 結果與設計含義

|情境，200股票|12季度三項聯合80% MDE|16季度三項聯合80% MDE|
|---|---:|---:|
|完全獨立|.000572|.000478|
|中度相關|.002575|.002184|
|強相關|.005877|.005027|

以上只適用σ參考，不代表六比較整體已具功效。J200、改善.001時，獨立需6季、mild19季、moderate91季（22.75年）；strong／stress於200季搜尋範圍仍未達標。改善.0025時moderate需13季，strong66季。由此不能只建議「多抓幾檔股票」；時間共同衝擊與更新頻率才可能是瓶頸。[全部情境](tables/power_design_grid.csv)、[所需期間](tables/required_period_scenarios.csv)、[16季比較](tables/variance_stress_and_16quarter_candidate.csv)。

**最關鍵的限制**：F-vs-prior季度σ最大 .008295；強XGBoost總改善 .006330；弱高維Logistic總改善 .058850，約為本參考10倍。尚無真正Early(P+M+F)對P+M的CV變異量。因此不能把matched-shrink結果當作所有H1／H3的功效保證。條件校準、panel訓練與更廣股票也會改變σ。[變異適用範圍](tables/variance_reference_limits.csv)。

## 4. 模擬與穩健性

每情境20,000次已知SE高斯panel-mean模擬，固定6項Holm、效果0/.0005/.001/.0025/.005、比較間相關0/.5/.9；報H3末三項聯合成功率與Monte Carlo SE。[模擬表](tables/power_simulation.csv)。它檢查規劃算術，不是對實際雙向cluster／block bootstrap檢定尺寸的驗證；null下保守也不能保證真實資料中正確。

SESOI預先暫定絕對Brier .001，規劃目標 .0025（相對.25約1%）；此為研究價值門檻，非經濟獲利換算，也非由測試期最佳效果取值。若將來CI寬，結論應為不足以判別；若要排除|δ|≥.001需另按固定界線作多重校正等效檢定，不能把p>.05當作無資訊。

## 5. 可行方案與啟動條件

近期先完成20公司PIT原型，再取得≥100開發公司×≥40季度，估計每個主比較的σ與共同時間依賴，進行實際推論null／coverage模擬。候選確認樣本為200股×16未來季度；只有在六項比較都通過最壞合理情境joint80%規劃且檢定尺寸合格時才註冊。這不是目前已可執行的保證；若σ接近弱Logistic或強共同衝擊，四年仍不足，應縮小論文主張或改為精確度／方法稽核研究，不追逐更多模型。

![股票數與MDE](figures/power_vs_stocks.png)

![期間與MDE](figures/power_vs_years.png)

初稿5比較的功效輸出完整保留在`drafts/five_contrast_planning/`；正式候選採6比較。本文件所有主數字為6比較，原始開發變異表中`Bonf5`欄只屬初稿診斷，不能作本協定功效引用。
'''
    docs['PREREGISTERED_EVALUATION_PROTOCOL.md']='''# E7正式預分析協定候選 v1.0

**狀態：NOT EXTERNALLY REGISTERED／NOT EXECUTED。** 文件名稱遵循研究交付要求；尚無OSF登錄、外部受理編號或已取得的200股資料。這是2026-11-06凍結的設計候選。資料manifest、六比較功效及檢定尺寸通過後，才可另完成外部預註冊；不得將目前文件稱為已完成確認性註冊。[完整JSON](protocol_candidate.json)是參數清單，與本文件同時版本化。

## 1. 假說與主估計量

H1：在相同可得價格資訊與metadata下，真實基本面數值能改善5日反轉概率，且超過等維價格重複表示。H3：P／F融合提供超過收縮與最佳單一預測的互補。H2延後；不建立新的市場狀態專家或依測試挑子群。

主母體為所有合格交易日。每公司內同日期成對Brier差，再公司等權平均；正值表示候選較好。主概率為五seed(42–46)概率的平均，**不是五seed平均loss**；後者列次要穩定性。這是相對E6的明確估計量變更，不能直接用舊表當新實驗結果。急漲跌事件與既有狀態只作預先指定診斷。

## 2. 標籤與資訊時間

交易日t 17:00紐約時間凍結資訊；市場及VIX／VXN實際finalization若較晚則該日不合格。參考方向為過去5日收盤log報酬符號；在t+1官方開盤進入，t+5官方收盤退出，以可交易公司行動財富報酬R計算：`y_rev=1{sign(past5)*R<0}`。過去flat排除、未來flat非反轉。直接上漲`1{R>0}`為次要。

拆股／股利／退市／併購使用已知公司行動與實際結算；無退出價格不能默認0或刪除破產者，依預先凍結的資料供應商結算規則並揭露無法對帳案例。這部分新嚴格PIT價格管線尚須實作驗證；舊全歷史調整價格只是探索性代理。特徵每日as-of、修訂晚到不回填；缺失不等於經濟上沒有事件。所有partition要求標籤退出留在區塊內，另外統一刪最後20交易日；60日歷史可以跨區塊邊界，但只含已知值。

## 3. 資訊、基準與六項固定比較

P為E5 T51的價格、波動、既有多尺度與技術／QQQ定義，所有模型同60日可得序列。M為release age、七數值缺失旗標、四來源品質旗標、四事先固定產業旗標；企業ID不作可記憶的one-hot。F數值為營收YoY、對稱EPS YoY、gross/net/operating/CFO margin、cash/assets。當季與去年同季須各自在cutoff前可得；禁止後來修訂回填。

基準包含Beta(1,1)訓練先驗、同校準日期先驗、固定strength20的條件機率（reference sign×訓練中位VIX），強P、metadata-only、F-only、Early、Late、同權重常數收縮、獨立調權重收縮、最佳單模型。F expert使用低維最新數值＋M＋方向；其低維正則化優勢不能自動算新資訊。

|ID|假說|候選|基準|
|---|---|---|---|
|C1|H1|Early P+M+F|P+M＋七零填充欄|
|C2|H1|Early P+M+F|P+M＋七個重複價格欄|
|C3|H1|Early P+M+F|強P|
|C4|H3|Late(P,F)|同一α的P與訓練常數混合|
|C5|H3|Late(P,F)|獨立開發期調好α的常數收縮|
|C6|H3|Late(P,F)|開發期選定的最佳單模型|

重複欄固定past5/20/60/120、RV5、RV20、Close，不能依分數另選。C1／C2同寬但不假設有效自由度相同。Late `q=(1−α)P+αF`，α∈{0,.25,.5,.75,1}；收縮使用同一或獨立以相同grid調好的α，常數不取測試均值。H1需C1–C3全部正向且Holm6<.05；H3需C4–C6全部正向且Holm6<.05，另要求α在(0,1)。α=1只代表選到F，不能宣稱互補。

## 4. 校準與機制控制

所有完整pipeline採同日期、相同objective的單調ridge Platt：最小化sum logloss +20[(a−1)²+b²]，a∈[0,3]、b∈[−5,5]，初值(1,0)，概率clip1e−6。不能從測試選raw或calibrated；calibrated為主，raw固定次要。訓練median／scale與閾值每fold重估。常數基準也可取同校準期Beta先驗，與模型公平取得標籤。

原始未校準平方損失的精確式：若q0=(1−α)p+αc，則`L(q0,y)−L(q,y)=2α(f−c)(y−q0)−α²(f−c)²`。可報此機制診斷及raw/calibrated factorial；不同pipeline各自非線性校準後不再具有這個直接分解。式子不是新定理、不是因果資訊度量；synthetic顯示matched-shrink單一控制仍可能被duplicate-P通過。

## 5. 候選與時間序列選模

主要架構固定Logistic、XGBoost、LightGBM，每架構三候選，明列JSON；不做大規模搜尋。僅依P的前向開發Brier選一個強價格架構／config，再使用同一架構／config做全部Early與C1–C3，避免為每arm另給搜尋優勢。tree cap300、patience25；Logistic C=.001/.01/.1。F為Logistic同三C。Late／tuned shrink同五α、相同開發日期與預算。架構順序Logistic→XGB→LGBM，同分1e−6取前者／較小config，α同分取較小者。

開發outer eval固定2017–18、2019–20、2021–22；各outer之前最後兩年作inner eval，之前一年最後半年作stopping，其餘2012起資料fit。每outer的候選／權重只由inner決定，不能用該outer結果選自己的預測。最後配置僅用所有≤2022前向fold選定；nested outer用來估程序與功效，不把選後CV當全新確認。LSTM與真Mamba只作次要擴充，原3候選／60序列／小模型預算不加大；須公司數與季度支持、先通過資料／功效閘門，不以主檢定成績決定是否執行。沒有fallback，也沒有本輪新GPU訓練。

真正註冊後才可按固定配置在2012–2024 refit；迭代數取≤2022 inner-stopping選出之中位值，2025只依固定公式校準，不重新挑特徵、權重、架構、epoch或校準器。這是候選未來流程，E7a目前沒有執行這些refit／校準。

## 6. 樣本與一次獨立驗證

候選cohort為as-of2025-12-31合格美國普通股，SIC兩位區間10–19、20–39、40–59、70–89各50，共200；每SIC2最多20。股價≥$5、前60日median美元成交量≥$1m、≥250歷史價格與≥4歷史財報。依`SHA256(20261106|CIK)`排序抽樣，完整合格母體先凍結，不強制納入AAPL／TSLA；保留後續退出與結算，不依未來結果補股。需要授權的活躍／已退出與身分對照資料；**目前manifest未取得**。

候選一次未檢視期間2027-10-01至2031-09-30（16季度），鎖定期限2027-09-15。2027前期≥180交易日只作因果特徵warmup，不用2026金融資料、不用warmup績效選模。以每日append-only雜湊與存取帳本封存概率，標籤／績效由獨立管理人保管至預定期末；不得中途看分數停試或延長。預測失敗日不選擇性丟棄，主分析使用固定先驗fallback並報缺失率／原因，完整案例為敏感性。

須在註冊前通過資料品質、100開發公司×40季度、六項變異／功效與推論尺寸閘門。未過不能宣稱四年足夠；改設計後需在新的未檢視期之前另註冊。2027–2031只是一個可討論的長期候選，不承諾目前已有資源或適合畢業時間表。更近的獨立未見股票歷史庫須由他人持有、事先登記，可作外部橫斷面驗證但不能代替真正未來驗證；目前也尚未取得。

## 7. 指標、推論與報告規則

Brier為唯一主要score，LogLoss、ROC-AUC、Balanced Accuracy、MCC、固定10bins ECE與校準斜率／截距為次要，分類閾值.5。所有六對比共享日期。公司等權、日期配對；公司歷史及同步calendar blocks聯合resample，主block120、20,000 centered studentized replicates、seed20261106；60／250敏感性、跨公司日平均HAC120與公司／季度雙向cluster作對照。這個候選推論必須先用開發期真結構null／coverage模擬驗證，不能把任意雙重bootstrap當成已有定理。至少2000rep，nominal.05的型一錯誤上95%界> .075即不通過；改善方法須在註冊前完成。

主6比較雙尾Holm .05並同時要求正向，公布全部估計、未校正／校正p、CI與同時多重性限制。一般95% CI為pointwise，不能與校正p混稱同時區間；另報Bonferroni同時區間。SESOI=.001、規劃目標=.0025；無顯著且CI寬叫作不確定。等效性若啟動用事先±.001界線、Holm6之TOST，亦不等於經濟零效益。

次要模型／score成對比較按事先完整清單另Holm，不挽救失敗主假說；事件樣本<20或單一標籤AUC不作推論，狀態及個股結果描述，不挑最佳子群。Brier可靠度／解析度分箱只作描述，避免將有限樣本分解當資訊因果量。沒有交易獲利主張。

## 8. 版本、停止與完整性

保存原始版本、license、輸入SHA、抽樣manifest、每fold設定／preprocessing、所有候選概率、容器／環境、日誌與偏離。一次只一個GPU工作，任何GPU錯誤只停自己的工作；不改系統或舊環境。不依測試成功失敗換模型／刪股票／改標籤。

E3c2026協定原封不動；E6/E7不可事後加入。2024–2025已反覆檢視；先前部分2026新聞與財報標題資訊有意外接觸，不能稱為零暴露。E7獨立資料需另安排。本草案註冊前任何修訂保留理由與差異；註冊後可做工程修復，但必須揭露、封存舊版，不變更結果依賴的決策。
'''
    docs['PAPER_OUTLINE.md']='''# 論文定位與必要證據

## 1. 題目候選與主張

中文：**價格以外資訊，還是機率收縮？股票短期反轉預測增益的可重現稽核**。

英文：**Information or Shrinkage? Auditing Incremental Predictive Value in Short-Horizon Equity Reversal Forecasts**。

目前可寫的摘要應明示兩股探索性研究與PIT限制；未來完成跨股票PIT與一次外部驗證後，才能升級為資訊增量／互補性的確認性主張。不要把架構清單當學術貢獻，也不要因負面結果把摘要寫成所有市場皆無訊號。

## 2. 章節架構

1. Introduction：具體識別問題，H1與H3，既有研究與本文實證貢獻。
2. Related work：金融ML、會計／新聞、融合與校準、data snooping與PIT。
3. Data and information sets：來源版本、合法性、身分／公司行動、真實cutoff、缺失與更新頻率。
4. Identification by controls：P／M／F、等維重複、Early／Late、同權重與tuned shrink、最佳單模型；raw/calibrated區別。
5. Evaluation protocol：標籤、nested前向切分、功效、六對比、面板推論與獨立驗證。
6. Exploratory evidence：E0–E6重整，分母／任務清楚；E7a synthetic反例、資料未就緒與功效情境。
7. Prospective validation results：目前留空，未執行；不能用2024–2025填入確認性章節。
8. Discussion and limitations：預測資訊≠因果機制≠可交易利潤、跨公司／期間與授權外推限制。
9. Reproducibility and conclusion：可公開程式／彙整與受限原始資料的取得流程，結果若為零亦完整報告。

## 3. 必要圖表與目前狀態

|圖表|目的|目前是否具備|
|---|---|---|
|資訊cutoff／申報／修訂時間線|展示PIT與標籤無洩漏|規格已定，真跨股資料鏈未建成|
|E0–E6證據矩陣|避免任務與分母混淆|已具帳本CSV|
|兩種假增益合成反例|說明收縮／重複表示控制|已具method_control_counterexamples圖|
|股票數／季度數與MDE|解釋共同時間風險|已具2張功效圖；情境而非保證|
|跨公司來源與corefield覆蓋|排除取得／缺失metadata假訊號|現有兩股表；擴展尚缺|
|六比較forest plot＋同時CI|資訊增量與互補主要實證|未來實驗，現在不可製造|
|raw／calibrated／constant控制圖|區分校準與時機辨識|E6探索性已有；新面板未執行|
|一次未檢視結果與穩定性圖|外部可驗證性|尚未執行|

## 4. 投稿路徑與實際限制

International Journal of Forecasting的官方範圍包含預測方法、應用與評估，並公布data/code sharing policy；Journal of Forecasting亦涵蓋方法與應用。兩者可作定位參考，但「符合議題」是本研究判斷，並非收稿保證，不虛報排名、費用或Registered Reports接受政策。[IIF官方IJF](https://forecasters.org/ijf/)、[Wiley官方JoF](https://onlinelibrary.wiley.com/page/journal/1099131x/homepage/productinformation.html)。

可先完成探索性工作論文／資料與識別稽核稿，清楚分隔尚未驗證的主張；若要以實證增量論文投稿，主要缺口依序為PIT授權面板、真效應與推論功效、完整方法控制、真正未見結果、最近鄰文獻全文比較與外部重現。單純增加股票或再調Mamba不會填補這些缺口。長期未來研究可能超過大學專題時程，需與教授決定以方法稽核論文為近期成果或持續收集確認性資料。
'''
    docs['REPRODUCIBILITY.md']='''# E7a重現與稽核邊界

本階段沒有新的金融模型訓練、GPU工作、2026驗證或2024–2025選模。可公開重現：季度彙整輸入的功效算術、合成控制、PIT契約測試、文獻及主張帳本。不能僅靠彙整CSV重建全部舊模型、驗證vendor承諾或取得原始授權資料。

本地既有環境（不需安裝）：

```bash
.venv-e3b/bin/python -B scripts/test_e7a.py
E7A_OUTPUT=outputs/e7a_20261106 .venv-e3b/bin/python -B scripts/e7a_public_replay.py --bundle outputs/e7a_20261106 --output-dir outputs/e7a_replay_new
```

完整從既有開發期結果重算需原E5／E6受限輸入與固定CV檔：使用新的`E7A_OUTPUT`執行`e7a_development_audit.py`，再執行literature、evidence與write_design；不可覆寫已封存目錄。來源CSV副本只有≤2022，雖檔名保留through2025以相容舊loader。`audits/power_input_manifest.csv`記錄實際日期與SHA。公開版只帶季度彙整，不帶市場／新聞／checkpoint。

315份舊報告／結果／protocol成員由`protected_prior_artifacts.json`逐檔驗證；既有E3c2026協定不變。本輪設計初稿5對比與改成6的原因均保留。CPU測試涵蓋時鐘、版本修訂、重疊標籤、共同衝擊功效下界及假資訊增益反例；這些測試不是新市場訊號的證據。
'''
    for name,body in docs.items():(OUT/name).write_text(body.strip()+'\n')
    dump(OUT/'audits/final_design_document_hashes.json',{n:sha(OUT/n) for n in docs}|{'protocol_candidate.json':sha(OUT/'protocol_candidate.json')})
    return docs

if __name__=='__main__':write()
