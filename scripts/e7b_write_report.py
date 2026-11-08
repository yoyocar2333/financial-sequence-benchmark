"""Render a data-gate audit report; no affirmative PIT claims without evidence."""
import json
from pathlib import Path
import pandas as pd
from e7b_setup import OUT,dump

def write():
 s=json.loads((OUT/'audits/audit_results.json').read_text());d=json.loads((OUT/'audits/descriptive_diagnostics.json').read_text())
 cv=pd.read_csv(OUT/'tables/company_PIT_coverage.csv')
 table='|公司／原型ID|預設研究組|可讀索引|財務rendered頁|歷史行情列|嚴格季度|\n|---|---|---:|---:|---:|---:|\n'+'\n'.join(f"|{r.prototype_id}|{r.industry}|{r.readable_unique_filing_indexes}|{r.rendered_financial_tables}|{r.historical_price_rows}|0|" for r in cv.itertuples())
 docs={}
 docs['E7B_SUMMARY.md']=f'''# E7b：20公司Point-in-Time財務資料原型

日期：2026-11-07。研究範圍：公開來源、2012–2022開發期。狀態：**資料取得／稽核與fail-closed工程原型完成；尚未建立可供H1／H3正式推論的合格PIT面板**。新增模型擬合0次、模型搜尋0次、GPU工作0次。使用者已確認目前沒有機構授權匯出，本輪不購買或假設具備權限。

## 1. 主要結果與可用範圍

|項目|實際取得／檢查|能否算正式資格|
|---|---:|---|
|固定公司／研究組|20／4|目的性技術與身分壓力樣本，不是代表性機率抽樣|
|由官方歷史索引核對CIK|20家|只確認所示歷史申報身分，不代表2011上市母體資格已核對|
|可讀唯一申報索引|21份|含額外AAPL2022案例；不能算21份原始申報全文|
|可讀SEC財務rendered頁|17頁、10家、90列候選顯示觀測|含parenthetical頁；非每家三大報表，更非原始XBRL context|
|查詢代號取得歷史行情|17個、45,893列|16個覆蓋2012–2022；舊Dell僅2016起，均未認證as-traded／身分鏈|
|原始SEC HTTP文件／XBRL instance bytes|0／0|未取得，不能以文字轉出檔雜湊替代|
|嚴格合格公司季度|0|不是宣稱公司沒財報，而是證據鏈尚未完成|
|獨立人工原文件核對|0／目標200|模型輔助索引閱讀與23項程式測試不等於人工200文件|
|六項主要比較的真損失變異／尺寸|NOT_ESTIMABLE|不補0、不拿價格相關代替、不啟動訓練|

本次取得成功與資格失敗同時保留。當前名義20×44季度＝880個公司日曆季度、7欄＝6,160個目標格；但退出／身分／交易資格母體尚未確認，這不是已認證的可觀測樣本分母，也不能要求每家公司都活滿44季。所有資格不足格均為null與原因，沒有填成經濟上的0。

## 2. 樣本及來源追溯

{table}

四組是能源／電腦硬體與半導體／零售／軟體服務的原型研究組，**不是E7a四個SIC大區間母體的已完成抽樣**。其中COP在原型預設13，但2013申報索引實際SIC為2911；保留不一致，不推定哪個分類一定正確，不偷偷換公司或改碼。完整[公司稽核](tables/company_PIT_coverage.csv)、[索引](tables/filing_index_metadata.csv)、[來源manifest](tables/source_manifest.csv)、[列示原始檔案位置與大小](tables/SEC_listed_artifact_manifest.csv)。

工作站普通公開請求在Sandbox內遇DNS限制，正常Sandbox外讀取SEC API／Archives／歷史index均回403；FSDS請求顯示Request Rate Threshold Exceeded，停止直接重試，沒有旋轉代理、偽裝身分或繞過限制。內建網頁服務可讀部分官方頁，卻不能匯出原始XML／ZIP bytes。這是本執行環境的取得限制，不是聲稱官方資料不存在。四筆HTTP失敗的原response未保存，所以SHA保持null，沒有捏造raw檔案。詳見`audits/direct_SEC_access_failures.json`。

## 3. 時間與版本：具體觀察

21份索引的period end至顯示Accepted日期差中位數為**50日**；10份顯示鐘面晚於17:00，2份顯示Accepted日期與Filing Date不同。AAPL2022顯示Accepted 2022-10-27 18:01:14、Filing Date 10/28；Sears顯示2013-03-19 19:43:54、Filing Date 3/20。這說明期末日、Filing Date與處理時刻不能互換。[時間診斷](tables/source_timing_diagnostics.csv)。

上述為官方索引的原顯示鐘面，尚未完成原SGML／時區／dissemination鏈的交叉認證；不直接把10筆視為已認證的紐約17:00後事件。50日是**相對SEC來源文件**的日期差，不是首次財報發布延遲；同一數字可能更早在公司發布稿出現。不得據此宣稱所有數值直到Accepted才首次公開。

來源公開／acceptance、歷史供應商received與現在retrieved分開儲存。未取得received不等於從未收到；retrieved2026不能當成2012可得證據。對可驗證原始SEC來源，E7a允許SOURCE_EVENT等級與COLLECTOR_ARRIVAL分開；本輪失格是原始檔、時鐘及修訂盤點未完成，**不是任意要求所有基本面都必須有付費供應商first-seen**。

![取得與資格分開](figures/evidence_acquisition_vs_qualification.png)

![期末日不是可得時點](figures/period_end_is_not_availability.png)

## 4. 價格、公司行動與身分

- AAPL2014拆股前後供應商Close比約0.984，並未出現未調整價格約7倍的尺度變化；2020約0.967，亦非4倍。這與其Close已做拆股調整一致，不能稱當時未調整成交價。[拆股診斷](tables/split_adjustment_diagnostics.csv)。市場漲跌會影響比率，因此此圖不是單獨的公司行動認證。
- AAPL2012當年官方每股現金股利$2.65，供應商歷史事件金額0.094643，相差約28倍，與後來7×4拆股單位一致。官方record date 8/13、payment 8/16與供應商ex-date 8/9是不同時點；不能將它們不一致視為錯價。[股利單位案例](tables/cash_dividend_share_basis_witness.csv)。[發行公司來源](https://investor.apple.com/dividend-history/default.aspx)。
- 舊Dell CIK826083於2013收購轉為現金權利；現今DELL查詢返回2016-08-17起1,605列，而Dell Technologies為另一CIK1571996，且涉及Class V／Class C轉換。沒有證券與換股鏈就不得銜接回2012舊Dell。[舊Dell](https://www.sec.gov/Archives/edgar/data/826083/000119312513416110/d619138d8k.htm)、[新Dell](https://www.sec.gov/Archives/edgar/data/1571996/000157199619000008/delltechnologiesfy1910k.htm)。
- Chesapeake同CIK／CHK代號仍可能跨越2021舊股註銷與新股發行；CIK相同也不保證同一證券。[官方文件](https://www.sec.gov/Archives/edgar/data/895126/000089512621000033/ex9922021-02x09pr.htm)。
- Sears的2018 Nasdaq退出後預期轉SHLDQ OTC，不代表當日股權歸零；Yahoo更名Altaba也不是立即破產歸零。缺少退出／分配／結算時標為未知，不能把缺失報酬補成−100%。[Sears](https://www.sec.gov/Archives/edgar/data/1310067/000119312518299298/d622556d8k.htm)、[Yahoo／Altaba](https://www.sec.gov/Archives/edgar/data/1011006/000119312517198146/d409905dsctoia.htm)。

這些問題不表示所有舊回溯報酬必然錯誤；共同常數調整可能在報酬比率中相消。但不能因此把調整後絕對價格、不同股利單位與跨證券歷史視為已認證可執行財富序列。

## 5. as-of工程與品質閘門

`e7b_pit.py`實作來源／到達兩種可得模式、版本不回填、同concept／period／unit才選版本、原始XML與well-formed XHTML iXBRL數值／scale／context解析、財季／YTD／年度分離、EPS每股基準、雙時間證券身分及拆股／股利／退市財富會計。這是fail-closed原型，不是已涵蓋全部SEC HTML、taxonomy extension或供應商的production parser；不支援格式與未知會計映射須隔離。

`e7b_build_asof.py`另要求原始bytes雜湊及來源verification records，不能只在fact表把旗標設True。已產生880個17:00紐約鐘面轉UTC的日曆季末查詢；**不是已核對交易日**。0個合格輸入導致6,160個null值並附拒用理由；不作插補或模型擬合。[品質閘門](tables/quality_gates.csv)、[人工核對狀態](tables/manual_document_QA_gate.csv)、[六比較可行性](tables/six_contrast_variance_feasibility.csv)。

來源追溯100%、每欄80%、共同日期90%、人工200文件／零重大錯誤、數值99%、公司行動99.9%等E7a閘門均未被降標或假裝通過。對空資料集不報「100%合規」；對未核對文件不報「0錯誤所以合格」。

## 6. 存活者偏誤、擴充與近期成果

**2025年底股票規則若倒用於2012–2022訓練／回測，會條件化於未來存活、上市狀態與資料可取得性。** 它仍可定義之後未來樣本的條件母體，但不能回溯變成無存活者偏誤的歷史母體。四個退出壓力案例也不能恢復母體代表性。已提供[可稽核修正版](HISTORICAL_UNIVERSE_CORRECTION.md)與獨立selector，不改E7a封存檔或E3c2026協定。

16個非legacy查詢代號的共同2,767個開發期Close log報酬，成對相關中位數**{d['median_pairwise_price_return_correlation']:.4f}**。這只是未認證快照的資料診斷，**不是六比較損失差ICC，不能塞進功效公式當作實測ρ**。沒有PIT面板與六組相同資訊的固定預測，因此真變異、依賴與檢定尺寸維持NOT_ESTIMABLE。

![價格相關只作診斷](figures/development_price_correlation_diagnostic.png)

100公司×40日曆季度是名義4,000公司季度，不能篩選「完整活滿40季」的100公司。應以歷史時點安全母體選股，保留退出與新進，計算實際不平衡樣本／cluster數。按本次索引檔案大小的粗略情境，4,000份main HTML＋native XBRL約25.7GB，完整submission約86GB；這是所選年度文件尺度外推，不是實測下載量、供應商報價或足夠功效保證。[擴充／成本](EXPANSION_FEASIBILITY.md)。

近期最可行的是**資料時點、股利單位與證券身分稽核工作論文**，用可追溯案例與合成反例展示錯誤如何發生，完整保留失敗與來源偏差，不聲稱市場可預測性或新獨立確認。2027–2031確認性路線另維持為待資料／功效／推論閘門通過後的候選。[近期路線](SHORT_TERM_WORKING_PAPER_ROUTE.md)。

## 7. 完整性與重現

23項資料契約測試通過；它們是合成或工程測試，不是200份獨立人工財報核對，也不是H1/H3檢定尺寸驗證。完整離線重現會從保存的來源轉出／歷史sanitized arrays重算稽核與as-of；公開GitHub版只有自製程式、彙整、少量診斷與來源索引，不上傳完整行情、財報全文或當期報價envelopes。[重現說明](REPRODUCIBILITY.md)、[欄位字典](DATA_DICTIONARY.md)。

歷史搜尋曾附帶2026 filing／compensation片段，Yahoo回應也可能附帶當期quote metadata；前者限discovery，後者原始envelopes本機隔離，只有嚴格2012–2022 arrays進稽核。沒有用2026選模／調參／評分，沒有執行E3c2026驗證，不宣稱零暴露。既有382個成果／協定檔案以SHA保護。
'''
 docs['HISTORICAL_UNIVERSE_CORRECTION.md']='''# 歷史母體修正：E7B-v2候選，非修改既有協定

## 1. 設計診斷

E7a候選以as-of2025-12-31的公開普通股及當時流動性抽200股，再用它們的2012–2022歷史。對2027後的條件母體，事前固定2025名單本身不等於使用未來績效；但把同名單的舊歷史稱為代表2012市場，會排除其後退市、破產、私有化或轉投資公司的證券，並可能用後來的產業／代號回填。

「每公司必須有40完整季度」會再條件化於存活、穩定揭露及被供應商保留；不能以完整案例篩選來解決資料品質。CIK是申報公司ID，不是普通股永久ID；Chesapeake舊／新股同CIK，舊Dell／新Dell不同CIK與股權類別；Yahoo／Altaba的經濟活動與產業也改變。

本輪20家是預先鎖定的目的性工程壓力樣本，刻意加入已知退出情境；不是從已取得的2011歷史證券母體隨機抽樣，不能用它估母體資料失敗率、存活者偏誤大小或一般模型效能。COP預設13與申報SIC2911不一致保留，經濟研究組不可冒充正式SIC分層。

## 2. 歷史開發期母體候選

1. 從合法且含inactive securities的歷史master，取得2011-12-30收盤資訊；若確認非該市場最後交易日則由事先固定交易日曆給出上一交易日，不硬猜。
2. 只用當時可得的US primary common equity、永久security ID、issuer／CIK、as-of SIC、≥$5、過去60日median美元成交量≥$1m、≥250個過往價格日及≥4個已公開財報。2011 warmup與來源也需保存；本輪2012後少量索引不能驗證這個母體。
3. 沿用E7a四SIC區間10–19／20–39／40–59／70–89，各先抽25公司作100公司開發pilot，每SIC2最多20。多股類只選當時較高流動性的一類，tie取永久ID。樣本不足就報不足，不以已知贏家補滿。
4. 依`SHA256(E7Bv2|20261106|asofUTC|security_id)`排序；先保存完整eligible pool、每項排除原因、來源與抽樣hash，再取得未見結果。`e7b_historical_universe.py`提供selector。
5. 保留之後退市／破產／併購、合法股票轉換和分配；無法核對結算標未知，不刪除或補−100%。公司40季度不完整屬實際at-risk樣本，不以後來存活作事前資格。
6. 可另事先固定每年初新增eligible上市公司cohort；同一公司與security的多次出現仍按公司叢聚，不算多個獨立股票。列出每年風險集合、entry／exit、缺失與可用公司季度，不能稱始終平衡100×40。

目前未取得歷史master／inactive價格／公司行動全鏈；上述是可稽核算法與輸入契約，**不是已重建完成的無偏母體**。輸入的歷史snapshot／身分證據必須為真布林True且可追溯，字串False、現在的ticker list或2026最新欄位不可當作合格來源。

## 3. 與長期候選樣本分開

E7a的2025固定未來cohort保持封存作候選；若日後使用，先註冊2025至正式起點間的退出處理，不在看到未來表現後替換。歷史開發母體採上面的當時資格，未來母體則以其自己的ex-ante資訊定義，兩者外推範圍分開。

這個修正不產生新的2024–2025測試、也不改E3c2026協定。歷史母體與未來cohort須在資料與功效閘門後一起做正式版本修訂／外部註冊；不能把目前候選JSON標為已註冊。
'''
 docs['EXPANSION_FEASIBILITY.md']='''# 擴充至100公司×40開發季度：可行性與成本

## 1. 本輪能與不能證明

20家CIK均有可讀的官方歷史索引，代表跨公司文件線索可找；不代表取得了完整季度歷史。10家有少量rendered頁、17個symbol有行情array，皆未通過嚴格主面板資格。取用成功率受工具快取、網站與不同來源影響，不可解讀成金融資訊實際披露率。使用者確認目前沒有CRSP／Compustat PIT等授權匯出；沒有自行購買、註冊或假設校內有權限。

## 2. 三條資料路線

A. 公開SEC原始申報＋版本／日曆／身分工程。SEC提供公司API及歷史index；本工作站普通下載回403，web讀取器不匯出XML／ZIP bytes。下一步是在符合官方fair access且正常可使用的取得管道取得原始檔，再保存SHA、原header／clock、申報清單與修訂；不是旋轉IP／代理或重試突破封鎖。可使用由合法正常存取管道提供的本機原始檔，再離線核對。公開資料不代表原始申報的每個第三方附件都可任意重發。[SEC官方開發說明](https://www.sec.gov/about/developer-resources)。

B. 原始SEC基本面＋授權的歷史security master／價格／公司行動。對主研究較實際：數值可源自公開原文，母體、永久ID、退市和結算由可靠歷史庫補齊。CRSP官方列active/inactive與PERMNO／PERMCO，是應調查的機構路線，不代表本次已有使用權。[CRSP](https://www.crsp.org/research/crsp-us-stock-databases-2025-layout/)。

C. 專門PIT財報／預期資料產品。Compustat PIT、I/B/E/S PIT等需確認具體產品、原版本與收到時間，不能把普通最新版財報當PIT。當前沒有資料也沒有可驗證報價，不虛報金額或製造surprise。分析師預期不是本輪prototype必需條件；先做好原始基本面即可。

## 3. 可核對的體積情境

按本次20份sequence1的年度HTML，median 2,362,249 bytes；20份native XBRL median 4,071,280 bytes。若粗乘4,000份，兩者約25.7GB（decimal）；21份complete submission median21,495,179 bytes，粗乘約86.0GB。完整submission包含許多相同文件，這兩方案不能直接相加。季度通常不同於年度大小，taxonomy、附件、修訂、身份資料與重現副本另計；表中是場景計算，不是下載吞吐量、最低需求或總成本估計。[明細](tables/acquisition_size_scenarios.csv)。

若以1 request/s、每filing取main／XBRL／header共3檔，4,000份理想下限12,000秒約3.3小時，只是零重試／零延遲的排程算術；不是實際工期，還需source discovery、network、parser、對帳與QA。人工200文件若每份10–20分鐘，約33–67人時，屬人力假設而非本次實測。機構授權費尚未知，不填免費或估價。100×40也須改成保留退出的不平衡面板，實際文件數由母體決定。

## 4. 擴充的go／no-go

1. 先取得20家完整來源與正常下載／合法本機原檔輸入；原始bytes、時鐘、修訂與會計映射都可回查。
2. 完成200獨立原文件人工QA（不把同accession的多頁／重複格式算多份），0重大時鐘／版本錯誤，數值一致≥99%。當前0份，非0錯誤合格。
3. 取得可追溯歷史母體與至少4個退出／轉換案例的完整價格及財富結算；99.9%回報對帳門檻不變。
4. 每核心欄覆蓋≥80%、共同日期≥90%。跨產業gross margin、CFO的quarter／YTD、EPS拆股基準等須先做會計可比性審查；不能把不適用當0或測試後刪欄。若需變更欄位，另作E7設計修訂，不改E7a封存稿。
5. 然後才擴100開發公司與≥40日曆季度，僅跑固定六比較所需程序量測損失變異、公司／日曆依賴與null尺寸；不按gain挑股票，不搜2024–2025最佳組合。

當前對4／5的統計資格均不足，六比較真變異與檢定尺寸為NOT_ESTIMABLE。16個價格快照相關中位.3454不是Brier損失差ICC，不拿來通過功效。若只剩公開fragment，近期應走資料／方法稽核工作論文，而非擴大搜尋或宣稱100股票已可確認H1/H3。
'''
 docs['SHORT_TERM_WORKING_PAPER_ROUTE.md']='''# 近期工作論文路線與長期確認性驗證分開

## 1. 近期題目候選

**Before Prediction: Auditing Filing-Time, Security Identity, and Adjustment Semantics in a Twenty-Company Financial Dataset Prototype**

中文：**預測之前：20公司財務資料原型的申報時點、證券身分與調整單位稽核**。

近期成果定位是有邊界的資料與方法稽核工作論文，不預先宣稱有可交易訊號、基本面無價值或複雜模型劣勢。E7a文獻已顯示PIT、多模態、缺失資訊與融合並非新概念；本稿貢獻候選是可重現的識別失敗案例、證據等級與負面控制，而非首次發明as-of join。

## 2. 現在可以寫的結果

- 固定20家公司、四個研究組及四類已知退出／變更案例，明示目的性抽樣與工具可取得性偏差。
- 21份索引的期末日／Accepted／Filing Date差異；原始時計未認證時保留raw表示，不用retrieval補歷史時間。
- Apple拆股／股利單位、Dell兩個CIK與股類、CHK同CIK新舊股票、Sears OTC及Yahoo投資公司轉換的機械風險。
- 工程對照：合成修訂回填、晚到資料、年度當季度、EPS未調每股基準、ticker拼接、未知退市補零，展示fail-closed拒用及正確計算。
- 來源／資格分離：有資料線索不等於合格PIT；報告失敗及閘門未過，而非把公開來源稀疏說成金融市場沒有資訊。

這些都不是新的獨立市場效果證據；21個索引、17張rendered表、23個合成測試與200份人工原報告是不同單位，必須分開。

## 3. 建議近期工作包（可依公開資料實際進度調整）

第一階段，1–2週：透過正常合法來源取得一小批完整原始SEC文件，優先補足四種身分風險與四個產業；由研究者人工記錄查核，不以模型讀取冒充獨立人工。若仍無raw，先發透明的工程原型／資料可行性工作稿，限制主張。

第二階段，2–4週：原文件可得後，鎖定來源稽核問題、故障分類、樣本與QA清單，完成200份分層獨立原文件核對；補歷史證券母體，明確現金／股類／退市結算，不強迫平衡存活者面板。可以評估pipeline錯誤與數值一致性，暫不做模型增益搜尋。

第三階段，4–6週：寫出資料、時點／版本方法、身份／公司行動案例、合成測試、實際缺口及合法重現資產；教授逐項核對，做最近鄰全文文獻比較。公開程式、schema、原始URL及SHA、必要的自製彙整圖，依權限保留受限原文／行情。不將工程測試通過寫成研究假說通過。

上述是工期建議，不是保證資料會取得、能完成投稿或已通過同儕審查。若未取得歷史母體，工作稿只能描述目的性案例，不能估計全市場錯誤率或無偏效果。

## 4. 長期路線

2027–2031仍是E7a待資料／功效／推論／外部註冊門檻的候選確認性規劃，不是近期工作稿的已取得證據。E3c2026協定不變、未執行、不加入新模型。若未來有由獨立管理人保管、團隊真未接觸的歷史公司資料，可另事先註冊一次橫斷面外驗證；目前沒有這種資料或保管安排，不把它寫成已完成。
'''
 docs['DATA_DICTIONARY.md']='''# 資料層與欄位字典

- `cohort_locked.csv`：20個目的性prototype ID及候選CIK／產業組，鎖定前不是已驗證歷史母體。初始PENDING旗標保留不回改；後驗查核另列company表的verified欄。
- `filing_index_metadata.csv`：21個唯一accession、SEC index來源、filing／period date及Accepted原顯示鐘面。`accepted_display_local_unverified_timezone`不等於已認證UTC；provider received未知留空。
- `SEC_listed_artifact_manifest.csv`：官方索引列出的文件名、type、sequence、大小與預計URL。列示不等於檔案已下載；`file_retrieved_as_original=False`。
- `source_manifest.csv`：所有web來源／discovery與價格HTTP記錄。`extract_file_sha256`只驗證工具轉出檔；不填入原SEC body hash。web的retrieval_recorded是本次工具回應保存時間，非上游首次HTTP抓取；工具Crawled也不是當年first-seen。Yahoo原envelope SHA是真實回應hash，但原envelope隔離，不作歷史可得或SEC原文證明。
- `rendered_display_observations.csv`：90個候選顯示列，保留source URL／label／display cells；沒有自動聲稱其period、unit、taxonomy context或數值與原XML認證。不混入normalized facts。
- `market_quality_by_company.csv`及year表：17個symbol成功、3個HTTP失敗；歷史array與CIK／security歸屬分開。quote Close不是已認證as-traded。數值格式檢查不等於99.9%回報對帳。
- `company_calendar_quarter_coverage.csv`：880個名義日曆格，membership與完整申報清單未知；`strict_eligible_core_cells=0`指目前沒有合格輸入，不是公司0營收或沒有財報。
- `derived/normalized_verified_facts.json`與`authenticated_source_registry.json`：當前`[]`／`{}`，沒有把顯示觀測、合成樣本或缺失塞成真facts。
- `derived/asof_strict_calendar_queries.csv`：各公司44個季末17:00紐約時間（DST轉UTC）查詢，週末等尚非核對交易日。七特徵null及拒用原因；新版輸出為`derived/asof_build_v1_1/`。
- `asof_rejection_trace.csv`：每query因缺原始認證輸入而拒用；未獲資料不是經濟0。不以當年財年結束日作public時點。
- `quality_gates.csv`與`manual_document_QA_gate.csv`：200人工作業未完成、agreement不可評估；不因沒有受檢資料就填100%一致或0錯誤合格。
- `diagnostic_price_return_correlations.csv`：16個非legacy查詢代號的split-adjusted Close log報酬配對相關；不是預測損失相關／母體ICC。
- `cash_dividend_share_basis_witness.csv`：來源amount單位與declaration／record／ex／payment不同；沒有計算投資績效。
- `six_contrast_variance_feasibility.csv`：沿用E7a C1–C6，真變異／依賴／尺寸均null與NOT_ESTIMABLE。

raw web extract可讀與否不能推論公司是否披露；原SHA與轉出SHA、source public與vendor received、retrieval與historical first-seen分開。`source_event`可得模式不宣稱當年collector已收到；`arrival`模式需額外歷史received證明。合成測試全部以SYNTHETIC ID標示，永不計入20家資料。

解析器支援原生XBRL XML及well-formed XHTML iXBRL的有限數值transform、scale、sign、nil、entity、period與units；DTD／entity、continued numeric及未知格式拒用。並非完整SEC taxonomy mapping／HTML修復／quarter reconstruction產品；其輸出不會自動認證發布時間或修訂歷史。
'''
 docs['REPRODUCIBILITY.md']='''# E7b完整與公開重現

完整本機bundle保存來源工具轉出、historical-only行情arrays、來源manifest、設定、audit結果與程式快照。原始Yahoo envelopes可能帶當期quote，留在本機quarantine；ZIP排除所有`.bin`。既有受保護成果與原2026協定不改。

使用現有`.venv-e3b`（Python3.10、numpy／pandas等既有套件），不需安裝或GPU：

```bash
.venv-e3b/bin/python -B scripts/test_e7b.py
.venv-e3b/bin/python -B scripts/e7b_replay.py --bundle outputs/e7b_20261107 --output-dir outputs/e7b_replay_new
```

從完整ZIP解壓後，在bundle目錄：

```bash
python code/e7b_replay.py --bundle . --output-dir ../e7b_replay_new
python code/test_e7b.py
```

replay以保存的web轉出及已排除當期quote欄的2012–2022資料，重算稽核／描述統計與as-of，逐表比對。它不是重新下載原始SEC或證明歷史PIT；raw來源當前未取得，其缺口不可由replay成功填補。

公開GitHub版不包含完整行情、web全文、quarantine或私人環境，提供`e7b_public_replay.py --bundle research/E7b`核對公開彙整、時間診斷、gate狀態與23項合成測試。不能僅靠公開彙整重建完整行情相關或原申報數值；這個範圍明確區分。

原始SEC manifest／時鐘／版本registry將來補齊後，可用`e7b_build_asof.py`產生特徵；工具要求新的輸出目錄、source raw SHA與verification records。當前空facts已生成880個拒用query，沒有填造數據。完整程式例：

```bash
python scripts/e7b_build_asof.py --bundle outputs/e7b_20261107 --facts outputs/e7b_20261107/derived/normalized_verified_facts.json --source-registry outputs/e7b_20261107/derived/authenticated_source_registry.json --queries outputs/e7b_20261107/derived/asof_strict_calendar_queries.csv --output-dir outputs/e7b_asof_new
```

E7a方案、來源SHA、研究成果382份保護檔與E3c2026協定將在finalize時重新逐檔核對。無新模型搜尋、無2024–2025最優組合尋找、無2026驗證、無外部預註冊申報。
'''
 for name,body in docs.items():(OUT/name).write_text(body.strip()+'\n')
 correction={'version':'E7B-historical-sampling-candidate-v2','status':'IMPLEMENTED_SELECTOR_NO_HISTORICAL_MASTER_OBTAINED','supersedes_for_historical_development_only':'E7a retrospective use of2025-12-31 survival-conditioned universe; original file preserved','historical_inception_candidate':'2011-12-30T22:00:00Z after verified last trading session','strata_SIC2':[[10,19],[20,39],[40,59],[70,89]],'target_initial_per_stratum':25,'max_per_SIC2':20,'selection':'One primary common class per issuer by past60 liquidity; SHA256(E7Bv2|20261106|asofUTC|security_id) within fixed strata','eligibility':'historical verified identity/snapshot only, price>=5USD, median60 dollarvolume>=1e6, prior250 prices and4published reports, no future survival/completeness filter','future_exits_kept':True,'balanced40quarter_survival_required':False,'population_manifest_obtained':False,'prospective2025_candidate':'not erased; separately defined target population, not backward reconstruction','old_E3c2026_protocol':'UNCHANGED_NOT_EXECUTED'}
 dump(OUT/'historical_sampling_rules_v2.json',correction)
 issues=[('I01','Original SEC acquisition','403 blocks and unsupported XML/ZIP export','OPEN_CRITICAL'),('I02','Time and revision proof','Index clocks acquired, original timezone/dissemination/amendment chain absent','OPEN_CRITICAL'),('I03','Security identity','LegacyDell/newDell and sameCIK CHK cancellation/reissue must not splice','OPEN_CRITICAL'),('I04','Adjustment semantics','Vendor Close and cash dividends use adjusted share units','OPEN_CRITICAL'),('I05','Sampling','2025 retrospective population and balanced panel condition on survival','CORRECTION_DESIGNED_NOT_IMPLEMENTED_ON_REAL_MASTER'),('I06','Manual QA','0/200 independent original documents; not counted by automated tests','NOT_COMPLETED'),('I07','Accounting comparability','Gross margin/EPS split basis/CFO YTD mappings need source review','OPEN'),('I08','SIC classification','COP candidate13 versus historical filing2911 retained','OPEN_MAPPING_DIFFERENCE'),('I09','Unrequested current metadata','Discovery snippets and vendor envelopes quarantined/excluded from financial inputs','DISCLOSED_NOT_USED'),('I10','Power/inference','No qualified six-contrast panel; no empirical covariance or size estimate','NOT_ESTIMABLE')]
 pd.DataFrame(issues,columns=['issue_id','area','observed_issue','status']).to_csv(OUT/'tables/issue_register.csv',index=False)
 print('E7b report documents written; qualification remains NOT READY')
if __name__=='__main__':write()
