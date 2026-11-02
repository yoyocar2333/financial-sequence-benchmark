"""Frozen paths, training configuration, and integrity guards for stage 2."""
import datetime as dt
import json
from pathlib import Path

from run_mamba_e1_e2b import load_protocol, parse_args, sha256, write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/mamba_multiseed_20261020'
OLD = ROOT / 'outputs/mamba_low_resource_20261019_seed42'
MARKET = ROOT / 'data/market_20261019'
SEEDS = (42,43,44,45,46)
NEW_SEEDS = (43,44,45,46)
PAIRS = (('AAPL','E1'),('AAPL','E2b'),('TSLA','E1'),('TSLA','E2b'))
TASKS = [(seed,ticker,arm) for seed in NEW_SEEDS for ticker,arm in PAIRS]
STAT_PLAN = {
    'stage':'exploratory stability on already-inspected 2024-2025 sample; not preregistration or new confirmation',
    'seeds':list(SEEDS),'new_training_seeds':list(NEW_SEEDS),
    'loss_differential':'abs(error_E1) - abs(error_E2b); positive favors E2b',
    'hypothesis':'two-sided zero mean daily absolute-loss differential',
    'primary_inference':'Newey-West/Bartlett HAC, fixed lag 10, normal approximation, no small-sample correction',
    'bootstrap':'circular fixed-length blocks of consecutive retained trading observations; all paired losses kept together',
    'bootstrap_replicates':9999,'bootstrap_rng_seed':20261020,
    'primary_block_length':10,'sensitivity_lengths':[5,20],
    'bootstrap_p':'null-centered bootstrap mean, two-sided absolute statistic, plus-one Monte Carlo correction',
    'bootstrap_ci':'basic 95% interval, nominal not simultaneous',
    'multiplicity':'one pre-specified family of 12 comparisons (2 tickers x [5 same-seed pairs + daily seed-average]); Holm across 12 separately for each fixed method/bandwidth',
    'decision_rule':'primary HAC lag10 Holm-adjusted p<0.05; bootstrap is corroboration, not an alternative significance selector',
    'aggregate_unit':'501 dates; average five same-date seed loss differentials before HAC/bootstrap; never pool seeds as independent days',
    'seed_sd':'sample standard deviation ddof=1 across five seeds; not a test-data standard error',
    'extremes':'same training-target p95 thresholds as seed42; retrospective outcome stratum',
    'market_regimes':'cutoff VXN >= training VXN p75 versus lower; year2024/year2025; descriptive only, no regime p-value selection',
    'nonstationarity_limit':'HAC/bootstrap require weak dependence/approximate stationarity; regime shifts and small tail samples limit inference',
    'references':[
        'https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html',
        'https://bashtage.github.io/arch/bootstrap/generated/arch.bootstrap.CircularBlockBootstrap.html',
        'https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html']}


def case_root(seed,ticker,arm):
    return (OLD if seed==42 else OUT/f'seed_{seed}')/f'{ticker}_{arm}'


def leaf(seed,ticker,arm):
    return case_root(seed,ticker,arm)/f'{ticker}_{arm}'


def check_protected():
    manifest=json.loads((OUT/'protected_seed42_manifest.json').read_text())
    actual={str(p.relative_to(OLD)):sha256(p) for p in OLD.rglob('*') if p.is_file()}
    if actual!=manifest['files']:
        raise RuntimeError('Seed42 tree changed; stop without overwriting or retraining it')
    locked=json.loads((OUT/'integrity_manifest.json').read_text())
    for name,h in locked['files'].items():
        if sha256(ROOT/name)!=h:raise RuntimeError('Frozen code/data changed: '+name)


def prepare():
    import numpy as np
    if (OUT/'preparation_complete.json').exists():
        check_protected()
        return
    if json.loads((OLD/'suite_status.json').read_text())['status']!='COMPLETE':
        raise RuntimeError('Seed42 not complete')
    OUT.mkdir(parents=True,exist_ok=True)
    old_status=json.loads((OLD/'suite_status.json').read_text())
    for name,h in old_status['script_sha256'].items():
        if sha256(ROOT/name)!=h:raise RuntimeError('Cannot change validated trainer: '+name)
    write_json(OUT/'protected_seed42_manifest.json',{'files':{str(p.relative_to(OLD)):sha256(p) for p in OLD.rglob('*') if p.is_file()}})
    provenance=json.loads((MARKET/'provenance.json').read_text())
    files={str((MARKET/'provenance.json').relative_to(ROOT)):sha256(MARKET/'provenance.json')}
    for ticker,info in provenance['symbols'].items():
        for p,h in [(MARKET/f'{ticker}.csv',info['adjusted_sha256']), (MARKET/'raw'/f'{ticker}.csv',info['raw_sha256'])]:
            if sha256(p)!=h:raise RuntimeError('Market input hash mismatch: '+str(p))
            files[str(p.relative_to(ROOT))]=h
    for p in [ROOT/'scripts/run_mamba_e1_e2b.py',ROOT/'scripts/mamba_resource_guard.py',
              ROOT/'volatility_e1_e2/experiments/volatility_e1_e2.py',ROOT/'requirements-mamba.lock.txt']:
        files[str(p.relative_to(ROOT))]=sha256(p)
    write_json(OUT/'integrity_manifest.json',{'files':files})
    plan={**STAT_PLAN,'frozen_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    write_json(OUT/'statistical_plan.json',plan)
    protocol=load_protocol();args=parse_args([])
    sources={n:protocol.load_market_data(n,MARKET,args.download_start,args.download_end) for n in ('AAPL','TSLA','QQQ','VXN','VIX')}
    audit=json.loads((OLD/'data_audit_frozen.json').read_text())
    states={}
    for ticker in ('AAPL','TSLA'):
        frame=protocol.build_dataset(sources[ticker],sources['QQQ'],sources['VXN'],sources['VIX'])
        masks=protocol.make_masks(frame,args)
        indexes=np.flatnonzero(masks['test'] & (np.arange(len(frame))>=args.seq_len-1))
        if frame.index[indexes].strftime('%Y-%m-%d').tolist()!=audit['tickers'][ticker]['test_dates']:
            raise RuntimeError('Seed42 test calendar changed')
        p95=float(frame.loc[masks['train'],'TargetMagnitudePct'].quantile(.95))
        if p95!=audit['tickers'][ticker]['extreme_threshold_train_p95']:
            raise RuntimeError('Extreme threshold changed')
        p75=float(frame.loc[masks['train'],'VXN'].quantile(.75))
        selected=frame.iloc[indexes]
        state=selected[['LabelDate','TargetMagnitudePct','VXN']].copy()
        state['extreme']=state.TargetMagnitudePct>=p95
        state['high_vxn']=state.VXN>=p75
        state['year']=state.index.year
        state.rename_axis('date').to_csv(OUT/f'{ticker}_frozen_states.csv')
        states[ticker]={'extreme_train_p95':p95,'vxn_train_p75':p75,'n_test':len(state),
                        'state_csv_sha256':sha256(OUT/f'{ticker}_frozen_states.csv')}
    write_json(OUT/'frozen_state_thresholds.json',states)
    (OUT/'environment.lock.txt').write_bytes((ROOT/'requirements-mamba.lock.txt').read_bytes())
    for p in [OUT/'statistical_plan.json', OUT/'frozen_state_thresholds.json',
              OUT/'AAPL_frozen_states.csv', OUT/'TSLA_frozen_states.csv',
              ROOT/'scripts/multiseed_common.py', ROOT/'scripts/analyze_mamba_multiseed.py',
              ROOT/'scripts/run_mamba_multiseed.py', ROOT/'scripts/start_mamba_multiseed.sh']:
        files[str(p.relative_to(ROOT))]=sha256(p)
    write_json(OUT/'integrity_manifest.json',{'files':files})
    check_protected()
    write_json(OUT/'preparation_complete.json',{'status':'READY','new_cases':16,'total_cases':20})
