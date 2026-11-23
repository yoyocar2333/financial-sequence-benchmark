# 第二輪可讀性修訂報告

日期：2026-11-23。目標讀者：首次接觸本研究的機器學習研究者。

## 基準及來源

本輪從使用者目前的六頁 `ICEIB2027_FULL_PAPER.pdf` 與相符 Word 開始。PDF 為 Microsoft Word 2021 匯出，SHA256 `e088c1090e78ea8e4d3714bc8503916375623e285694fc05e041f000aeb2d45e`；Word SHA256 `0435ab6f50a61dc311bcda094133bc92f770ef382e37b84147ef9ce51299a31a`。兩檔另存私有唯讀基準；原路徑未覆寫。舊 Linux 七頁渲染與十五頁工作論文都不是本輪編輯基準。E9b 僅用於核對證據。

實際來源為 [REVISED_PAPER_TEMPLATE.md](REVISED_PAPER_TEMPLATE.md)、[新版生成程式](../../../scripts/iceib2027_r2_build.py) 及 [Word 編排程式](../../../scripts/iceib2027_r2_docx.py)。同版 Markdown → 使用者 Word 樣式 → 新 DOCX → PDF。原作者姓名保留；示範學校、dummy correspondence、假會議日期改為待確認欄位。

## 讀者問題與修改

| 問題／原稿呈現 | 修訂後 | 檢查依據 |
| --- | --- | --- |
| 四段結果直到結論才整合 | 4.1 先交代共同研究問題及相應控制；4.6 統整五個診斷環節 | 新正文 4.1、4.6，Figure 1、Table 3 |
| 只見小數／p-value，難判斷量級 | 先列 reference Brier，再列正向為改善的差值、相對百分比與來源 CI | Tables 1–2；73 列完整算式 |
| `B38/T51/C39` 等內碼 | 改為 multiscale prices、technical representations、relative-market-only control | 主文無這些內碼 |
| `Late/PriorBlend` | 改為 accounting fusion / same-weight constant shrinkage | 方法 2.2 與結果 4.3 |
| `C1–C6/Holm6/Holm12` | 直接寫 values vs zeros/duplicates、prior-selected single expert，明列六項／十二項家族 | 4.4 與補充 Table S3 |
| calibration 後的小幅正數容易被理解為新資訊 | 原始十組皆較常數收縮差；兩個 AAPL 正數只是 0.395%／0.482% 的損失下降，CI 跨零 | Table 1、Figure 2、4.3 解讀 |
| C6 局部顯著容易被寫成持續融合 | 說明全部來自 2017–2018 初始配置；後續兩策略相同，block120 不顯著 | 4.4；原逐 fold 選擇表 |
| 新聞模型優於弱價格模型容易被誤讀 | 分開密度、額外情緒、簡單歷史概率；後者點 Brier 仍較低 | 4.5、Table 2 |
| 六個零保留窗口被當作「沒有新聞」 | 說明是來源窗口沒有保留文章，無全市場監測完整性證據 | 2.1、4.5 |
| 內部 2026 工作流程占用主文 | 刪除行政敘述，連至保留的原始完整性紀錄；重複探索與 PIT 限制仍在主文 | Discussion；[誠信補充](SUPPLEMENTARY_INTEGRITY.md) |

## 新的第 4 章

1. Overview：先提出「增益來自何處」，讓讀者在數字之前理解控制設計。
2. Technical：問題、八項完整比較、例示效果與區間，再解釋相關性與前向重建不是同一診斷。
3. Fusion：同權重收縮 → raw/calibrated 對照 → 機率分布／reliability 解釋；保留次要直接方向例外。
4. Matched controls：用有意義的比較名稱取代代碼；區分數值內容與輸入格式、初始化與持續互補。
5. News：先控制密度，才談情緒；同時檢查歷史概率、延遲與同狀態排序。
6. Synthesis：在結果章內回答哪些改善在更強控制下仍不確定，以及這對研究設計的意義。

每個實質實驗小節均有研究問題、比較、數值、解讀與主題連結；總覽／統整不另造新實驗。

## 正文與補充的分工

主文保留兩張原創圖（三來源控制總覽、AAPL raw/calibrated 不確定性）及三張表（四組神經融合、五個新聞對照、跨研究統整）。完整八項技術比較、十組融合的 raw/calibrated 共二十列、六 LR 加六 tree 的三種區塊敏感性共三十六列，以及全部八個新聞預測器與不利 event-feature 結果，見 [SUPPLEMENTARY_RESULTS.md](SUPPLEMENTARY_RESULTS.md)。另有完整效果圖 S1/S2。主文例示不構成挑選最佳模型；兩檔股票、所有比較的完整家族皆保留。

縮短的是重複背景、內部符號解碼及表格逐列重述，不是統計不確定性。研究貢獻在 Introduction、Results、Discussion、Conclusion 均為「配合資訊來源的控制流程」，沒有聲稱新原創演算法或獨立確認的預測優勢。

## 編輯限制

百分比只量化同一參照下的 Brier 損失變動，不是正確率、經濟意義或獲利。沒有更改資料切分、模型／seed、原始分數、CI、p-value、檢定家族。沒有新增訓練或以 2024–2025 選新模型。程式／排版檢查不是獨立人工研究 QA，也不證明歷史 PIT 合格。
