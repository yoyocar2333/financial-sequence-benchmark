# Research code entrypoints

All source modules live together in `scripts/` to preserve their original imports and project-relative ROOT. Per-stage human-facing organization lives in `research/`. No model executes when a module is merely inspected; do not run training CLI flags during publication checks.

| Stage | Core / execution | Inputs required beyond public tables |
|---|---|---|
| E0 | preserved `notebooks/stock_market_models.ipynb` | legacy market download; not rerun here |
| E1/E2 | `run_mamba_e1_e2b_own_safety.py`, `analyze_mamba_multiseed.py`, `volatility_e1_e2/experiments/volatility_e1_e2.py` | frozen OHLCV/VIX/VXN, original study manifests |
| E3a | `e3a_core.py`, `run_e3a.py`, `plot_e3a.py` | frozen market, earlier prediction artifacts |
| E3b | `e3b_protocol.py`, `e3b_models.py`, `run_e3b.py`, `analyze_e3b.py` | frozen market; public single-fit adapter avoids private archive dependencies |
| E3c | `e3c_core.py`, `e3c_calibration_v1_1.py`, `recover_e3c_v1_1.py`, `analyze_e3c.py` | market, reference model predictions, original fit manifests; see numerical recovery record |
| E4a | `e4a_core.py`, `run_e4a.py`, `extend_e4a_phase7a.py` | authorized original news / timing records |
| E4b | `recover_e4b_news.py`, `extract_e4b_features.py`, `analyze_e4b.py` | authorized news, separately obtained companion project, FinBERT |
| E4c | `e4c_protocol.py`, `run_e4c.py`, `analyze_e4c.py`, `audit_e4c_fnspid.py` | authorized frozen news features and market; FNSPID audit separate |
| E5 | `e5_core.py`, `run_e5.py`, `analyze_e5.py`, `backtest_e5.py` | original market / baseline artifacts; public single-fit adapter available |
| Public replay | `reproduce_public.py`, `validate_publication.py`, `run_public_model.py` | released tables for replay; externally authorized hashed OHLCV for fit |

Legacy orchestration scripts may refer to private `outputs/` trees and copy local reports into manifests. Those trees are intentionally absent. Their preservation is algorithmic provenance, not a promise they can execute from an empty public checkout. See [reproducibility](../docs/REPRODUCIBILITY.md).

`mamba_resource_guard.py` is an archived predecessor; current benchmark runners select `mamba_resource_guard_own_safety.py`. Neither may terminate other users' processes. CUDA/OOM/device errors stop only our work; the old external-growth stop behavior is not the active policy.

The only public adaptation to copied scientific code is the E1 download default's exclusive end date, changed from2026-01-15 to2026-01-01 to avoid accidentally requesting holdout sessions. Frozen-input model calculations are unchanged. The new public adapter and checks are separate code, not replacements for historical measurements.
