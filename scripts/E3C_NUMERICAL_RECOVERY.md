# E3c numerical solver revision1.1

Original output `outputs/e3c_20261026` stopped at66/72 raw CV fits, before any final training/test prediction. Original frozen code, data, model fits and traceback are preserved and hash-protected. No original frozen source is edited.

Failure: TSLA XGBoost candidate1, fold2020, event hybrid calibration. L-BFGS-B returned `ABNORMAL` at theta `[1.0086627655,0.1304032072]`, objective73.66074533490463, gradient `[-1.70e-7,8.57e-7]`. This is a numerical termination issue near the strictly convex optimum, not a data/CUDA/model failure.

New `e3c_calibration_v1_1.py` solves the identical2-parameter objective with projected damped Newton, the exact same penalty20, prior(1,0), slope bounds0..3 and calibration dates. Its Hessian is positive definite because of the fixed ridge penalty. KKT projected gradient tolerance1e-8 is verified and recorded. No event threshold, feature, candidate, seed, label, split, calibration prior, metric or test family changed. One-parameter event heads keep the original solver/formula.

`recover_e3c_v1_1.py` explicitly substitutes the numerical calibration implementation and sends analysis to the new output directory. Its source, the original source and repair tests are all frozen in the new code manifest.66 completed raw fits are copied only after verifying their recorded hashes; they are not retrained. No automatic retry of the stopped original run occurs.

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 CUDA_VISIBLE_DEVICES='' \
  .venv-e3b/bin/python -B scripts/test_e3c_calibration_v1_1.py
.venv-e3b/bin/python -B scripts/recover_e3c_v1_1.py
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 CUDA_VISIBLE_DEVICES='' \
  .venv-e3b/bin/python -B -u scripts/recover_e3c_v1_1.py --execute \
  > outputs/e3c_20261026_v1_1/logs/e3c_run.log 2>&1
```

The completed revised output/ZIP is in `outputs/e3c_20261026_v1_1/`. Original README execution paths describe the preserved first attempt; use this versioned recovery entrypoint for the completed study. CPU analysis replay uses the archived `code/analyze_e3c.py` and the completed revised directory as `--replay-source`; no numerical calibration fitting is needed during replay because all probabilities are archived.
