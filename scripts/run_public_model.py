"""Explicit, fresh-output E3b/E5 single-fit adapter for authorized frozen market files.

Nothing is downloaded. A GPU fit requires --allow-gpu. Publication never runs it.
"""
import argparse,csv,json,shutil
from pathlib import Path
import numpy as np
import pandas as pd
import e3b_protocol as bp
import e5_core as ec

ROOT=Path(__file__).resolve().parents[1]

def load_authorized_market(directory,ticker):
    with (ROOT/'docs/FROZEN_INPUTS.csv').open(newline='') as f:
        expected={r['file']:r['sha256'] for r in csv.DictReader(f)}
    names=[n+'_adjusted_through2025.csv' for n in [ticker,'QQQ','VIX','VXN']]
    for n in names:
        p=directory/n
        if not p.is_file():raise FileNotFoundError('Authorized frozen input missing: '+n)
        if bp.sha(p)!=expected[n]:raise ValueError('Frozen input hash mismatch: '+n+'; do not substitute revised downloads')
        with p.open(newline='') as f:
            dates=[r['Date'] for r in csv.DictReader(f)]
        if any(d[:10]>'2025-12-31' for d in dates):raise ValueError('Post2025 input prohibited')
    return names

def arrays_for(f,stage,arm):
    if stage=='E5':return ec.block_arrays(f,arm,bp.FINAL)
    x,meta=bp.feature_matrix(f,arm,bp.FINAL['fit_end'])
    ranges={'fit':('2012-01-01',bp.FINAL['fit_end']),'stop':(bp.FINAL['stop_start'],bp.FINAL['stop_end']),
        'cal':(bp.FINAL['cal_start'],bp.FINAL['cal_end']),'test':(bp.FINAL['test_start'],bp.FINAL['test_end'])}
    ids={k:bp.indices(f,a,b) for k,(a,b) in ranges.items()}
    arrays={k:(bp.windows(x,ii),f.y5.iloc[ii].to_numpy()) for k,ii in ids.items()}
    return arrays,ids,meta

def execute(a):
    if a.output.exists():raise FileExistsError('Output must be new; refuse overwrite')
    if a.model in ['mamba','lstm'] and not a.allow_gpu:raise ValueError('Neural training requires explicit --allow-gpu')
    if a.arm not in (['A','B'] if a.stage=='E3b' else ['B','T']):raise ValueError('Unsupported stage/arm')
    if a.allow_gpu and a.model not in ['mamba','lstm']:raise ValueError('--allow-gpu is unnecessary for CPU models')
    names=load_authorized_market(a.market_dir,a.ticker)
    a.output.mkdir(parents=True);(a.output/'inputs').mkdir()
    for n in names:shutil.copy2(a.market_dir/n,a.output/'inputs'/n)
    # All state derives from external frozen files, never the original project path.
    if a.stage=='E5':
        ec.SOURCE=a.output;f=ec.load(a.ticker)
    else:f=bp.load_frame(a.ticker,source=a.output)
    arrays,ids,meta=arrays_for(f,a.stage,a.arm)
    assert len(ids['test'])==482 and np.isfinite(arrays['fit'][0]).all()
    if a.stage=='E3b' or a.arm=='B':
        selected=json.loads((ROOT/'research/E3b/config/selected_configs.json').read_text())
        config=selected[f'{a.ticker}_h5_{a.arm}_{a.model}']['config']
    else:
        selected=json.loads((ROOT/'research/E5/config/selected_configs.json').read_text())
        config=selected[f'{a.ticker}_{a.model}_{a.arm}']['config']
    guard=None
    try:
        if a.allow_gpu:
            from mamba_resource_guard_own_safety import ResourceGuard
            (ROOT/'logs').mkdir(exist_ok=True)
            guard=ResourceGuard(ROOT,a.output,fraction=.10,duty=.50)
            if a.model=='mamba':
                from mamba_ssm import Mamba
                import selective_scan_cuda
                assert Mamba.__module__.startswith('mamba_ssm.')
        from e3b_models import fit_job
        raw,info=fit_job(a.model,config,a.seed,arrays,a.output/'fit',{'stage':a.stage,'ticker':a.ticker,'arm':a.arm,'preprocessing':meta,'source':'authorized hash-checked public adapter'},guard)
        p,c=bp.calibrate(raw['cal'],arrays['cal'][1],raw['test'])
        result=pd.DataFrame({'date':f.index[ids['test']].strftime('%Y-%m-%d'),'target_reversal':arrays['test'][1],'p_raw':raw['test'],'p_calibrated':p})
        result.to_csv(a.output/'predictions.csv',index=False)
        bp.write_json(a.output/'run.json',{'stage':a.stage,'ticker':a.ticker,'model':a.model,'arm':a.arm,'seed':a.seed,'config':config,'calibration':c,'fit':info,'Brier':float(np.mean((p-arrays['test'][1])**2)),'snapshot_hashes':{n:bp.sha(a.output/'inputs'/n) for n in names},'2026_used':False})
    finally:
        if guard is not None:guard.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage',choices=['E3b','E5'],required=True);p.add_argument('--ticker',choices=['AAPL','TSLA'],required=True)
    p.add_argument('--model',choices=['logistic','xgboost','lightgbm','lstm','mamba'],required=True);p.add_argument('--arm',choices=['A','B','T'],required=True)
    p.add_argument('--seed',choices=[42,43,44,45,46],type=int,required=True);p.add_argument('--market-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--allow-gpu',action='store_true')
    execute(p.parse_args())
