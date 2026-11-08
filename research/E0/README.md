# E0 — Legacy next-day price regression

保留原始 [notebook](../../notebooks/stock_market_models.ipynb)、[RESULTS.md](../../RESULTS.md)、[原 README](LEGACY_README.md) 與既有 Git 歷史，不重新訓練或改寫舊數字。

任務為2025年11月的隔日股價水準預測，指標是MAPE（%），不是E1的絕對報酬百分點，也不是E3–E5的Brier。

| 股票 | Naive | XGBoost | HMM+DT | LSTM | Mamba | Multi-scale Hybrid |
|---|---:|---:|---:|---:|---:|---:|
| AAPL | 0.6766 | 1.2044 | 0.8592 | 2.2306 | 1.0470 | 1.7883 |
| TSLA | 2.6378 | 2.8604 | 2.9439 | 3.5060 | 3.4684 | 3.8792 |

來源是既有Repository的recorded table（base commit e6aceaac73b4c66744f0fe9098da613de63d140f）。此次只核對舊記錄，沒有重跑或取得逐日預測重新驗證。舊表說明notebook曾在成功執行後清除洩漏情緒、模擬軌跡與假的Mamba fallback，因此不能將舊表視為本次對清理後notebook的獨立重現。

兩股均未顯示複雜模型一定勝過Naive；單月兩股不足以支持普遍模型排名。舊notebook可能下載當前資料，不是後續研究的2026 holdout入口；本次整理沒有執行它。
