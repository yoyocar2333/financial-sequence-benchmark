# Market-Model Benchmark — Financial Time-Series Forecasting

Structured-data branch of my undergraduate research project on high-noise financial time series.

This repository compares classical machine learning, latent-regime modeling, recurrent neural networks, and selective state-space models under one chronological evaluation framework.

## Research task

**Next-trading-day price regression** on AAPL and TSLA.

Models:
- Naive persistence baseline
- XGBoost
- Gaussian HMM + Decision Tree
- LSTM
- Mamba
- Multi-scale LSTM Hybrid

Primary metric: **MAPE**.

## Why this repository is separate

The broader project has two different prediction tasks:

1. **Structured market data → next-day price regression** — this repository.
2. **Financial news → next-day direction classification** — companion StockLLM repository.

Keeping them separate avoids mixing targets, metrics, and experimental assumptions while still presenting them as two branches of one research project.

Companion repository: https://github.com/yoyocar2333/stock2

## Research-integrity decisions

The public notebook was cleaned before publication:

- chronological evaluation only;
- rolling features are never back-filled from future observations;
- a real `mamba_ssm` model is required — no identity fallback;
- an earlier prototype sentiment feature that used `future_return` was removed because it introduced look-ahead leakage;
- simulated prediction trajectories were removed;
- HMM+DT is described accurately as Gaussian HMM + Decision Tree, not as a full HHMM reproduction;
- the multi-scale Hybrid is a moving-average decomposition inspired by decomposition methods, not MEMD.

## Quick start

Open:

`notebooks/stock_market_models.ipynb`

The notebook downloads market data with `yfinance`, trains each model chronologically, exports daily predictions and a MAPE summary to `outputs/`.

Recommended environment: Google Colab or a CUDA-enabled Python environment compatible with `mamba-ssm`.

## Reproducibility

The notebook controls random seeds and includes an optional multi-seed stability diagnostic for LSTM, Mamba and the Hybrid model.

## Limitations

AAPL/TSLA and one fixed month are not sufficient to establish universal model superiority. The repository is intended as an auditable benchmark and research artifact, not as trading advice.
