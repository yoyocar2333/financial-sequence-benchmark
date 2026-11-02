# Recorded Backtest Results

Target month: **2025-11**

Task: next-trading-day **price regression**

Metric: mean MAPE (%) across valid trading days in the month.

| Ticker | HMM+DT | Hybrid | LSTM | Mamba | XGBoost | Naive |
|---|---:|---:|---:|---:|---:|---:|
| AAPL | 0.8592 | 1.7883 | 2.2306 | 1.0470 | 1.2044 | 0.6766 |
| TSLA | 2.9439 | 3.8792 | 3.5060 | 3.4684 | 2.8604 | 2.6378 |

## Interpretation

- On AAPL, Mamba produced lower error than LSTM and the heuristic multi-scale Hybrid, but did not beat the Naive or HMM+DT baselines.
- On TSLA, Mamba and LSTM were close, while Naive and XGBoost remained more competitive.
- The result does **not** support a claim that model complexity guarantees lower forecasting error.
- The experiment is a fixed-window benchmark on two tickers, not evidence of universal superiority or trading profitability.

## Reproducibility note

These values are from the successfully executed six-model notebook run. The public notebook was subsequently cleaned to remove exploratory sentiment leakage, simulated demonstration outputs, and the old fake-Mamba fallback while preserving the market-model benchmark logic.
