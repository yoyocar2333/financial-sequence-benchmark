# E9b 完整檢查與重現報告

2026-11-15。檢查分別回答工程一致性與研究證據問題；沒有獨立人工資格認證。

|檢查|實際結果|範圍|
|---|---|---|
|原始科學成果保護|2482工作站檔、1669分析輸入SHA一致；430舊公開research/code檔未變|含舊E9a私有產物與既有協定；不新增2026評估|
|Claim/source核對|319項、原103全部既有欄位保留、216新增；40reference IDs一致|精確selector、列、欄位及來源hash|
|原E6 metric重算|88組Brier誤差<1e-12|原始逐日raw/cal預測；未改原表|
|Private source no-refit replay|35張表數值重算一致，稿件與claim byte-identical|24LR係數、36native trees、6Ridge重用；重播0新fit|
|Public aggregate replay|目前稿件／claim／catalog逐byte相同、三主圖與七supp圖重新繪製|公開表格層級，非由公開raw data重算|
|單元測試|舊E9a7項＋新E9b7項通過|來源歧義、範圍、次要顯著保留、binary白名單與pin、連續分箱G、raw恆等式、Holm、同路徑兩股不增加獨立性、前序選擇|
|文件技術|15頁、5表、3圖、130來源段落、字型嵌入、繁中可擷取、頁碼／目錄更新|無缺字替代符／頁外文字／內嵌檔案／外部檔案關係；代表頁由作者agent目視|
|文字對照|固定句型38→0、not/cannot/never124→0；38句逐項配置與12段比較|heuristic語句計數，非科學品質評分|

兩處工程修復與數值界線：舊loader的bundle/inputs契約由byte-identical cutoff副本銜接；raw mixture的float32 archive rounding單獨保留，以float64重建驗證恆等式。它們均未修改原科學輸入／結果。首次public `--figures`重播因既有環境matplotlib不在path而停止；使用已安裝的使用者site-packages後完成，沒有安裝套件。來源保護檢查的初次相對路徑錯誤已修正為resolve後重跑。文件檢查以規格化空白處理LibreOffice分拆中文字run，不忽略文字內容。

機器紀錄見 `checks/`。公開內容、relative links、原E0及來源SHA另由全庫publication validator檢查。私有inputs/models不在GitHub或公開ZIP內；合格L3/L4仍0、獨立人工QA仍0。新增分析計畫及tree addendum的先後次序保留，不稱為原實驗預註冊。
