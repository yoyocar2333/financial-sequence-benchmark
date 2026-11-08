# 論文定位與必要證據

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
