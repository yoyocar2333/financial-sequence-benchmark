"""Replay completed E5 analysis in a fresh directory; never train models."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
import numpy as np
import pandas as pd
from e5_core import indicators,TECH,RELATIVE

def run(source,destination,plots=True):
    source=source.resolve();destination=destination.resolve()
    if destination.exists():raise FileExistsError('Replay destination must be new')
    destination.mkdir(parents=True)
    for d in ['inputs','predictions','cv','final']:
        shutil.copytree(source/d,destination/d,copy_function=shutil.copy2)
    for n in ['status.json','selection_locked.json','selected_configs.json','evaluation_plan.json']:
        shutil.copy2(source/n,destination/n)
    for d in ['logs','tables','audits','figures']:(destination/d).mkdir()
    for t in ['AAPL','TSLA']:
        # Match read_pre2026: default C parsing can perturb small-price rolling SD.
        def read(n):return pd.read_csv(destination/'inputs'/n,parse_dates=['Date'],float_precision='round_trip').set_index('Date')
        original=read(t+'_technical_and_labels.csv');rebuilt=indicators(read(t+'_adjusted_through2025.csv'),read('QQQ_adjusted_through2025.csv'))
        np.testing.assert_allclose(original[TECH+[RELATIVE]],rebuilt[TECH+[RELATIVE]],rtol=1e-12,atol=1e-12,equal_nan=True)
    env={**os.environ,'OPENBLAS_NUM_THREADS':'2','OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','CUDA_VISIBLE_DEVICES':''}
    code=Path(__file__).resolve().parent
    scripts=['analyze_e5.py','backtest_e5.py']+(['plot_e5.py'] if plots else [])
    for name in scripts:
        with (destination/'logs'/name.replace('.py','.log')).open('w') as f:
            subprocess.run([sys.executable,'-B',str(code/name),'--directory',str(destination)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    verified=[]
    for name in ['metrics_per_seed.csv','metrics_comparison.csv','feature_gains.csv','paired_tests.csv','within_state_ranking.csv','trading_comparison.csv','trading_per_schedule.csv']:
        a=pd.read_csv(source/'tables'/name);b=pd.read_csv(destination/'tables'/name)
        pd.testing.assert_frame_equal(a,b,check_exact=False,rtol=1e-11,atol=1e-12)
        verified.append(name)
    result={'status':'PASSED','source':str(source),'destination':str(destination),'technical_features_recomputed_from_frozen_adjusted_OHLCV':True,'tables_reproduced':verified,'new_training':False,'GPU_used':False,'2026_validation':False}
    (destination/'audits/replay_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--destination',required=True,type=Path);p.add_argument('--no-plots',action='store_true');a=p.parse_args()
    run(a.source,a.destination,not a.no_plots)
