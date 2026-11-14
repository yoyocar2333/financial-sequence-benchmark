# E9a 文獻與引用稽核

查證日 2026-11-14。本輪共 32 筆論文／方法引用；25 個 Crossref DOI metadata 核對、3 個 arXiv 官方紀錄 DOI、4 個官方出版社／會議／期刊 stable URL，未替無 DOI 項目捏造 DOI。逐筆狀態、年份、標題、DOI及連結見 [citation_audit.csv](literature/citation_audit.csv)；完整 metadata 見 [citation_catalog.json](literature/citation_catalog.json)。

## 核對方法與誠實邊界

1. 既有 E7a 定向文獻整理與原報告作起點；逐項比對作者、標題、年份與 DOI。Crossref 是出版登錄 metadata，不能取代全文方法審查；有縮寫標題或年份差異時再查作者／出版社。
2. 32 筆不是 PRISMA 系統性回顧，也不是無遺漏的新穎性認證。部分只檢查 metadata、摘要及原 E7a 定向閱讀，不能寫成已逐篇完整複製。
3. 每個 DOI 查核的 response SHA 表示當次 metadata 回應的一致性；未保存 HTTP 原始 bytes，不把該 hash 宣稱成原始出版檔案保存。Web evidence cards 是人工整理筆記，非全文或歷史金融版本。
4. 文獻用來界定相關問題及方法；不把廣泛資產定價、股利或長期報酬證據搬成 AAPL／TSLA 五日反轉已確認效果。

## 已處理的引用問題

|項目|發現|處理|
|---|---|---|
|Holm 1979|候選 `10.2307/4615733` 未能由 DOI 查核通過；JSTOR 期刊卷期可核對作者、題名、65–70頁|正式引用 stable URL；DOI 留空，保存失敗結果，不把穩定識別碼冒充有效 DOI|
|XGBoost 2016|Crossref 題名只有 XGBoost，與完整題名文字比對不足|作者 arXiv 官方頁明列完整標題、兩位作者與同一 ACM DOI；保留原警示與補充 resolution|
|線上及印刷年份|例如 Welch/Goyal、Loughran/McDonald、Missing Financial Data、舊 JOF archive 上線時間與期刊年不同|正文使用所引期刊卷期年；metadata 原日期不覆寫；不把 archive 數位上線日當原研究年|
|FinMultiTime|2025 arXiv v2頁標為 under review|列預印本；不當成已通過同儕審查的 PIT 或增益證據|
|Mamba|引用原作者 selective-state-space 方法紀錄|不由實作名稱推論金融優勢；E6僅凍結 P 做 Late，不冒充新基本面神經訓練|
|bootstrap|Politis/Romano 為 stationary bootstrap|只作相關方法背景；原實驗為 circular blocks，未宣稱兩者是同演算法|

## 新穎性及論述稽核

可支持：跨階段且可追索的增量價值稽核；具體展示條件平均、校準、縮減和資料資格與較好分數不同；將失敗與局部正向結果完整呈現。不能支持：第一個融合模型、第一個 PIT 方法、新數學定理、已證明市場無法預測、已確認基本面／新聞無效。匹配收縮對照本身也不能排除所有重複價格或模型容量效應。

## 投稿前待人工完成

- 作者／教授逐篇確認最關鍵方法及金融文獻的全文適用範圍，補足與目標期刊最接近的研究，不能只依 metadata 宣稱無既有研究。
- 對 FinBERT／LLM 版本、語料訓練期與時間一致性作更完整來源核對。
- 選定期刊後調整引用格式、字數及資料政策；沒有捏造目標期刊接受率或保證接受。
- 正文每個主要數字由 CLAIM_EVIDENCE_MATRIX 定位；圖表只重排原 aggregate，不產生新統計量。
