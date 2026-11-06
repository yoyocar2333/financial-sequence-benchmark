# 跨股票資料可行性與Point-in-Time稽核

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
