# 人工QA先導協定與待簽核材料

目前：真實候選0、材料包0、獨立人工完成0；`MANUAL_QA_PENDING.csv`僅表頭。先導30–50筆材料目標與E8b正式100份獨立文件QA分開，沒有預填通過或捏造reviewer。

## 有授權資料後的固定抽樣

目標40份文件／版本：兩股各20，橫跨至少四年（2train、1val、1test角色），每股每年5。資料充分才依年度分層；稀少年份／無修改刪除情形保留欠額，不以複製或合成補齊。版本組視為同一文件cluster，不能用一篇多次擷取抵100份文件。

分層固定含日內／日期／午夜品質、17NY前後、假日、parent／reshare、ticker歧義；若來源有真實edit/delete，以同文件版本對照保留。依source+stableID+version的固定SHA256排序抽取，拒用未來label、收益／模型誤差挑樣。缺少某種層就標NOT_AVAILABLE，不發明刪除證據。

## 每筆核對

1. 來源、原始bytes hash、document/version/parent、公司實體／cashtag；Apple一般名詞與ticker要分開。
2. 原始日期與時區語意、發布／修改／刪除／捕獲／到達是否分清；UTC午夜是否只是日期占位。
3. 證據是否同內容版本、是否可獨立核對；該版本在本次decision cutoff前的可得上界。
4. 重複、轉發、thread、一文多股、刪除與版本更新；不可把今天新內容接到舊created_at。
5. 原文情緒、原生bull/bear或模型輸出的語意差異及未提供狀態；這不是5日反轉gold。
6. 使用／保存／再散布是否在本專案範圍、刪除是否已遵循。

reviewer須填獨立研究者識別、實際審核時間、具體證據URI/hash、判定PASS/FAIL/UNRESOLVED與理由。建議另一位研究者複核關鍵時間錯誤；人工工具生成建議不算review。未填reviewer／time／evidence或未解決的重要錯誤不得計完成。

E8b100份要求、零關鍵前視／版本錯誤及reviewed entity relevance≥95%不變；40份pilot即使完成也不代表100份gate通過。真實授權證據尚缺，本輪不能評估實際一致率／語意正確率，也不把0審查寫成0錯誤率。
