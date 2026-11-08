"""Curated primary-source evidence map; not an exhaustive bibliometric census."""
from pathlib import Path
import pandas as pd
from e7a_development_audit import OUT,dump

# Short original notes only; publisher abstracts/full articles not redistributed.
WORKS=[
('L01','金融ML','Gu, Kelly & Xiu (2020). Empirical Asset Pricing via Machine Learning. RFS33,2223–2273.','https://doi.org/10.1093/rfs/hhaa009','跨股票長期樣本與非線性交互作用提供重要比較框架。','月度風險溢酬，不是兩股5日反轉；不能直接移植其優勢。'),
('L02','股票預測','Welch & Goyal (2008). A Comprehensive Look at the Empirical Performance of Equity Premium Prediction. RFS21,1455–1508.','https://doi.org/10.1093/rfs/hhm014','強歷史平均基準與樣本外不穩定性不可省略。','總體股權溢酬任務不同；不代表所有個股無訊號。'),
('L03','基本面','Piotroski (2000). Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers. JAR38,1–41.','https://www.ivey.uwo.ca/media/3775523/value_investing_the_use_of_historical_financial_statement_information.pdf','會計資訊具有研究動機，應重視品質與經濟定義。','價值股橫斷面策略，未證實短期反轉。'),
('L04','基本面','Bernard & Thomas (1989). Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium? JAR27,1–36.','https://doi.org/10.2307/2491062','公布時間與預期落差對盈餘事件研究重要。','無歷史預期快照就不能宣稱已測到分析師surprise。'),
('L05','基本面','Novy-Marx (2013). The Other Side of Value: The Gross Profitability Premium. JFE108,1–28.','https://www.nber.org/papers/w15940','獲利能力的定義與橫斷面報酬有既有研究。','NBER連結為作者工作論文版本；持有期間與本案不同。'),
('L06','技術表示','Lo, Mamaysky & Wang (2000). Foundations of Technical Analysis. Journal of Finance55,1705–1765.','https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00265','技術型態可形式化並接受統計檢驗。','可檢驗不等於已證實可交易優勢或新的外生資訊。'),
('L07','技術表示','Sullivan, Timmermann & White (1999). Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. Journal of Finance54,1647–1691.','https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00163','技術規則搜尋的完整候選宇宙會改變推論。','只校正最後留下的少數結果不恢復過去測試獨立性。'),
('L08','金融文本','Tetlock (2007). Giving Content to Investor Sentiment. Journal of Finance62,1139–1168.','https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2007.01232.x','媒體情緒與價格動態有可研究關係。','媒體來源與企業Newsroom差異大；相關性非因果。'),
('L09','金融文本','Loughran & McDonald (2011). When Is a Liability Not a Liability? Journal of Finance66,35–65.','https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2010.01625.x','金融語境影響字典與情緒指標意義。','文本分類品質不能直接等同股價預測能力。'),
('L10','金融文本','Araci (2019). FinBERT: Financial Sentiment Analysis with Pre-trained Language Models. arXiv1908.10063.','https://arxiv.org/abs/1908.10063','金融情緒編碼器可作固定特徵工具。','碩士論文/preprint；情緒標籤成績不是PIT股價證據。'),
('L11','預測融合','Bates & Granger (1969). The Combination of Forecasts. ORQ20,451–468.','https://doi.org/10.1057/jors.1969.103','組合預測及誤差互補是已知方法。','不能把凸組合本身宣稱為新演算法貢獻。'),
('L12','預測融合','Smith & Wallis (2009). A Simple Explanation of the Forecast Combination Puzzle. OBES71,331–355.','https://onlinelibrary.wiley.com/doi/10.1111/j.1468-0084.2008.00541.x','估計權重的不確定性可使簡單平均有優勢。','有限樣本權重誤差不是新資訊效果。'),
('L13','預測融合','Wang, Hyndman, Li & Kang (2023). Forecast combinations: An over50-year review. IJF39,1518–1547.','https://www.sciencedirect.com/science/article/pii/S0169207022001480','融合、權重與資訊重疊已有廣泛文獻。','作者2022preprint為arXiv2205.04216；文獻缺口需定位在實證稽核。'),
('L14','預測融合','Frazier, Covey, Martin & Poskitt (2023). Solving the Forecast Combination Puzzle. arXiv2308.05263.','https://arxiv.org/abs/2308.05263','組合比較的虛無分布與功效也可能有非標準性。','此處核對為作者preprint，不假定已同儕審查。'),
('L15','機率評估','Gneiting & Raftery (2007). Strictly Proper Scoring Rules, Prediction, and Estimation. JASA102,359–378.','https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf','使用proper score評估概率，而不是只報命中率。','Brier改善仍不能單獨辨識資訊、校準與正則化機制。'),
('L16','機率評估','Murphy (1973). A New Vector Partition of the Probability Score. JAM12,595–600.','https://journals.ametsoc.org/abstract/journals/apme/12/4/1520-0450_1973_012_0595_anvpot_2_0_co_2.xml','Brier的可靠度與解析度需分開理解。','有限樣本分箱分解不是無偏的條件資訊估計。'),
('L17','機率校準','Niculescu-Mizil & Caruana (2005). Predicting Good Probabilities with Supervised Learning. ICML,625–632.','https://icml.cc/Conferences/2005/proceedings/papers/079_GoodProbabilities_NiculescuMizilCaruana.pdf','校準可改變模型概率比較；AUC與概率品質不同。','需要獨立校準區段，不能在測試上擬合再報改善。'),
('L18','機率校準','Guo et al. (2017). On Calibration of Modern Neural Networks. PMLR70,1321–1330.','https://proceedings.mlr.press/v70/guo17a.html','神經模型的校準不是架構名稱可保證的。','影像/文本分類結果不能保證金融非平穩場景有效。'),
('L19','資料探勘','White (2000). A Reality Check for Data Snooping. Econometrica68,1097–1126.','https://onlinelibrary.wiley.com/doi/10.1111/1468-0262.00152','反覆搜尋同一歷史樣本須處理選擇。','需要完整搜尋紀錄；不能補救未記錄的整個研究歷程。'),
('L20','資料探勘','Hansen (2005). A Test for Superior Predictive Ability. JBES23,365–380.','https://papers.ssrn.com/sol3/papers.cfm?abstract_id=264569','相對共同基準的多模型比較需專門推論。','不是將任意大量新搜索合法化；本輪不實作SPA。'),
('L21','多重推論','Romano & Wolf (2005). Stepwise Multiple Testing as Formalized Data Snooping. Econometrica73,1237–1282.','https://users.ssc.wisc.edu/~behansen/718/RomanoWolf2005.pdf','共同重抽樣能利用比較間相依。','正式E7仍以固定Holm家族為主；不依測試換校正法。'),
('L22','資料探勘','Harvey, Liu & Zhu (2016). …and the Cross-Section of Expected Returns. RFS29,5–68.','https://doi.org/10.1093/rfs/hhv059','金融文獻的大量候選使一般顯著門檻不足。','不能把全領域的t門檻機械地套成5日Brier定理。'),
('L23','研究選擇','Bailey et al. (2017). The Probability of Backtest Overfitting. JCF20,39–69.','https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf','回測選擇本身會產生過擬合。','作者PDF2015版本與2017期刊版分開標示；PBO不取代時序外驗證。'),
('L24','預測推論','Diebold & Mariano (1995). Comparing Predictive Accuracy. JBES13,253–263.','https://doi.org/10.1080/07350015.1995.10524599','比較成對損失並處理序列相關。','嵌套或退化組合下不能保證一般常態近似有效。'),
('L25','預測推論','Giacomini & White (2006). Tests of Conditional Predictive Ability. Econometrica74,1545–1578.','https://onlinelibrary.wiley.com/doi/10.1111/j.1468-0262.2006.00718.x','預測程序與條件預測能力的推論需明確定義。','特定估計視窗假設不可忽略；本輪不冒稱實作其完整檢定。'),
('L26','時間相依','Newey & West (1987). A Simple, Positive Semi-Definite HAC Covariance Matrix. Econometrica55,703–708.','https://papers.ssrn.com/sol3/papers.cfm?abstract_id=225071','HAC是序列相關標準誤的基本工具。','長記憶、少季度與非平穩仍限制近似。'),
('L27','時間相依','Politis & Romano (1994). The Stationary Bootstrap. JASA89,1303–1313.','https://doi.org/10.1080/01621459.1994.10476870','區塊重抽樣針對弱相依而非IID列。','不是任意非平穩時間序列的萬用有效性保證。'),
('L28','面板叢聚','Cameron, Gelbach & Miller (2011). Robust Inference With Multiway Clustering. JBES29,238–249.','https://cameron.econ.ucdavis.edu/research/JBESpaper2009version.pdf','同公司與共同日曆衝擊需同時考慮。','作者2009版本；少時間clusters依然是限制。'),
('L29','面板叢聚','Petersen (2009). Estimating Standard Errors in Finance Panel Data Sets. RFS22,435–480.','https://academic.oup.com/rfs/article-abstract/22/1/435/1585940','金融面板的殘差依賴會影響推論。','增加公司數不等於消除共同市場時間風險。'),
('L30','選模驗證','Cawley & Talbot (2010). On Over-fitting in Model Selection and Subsequent Selection Bias. JMLR11,2079–2107.','https://www.jmlr.org/papers/v11/cawley10a.html','選模準則本身會被過擬合。','需nested時序選模與一次保留集；最後少量p值不恢復獨立性。'),
('L31','時序驗證','Roberts et al. (2017). Cross-validation strategies for structured data. Ecography40,913–929.','https://onlinelibrary.wiley.com/doi/10.1111/ecog.02881','分割方式需符合資料依賴及外推任務。','生態場景的方法原則不是金融模型成績的直接證據。'),
('L32','時序驗證','Bergmeir, Hyndman & Koo (2018). Validity of Cross-Validation for Autoregressive Time Series Prediction. CSDA120,70–83.','https://robjhyndman.com/papers/cv-wp.pdf','某些純AR且誤差不相關條件可允許K-fold。','本案重疊標籤/PIT/非平穩不自動滿足；仍採前向分割。'),
('L33','功效','Lakens (2022). Sample Size Justification. Collabra: Psychology8,33267.','https://pure.tue.nl/ws/files/214011492/collabra_2022_8_1_33267.pdf','樣本量須以效果、精確度或資源限制透明辯護。','通用設計文獻，沒有替本案估計金融ICC。'),
('L34','等效推論','Lakens (2017). Equivalence Tests: A Practical Primer. SPPS8,355–362.','https://pmc.ncbi.nlm.nih.gov/articles/PMC5502906/','未顯著與小到無實務意義應分開。','等效界線與多重性需事先固定；不能用大p證明無資訊。'),
('L35','預註冊','Nosek et al. (2018). The Preregistration Revolution. PNAS115,2600–2606.','https://doi.org/10.1073/pnas.1708274114','生成與驗證假說應分開並保留時間戳承諾。','GitHub草案或事後凍結不自動等於外部完成註冊。'),
('L36','序列架構','Gu & Dao (2023/2024). Mamba: Linear-Time Sequence Modeling with Selective State Spaces. arXiv2312.00752.','https://arxiv.org/abs/2312.00752','真正的selective state-space模型可作次要架構對照。','一般序列任務效能不是金融基本面增益的證據。')]


WORKS.extend([
('L37','複雜度反證','Kelly, Malamud & Zhou (2024). The Virtue of Complexity in Return Prediction. Journal of Finance79,459–503.','https://onlinelibrary.wiley.com/doi/10.1111/jofi.13298','同一資訊集的複雜表示也可能改善預測及投資績效；不能預設簡單模型普遍勝出。','總體月報酬與投資效用不同於個股5日Brier；本文只檢驗固定任務。'),
('L38','價格表示','Jiang, Kelly & Xiu (2023). (Re-)Imag(in)ing Price Trends. Journal of Finance78,3193–3249.','https://onlinelibrary.wiley.com/doi/10.1111/jofi.13268','價格圖形與CNN是既有的表示學習與短期方向預測研究。','表示有價值不代表新增外部資訊；本案不能將技術圖形當新學術概念。'),
('L39','金融ML','Chen, Pelger & Zhu (2024 issue; online2023). Deep Learning in Asset Pricing. Management Science70,714–750.','https://pubsonline.informs.org/doi/abs/10.1287/mnsc.2023.4695','公司及總體資訊的非線性融合與深度資產訂價已有成熟先例。','無套利SDF與投資組合目標，不是本案反轉概率；不能橫比成績。'),
('L40','缺失資訊','Bryzgalova, Lerner, Lettau & Pelger (2025 issue; online2024). Missing Financial Data. RFS38,803–882.','https://doi.org/10.1093/rfs/hhae036','基本面缺失具結構，樣本選擇與填補不是無害工程細節。','metadata與缺失並非新發現；本案貢獻候選是將其納入增益歸因控制。'),
('L41','多模態資料','Xu et al. (2025). FinMultiTime: A Four-Modal Bilingual Dataset for Financial Time-Series Analysis. arXiv2506.05019.','https://arxiv.org/abs/2506.05019','已存在價格、新聞、財報表格及圖形的跨股票多模態資料基準。','本次核對作者preprint；未下載、未驗證逐申報歷史版本／實際可得時鐘或原資料再授權，不視為現成嚴格PIT解方。')])

def write():
    rows=[]
    for ident,topic,citation,url,note,limit in WORKS:
        rows.append({'work_id':ident,'topic':topic,'citation':citation,'primary_url':url,'method_note':note,'scope_limit':limit,'screening_status':'INCLUDED_PRIMARY_OR_AUTHOR_SOURCE','reading_depth':'abstract/metadata and targeted relevant material; not a full-text systematic extraction','verified_date':'2026-11-06','peer_review_status':'preprint_or_thesis' if ident in ['L10','L14','L36','L41'] else 'published_work; linked author version may predate publication'})
    pd.DataFrame(rows).to_csv(OUT/'tables/literature_evidence_map.csv',index=False)
    queries=[('finance_ML','Gu Kelly Xiu2020; Welch Goyal2008; financial return prediction baselines'),('fundamentals','Piotroski2000; Bernard Thomas1989; Novy-Marx2013'),('technical','Lo Mamaysky Wang2000; Sullivan Timmermann White1999'),('news','Tetlock2007; Loughran McDonald2011; FinBERT1908.10063'),('combination','Bates Granger1969; Smith Wallis2009; Wang etal50-year review; Frazier2308.05263'),('probability','Gneiting Raftery2007; Murphy1973; Niculescu-Mizil Caruana2005; Guo2017'),('selection','White2000; Hansen2005; Romano Wolf2005; Harvey Liu Zhu2016; BaileyPBO'),('inference','Diebold Mariano1995; Giacomini White2006; Newey West1987; Politis Romano1994; Petersen2009; Cameron Gelbach Miller2011'),('validation','Cawley Talbot2010; Roberts2017; Bergmeir Hyndman Koo2018'),('design','Lakens2022 sample size; Lakens2017 equivalence; Nosek2018 preregistration'),('data','SEC EDGAR/FSDS acceptance; CRSP active inactive; Compustat PIT; FactSet PIT; LSEG IBES; Nasdaq SF1'),('recent_closest','Kelly Malamud Zhou2024; Jiang Kelly Xiu2023; Chen Pelger Zhu2024; Missing Financial Data2025; FinMultiTime2506.05019'),('venue','IIF International Journal of Forecasting authors; Wiley Journal of Forecasting scope')]
    pd.DataFrame([{'topic':a,'queries_and_seed_terms':b,'search_date':'2026-11-06','method':'web search and direct primary URL verification; seed-led structured rapid review','retrieved_record_count':'NOT_REPORTED_SEARCH_ENGINE_TOTAL_UNAVAILABLE'} for a,b in queries]).to_csv(OUT/'tables/literature_search_log.csv',index=False)
    dump(OUT/'audits/literature_screening.json',{'included_unique_works':len(rows),'topics':len(set(x['topic'] for x in rows)),'deduplication':'author/year/work identity; author preprint and publisher version counted once','inclusion':'primary paper/publisher/author source relevant to the control or validation question','excluded':'marketing stock-prediction blogs, unverified bibliographic summaries, reddit assertions, lookalike publisher domains; no fulltext redistribution','not_exhaustive':True,'not_PRISMA_meta_analysis':True,'no_subscription_database_export':True,'no_claim_no_prior_paper_exists':True,'lookalike_domain_excluded':'sciencedirectelsevier.com is not used as an Elsevier source','unverified_venue_feature':'PLOS Registered Reports URL inaccessible; not asserted as a checked submission option'})
    return rows

if __name__=='__main__':write()
