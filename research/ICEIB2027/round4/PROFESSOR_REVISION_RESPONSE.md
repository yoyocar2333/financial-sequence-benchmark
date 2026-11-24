# 丁老師建議修改對照 — 2026-11-24

本輪延續最新第三輪會議稿，原 Word/PDF 與來源另存私有 baseline；沒有回退長篇工作論文。科學數字、CI、p-value、資料切分與原控制組不變。

| 建議 | 完成內容 |
| --- | --- |
|1. 標題只有最開頭大寫|`Diagnosing apparent predictive gains in financial machine learning`；正文、Word核心標題與Markdown一致|
|2. 摘要稍長並提及效果|100→134字；包含研究問題、matched controls、AAPL兩個融合效果及CI跨零、TSLA負向、初始化與新聞結果|
|3. Introduction/Related Work加強|41→158字；說明新增資訊、價格表示、機率處理三種解釋，連結ML/technical/text、forecast pooling、calibration及時間有效性文獻|
|4. Section2先提創新貢獻|方法章開頭提出來源專屬控制的共同診斷流程，避免宣稱新預測演算法|
|5. Section2增加公式|5→8條：增加Brier定義、絕對/相對gain、signed grouping remainder公式；raw混合恆等式與Platt規則保留|
|6. 原Section3併入Section2|改為2.4 Development Controls and Statistical Evaluation；Results/Discussion/Conclusion依序為3/4/5，結果統整保留在3.6|
|7. 結論與References間的項目|六項標準聲明全部依序列出，另保留簡短AI輔助Acknowledgments；參考私有學長論文的格式|
|8. 作者|Hsieh Hao-Hsuan and Jian-Jiun Ding *；星號於Word為上標|
|9. 單位|Graduate Institute of Communication Engineering, National Taiwan University, Taipei 106319, Taiwan;|
|10. 通訊|* correspondence: jjding@ntu.edu.tw; Tel.: +886-3-33669652；依教授提供原文保留|
|11. 會議|7th International Conference on Electronic Communications, Internet of Things and Big Data 2027 (ICEIB 2027). April 23-25, 2027, Tamkang University|

## 聲明依據

使用者確認無外部經費、無利益衝突；Hsieh Hao-Hsuan負責實驗，Jian-Jiun Ding負責指導。只填這兩項已確認分工，沒有代填概念設計、經費取得、其他寫作角色或「兩作者已批准投稿」。IRB與Informed Consent採研究未涉及人／動物實驗的Not applicable格式；未聲稱取得倫理審查核准。

已找到並閱讀使用者提供的 `學長論文.docx`，SHA256 `87156b01bf389052c22552eccff326f98d83d9357b9bdaae567b7500174a2fe2`。只參考聲明與通訊格式，沒有沿用學長的計畫經費、分工或「No new data」聲明，也沒有公開第三方Word檔。出版管道／最後作者批准仍需投稿前確認。

## 篇幅及呈現

實測8頁（包括全部聲明及12篇文獻），使用模板原字級、樣式與邊界。新增cohort表分開市場與新聞樣本；融合與校準整合為同表A/B面板，保留兩股不利結果和兩個AAPL校準例子。八項技術比較及跨實驗統整仍在正文。架構圖只減少留白，文字字級不變。

為避免增加章節後超頁，刪除重複概述，文獻使用標準刊名／會議縮寫；Holm文獻保留完整作者、題名、卷頁，非必要JSTOR網址移至來源索引。期刊/會議名稱縮寫不改作者、文章題名、年份、DOI與引用順序。連續公式同組排版；公式、資料表數值與不確定性未改。

Data Availability段落含長網址，單獨採靠左以避免過度拉開字距；模板樣式XML、字型尺寸、行距與頁面幾何仍相同。PDF的下標k讀取順序與顯示順序不同，核對八條完整公式、全部六個下標與視覺呈現後才通過。

## 仍須投稿前處理

Linux預覽PDF使用P052替代未安裝的Palatino Linotype；Word保留模板原宣告與尺寸。正式以原生字型匯出後需再核對頁數。作者應完成最後內容批准、出版管道與實際系統欄位確認；本輪不投稿、不付款、不合併main。
