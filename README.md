# Stock Market Sequence Model Benchmark

This repository contains the **structured market-data branch** of my undergraduate research project on financial time-series prediction.

The project compares classical machine learning, regime-aware models, recurrent neural networks, and selective state-space models under the same chronological evaluation setup.

## Models

- Naive persistence baseline
- XGBoost
- Gaussian HMM + Decision Tree
- LSTM
- Mamba
- Multi-scale LSTM Hybrid

## Task

**Next-trading-day price regression** for AAPL and TSLA.

Primary metric: **MAPE**.

## Research emphasis

The goal is not to claim that a more complex model is always better. The notebook emphasizes:

- chronological evaluation instead of random train/test splitting;
- strong simple baselines;
- causal rolling features without backward filling;
- real `mamba_ssm` execution with no identity fallback;
- clear separation between the price-regression branch and the news/LLM branch;
- reproducible daily predictions and optional multi-seed stability analysis.

## Important cleanup from the exploratory notebook

The public notebook intentionally removes several exploratory components that are not valid research evidence:

1. an early prototype sentiment feature that used `future_return` and therefore caused look-ahead leakage;
2. an old Mamba import fallback that behaved like an identity layer when `mamba_ssm` was unavailable;
3. simulated prediction-trajectory visualizations.

The resulting notebook keeps only the auditable market-model benchmark.

## Repository structure

```
notebooks/
  stock_market_models.ipynb
README.md
requirements.txt
.gitignore
```

## Companion project

The non-structured news branch — Gemini, FinBERT, Point-in-Time alignment, Time Decay, paired evaluation, and Market + News fusion — is maintained separately in:

**StockLLM / news prediction:** https://github.com/yoyocar2333/stock2

Together, the two repositories correspond to one broader research project: structured market modeling + non-structured news information fusion.

## Notes

- The HMM implementation is Gaussian HMM + Decision Tree, inspired by regime-aware hybrid forecasting literature; it is not a full HHMM + rough-set reproduction.
- The multi-scale Hybrid uses a lightweight moving-average decomposition and should not be interpreted as MEMD.
- This repository is for research and reproducibility, not trading advice.
