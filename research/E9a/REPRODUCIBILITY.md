# E9a 重現與來源邊界

## 已完成的工作

這是既有研究的整合、來源核對、圖表重排與文件製作。103項主張中91項對應CSV確切列，另12項為文件段落；32筆文獻的metadata及主要紀錄已核對。沒有重新訓練、重新估計Brier/AUC/p-value、下載市場或社群資料、執行2026金融驗證、寄信或付款。

論文是英文工作初稿，含繁中重點摘要；授權決策及品質審查為繁中。作者、機構及學校格式仍待教授確認。

## 公開版離線重現

於 repository 根目錄，以 Python 3.10+ 執行：

```bash
python -B scripts/e9a_validate.py --bundle research/E9a
python -B scripts/test_e9a.py
python -B scripts/e9a_reproduce.py --bundle research/E9a --out outputs/e9a_replay_NEW
# 若已有 matplotlib / numpy，可重畫三圖與依模板重建正文：
python -B scripts/e9a_reproduce.py --bundle research/E9a --out outputs/e9a_figures_NEW --figures
```

輸出目錄必須全新。第一項核對固定21個來源檔案的SHA、原表唯一selector、91筆來源列、103項主張及引用；不能只把輸出CSV欄位改成verified=true。這只保證現有aggregate與本稿一致，不認證原金融資料或檢定假設。

不加 `--figures` 時正文為原稿複製，重播的是來源與表格，不宣稱重建排版；加上時才從模板與原表重建正文。Word另需已有python-docx：

```bash
python -B scripts/e9a_docx.py --out research/E9a
```

上述Word指令會在指定目錄產生新Word，若保護發布原檔請先複製至新目錄。正式重播不自動重寫凍結Word／PDF。PDF需已有LibreOffice及Noto Serif TC；通用環境可從新DOCX由LibreOffice匯出並更新目錄，或使用 `e9a_render_pdf.py --out <new_bundle> --program <existing_LO_program> --registry <existing_LO_registry>`，其Python須能import uno。本工作站重用既有私人renderer、字型及獨立E9a profile，未安裝系統套件；私人工具與個人路徑不公開。不同LibreOffice或字型版本可有頁面差異，不承諾二進位一致。

## 來源索引與可檢查範圍

- `SOURCE_MANIFEST.csv`：本輪凍結main的公開研究來源、SHA及階段；不是原市場／新聞逐篇manifest。
- `CLAIM_EVIDENCE_MATRIX.csv`、`audits/cell_provenance.json`：每項主張的selector、原表列及限制；source_file相對repo根。
- `audits/table_source_hashes.json`：正文使用的來源檔案，重播前必須吻合。
- `literature/verified_doi_records.json`：保留原DOI核對警示及失敗；`citation_catalog.json`含後續人工紀錄式resolution，不擦除失敗。
- `literature/current_policy_evidence.json`：當前官方政策的摘要筆記，不是原始HTTP、歷史內容證據或取得授權。
- `checks/`：來源、文件與公開安全檢查。技術PASS≠科學獨立確認。
- 舊研究原資料／全文／API回應／checkpoint不打包；原E0及歷史成果不覆寫。E3c2026協定不改未執行。

完整原始模型重現須另外合法取得相同凍結資料、原版本、環境及先前實驗的資產；本輪不替使用者重新授權，亦不讓公開repo自動啟動訓練或收集。新聞原方法參考 [stockllm-pit-news](https://github.com/yoyocar2333/stockllm-pit-news)。

## 版本與發布

基準main：`e2bc7a3f686a213e25635172a19018934df944cb`。E9a以新branch/PR提供；本輪明確不merge。僅新增論文、彙整索引、自製圖與工程程式；若為公開Word/PDF擴充publication validator，變更限定這兩個自製文件，另列非科學工具變更，不改舊科學成果。
