"""M-E1/M-E2: next-trading-day absolute log-return forecasting.

Scope: AAPL/TSLA, comparable E1/E2a/E2b/E2c samples. The script contains
NO downloaded observations and makes NO claim about empirical performance
until --download or locally supplied historical CSV data is used.

Forecast cutoff: after market data for session t become available.
Target: 100 * |log(adjusted_close[t+1] / adjusted_close[t])|.
All learned transforms/weights are trained before the held-out test period.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler

BASE_FEATURES = [
    "Open", "High", "Low", "Close", "Volume", "MA5", "MA20", "Volatility_10",
]
FEATURES = {
    "E1": BASE_FEATURES,
    "E2a": BASE_FEATURES + ["RV5", "RV20"],
    "E2b": BASE_FEATURES + ["RV5", "RV20", "VXN", "VXN_Change", "VIX", "VIX_Change"],
    "E2c": BASE_FEATURES + ["RV5", "RV20", "VXN", "VXN_Change", "VIX", "VIX_Change",
                            "VRP_QQQ", "VRP_Ratio", "VRP_Z252"],
}
ALL_FEATURES = FEATURES["E2c"]
BASELINES = ["RollingMean20", "RollingMedian20"]


def normalize_ohlcv(data: pd.DataFrame, name: str, index_only: bool = False) -> pd.DataFrame:
    """CSV requirements: Date, Close (+ Open/High/Low/Volume for tickers)."""
    data = data.copy()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    if "Date" in data.columns:
        data["Date"] = pd.to_datetime(data["Date"], utc=True).dt.tz_localize(None).dt.normalize()
        data = data.set_index("Date")
    else:
        data.index = pd.to_datetime(data.index, utc=True).tz_localize(None).normalize()
    data = data.sort_index()
    if data.index.has_duplicates:
        raise ValueError(f"{name}: duplicate trading sessions")
    required = ["Close"] if index_only else ["Open", "High", "Low", "Close", "Volume"]
    missing = set(required) - set(data.columns)
    if missing:
        raise ValueError(f"{name}: missing columns {sorted(missing)}")
    data = data[required].apply(pd.to_numeric, errors="coerce")
    if (data["Close"].dropna() <= 0).any():
        raise ValueError(f"{name}: non-positive closes")
    return data


def load_market_data(ticker: str, market_dir: Path | None, start: str, end: str) -> pd.DataFrame:
    symbols = {"VXN": "^VXN", "VIX": "^VIX"}
    if market_dir is not None:
        file_path = market_dir / f"{ticker}.csv"
        if not file_path.is_file():
            raise FileNotFoundError(f"Missing input {file_path}")
        frame = pd.read_csv(file_path)
    else:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError("For online use, run: pip install yfinance") from exc
        # auto_adjust=True adjusts for dividends and splits; use identical
        # return conventions for both price labels and realized volatility.
        frame = yf.download(symbols.get(ticker, ticker), start=start, end=end,
                            auto_adjust=True, progress=False, threads=False)
        if frame.empty:
            raise RuntimeError(f"No Yahoo data for {ticker}")
    return normalize_ohlcv(frame, ticker, index_only=ticker in ("VXN", "VIX"))


def annualized_rv(closes: pd.Series, n: int) -> pd.Series:
    returns = np.log(closes / closes.shift(1))
    return 100 * np.sqrt(252) * returns.rolling(n, min_periods=n).std(ddof=1)


def build_dataset(stock: pd.DataFrame, qqq: pd.DataFrame, vxn: pd.DataFrame,
                  vix: pd.DataFrame) -> pd.DataFrame:
    """Calculate all features at t, independently of tomorrow's target."""
    stock = stock.sort_index()
    frame = stock.copy()
    frame["MA5"] = frame["Close"].rolling(5, min_periods=5).mean()
    frame["MA20"] = frame["Close"].rolling(20, min_periods=20).mean()
    frame["Volatility_10"] = frame["Close"].rolling(10, min_periods=10).std()
    log_ret = np.log(frame["Close"] / frame["Close"].shift(1))
    frame["RV5"] = 100 * np.sqrt(252) * log_ret.rolling(5, min_periods=5).std(ddof=1)
    frame["RV20"] = 100 * np.sqrt(252) * log_ret.rolling(20, min_periods=20).std(ddof=1)
    frame["RollingMean20"] = (100 * log_ret.abs()).rolling(20, min_periods=20).mean()
    frame["RollingMedian20"] = (100 * log_ret.abs()).rolling(20, min_periods=20).median()

    # Derive labels BEFORE joining exogenous series, preserving the literal
    # next stock trading session even if a volatility index observation is missing.
    frame["TargetMagnitudePct"] = 100 * np.log(frame["Close"].shift(-1) / frame["Close"]).abs()
    frame["LabelDate"] = pd.Series(frame.index, index=frame.index).shift(-1)

    qqq_rv20 = annualized_rv(qqq["Close"], 20).rename("QQQ_RV20")
    vxn_close = vxn["Close"].rename("VXN")
    vix_close = vix["Close"].rename("VIX")
    frame = frame.join(qqq_rv20).join(vxn_close).join(vix_close)
    # Compute changes from the ORIGINAL index series rather than after joining
    # to the stock (so we do not silently bridge a missing exogenous date).
    frame = frame.join((vxn["Close"].pct_change(fill_method=None) * 100).rename("VXN_Change"))
    frame = frame.join((vix["Close"].pct_change(fill_method=None) * 100).rename("VIX_Change"))

    # A same-underlying volatility-spread proxy: VXN is an implied-vol index
    # for NASDAQ-100, and QQQ realizes NASDAQ-100 index-like price volatility.
    # This is NOT a single-stock VRP, and is not the textbook variance premium.
    frame["VRP_QQQ"] = frame["VXN"] - frame["QQQ_RV20"]
    frame["VRP_Ratio"] = frame["VXN"] / frame["QQQ_RV20"].replace(0, np.nan)
    # Standardize against the 252 PREVIOUS market observations, not future ones.
    past_vrp = frame["VRP_QQQ"].shift(1)
    vrp_mean = past_vrp.rolling(252, min_periods=252).mean()
    vrp_std = past_vrp.rolling(252, min_periods=252).std(ddof=1)
    frame["VRP_Z252"] = (frame["VRP_QQQ"] - vrp_mean) / vrp_std.replace(0, np.nan)

    valid = ALL_FEATURES + BASELINES + ["TargetMagnitudePct", "LabelDate"]
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=valid).copy()
    return frame


def make_masks(frame: pd.DataFrame, args: argparse.Namespace) -> dict[str, np.ndarray]:
    t = frame.index
    label = pd.to_datetime(frame["LabelDate"])
    intervals = {
        "train": (args.train_start, args.train_end),
        "val": (args.val_start, args.val_end),
        "test": (args.test_start, args.test_end),
    }
    masks = {}
    for group, (start, end) in intervals.items():
        lo, hi = pd.Timestamp(start), pd.Timestamp(end)
        masks[group] = np.asarray((t >= lo) & (t <= hi) & (label <= hi) & (label > t))
    if any(masks[a].sum() == 0 for a in intervals):
        raise ValueError(f"Empty split after complete-case and label-boundary filtering: "
                         f"{ {a: int(b.sum()) for a,b in masks.items()} }")
    # Check no target crosses its own held-out split, and no temporal overlaps.
    assert pd.Timestamp(args.train_end) < pd.Timestamp(args.val_start)
    assert pd.Timestamp(args.val_end) < pd.Timestamp(args.test_start)
    return masks


def make_sequences(x: np.ndarray, y: np.ndarray, n: int, group_mask: np.ndarray):
    # Each window ENDS at the feature cutoff t, and the label is r[t+1].
    indexes = np.flatnonzero(group_mask & (np.arange(len(x)) >= n - 1))
    if len(indexes) == 0:
        raise ValueError("Sequence length exceeds available split")
    x_windows = np.stack([x[i - n + 1:i + 1] for i in indexes]).astype("float32")
    return x_windows, y[indexes].astype("float32"), indexes


def fit_tree(model_name: str, xtr, ytr, xval, yval, xte, seed: int) -> np.ndarray:
    if model_name == "lightgbm":
        import lightgbm as lgb
        model = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.035,
                                 num_leaves=15, max_depth=-1, min_child_samples=30,
                                 colsample_bytree=0.9, objective="regression_l1",
                                 random_state=seed, n_jobs=2, verbosity=-1)
        model.fit(xtr, ytr, eval_set=[(xval, yval)], eval_metric="l1",
                  callbacks=[lgb.early_stopping(40, verbose=False)])
    elif model_name == "xgboost":
        import xgboost as xgb
        model = xgb.XGBRegressor(n_estimators=600, learning_rate=0.035,
                                 max_depth=3, min_child_weight=8,
                                 subsample=0.85, colsample_bytree=0.9,
                                 objective="reg:absoluteerror", eval_metric="mae",
                                 early_stopping_rounds=40, tree_method="hist",
                                 random_state=seed, n_jobs=2)
        model.fit(xtr, ytr, eval_set=[(xval, yval)], verbose=False)
    else:
        raise ValueError(f"Unknown tree model {model_name}")
    return np.clip(model.predict(xte), 0, None)


def fit_sequence(model_name: str, xall: np.ndarray, yall: np.ndarray,
                 masks: dict[str, np.ndarray], seq_len: int, seed: int,
                 epochs: int, batch_size: int) -> tuple[np.ndarray, np.ndarray]:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    xscaler = StandardScaler().fit(xall[masks["train"]])
    yscaler = StandardScaler().fit(yall[masks["train"]].reshape(-1, 1))
    x = xscaler.transform(xall)
    y = yscaler.transform(yall.reshape(-1, 1)).reshape(-1)
    xtr, ytr, _ = make_sequences(x, y, seq_len, masks["train"])
    xval, yval, _ = make_sequences(x, y, seq_len, masks["val"])
    xte, _, indexes = make_sequences(x, y, seq_len, masks["test"])

    class LSTMRegressor(nn.Module):
        def __init__(self, n_features):
            super().__init__()
            self.encoder = nn.LSTM(n_features, 64, num_layers=2, batch_first=True, dropout=0.15)
            self.head = nn.Linear(64, 1)

        def forward(self, z):
            output, _ = self.encoder(z)
            return self.head(output[:, -1, :]).squeeze(-1)

    class MambaRegressor(nn.Module):
        def __init__(self, n_features):
            super().__init__()
            try:
                from mamba_ssm import Mamba
            except ImportError as exc:
                raise RuntimeError("Real mamba-ssm is required. No substitute is used.") from exc
            self.proj = nn.Linear(n_features, 64)
            self.encoder = Mamba(d_model=64, d_state=16, d_conv=4, expand=2)
            self.norm = nn.LayerNorm(64)
            self.head = nn.Linear(64, 1)

        def forward(self, z):
            hidden = self.norm(self.encoder(self.proj(z)))
            return self.head(hidden[:, -1, :]).squeeze(-1)

    if model_name == "mamba" and not torch.cuda.is_available():
        raise RuntimeError("mamba-ssm sequence benchmark requires a CUDA runtime")
    model = (LSTMRegressor if model_name == "lstm" else MambaRegressor)(xall.shape[1]).to(dev)
    optimizer = torch.optim.AdamW(model.parameters(), lr=8e-4, weight_decay=1e-4)
    loss_fn = nn.SmoothL1Loss(beta=0.35)
    loader = DataLoader(TensorDataset(torch.from_numpy(xtr), torch.from_numpy(ytr)),
                        batch_size=batch_size, shuffle=True)
    xval_t = torch.from_numpy(xval).to(dev)
    yval_t = torch.from_numpy(yval).to(dev)
    best_state = None
    best = float("inf")
    stale = 0
    for epoch in range(epochs):
        model.train()
        for xb, yb in loader:
            optimizer.zero_grad()
            out = model(xb.to(dev))
            loss = loss_fn(out, yb.to(dev))
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        model.eval()
        with torch.no_grad():
            val = torch.mean(torch.abs(model(xval_t) - yval_t)).item()
        if val < best - 1e-5:
            best = val
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= 6:
                break
    assert best_state is not None
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        preds = model(torch.from_numpy(xte).to(dev)).cpu().numpy().reshape(-1, 1)
    return np.clip(yscaler.inverse_transform(preds).ravel(), 0, None), indexes


def hac_dm_pvalue(y: np.ndarray, reference: np.ndarray, proposal: np.ndarray,
                  max_lag: int = 5) -> tuple[float, float]:
    """Two-sided asymptotic DM-style test with Bartlett/HAC loss differential.

    Positive mean differential means the proposal beats the reference.
    This is an exploratory statistic, not a guarantee of independence.
    """
    diff = np.abs(y - reference) - np.abs(y - proposal)
    diff = np.asarray(diff, dtype=float)
    n = len(diff)
    if n < 12:
        return float(diff.mean()), float("nan")
    residual = diff - diff.mean()
    long_var = float(np.dot(residual, residual) / n)
    for lag in range(1, min(max_lag, n - 1) + 1):
        cov = float(np.dot(residual[lag:], residual[:-lag]) / n)
        long_var += 2 * (1 - lag / (max_lag + 1)) * cov
    if long_var <= 1e-14:
        return float(diff.mean()), float("nan")
    stat = diff.mean() / math.sqrt(long_var / n)
    return float(diff.mean()), float(2 * norm.sf(abs(stat)))


def run_for_ticker(ticker: str, dataset: pd.DataFrame, args, results: list,
                   metrics: list, tests: list):
    masks = make_masks(dataset, args)
    test_rows = dataset.iloc[np.flatnonzero(masks["test"])].copy()
    ytest = test_rows["TargetMagnitudePct"].to_numpy(float)
    base_mean = test_rows["RollingMean20"].to_numpy(float)
    for name in BASELINES:
        forecast = test_rows[name].to_numpy(float)
        results.extend(dict(ticker=ticker, date=dt.strftime("%Y-%m-%d"),
                            label_date=pd.Timestamp(ld).strftime("%Y-%m-%d"),
                            arm="BASELINE", model=name, seed=args.seed,
                            actual_mag_pct=float(truth), forecast_mag_pct=float(pred))
                       for dt, ld, truth, pred in zip(test_rows.index, test_rows["LabelDate"], ytest, forecast))
        metrics.append(dict(ticker=ticker, arm="BASELINE", model=name, seed=args.seed,
                            n=len(ytest), mae_pp=float(mean_absolute_error(ytest, forecast)),
                            rmse_pp=float(np.sqrt(mean_squared_error(ytest, forecast))),
                            improvement_vs_mean20_pct=(100 * (mean_absolute_error(ytest, base_mean)
                                                         - mean_absolute_error(ytest, forecast)) /
                                                         mean_absolute_error(ytest, base_mean))))

    for arm, columns in FEATURES.items():
        X = dataset[columns].to_numpy(float)
        y = dataset["TargetMagnitudePct"].to_numpy(float)
        for model in args.models:
            if model in ("lightgbm", "xgboost"):
                pred = fit_tree(model, X[masks["train"]], y[masks["train"]],
                                X[masks["val"]], y[masks["val"]], X[masks["test"]], args.seed)
                indexes = np.flatnonzero(masks["test"])
            else:
                pred, indexes = fit_sequence(model, X, y, masks, args.seq_len,
                                             args.seed, args.epochs, args.batch_size)
            actual = y[indexes]
            baseline = dataset["RollingMean20"].to_numpy(float)[indexes]
            selected = dataset.iloc[indexes]
            mae = mean_absolute_error(actual, pred)
            base_mae = mean_absolute_error(actual, baseline)
            metrics.append(dict(ticker=ticker, arm=arm, model=model, seed=args.seed,
                                n=len(actual), mae_pp=float(mae),
                                rmse_pp=float(np.sqrt(mean_squared_error(actual, pred))),
                                improvement_vs_mean20_pct=float(100 * (base_mae - mae) / base_mae)))
            mean_diff, p = hac_dm_pvalue(actual, baseline, pred)
            tests.append(dict(ticker=ticker, arm=arm, model=model,
                              n=len(actual), mean_absolute_error_reduction_pp=mean_diff,
                              p_value_two_sided=p, hac_lags=5))
            results.extend(dict(ticker=ticker, date=dt.strftime("%Y-%m-%d"),
                                label_date=pd.Timestamp(ld).strftime("%Y-%m-%d"),
                                arm=arm, model=model, seed=args.seed,
                                actual_mag_pct=float(truth), forecast_mag_pct=float(fcast))
                           for dt, ld, truth, fcast in zip(selected.index, selected["LabelDate"], actual, pred))
            print(f"  {ticker} {arm:4s} {model:9s} n={len(actual)} MAE={mae:.4f} pp "
                  f"change={100*(base_mae-mae)/base_mae:+.2f}%")


def holm_adjust(tests: pd.DataFrame) -> pd.DataFrame:
    # Family: all model-arm comparisons vs baseline within the same ticker.
    df = tests.copy()
    df["holm_p_within_ticker"] = np.nan
    for ticker, positions in df.groupby("ticker").groups.items():
        indices = [ix for ix in positions if np.isfinite(df.at[ix, "p_value_two_sided"])]
        ordered = sorted(indices, key=lambda i: df.at[i, "p_value_two_sided"])
        previous = 0.0
        m = len(ordered)
        for i, ix in enumerate(ordered):
            previous = max(previous, min(1.0, float(df.at[ix, "p_value_two_sided"]) * (m - i)))
            df.at[ix, "holm_p_within_ticker"] = previous
    return df


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--market-dir", type=Path, default=None, help="Offline CSV directory; otherwise use Yahoo")
    p.add_argument("--out", type=Path, default=Path("outputs/volatility_e1_e2"))
    p.add_argument("--tickers", nargs="+", default=["AAPL", "TSLA"])
    p.add_argument("--models", nargs="+", choices=["lightgbm", "xgboost", "lstm", "mamba"],
                   default=["lightgbm", "xgboost", "lstm"])
    p.add_argument("--download-start", default="2010-01-01")
    p.add_argument("--download-end", default="2026-01-15", help="Yahoo exclusive end date")
    p.add_argument("--train-start", default="2012-01-01")
    p.add_argument("--train-end", default="2022-12-31")
    p.add_argument("--val-start", default="2023-01-01")
    p.add_argument("--val-end", default="2023-12-31")
    p.add_argument("--test-start", default="2024-01-01")
    p.add_argument("--test-end", default="2025-12-31")
    p.add_argument("--seq-len", type=int, default=60)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    if args.seq_len < 2:
        raise ValueError("--seq-len must be >= 2")
    sources = {symbol: load_market_data(symbol, args.market_dir, args.download_start, args.download_end)
               for symbol in [*args.tickers, "QQQ", "VXN", "VIX"]}
    preds, metrics, tests, audit = [], [], [], {}
    for ticker in args.tickers:
        df = build_dataset(sources[ticker], sources["QQQ"], sources["VXN"], sources["VIX"])
        masks = make_masks(df, args)
        audit[ticker] = {key: {"n": int(mask.sum()),
                               "first_feature_date": df.index[mask][0].strftime("%Y-%m-%d"),
                               "last_label_date": pd.Timestamp(df.loc[df.index[mask][-1], "LabelDate"]).strftime("%Y-%m-%d")}
                         for key, mask in masks.items()}
        print(f"\n{ticker} time splits: {audit[ticker]}")
        run_for_ticker(ticker, df, args, preds, metrics, tests)
    df_preds, df_metrics, df_tests = pd.DataFrame(preds), pd.DataFrame(metrics), pd.DataFrame(tests)
    if not df_tests.empty:
        df_tests = holm_adjust(df_tests)
    # Paired ablation tests for the key research question: does added information
    # improve the SAME model on the EXACT SAME held-out dates?
    ablations = []
    comparisons = [("E1", "E2a"), ("E2a", "E2b"), ("E2b", "E2c"),
                   ("E1", "E2b"), ("E1", "E2c")]
    for ticker in args.tickers:
        for model in args.models:
            block = df_preds[(df_preds["ticker"] == ticker) & (df_preds["model"] == model)]
            pred_table = block.pivot(index="date", columns="arm", values="forecast_mag_pct")
            truths = block.drop_duplicates("date").set_index("date")["actual_mag_pct"]
            if (not truths.index.is_unique) or pred_table.isna().any().any():
                raise RuntimeError(f"Ablation samples are not paired: {ticker} {model}")
            actual = truths.loc[pred_table.index].to_numpy(float)
            for ref, candidate in comparisons:
                reference = pred_table[ref].to_numpy(float)
                proposed = pred_table[candidate].to_numpy(float)
                gain, p_value = hac_dm_pvalue(actual, reference, proposed)
                ablations.append(dict(ticker=ticker, model=model, reference=ref,
                                      candidate=candidate, n=len(actual),
                                      mae_reference_pp=float(mean_absolute_error(actual, reference)),
                                      mae_candidate_pp=float(mean_absolute_error(actual, proposed)),
                                      mae_reduction_pp=gain, p_value_two_sided=p_value))
    df_ablations = holm_adjust(pd.DataFrame(ablations))
    df_preds.to_csv(args.out / "predictions.csv", index=False)
    df_metrics.to_csv(args.out / "metrics.csv", index=False)
    df_tests.to_csv(args.out / "dm_tests.csv", index=False)
    df_ablations.to_csv(args.out / "ablation_tests.csv", index=False)
    (args.out / "data_audit.json").write_text(json.dumps({
        "dataset_source": "user CSV" if args.market_dir else "Yahoo via yfinance (auto_adjust=True)",
        "date_cutoff": "after daily session t market and volatility closes published",
        "label": "100 * abs(log(adjusted_close[t+1]/adjusted_close[t]))",
        "common_complete_case_sample": True,
        "all_feature_columns": ALL_FEATURES,
        "features_by_arm": FEATURES,
        "split_boundaries": {x: getattr(args, x) for x in ["train_start", "train_end", "val_start", "val_end", "test_start", "test_end"]},
        "parameters": {"models": args.models, "seq_len": args.seq_len, "epochs": args.epochs,
                       "seed": args.seed},
        "n_per_split": audit,
        "research_limits": [
            "VXN-QQQ_RV20 is a volatility-spread proxy, not conventional variance risk premium",
            "AAPL/TSLA are predicted using index-level VXN/QQQ risk information",
            "No transaction costs or strategy profit assessed",
            "Historical Yahoo data may be revised; record raw download/version for publication",
            "2025 news-study test results are already inspected, so 2025 cannot be a fresh fusion holdout",
        ],
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved files: {args.out.resolve()}")
    return df_metrics


if __name__ == "__main__":
    main()
