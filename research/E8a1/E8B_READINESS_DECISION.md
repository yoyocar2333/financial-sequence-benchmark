# E8b Readiness：NOT_READY

主要依據仍為main固定E8a門檻，原件與hash在inputs/e8a_contract；[本輪逐閘門CSV](tables/E8b_readiness_decision.csv)保留舊狀態與新的PASS/FAIL/NOT_EVALUABLE/BLOCKED標記。沒有新建較寬鬆規則。

| Gate | 狀態 | 不能通過的證據 |
|---|---|---|
| permitted_research_and_reproduction | BLOCKED | 沒有本專案適用的研究／保存／刪除及重現授權 |
| strict_historical_content_and_availability | FAIL | PILOT_SAMPLE_MANIFEST只有表頭，真實L3=0、L4=0 |
| same_source_2train_1validation_1test_years | NOT_EVALUABLE | 未取得合格逐股面板；官方服務history不是實際連續樣本 |
| documented_session_monitoring_at_least90percent | NOT_EVALUABLE | 沒有歷史固定query／完整監測ledger；synthetic比例不使用 |
| nonoverlap_event_and_class_support | NOT_EVALUABLE | 真實合格panel0，不能計算兩股100/40/60與類別20/10/20支持 |
| 100_independent_manual_version_and_relevance_QA | BLOCKED | 人工候選0、完成0；30–50材料先導與100要求分開 |
| development_only_paired_loss_power_and_size | NOT_EVALUABLE | 無新paired losses、跨股／時間變異或檢定功效，不製造估計 |
| unseen_preregistered_E8_validation | BLOCKED | 2024–2025早已探索；2026舊E3c不能改作E8保留集；新協定未註冊 |

來源完整度每段≥90%、每股100/40/60非重疊事件與最低類別量、100文件QA與零關鍵錯誤／95%公司相關性維持原要求；它們仍只是screen，不能保證足夠joint power。即使日後40筆全有L3，也不能替整個年度／股票面板認證。

只有八gate全部具實際證據PASS後才考慮另立E8b執行計畫。現在完成的是資料可行性與工程先導，沒有比較金融模型、搜尋較佳測試樣本，亦不對新聞／社群預測力作肯定或否定結論。
