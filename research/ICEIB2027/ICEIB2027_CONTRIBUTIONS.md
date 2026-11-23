# ICEIB2027：三項主貢獻與文獻定位

推薦標題：**Explaining Apparent Predictive Gains in Financial Machine Learning**。

## 1. Unified Incremental Information Evaluation

既有金融ML、技術分析及price/text研究已建立多來源模型與特徵表示方法（Gu et al.2020；Lo et al.2000；Xu & Cohen2018）。本研究的整合設計在同一可追溯流程中區分資訊來源、表示和估計，使用完整股票／架構比較、metadata、等維重複價格及forward representation診斷。

新增洞察是高訓練相關與不穩定前向線性重建能同時出現；不能僅由相關推論條件資訊完全重複，也不能由負R²推論存在新反轉訊號。八項主要技術增益及所有負面結果保留。

## 2. Calibration- and Shrinkage-Aware Fusion Analysis

組合與概率池不是新方法（Bates & Granger1969；Ranjan & Gneiting2010；Claeskens et al.2016），可靠度診斷亦有既有理論（Bröcker2008；Dimitriadis et al.2021）。本研究把同權重常數、前序獨立調權重常數、metadata／數值／重複價格及raw/calibrated管線一起比較。

具體發現是十組raw融合皆輸給匹配常數；AAPL兩個神經管線的小額calibrated點改善之區間仍跨0；新增LR正向分支比較集中冷啟動，且對長區塊敏感。這是一套辨認表觀改善來源的實證控制流程，並非新融合演算法、因果份額分解或穩定模型優勢。

## 3. News Attention versus Sentiment

媒體／文本與價格聯合研究已有先例。此處以保留來源篇數作操作性的密度proxy，不直接量測真實投資人注意力。相同日期／標籤下加入density-only對照，顯示密度重現大部分LR新聞點改善；情緒額外差異隨來源密度而異。原hierarchical次要顯著、延遲敏感性及同狀態排序證據全部保留。

## Temporal Data Integrity 的位置

D作三項貢獻的共同資格限制，而非第四項大型主文：內容版本、可得／arrival時間、資料完整度與feature-model vintage決定研究資訊集。嚴格L3/L4仍0；計算測試不是PIT認證。完整資料稽核保留於原E7/E8與E9b supplement。

## 論述界線

創新是整合比較設計及具名cohort的實證洞察；不宣稱全球首次、發明校準／收縮、因果識別、普遍預測無效或新獨立確認。主稿保留12項核心文獻；原40項書目、模型原始論文及較詳細現代融合比較見E9a catalog與E9b Literature Positioning Update。不同樣本Brier不直接合併排名。
