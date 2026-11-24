# Scientific Completeness Review — Third Round

本輪基準為使用者指定的 `ICEIB2027_REVISED_FULL_PAPER.pdf` 與相符 Word。實際檔案為8頁；使用者已澄清沒有另一版本，確認使用此檔。原8頁完整副本與先前6頁初稿均保留於私有baseline，未回退十五頁E9b工作論文。R2來源commit為 `bfe6ea950b785880dfb48ed0a32e663940a6f11d`；264份研究／R2檔案雜湊受保護。

| R2 過度精簡之處 | R3 恢復內容 | 證據與界限 |
| --- | --- | --- |
| 會計偏離／收縮缺少形式定義 | p,f,c,w、raw q/q₀、損失恆等式及alignment/penalty解釋 | Methods2.2；原十組raw identity，不套用至各自校準後混合 |
| REL/RES/G只有敘述 | 明列連續BS=REL−RES+UNC+G、固定分箱及完整定義 | 主文簡式，補充G的方差／共變異公式；不省略帶符號餘項 |
| 只說負斜率「可能」影響AUC | 保存係數直接套回機率；全30組逐seed a,b、AUC、Brier、SD、同狀態排序 | 六pipeline完整稽核；seed46 Mamba三管線負斜率，LSTM皆正，未重新擬合 |
| 相關／重建方法不足 | Spearman2768日期、alpha10、38→13特徵、三fold、scaler與purging、R²平均方式 | 同日特徵的時間前向評估，非明日RSI；原負R²保留 |
| 技術八項主比較不在正文 | Table1四模型×兩股並排，正向benefit與Holm8 p | Logistic未列入這八項；無捏造第九／第十項 |
| 神經融合容易只看AAPL | Table2保留兩股四例與原CI／p家族 | TSLA負向結果仍在正文；全部十設定×raw/cal仍在補充 |
| 校準表可能擁擠 | Table3兩個fusion例子；六管線30組完整資料補充 | 按同一類型保留兩架構，非依分數挑seed或省略不利案例 |
| 集中於表格仍缺共同意義 | 保留Figure1及Results4.1–4.6，精簡重複統整句 | Table4仍在結果章回答表示、收縮、初始化、密度的共同歸因問題 |
| flat方向／quarter gate語氣不自然 | 明確非零五日方向；直接介紹compact logistic expert | 排除數AAPL2/TSLA3（train），其餘0；原neural gate放補充 |
| 修稿行政詞／模糊版本 | 正文無Codex/E9b/Original/Existing/Remains；固定來源commit | 科學術語grouping remainder保留；引用真實commit、不造DOI |

## 科學推論

R3確認的是校準係數與單seed排序的直接關係，並非會計資訊導致Brier改善的因果識別。兩個AAPL校準後gain仍為0.000980/0.001198、block60 CI跨零；兩個TSLA gain為負。初始化比較的正向效果集中2017–2018，後兩fold策略同一；原Holm6/12及block120敏感性不變。新聞的主要不顯著與次要延遲敏感例外、歷史概率較佳點分數也保留。

正文四表分別服務：技術八比較、兩股融合與不確定性、實際校準例證、跨研究統整。R2的第二張不確定性圖移補充，原檔與完整來源未刪；Figure1控制架構保留。這個取捨騰出公式與方法空間，未縮小模板字型或邊界。

## 資料誠信與先前接觸

主文保留兩股、反覆探索2024–2025、非全研究歷程校正、重疊標籤、有限季度更新、校準敏感、稀疏新聞及未認證PIT等實質限制，並明說新聞來源稽核嚴格L3/L4各0。沒有把「今天取得」或工程驗證當作歷史版本／arrival資格。

查閱 [E9b完整性S6](../../E9b/SUPPLEMENTARY_METHODS_AND_INTEGRITY.md)、[R2完整性補充](../round2/SUPPLEMENTARY_INTEGRITY.md)、[E6計畫](../../E6/config/evaluation_plan.json) 與 [E4c計畫](../../E4c/config/research_plan.json)。早期2026新聞彙總／discovery material、供應商頁面行情chrome等接觸紀錄保留，不能把未來期間自動宣稱未見。保存的管線／來源範圍沒有顯示本文以2026金融標籤選擇模型或門檻；目前仍無法排除未記錄研究選擇的影響，故主文維持探索性定位、沒有獨立成功主張。行政協定歷史不重塞主文，亦不刪原揭露。

本輪無新模型、校準器擬合、新p-value或CI；E3c2026協定受hash保護，未執行、未修改。本報告與自動檢查不是獨立人工科學QA。作者仍須確認投稿欄位、出版管道、原生字型與最終審核。
