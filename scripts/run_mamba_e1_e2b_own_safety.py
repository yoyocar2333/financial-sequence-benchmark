"""Independent genuine-Mamba E1/E2b runner; default action is a CPU-only plan.

Reuses only the preserved original's data/statistics functions. Never invokes
its main(), tree models, LSTM, E2a training, or E2c training.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata
import importlib.util
import json
import logging
import os
from pathlib import Path
import random
import subprocess
import sys
import traceback
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'volatility_e1_e2/experiments/volatility_e1_e2.py'
LOG = logging.getLogger('mamba-e1-e2b')
sys.dont_write_bytecode = True
RESOURCE_GUARD = None


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str,
                                    allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def load_protocol():
    manifest = json.loads((ROOT / 'logs/original-archive-manifest.json').read_text())
    relative = str(SOURCE.relative_to(ROOT))
    if sha256(SOURCE) != manifest['files'][relative]:
        raise RuntimeError('Original protocol changed; review and update provenance before use')
    spec = importlib.util.spec_from_file_location('preserved_e1_e2_protocol', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tickers', nargs='+', choices=['AAPL', 'TSLA'], default=['AAPL', 'TSLA'])
    p.add_argument('--arms', nargs='+', choices=['E1', 'E2b'], default=['E1', 'E2b'])
    source = p.add_mutually_exclusive_group()
    source.add_argument('--market-dir', type=Path, help='Existing adjusted market CSVs')
    source.add_argument('--download-data', action='store_true', help='Download and freeze Yahoo auto_adjust=True data')
    p.add_argument('--csv-price-policy', choices=['adjusted'], help='Required acknowledgement for local CSV inputs')
    p.add_argument('--out', type=Path, default=ROOT / 'outputs/mamba_e1_e2b_seed42')
    p.add_argument('--download-start', default='2010-01-01')
    p.add_argument('--download-end', default='2026-01-15', help='Yahoo exclusive end date')
    for split, start, end in [('train', '2012-01-01', '2022-12-31'),
                              ('val', '2023-01-01', '2023-12-31'),
                              ('test', '2024-01-01', '2025-12-31')]:
        p.add_argument(f'--{split}-start', default=start)
        p.add_argument(f'--{split}-end', default=end)
    p.add_argument('--seq-len', type=int, default=60)
    p.add_argument('--epochs', type=int, default=30)
    p.add_argument('--batch-size', type=int, default=8)
    p.add_argument('--eval-batch-size', type=int, default=8)
    p.add_argument('--memory-fraction', type=float, default=0.10)
    p.add_argument('--gpu-duty-cycle', type=float, default=0.25)
    p.add_argument('--validation-only', action='store_true', help='Health probe: no test evaluation')
    p.add_argument('--max-train-batches', type=int, default=None, help='Only permitted for validation-only health probe')
    p.add_argument('--seed', type=int, default=42)
    action = p.add_mutually_exclusive_group()
    action.add_argument('--plan', action='store_true', help='Print plan without imports, data downloads, or GPU access')
    action.add_argument('--execute-training', action='store_true', help='Start formal training ONLY after separate user confirmation')
    args = p.parse_args(argv)
    args.out = args.out.resolve()
    if not args.out.is_relative_to((ROOT / 'outputs').resolve()) or args.out == ROOT / 'outputs':
        p.error('--out must be a run subdirectory under stock_prediction/outputs')
    if args.seq_len < 2 or min(args.epochs, args.batch_size, args.eval_batch_size) < 1:
        p.error('Invalid sequence length, epoch count, or batch size')
    if not 0 < args.memory_fraction <= 0.10 or not 0 < args.gpu_duty_cycle <= 0.25:
        p.error('Low resource mode requires allocator fraction <=0.10 and duty cycle <=0.25')
    if args.max_train_batches is not None and (not args.validation_only or args.max_train_batches < 1):
        p.error('--max-train-batches is positive and only allowed for a validation-only probe')
    if args.batch_size > 8 or args.eval_batch_size > 8:
        p.error('Low resource mode caps training and evaluation batches at 8')
    if len(set(args.arms)) != len(args.arms) or len(set(args.tickers)) != len(args.tickers):
        p.error('Duplicate tickers/arms are not allowed')
    if args.execute_training:
        if not args.market_dir and not args.download_data:
            p.error('Select --market-dir or explicitly permit --download-data')
        if args.market_dir and args.csv_price_policy != 'adjusted':
            p.error('Local CSVs require --csv-price-policy adjusted and a verified common adjustment policy')
    return args


def plan(args):
    return {'action': 'TRAIN' if args.execute_training else 'PLAN_ONLY',
            'model': 'mamba_ssm.Mamba', 'tickers': args.tickers, 'arms': args.arms,
            'seed': args.seed, 'target': '100 * abs(log(adjusted_close[t+1]/adjusted_close[t]))',
            'features': {'E1': ['Open', 'High', 'Low', 'Close', 'Volume', 'MA5', 'MA20', 'Volatility_10'],
                         'E2b_added': ['RV5', 'RV20', 'VXN', 'VXN_Change', 'VIX', 'VIX_Change']},
            'splits': {s: [getattr(args, s + '_start'), getattr(args, s + '_end')]
                       for s in ('train', 'val', 'test')},
            'seq_len': args.seq_len, 'epochs_max': args.epochs, 'batch_size': args.batch_size,
            'eval_batch_size': args.eval_batch_size, 'early_stopping_patience': 6,
            'allocator_fraction': args.memory_fraction, 'gpu_duty_cycle_target': args.gpu_duty_cycle,
            'batch_size_deviation': '8 instead of original 64; more optimizer updates per epoch, altered stochastic trajectory; exploratory extension',
            'exploratory_extension': True, 'validation_only': args.validation_only,
            'sample_policy': 'original E2c common complete-case dates; retained-observation windows',
            'data': str(args.market_dir) if args.market_dir else ('Yahoo frozen on execution' if args.download_data else 'NOT_SELECTED'),
            'out': str(args.out), 'training_requires_separate_confirmation': True}


def prepare_arrays(protocol, dataset, columns, args):
    import numpy as np
    from sklearn.preprocessing import StandardScaler
    masks = protocol.make_masks(dataset, args)
    x = dataset[columns].to_numpy(float)
    y = dataset['TargetMagnitudePct'].to_numpy(float)
    xscaler = StandardScaler().fit(x[masks['train']])
    yscaler = StandardScaler().fit(y[masks['train']].reshape(-1, 1))
    x = xscaler.transform(x)
    y = yscaler.transform(y.reshape(-1, 1)).ravel()
    assert np.isfinite(x).all() and np.isfinite(y).all()
    arrays = {split: protocol.make_sequences(x, y, args.seq_len, masks[split])
              for split in ('train', 'val', 'test')}
    return arrays, xscaler, yscaler


def fit_mamba(arrays, xscaler, yscaler, args, artifact_dir):
    import numpy as np
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset
    from mamba_ssm import Mamba
    artifact_dir.mkdir(parents=True, exist_ok=False)
    log_handler = logging.FileHandler(artifact_dir / 'training.log')
    LOG.addHandler(log_handler)
    write_json(artifact_dir / 'environment.json', {'python': sys.version,
        'versions': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()},
        'torch_cuda': torch.version.cuda, 'allocator_fraction': args.memory_fraction})
    write_json(artifact_dir / 'config.json', vars(args))
    if not torch.cuda.is_available():
        raise RuntimeError('Genuine Mamba requires CUDA; no CPU fallback')
    if torch.cuda.mem_get_info()[0] < 2 * 1024**3:
        raise RuntimeError('Less than 2 GiB free GPU memory; defer formal training')
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.set_num_threads(2)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False

    class MambaRegressor(nn.Module):
        def __init__(self, n_features):
            super().__init__()
            self.proj = nn.Linear(n_features, 64)
            self.encoder = Mamba(d_model=64, d_state=16, d_conv=4, expand=2)
            self.norm = nn.LayerNorm(64)
            self.head = nn.Linear(64, 1)

        def forward(self, z):
            return self.head(self.norm(self.encoder(self.proj(z)))[:, -1, :]).squeeze(-1)

    xtr, ytr, _ = arrays['train']
    xval, yval, _ = arrays['val']
    xte, _, indexes = arrays['test']
    model = MambaRegressor(xtr.shape[-1]).cuda()
    optimizer = torch.optim.AdamW(model.parameters(), lr=8e-4, weight_decay=1e-4)
    loss_fn = nn.SmoothL1Loss(beta=0.35)
    generator = torch.Generator().manual_seed(args.seed)
    loader = DataLoader(TensorDataset(torch.from_numpy(xtr), torch.from_numpy(ytr)),
                        batch_size=args.batch_size, shuffle=True, generator=generator, num_workers=0)

    def predict_scaled(values):
        model.eval()
        output = []
        with torch.no_grad():
            for start in range(0, len(values), args.eval_batch_size):
                RESOURCE_GUARD.check()
                started = time.monotonic()
                batch = torch.from_numpy(values[start:start + args.eval_batch_size]).cuda()
                output.append(model(batch).cpu().numpy())
                RESOURCE_GUARD.paced_sync(started)
        result = np.concatenate(output)
        if not np.isfinite(result).all():
            raise RuntimeError('Nonfinite validation/test prediction')
        return result

    best, best_state, stale, history, best_epoch = float('inf'), None, 0, [], 0
    for epoch in range(args.epochs):
        model.train()
        total_loss, n = 0.0, 0
        first_batch_loss, last_batch_loss = None, None
        for batch_index, (xb, yb) in enumerate(loader):
            if args.max_train_batches is not None and batch_index >= args.max_train_batches:
                break
            RESOURCE_GUARD.check()
            started = time.monotonic()
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(xb.cuda()), yb.cuda())
            if not torch.isfinite(loss).item():
                raise RuntimeError('Nonfinite training loss')
            if first_batch_loss is None:
                first_batch_loss = loss.item()
            last_batch_loss = loss.item()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
            optimizer.step()
            total_loss += loss.item() * len(xb)
            n += len(xb)
            RESOURCE_GUARD.paced_sync(started)
        validation_mae = float(np.abs(predict_scaled(xval) - yval).mean())
        history.append({'epoch': epoch + 1, 'train_smooth_l1_scaled': total_loss / n,
                        'validation_mae_scaled': validation_mae,
                        'validation_mae_pp': validation_mae * float(yscaler.scale_[0]),
                        'cuda_allocated_bytes': torch.cuda.memory_allocated(),
                        'cuda_reserved_bytes': torch.cuda.memory_reserved(),
                        'cuda_peak_allocated_bytes': torch.cuda.max_memory_allocated(),
                        'first_batch_loss': first_batch_loss, 'last_batch_loss': last_batch_loss,
                        'train_batches': min(len(loader), args.max_train_batches or len(loader))})
        LOG.info('%s epoch=%d train_loss=%.6f validation_mae_scaled=%.6f',
                 artifact_dir.name, epoch + 1, total_loss / n, validation_mae)
        if validation_mae < best - 1e-5:
            best = validation_mae
            best_epoch = epoch + 1
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            torch.save(best_state, artifact_dir / 'best_state.pt.tmp')
            (artifact_dir / 'best_state.pt.tmp').replace(artifact_dir / 'best_state.pt')
            stale = 0
        else:
            stale += 1
        import pandas as pd
        pd.DataFrame(history).to_csv(artifact_dir / 'training_history.csv.tmp', index=False)
        (artifact_dir / 'training_history.csv.tmp').replace(artifact_dir / 'training_history.csv')
        torch.save({'epoch': epoch + 1, 'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
                    'seed': args.seed, 'best_validation_mae_scaled': best,
                    'batch_size': args.batch_size, 'memory_fraction': args.memory_fraction},
                   artifact_dir / 'checkpoint_latest.pt.tmp')
        (artifact_dir / 'checkpoint_latest.pt.tmp').replace(artifact_dir / 'checkpoint_latest.pt')
        write_json(artifact_dir / 'progress.json', {'status': 'TRAINING', 'epoch': epoch + 1,
                    'best_epoch': best_epoch, 'best_validation_mae_scaled': best,
                    'last_epoch': history[-1]})
        if stale >= 6:
            break
    if best_state is None:
        raise RuntimeError('No finite validation checkpoint')
    model.load_state_dict(best_state)
    evaluation_split = 'val' if args.validation_only else 'test'
    evaluation_x, _, indexes = arrays[evaluation_split]
    prediction = np.clip(yscaler.inverse_transform(predict_scaled(evaluation_x).reshape(-1, 1)).ravel(), 0, None)
    torch.cuda.synchronize()
    torch.save(best_state, artifact_dir / 'best_state.pt')
    write_json(artifact_dir / 'training.json', {
        'history': history, 'best_validation_mae_scaled': best, 'best_epoch': best_epoch,
        'parameter_count': sum(p.numel() for p in model.parameters()),
        'x_scaler': {'mean': xscaler.mean_.tolist(), 'scale': xscaler.scale_.tolist(),
                     'var': xscaler.var_.tolist(), 'n_samples_seen': int(xscaler.n_samples_seen_)},
        'y_scaler': {'mean': yscaler.mean_.tolist(), 'scale': yscaler.scale_.tolist(),
                     'var': yscaler.var_.tolist(), 'n_samples_seen': int(yscaler.n_samples_seen_)},
        'architecture': {'d_model': 64, 'd_state': 16, 'd_conv': 4, 'expand': 2},
        'optimizer': {'name': 'AdamW', 'lr': 8e-4, 'weight_decay': 1e-4},
        'loss': {'name': 'SmoothL1Loss', 'beta': 0.35},
        'shuffle_generator_seed': args.seed,
        'batch_size': args.batch_size, 'original_batch_size': 64,
        'memory_fraction': args.memory_fraction, 'gpu_duty_cycle': args.gpu_duty_cycle,
        'evaluation_split': evaluation_split, 'exploratory_extension': True,
    })
    write_json(artifact_dir / 'progress.json', {'status': 'COMPLETE', 'best_epoch': best_epoch,
               'evaluation_split': evaluation_split})
    LOG.removeHandler(log_handler)
    log_handler.close()
    return prediction, indexes


def run_training(args):
    global RESOURCE_GUARD
    from mamba_resource_guard_own_safety import ResourceGuard
    RESOURCE_GUARD = ResourceGuard(ROOT, args.out, args.memory_fraction, args.gpu_duty_cycle)
    import numpy as np
    import pandas as pd
    import torch
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    if Path(sys.prefix).resolve() != ROOT / '.venv-mamba':
        raise RuntimeError('Use stock_prediction/.venv-mamba/bin/python')
    smoke = json.loads((ROOT / 'logs/mamba-smoke-result.json').read_text())
    if (smoke.get('status') != 'PASSED' or smoke.get('torch') != torch.__version__
            or smoke.get('mamba_ssm') != importlib.metadata.version('mamba-ssm')):
        raise RuntimeError('A passing smoke test for the current environment is required')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; no CPU fallback')
    protocol = load_protocol()
    # Validate boundaries even before creating outputs or fetching data.
    for split in ('train', 'val', 'test'):
        if pd.Timestamp(getattr(args, split + '_start')) > pd.Timestamp(getattr(args, split + '_end')):
            raise ValueError('Reversed split interval: ' + split)
    if not (pd.Timestamp(args.train_end) < pd.Timestamp(args.val_start)
            and pd.Timestamp(args.val_end) < pd.Timestamp(args.test_start)):
        raise ValueError('Splits must be ordered and disjoint')
    if args.out.exists() and any(args.out.iterdir()):
        raise FileExistsError('Refusing to overwrite previous run: ' + str(args.out))
    args.out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                        handlers=[logging.StreamHandler(), logging.FileHandler(args.out / 'run.log')])
    write_json(args.out / 'config.json', vars(args))
    audit = {'status': 'RUNNING', 'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
             'source_sha256': sha256(SOURCE), 'runner_sha256': sha256(__file__),
             'versions': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()},
             'python': sys.version, 'torch_cuda': torch.version.cuda,
             'gpu': torch.cuda.get_device_name(0), 'cxx11_abi': torch._C._GLIBCXX_USE_CXX11_ABI,
             'plan': plan(args), 'inputs': {}, 'tickers': {},
             'resource_baseline': RESOURCE_GUARD.baseline,
             'limitations': ['Daily dates do not prove exact publication times.',
                            'E2c complete-case filtering can remove long intervals after missing VRP inputs.',
                            'Retained-row windows can span missing stock sessions.',
                            'Single seed does not measure initialization uncertainty.',
                            'Custom CUDA kernels may not be bitwise deterministic.',
                            'Historical adjusted Yahoo data are not a point-in-time archive.']}
    try:
        snapshot = args.out / 'market_snapshot'
        snapshot.mkdir()
        sources = {}
        for symbol in [*args.tickers, 'QQQ', 'VXN', 'VIX']:
            frame = protocol.load_market_data(symbol, args.market_dir, args.download_start, args.download_end)
            file = snapshot / f'{symbol}.csv'
            frame.rename_axis('Date').to_csv(file)
            entry = {'snapshot_sha256': sha256(file), 'rows': len(frame),
                     'first': str(frame.index.min()), 'last': str(frame.index.max()),
                     'price_policy': 'auto_adjust=True' if args.download_data else args.csv_price_policy}
            if args.market_dir:
                entry['input_sha256'] = sha256(args.market_dir / f'{symbol}.csv')
            audit['inputs'][symbol] = entry
            sources[symbol] = frame
        with (args.out / 'environment.lock.txt').open('w') as lockfile:
            subprocess.run([sys.executable, '-m', 'pip', 'freeze', '--all'], check=True, stdout=lockfile)
        write_json(args.out / 'data_audit.json', audit)
        results, metrics, baseline_tests, ablation_tests = [], [], [], []
        for ticker in args.tickers:
            dataset = protocol.build_dataset(sources[ticker], sources['QQQ'], sources['VXN'], sources['VIX'])
            masks = protocol.make_masks(dataset, args)
            stock_positions = sources[ticker].index.get_indexer(dataset.index)
            gaps = np.r_[0, (np.diff(stock_positions) > 1).astype(int)]
            prefix = np.r_[0, np.cumsum(gaps)]
            reference_indexes, forecasts = None, {}
            ticker_audit = {'source_stock_rows': len(sources[ticker]), 'retained_rows': len(dataset),
                            'removed_stock_feature_dates': sources[ticker].index.difference(dataset.index).strftime('%Y-%m-%d').tolist(),
                            'features': {a: protocol.FEATURES[a] for a in args.arms}, 'splits': {}}
            for split, mask in masks.items():
                indexes = np.flatnonzero(mask & (np.arange(len(dataset)) >= args.seq_len - 1))
                if not len(indexes):
                    raise ValueError('No sequence endpoints in ' + ticker + ' ' + split)
                ticker_audit['splits'][split] = {'n': len(indexes),
                    'first_cutoff': str(dataset.index[indexes[0]]),
                    'last_label': str(dataset.iloc[indexes[-1]]['LabelDate']),
                    'windows_with_session_gaps': int(np.sum(prefix[indexes + 1] - prefix[indexes - args.seq_len + 2] > 0))}
            audit['tickers'][ticker] = ticker_audit
            write_json(args.out / 'data_audit.json', audit)
            for arm in args.arms:
                arrays, xs, ys = prepare_arrays(protocol, dataset, protocol.FEATURES[arm], args)
                pred, indexes = fit_mamba(arrays, xs, ys, args, args.out / f'{ticker}_{arm}')
                if reference_indexes is None:
                    reference_indexes = indexes
                else:
                    np.testing.assert_array_equal(reference_indexes, indexes)
                forecasts[arm] = pred
            selected = dataset.iloc[reference_indexes]
            truth = selected['TargetMagnitudePct'].to_numpy(float)
            baseline = selected['RollingMean20'].to_numpy(float)
            baseline_mae = mean_absolute_error(truth, baseline)
            for name, forecast, arm in [(name, selected[name].to_numpy(float), 'BASELINE') for name in protocol.BASELINES] + [
                    ('mamba', forecasts[arm], arm) for arm in args.arms]:
                mae = mean_absolute_error(truth, forecast)
                metrics.append({'ticker': ticker, 'model': name, 'arm': arm, 'seed': args.seed,
                                'split': 'val' if args.validation_only else 'test',
                                'n': len(truth), 'mae_pp': mae,
                                'rmse_pp': float(np.sqrt(mean_squared_error(truth, forecast))),
                                'improvement_vs_mean20_pct': 100 * (baseline_mae - mae) / baseline_mae if baseline_mae else np.nan})
                results.extend({'ticker': ticker, 'date': date.strftime('%Y-%m-%d'),
                                'label_date': pd.Timestamp(label).strftime('%Y-%m-%d'),
                                'model': name, 'arm': arm, 'seed': args.seed,
                                'split': 'val' if args.validation_only else 'test',
                                'actual_mag_pct': float(actual), 'forecast_mag_pct': float(value)}
                               for date, label, actual, value in zip(selected.index, selected['LabelDate'], truth, forecast))
                if arm != 'BASELINE':
                    gain, pvalue = protocol.hac_dm_pvalue(truth, baseline, forecast)
                    baseline_tests.append({'ticker': ticker, 'model': name, 'arm': arm, 'n': len(truth),
                                           'mean_absolute_error_reduction_pp': gain,
                                           'p_value_two_sided': pvalue, 'hac_lags': 5})
            if 'E1' in forecasts and 'E2b' in forecasts:
                gain, pvalue = protocol.hac_dm_pvalue(truth, forecasts['E1'], forecasts['E2b'])
                ablation_tests.append({'ticker': ticker, 'model': 'mamba', 'reference': 'E1', 'candidate': 'E2b',
                                       'n': len(truth), 'mae_reduction_pp': gain,
                                       'mae_reference_pp': mean_absolute_error(truth, forecasts['E1']),
                                       'mae_candidate_pp': mean_absolute_error(truth, forecasts['E2b']),
                                       'p_value_two_sided': pvalue})
            pd.DataFrame(results).to_csv(args.out / 'predictions.csv', index=False)
            pd.DataFrame(metrics).to_csv(args.out / 'metrics.csv', index=False)
            for arm in args.arms:
                directory = args.out / f'{ticker}_{arm}'
                pp = pd.DataFrame(results)
                pp[(pp.ticker == ticker) & (pp.arm == arm)].to_csv(directory / 'predictions.csv', index=False)
                mm = pd.DataFrame(metrics)
                mm[(mm.ticker == ticker) & (mm.arm == arm)].to_csv(directory / 'metrics.csv', index=False)
                write_json(directory / 'environment.json', {'python': sys.version, 'versions': audit['versions'],
                           'torch_cuda': torch.version.cuda, 'gpu': audit['gpu'],
                           'allocator_fraction': args.memory_fraction, 'seed': args.seed,
                           'evaluation_split': 'val' if args.validation_only else 'test'})
        protocol.holm_adjust(pd.DataFrame(baseline_tests)).to_csv(args.out / 'dm_tests.csv', index=False)
        if ablation_tests:
            protocol.holm_adjust(pd.DataFrame(ablation_tests)).to_csv(args.out / 'ablation_tests.csv', index=False)
        else:
            pd.DataFrame(columns=['ticker', 'model', 'reference', 'candidate', 'n', 'mae_reduction_pp',
                                  'p_value_two_sided']).to_csv(args.out / 'ablation_tests.csv', index=False)
        audit['status'] = 'COMPLETE'
        write_json(args.out / 'data_audit.json', audit)
        LOG.info('Completed %s', args.out)
    except BaseException:
        audit.update(status='FAILED', traceback=traceback.format_exc())
        write_json(args.out / 'data_audit.json', audit)
        for ticker in args.tickers:
            for arm in args.arms:
                directory = args.out / f'{ticker}_{arm}'
                if directory.exists() and not (directory / 'metrics.csv').exists():
                    write_json(directory / 'failure.json', {'status': 'STOPPED', 'traceback': audit['traceback']})
        LOG.exception('Experiment failed; original data and partial artifacts retained')
        raise


def main(argv=None):
    args = parse_args(argv)
    if not args.execute_training:
        print(json.dumps(plan(args), indent=2, ensure_ascii=False))
        return 0
    for key, path in {'XDG_CACHE_HOME': '.cache', 'HF_HOME': '.cache/huggingface', 'TMPDIR': '.cache/tmp',
                       'TORCH_EXTENSIONS_DIR': '.cache/torch_extensions',
                       'TRITON_CACHE_DIR': '.cache/triton', 'CUDA_CACHE_PATH': '.cache/cuda'}.items():
        os.environ[key] = str(ROOT / path)
        (ROOT / path).mkdir(parents=True, exist_ok=True)
    os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
    run_training(args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
