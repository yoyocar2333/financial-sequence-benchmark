"""Replay frozen E4c without the external E4b folder or the large FNSPID CSV."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pandas as pd

def replay(src,dst):
    if dst.exists():raise RuntimeError('Destination exists; preserve prior runs and choose a new folder')
    dst.mkdir(parents=True)
    for n in ('inputs','data','code','protocol_2026_unchanged'):shutil.copytree(src/n,dst/n)
    for n in ('plan_locked.json','research_plan.json','environment.json'):shutil.copy2(src/n,dst/n)
    for n in ('audits','tables','models','predictions','figures','logs'):(dst/n).mkdir()
    for n in ('protected_files.json','thresholds.json'):shutil.copy2(src/'audits'/n,dst/'audits'/n)
    shutil.copy2(src/'tables/sample_support.csv',dst/'tables/sample_support.csv')
    env={**os.environ,'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','CUDA_VISIBLE_DEVICES':'','OPENBLAS_NUM_THREADS':'2','OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2'}
    for phase in ('train','predict'):
        with (dst/'logs'/f'{phase}.log').open('w') as log:subprocess.run([sys.executable,'-B',str(dst/'code/run_e4c.py'),phase,'--out',str(dst)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    with (dst/'logs/analysis.log').open('w') as log:subprocess.run([sys.executable,'-B',str(dst/'code/analyze_e4c.py'),'--out',str(dst)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    checks=[]
    for p in sorted((src/'tables').glob('*.csv')):
        if p.name=='sample_support.csv':continue
        q=dst/'tables'/p.name
        if q.exists():pd.testing.assert_frame_equal(pd.read_csv(p),pd.read_csv(q),check_exact=True);checks.append(str(p.relative_to(src)))
    for n in ('predictions/all_probabilities.csv.gz','predictions/test_probabilities.csv.gz','predictions/daily_mean_probabilities.csv.gz','models/fitted_models.pkl','selected_configs.json'):
        if (src/n).read_bytes()!=(dst/n).read_bytes():raise RuntimeError('Replay difference '+n)
        checks.append(n)
    (dst/'audits/replay_comparison.json').write_text(json.dumps({'status':'PASSED','exactly_equal_scientific_artifacts':checks},indent=2)+'\n')
    print('REPLAY PASSED',len(checks),'artifacts',dst)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args();replay(a.source.resolve(),a.destination.resolve())
