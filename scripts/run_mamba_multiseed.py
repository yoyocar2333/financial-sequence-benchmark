"""Sixteen serial GPU jobs; immutable seed42 reuse, then CPU inference/archive."""
import argparse
import datetime as dt
import fcntl
import json
import os
import subprocess
import sys
import traceback

from multiseed_common import ROOT,OUT,MARKET,TASKS,prepare,check_protected,case_root,leaf,write_json
from mamba_resource_guard import gpu_snapshot


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    with (ROOT/'logs/mamba-suite.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        prepare()
        if args.prepare_only:
            print('READY: data/code/statistics frozen; seed42 unchanged; no GPU used',flush=True)
            return
        status_file=OUT/'suite_status.json'
        if status_file.exists():raise FileExistsError('Refusing duplicate launch or overwrite')
        if any(case_root(s,t,a).exists() for s,t,a in TASKS):raise FileExistsError('New case output already exists')
        status={'status':'STARTING','pid':os.getpid(),'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                'order':[f'seed{s}_{t}_{a}' for s,t,a in TASKS],'completed':[],
                'seed42_reused':True,'market_dir':str(MARKET)}
        write_json(status_file,status)
        try:
            import numpy as np
            import pandas as pd
            for seed,ticker,arm in TASKS:
                check_protected()
                name=f'seed{seed}_{ticker}_{arm}'
                before=gpu_snapshot()
                write_json(OUT/f'{name}_gpu_before.json',before)
                if before['free_mib']<4096 or before['utilization_pct']>=90:
                    raise RuntimeError('GPU admission refused; stopping suite')
                with (OUT/f'{name}_nvidia_before.txt').open('w') as f:
                    subprocess.run(['nvidia-smi'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=20)
                cmd=[sys.executable,'-B','-u',str(ROOT/'scripts/run_mamba_e1_e2b.py'),
                     '--tickers',ticker,'--arms',arm,'--seed',str(seed),'--batch-size','8','--eval-batch-size','8',
                     '--memory-fraction','0.10','--gpu-duty-cycle','0.25','--market-dir',str(MARKET),
                     '--csv-price-policy','adjusted','--out',str(case_root(seed,ticker,arm)),'--execute-training']
                status.update(status='TRAINING',current=name,command=cmd)
                write_json(status_file,status)
                print('Starting',name,dt.datetime.now(dt.timezone.utc).isoformat(),flush=True)
                with (OUT/f'{name}_stdout.log').open('w') as f:
                    child=subprocess.Popen(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
                    status['child_pid']=child.pid;write_json(status_file,status)
                    code=child.wait()
                status.pop('child_pid',None)
                if code:raise RuntimeError(f'{name} exited {code}; no retry or subsequent training; see stdout log')
                folder=leaf(seed,ticker,arm)
                pred=pd.read_csv(folder/'predictions.csv')
                states=pd.read_csv(OUT/f'{ticker}_frozen_states.csv')
                history=pd.read_csv(folder/'training_history.csv')
                if pred.date.tolist()!=states.date.tolist() or set(pred['split'])!={'test'}:
                    raise RuntimeError('Frozen test calendar mismatch')
                if not np.isfinite(pred[['actual_mag_pct','forecast_mag_pct']].to_numpy()).all():
                    raise RuntimeError('Nonfinite predictions')
                if not (history.train_batches==346).all() or not np.isfinite(history.select_dtypes(include='number').to_numpy()).all():
                    raise RuntimeError('Invalid training history')
                if int(history.cuda_reserved_bytes.max())>before['total_mib']*1024**2*.10:
                    raise RuntimeError('Allocator reserve exceeds ten percent')
                check_protected()
                status['completed'].append(name)
                write_json(status_file,status)
                print('Completed',name,flush=True)
            status.update(status='ANALYZING',current=None);write_json(status_file,status)
            cpu_env={**os.environ,'CUDA_VISIBLE_DEVICES':''}
            with (OUT/'analysis.log').open('w') as f:
                subprocess.run([sys.executable,'-B','-u',str(ROOT/'scripts/analyze_mamba_multiseed.py')],
                               cwd=ROOT,env=cpu_env,stdout=f,stderr=subprocess.STDOUT,check=True)
            check_protected()
            with (OUT/'package.log').open('w') as f:
                subprocess.run([sys.executable,'-B','-u',str(ROOT/'scripts/analyze_mamba_multiseed.py'),'--package-only'],
                               cwd=ROOT,env=cpu_env,stdout=f,stderr=subprocess.STDOUT,check=True)
            check_protected()
            status.update(status='COMPLETE',finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                          archive=str(OUT/'mamba_multiseed_complete.zip'),
                          archive_sha256=(OUT/'archive_sha256.txt').read_text().split()[0])
            write_json(status_file,status)
            print('COMPLETE',json.dumps(status),flush=True)
        except BaseException:
            status.update(status='STOPPED',traceback=traceback.format_exc())
            write_json(status_file,status)
            print(status['traceback'],file=sys.stderr,flush=True)
            raise


if __name__=='__main__':main()
