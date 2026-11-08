# E4新聞研究與外部專案分工

同一研究脈絡使用兩個既有Repository，不另建新Repository：

- [financial-sequence-benchmark](https://github.com/yoyocar2333/financial-sequence-benchmark)：結構化市場、波動／反轉、條件式新聞增益與E5技術分析。
- [stockllm-pit-news](https://github.com/yoyocar2333/stockllm-pit-news)：新聞抽取、FinBERT／Gemini特徵及PIT方法。

| 階段 | 本Repository責任 | 主要資料限制 |
|---|---|---|
| [E4a](../research/E4a/README.md) | 恢復52摘要／36 Gemini，與E3c事件對齊 | 樣本少，當年到達與版本證據不足 |
| [E4b](../research/E4b/README.md) | 448篇重建全文、來源／時間／品質統計 | 回溯取得不證明當年PIT；語法事件不是人工gold |
| [E4c](../research/E4c/README.md) | AAPL P／S／T、條件機率、增量／排序檢定 | 2025僅65事件、官方新聞正向偏差、反轉率漂移 |
| [E4c FNSPID稽核](../research/E4c/results/T11_fnspid.csv) | 完整23.23GB EOF掃描後年度彙整 | 非連續長期資料；午夜時間多；未進入E4c模型 |

工作站方法revision：[fdf6103](https://github.com/yoyocar2333/stockllm-pit-news/tree/fdf6103ff22035a6cd9e6a7e946430f0c2b2e33d)；另有[e5a0767](https://github.com/yoyocar2333/stockllm-pit-news/tree/e5a0767415a9123f0a338a73068aa564fac90585)稽核記錄。FinBERT權重固定revision記在E4b程式；本repo不重新散布模型權重。

不能將E4a的摘要、E4b的不同文章版本、FNSPID局部標題與E4c全庫列數相加為獨立全文。新聞缺失與無新聞不同；「觀測窗口內沒有保留Apple文章」不能等同「市場沒有AAPL消息」。

本次PR不修改外部新聞Repository、不傳送訊息、不上傳任何逐篇內容。完整重現需要由研究者在合法權限下提供原凍結語料及特徵；公開統計重建不需新聞API或金鑰。

## E8a新聞與社群可行性

[E8a](../research/E8a/E8A_SUMMARY.md)接續E4，分開所有新聞／社群來源、版本、時間與觀測分母；新作者資料不混入E4c模型。官方社群來源僅做取得條件調查，未宣稱已授權或完整歷史。StockEmotions是selected2020語料，不是時序訓練切分；StockNetAAPL有額外2016Q1檔案，TSLA未列。研究抽取仍交叉連結[stockllm-pit-news](https://github.com/yoyocar2333/stockllm-pit-news)，公開repo不轉載本文／逐篇輸出。
