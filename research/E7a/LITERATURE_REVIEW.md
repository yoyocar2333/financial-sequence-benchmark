# 相關研究：結構化快速證據回顧

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

- **L01** Gu, Kelly & Xiu (2020). Empirical Asset Pricing via Machine Learning. RFS33,2223–2273. [原始／作者來源](https://doi.org/10.1093/rfs/hhaa009)。月度風險溢酬，不是兩股5日反轉；不能直接移植其優勢。
- **L02** Welch & Goyal (2008). A Comprehensive Look at the Empirical Performance of Equity Premium Prediction. RFS21,1455–1508. [原始／作者來源](https://doi.org/10.1093/rfs/hhm014)。總體股權溢酬任務不同；不代表所有個股無訊號。
- **L03** Piotroski (2000). Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers. JAR38,1–41. [原始／作者來源](https://www.ivey.uwo.ca/media/3775523/value_investing_the_use_of_historical_financial_statement_information.pdf)。價值股橫斷面策略，未證實短期反轉。
- **L04** Bernard & Thomas (1989). Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium? JAR27,1–36. [原始／作者來源](https://doi.org/10.2307/2491062)。無歷史預期快照就不能宣稱已測到分析師surprise。
- **L05** Novy-Marx (2013). The Other Side of Value: The Gross Profitability Premium. JFE108,1–28. [原始／作者來源](https://www.nber.org/papers/w15940)。NBER連結為作者工作論文版本；持有期間與本案不同。
- **L06** Lo, Mamaysky & Wang (2000). Foundations of Technical Analysis. Journal of Finance55,1705–1765. [原始／作者來源](https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00265)。可檢驗不等於已證實可交易優勢或新的外生資訊。
- **L07** Sullivan, Timmermann & White (1999). Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. Journal of Finance54,1647–1691. [原始／作者來源](https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00163)。只校正最後留下的少數結果不恢復過去測試獨立性。
- **L08** Tetlock (2007). Giving Content to Investor Sentiment. Journal of Finance62,1139–1168. [原始／作者來源](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2007.01232.x)。媒體來源與企業Newsroom差異大；相關性非因果。
- **L09** Loughran & McDonald (2011). When Is a Liability Not a Liability? Journal of Finance66,35–65. [原始／作者來源](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2010.01625.x)。文本分類品質不能直接等同股價預測能力。
- **L10** Araci (2019). FinBERT: Financial Sentiment Analysis with Pre-trained Language Models. arXiv1908.10063. [原始／作者來源](https://arxiv.org/abs/1908.10063)。碩士論文/preprint；情緒標籤成績不是PIT股價證據。
- **L11** Bates & Granger (1969). The Combination of Forecasts. ORQ20,451–468. [原始／作者來源](https://doi.org/10.1057/jors.1969.103)。不能把凸組合本身宣稱為新演算法貢獻。
- **L12** Smith & Wallis (2009). A Simple Explanation of the Forecast Combination Puzzle. OBES71,331–355. [原始／作者來源](https://onlinelibrary.wiley.com/doi/10.1111/j.1468-0084.2008.00541.x)。有限樣本權重誤差不是新資訊效果。
- **L13** Wang, Hyndman, Li & Kang (2023). Forecast combinations: An over50-year review. IJF39,1518–1547. [原始／作者來源](https://www.sciencedirect.com/science/article/pii/S0169207022001480)。作者2022preprint為arXiv2205.04216；文獻缺口需定位在實證稽核。
- **L14** Frazier, Covey, Martin & Poskitt (2023). Solving the Forecast Combination Puzzle. arXiv2308.05263. [原始／作者來源](https://arxiv.org/abs/2308.05263)。此處核對為作者preprint，不假定已同儕審查。
- **L15** Gneiting & Raftery (2007). Strictly Proper Scoring Rules, Prediction, and Estimation. JASA102,359–378. [原始／作者來源](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf)。Brier改善仍不能單獨辨識資訊、校準與正則化機制。
- **L16** Murphy (1973). A New Vector Partition of the Probability Score. JAM12,595–600. [原始／作者來源](https://journals.ametsoc.org/abstract/journals/apme/12/4/1520-0450_1973_012_0595_anvpot_2_0_co_2.xml)。有限樣本分箱分解不是無偏的條件資訊估計。
- **L17** Niculescu-Mizil & Caruana (2005). Predicting Good Probabilities with Supervised Learning. ICML,625–632. [原始／作者來源](https://icml.cc/Conferences/2005/proceedings/papers/079_GoodProbabilities_NiculescuMizilCaruana.pdf)。需要獨立校準區段，不能在測試上擬合再報改善。
- **L18** Guo et al. (2017). On Calibration of Modern Neural Networks. PMLR70,1321–1330. [原始／作者來源](https://proceedings.mlr.press/v70/guo17a.html)。影像/文本分類結果不能保證金融非平穩場景有效。
- **L19** White (2000). A Reality Check for Data Snooping. Econometrica68,1097–1126. [原始／作者來源](https://onlinelibrary.wiley.com/doi/10.1111/1468-0262.00152)。需要完整搜尋紀錄；不能補救未記錄的整個研究歷程。
- **L20** Hansen (2005). A Test for Superior Predictive Ability. JBES23,365–380. [原始／作者來源](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=264569)。不是將任意大量新搜索合法化；本輪不實作SPA。
- **L21** Romano & Wolf (2005). Stepwise Multiple Testing as Formalized Data Snooping. Econometrica73,1237–1282. [原始／作者來源](https://users.ssc.wisc.edu/~behansen/718/RomanoWolf2005.pdf)。正式E7仍以固定Holm家族為主；不依測試換校正法。
- **L22** Harvey, Liu & Zhu (2016). …and the Cross-Section of Expected Returns. RFS29,5–68. [原始／作者來源](https://doi.org/10.1093/rfs/hhv059)。不能把全領域的t門檻機械地套成5日Brier定理。
- **L23** Bailey et al. (2017). The Probability of Backtest Overfitting. JCF20,39–69. [原始／作者來源](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)。作者PDF2015版本與2017期刊版分開標示；PBO不取代時序外驗證。
- **L24** Diebold & Mariano (1995). Comparing Predictive Accuracy. JBES13,253–263. [原始／作者來源](https://doi.org/10.1080/07350015.1995.10524599)。嵌套或退化組合下不能保證一般常態近似有效。
- **L25** Giacomini & White (2006). Tests of Conditional Predictive Ability. Econometrica74,1545–1578. [原始／作者來源](https://onlinelibrary.wiley.com/doi/10.1111/j.1468-0262.2006.00718.x)。特定估計視窗假設不可忽略；本輪不冒稱實作其完整檢定。
- **L26** Newey & West (1987). A Simple, Positive Semi-Definite HAC Covariance Matrix. Econometrica55,703–708. [原始／作者來源](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=225071)。長記憶、少季度與非平穩仍限制近似。
- **L27** Politis & Romano (1994). The Stationary Bootstrap. JASA89,1303–1313. [原始／作者來源](https://doi.org/10.1080/01621459.1994.10476870)。不是任意非平穩時間序列的萬用有效性保證。
- **L28** Cameron, Gelbach & Miller (2011). Robust Inference With Multiway Clustering. JBES29,238–249. [原始／作者來源](https://cameron.econ.ucdavis.edu/research/JBESpaper2009version.pdf)。作者2009版本；少時間clusters依然是限制。
- **L29** Petersen (2009). Estimating Standard Errors in Finance Panel Data Sets. RFS22,435–480. [原始／作者來源](https://academic.oup.com/rfs/article-abstract/22/1/435/1585940)。增加公司數不等於消除共同市場時間風險。
- **L30** Cawley & Talbot (2010). On Over-fitting in Model Selection and Subsequent Selection Bias. JMLR11,2079–2107. [原始／作者來源](https://www.jmlr.org/papers/v11/cawley10a.html)。需nested時序選模與一次保留集；最後少量p值不恢復獨立性。
- **L31** Roberts et al. (2017). Cross-validation strategies for structured data. Ecography40,913–929. [原始／作者來源](https://onlinelibrary.wiley.com/doi/10.1111/ecog.02881)。生態場景的方法原則不是金融模型成績的直接證據。
- **L32** Bergmeir, Hyndman & Koo (2018). Validity of Cross-Validation for Autoregressive Time Series Prediction. CSDA120,70–83. [原始／作者來源](https://robjhyndman.com/papers/cv-wp.pdf)。本案重疊標籤/PIT/非平穩不自動滿足；仍採前向分割。
- **L33** Lakens (2022). Sample Size Justification. Collabra: Psychology8,33267. [原始／作者來源](https://pure.tue.nl/ws/files/214011492/collabra_2022_8_1_33267.pdf)。通用設計文獻，沒有替本案估計金融ICC。
- **L34** Lakens (2017). Equivalence Tests: A Practical Primer. SPPS8,355–362. [原始／作者來源](https://pmc.ncbi.nlm.nih.gov/articles/PMC5502906/)。等效界線與多重性需事先固定；不能用大p證明無資訊。
- **L35** Nosek et al. (2018). The Preregistration Revolution. PNAS115,2600–2606. [原始／作者來源](https://doi.org/10.1073/pnas.1708274114)。GitHub草案或事後凍結不自動等於外部完成註冊。
- **L36** Gu & Dao (2023/2024). Mamba: Linear-Time Sequence Modeling with Selective State Spaces. arXiv2312.00752. [原始／作者來源](https://arxiv.org/abs/2312.00752)。一般序列任務效能不是金融基本面增益的證據。
- **L37** Kelly, Malamud & Zhou (2024). The Virtue of Complexity in Return Prediction. Journal of Finance79,459–503. [原始／作者來源](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13298)。總體月報酬與投資效用不同於個股5日Brier；本文只檢驗固定任務。
- **L38** Jiang, Kelly & Xiu (2023). (Re-)Imag(in)ing Price Trends. Journal of Finance78,3193–3249. [原始／作者來源](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13268)。表示有價值不代表新增外部資訊；本案不能將技術圖形當新學術概念。
- **L39** Chen, Pelger & Zhu (2024 issue; online2023). Deep Learning in Asset Pricing. Management Science70,714–750. [原始／作者來源](https://pubsonline.informs.org/doi/abs/10.1287/mnsc.2023.4695)。無套利SDF與投資組合目標，不是本案反轉概率；不能橫比成績。
- **L40** Bryzgalova, Lerner, Lettau & Pelger (2025 issue; online2024). Missing Financial Data. RFS38,803–882. [原始／作者來源](https://doi.org/10.1093/rfs/hhae036)。metadata與缺失並非新發現；本案貢獻候選是將其納入增益歸因控制。
- **L41** Xu et al. (2025). FinMultiTime: A Four-Modal Bilingual Dataset for Financial Time-Series Analysis. arXiv2506.05019. [原始／作者來源](https://arxiv.org/abs/2506.05019)。本次核對作者preprint；未下載、未驗證逐申報歷史版本／實際可得時鐘或原資料再授權，不視為現成嚴格PIT解方。
