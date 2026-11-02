"""E3b frozen study; default CPU preparation, --execute runs serial background suite."""
import argparse
import datetime as dt
import fcntl
import gc
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import numpy as np
import pandas as pd
from e3b_protocol import (ROOT,OUT,SOURCE,SEEDS,HORIZONS,MODELS,CONFIGS,FOLDS,FINAL,PLAN,
                         sha,write_json,load_frame,feature_matrix,indices,windows,calibrate,sigmoid)
from e3b_models import fit_job,brier

CODE=('e3b_protocol.py','e3b_models.py','run_e3b.py','analyze_e3b.py','plot_e3b.py','e3b_status.py','start_e3b.sh','launch_e3b.py','test_e3b.py')


def protect():
    files={}
    for folder in (SOURCE,ROOT/'outputs/mamba_low_resource_20261019_seed42',ROOT/'outputs/mamba_multiseed_20261020'):
        for p in folder.rglob('*'):
            if p.is_file():files[str(p.relative_to(ROOT))]=sha(p)
    for p in (ROOT/'data/market_20261019').rglob('*'):
        if p.is_file():files[str(p.relative_to(ROOT))]=sha(p)
    files['requirements-mamba.lock.txt']=sha(ROOT/'requirements-mamba.lock.txt')
    return files


def verify_protected():
    saved=json.loads((OUT/'protected_previous_files.json').read_text())
    for name,h in saved.items():
        if sha(ROOT/name)!=h:raise RuntimeError('Prior research changed: '+name)


def verify_code():
    for name,h in json.loads((OUT/'code_manifest.json').read_text()).items():
        if sha(ROOT/name)!=h:raise RuntimeError('Frozen E3b source changed: '+name)


def prepare():
    if (OUT/'prepared.json').exists():verify_code();verify_protected();return
    if OUT.exists():raise FileExistsError('Incomplete preparation exists; preserve and review before creating new study')
    OUT.mkdir(parents=True)
    for n in ('inputs','cv','final','predictions','tables','figures','logs','code'): (OUT/n).mkdir()
    frozen={**PLAN,'frozen_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    write_json(OUT/'evaluation_plan.json',frozen)
    write_json(OUT/'protected_previous_files.json',protect())
    manifest=json.loads((SOURCE/'archive_manifest.json').read_text())['files']
    for name,h in manifest.items():
        if sha(SOURCE/name)!=h:raise RuntimeError('E3a archive input changed: '+name)
    for name in ('AAPL','TSLA','QQQ','VIX','VXN'):
        for kind in ('adjusted','raw'):
            p=SOURCE/'inputs'/f'{name}_{kind}_through2025.csv'
            shutil.copyfile(p,OUT/'inputs'/p.name)
    shutil.copyfile(SOURCE/'training_thresholds.json',OUT/'inputs/e3a_training_thresholds.json')
    shutil.copyfile(SOURCE/'inputs/original_snapshot_provenance.json',OUT/'inputs/original_snapshot_provenance.json')
    shutil.copyfile(SOURCE/'tables/data_audit.csv',OUT/'inputs/e3a_data_audit.csv')
    shutil.copyfile(SOURCE/'E3A_SUMMARY.md',OUT/'inputs/E3A_SUMMARY.md')
    shutil.copyfile(ROOT/'E3B_PROPOSAL.md',OUT/'inputs/E3B_PROPOSAL_original.md')
    hashes={}
    for name in CODE:
        p=ROOT/'scripts'/name;shutil.copyfile(p,OUT/'code'/name);hashes[str(p.relative_to(ROOT))]=sha(p)
    for name in ('e3a_core.py','mamba_resource_guard.py','mamba_resource_guard_own_safety.py'):
        p=ROOT/'scripts'/name;shutil.copyfile(p,OUT/'code'/name);hashes[str(p.relative_to(ROOT))]=sha(p)
    shutil.copyfile(ROOT/'README_E3B.md',OUT/'README_E3B.md')
    hashes['README_E3B.md']=sha(ROOT/'README_E3B.md')
    hashes[str((OUT/'evaluation_plan.json').relative_to(ROOT))]=sha(OUT/'evaluation_plan.json')
    write_json(OUT/'code_manifest.json',hashes)
    versions={p:importlib.metadata.version(p) for p in ('torch','mamba_ssm','causal_conv1d','triton','xgboost-cpu','lightgbm','numpy','pandas','scipy','scikit-learn')}
    write_json(OUT/'environment.json',{'python':sys.version,'prefix':sys.prefix,'versions':versions,
        'readonly_Mamba_base':str(ROOT/'.venv-mamba'),'new_tree_packages_installed_only_in':str(ROOT/'.venv-e3b')})
    lock=subprocess.check_output([sys.executable,'-B','-m','pip','freeze'],text=True)
    (OUT/'environment.lock.txt').write_text(lock)
    audit=[]
    for ticker in ('AAPL','TSLA'):
        f=load_frame(ticker);f.to_csv(OUT/'inputs'/f'{ticker}_labels_and_causal_features.csv')
        for name,a,b in [('fit','2012-01-01',FINAL['fit_end']),('stop',FINAL['stop_start'],FINAL['stop_end']),
                         ('cal',FINAL['cal_start'],FINAL['cal_end']),('test',FINAL['test_start'],FINAL['test_end'])]:
            ids=indices(f,a,b)
            audit.append({'ticker':ticker,'block':name,'n':len(ids),'first':str(f.index[ids[0]].date()),
                'last':str(f.index[ids[-1]].date()),'last_label20':str(f.end20.iloc[ids[-1]].date())})
        for arm in ('A','B'):
            _,meta=feature_matrix(f,arm,FINAL['fit_end']);write_json(OUT/'inputs'/f'{ticker}_{arm}_final_preprocessing.json',meta)
    pd.DataFrame(audit).to_csv(OUT/'tables/split_audit.csv',index=False)
    write_json(OUT/'prepared.json',{'status':'READY','CV_fits':540,'final_fits':300,'GPU_not_used_by_preparation':True})
    print('READY: plan frozen; 540 equal-budget CV fits, 300 final fits including logistic',flush=True)


class DataCache:
    def __init__(self):self.frames={t:load_frame(t) for t in ('AAPL','TSLA')};self.cache={}
    def get(self,ticker,arm,block):
        key=(ticker,arm,block['fit_end'])
        if key not in self.cache:
            f=self.frames[ticker];scaled,meta=feature_matrix(f,arm,block['fit_end'])
            ranges={'fit':('2012-01-01',block['fit_end']),'stop':(block['stop_start'],block['stop_end'])}
            if 'eval_start' in block:ranges['eval']=(block['eval_start'],block['eval_end'])
            else:ranges.update(cal=(block['cal_start'],block['cal_end']),test=(block['test_start'],block['test_end']))
            ids={n:indices(f,a,b) for n,(a,b) in ranges.items()}
            xs={n:windows(scaled,i) for n,i in ids.items()}
            self.cache[key]=(xs,ids,meta)
        return self.cache[key]
    def arrays(self,ticker,arm,h,block):
        xs,ids,meta=self.get(ticker,arm,block);f=self.frames[ticker]
        return {n:(x,f[f'y{h}'].iloc[ids[n]].to_numpy()) for n,x in xs.items()},ids,meta


def smoke(guard):
    import torch
    import mamba_ssm
    import selective_scan_cuda
    from e3b_models import neural_model
    results=[]
    for model in ('lstm','mamba'):
        for width in (32,64):
            net=neural_model(model,len(PLAN['feature_A'])+len(PLAN['feature_B_extra']),{'width':width}).cuda()
            x=torch.ones((64,60,38),device='cuda');y=torch.zeros(64,device='cuda')
            loss=torch.nn.functional.binary_cross_entropy_with_logits(net(x),y);loss.backward();torch.cuda.synchronize()
            if not torch.isfinite(loss) or not all(torch.isfinite(p.grad).all() for p in net.parameters() if p.grad is not None):raise RuntimeError('GPU classification smoke failed')
            results.append({'model':model,'width':width,'loss':float(loss),'peak_bytes':torch.cuda.max_memory_allocated()})
            del net,x,y,loss;gc.collect();torch.cuda.empty_cache()
    write_json(OUT/'GPU_SMOKE.json',{'status':'PASSED','GPU':torch.cuda.get_device_name(0),'torch':torch.__version__,'CUDA':torch.version.cuda,
        'Mamba':mamba_ssm.__version__,'selective_scan_cuda':selective_scan_cuda.__file__,'extension_sha256':sha(selective_scan_cuda.__file__),'tests':results})
    print('True Mamba/LSTM CUDA forward/backward smoke PASSED',flush=True)


def packet(f,ids,h,model,arm,seed,raw,cal,usage):
    return pd.DataFrame({'ticker':f.attrs['ticker'],'date':f.index[ids].strftime('%Y-%m-%d'),
        'label_date':pd.to_datetime(f[f'label_date{h}'].iloc[ids]).dt.strftime('%Y-%m-%d').to_numpy(),
        'horizon':h,'model':model,'arm':arm,'seed':seed,'usage':usage,
        'target_reversal':f[f'y{h}'].iloc[ids].to_numpy(),'executable_log_return_pp':f[f'nextopen_log{h}'].iloc[ids].to_numpy(),
        'reference_sign':f.reference_sign.iloc[ids].to_numpy(),'p_raw':raw,'p_calibrated':cal})


def baselines(data):
    for ticker in ('AAPL','TSLA'):
        f=data.frames[ticker];f.attrs['ticker']=ticker
        for h in HORIZONS:
            _,ids,_=data.arrays(ticker,'A',h,FINAL)
            yfit=f[f'y{h}'].iloc[ids['fit']].to_numpy();yc=f[f'y{h}'].iloc[ids['cal']].to_numpy()
            pt=(yfit.sum()+1)/(len(yfit)+2);pc=(yc.sum()+1)/(len(yc)+2)
            for model in ('train_prior','cal_prior','momentum20','mean_reversion5','hard_momentum20','hard_MR5'):
                raw={}
                for name in ('cal','test'):
                    z=f.iloc[ids[name]];side=z.reference_sign.to_numpy()
                    if model in ('train_prior','cal_prior'):p=np.full(len(z),pt if model=='train_prior' else pc)
                    elif model=='hard_MR5':p=np.ones(len(z))
                    elif model=='hard_momentum20':p=(np.sign(z.past20.to_numpy())*side<0).astype(float)
                    else:
                        past=20 if model=='momentum20' else 5
                        standardized=z[f'past{past}'].to_numpy()/(z[f'RV{past}'].to_numpy()/np.sqrt(252)*np.sqrt(past))
                        pup=sigmoid(standardized if model=='momentum20' else -standardized)
                        p=np.where(side<0,pup,1-pup)
                    raw[name]=p
                if model in ('momentum20','mean_reversion5'):
                    calibrated,info=calibrate(raw['cal'],yc,raw['test']);write_json(OUT/'predictions'/f'{ticker}_h{h}_{model}_calibration.json',info)
                else:calibrated=raw['test']
                packet(f,ids['test'],h,model,'shared',-1,raw['test'],calibrated,'test').to_csv(OUT/'predictions'/f'{ticker}_h{h}_{model}.csv',index=False)


def execute(resume=False):
    prepare();status_file=OUT/'status.json'
    if status_file.exists() and not resume:raise FileExistsError('Suite exists; use explicit --resume after reviewing status')
    previous=json.loads(status_file.read_text()) if status_file.exists() else {}
    if previous.get('status')=='COMPLETE':raise FileExistsError('Already complete; will not retrain')
    status={'status':'STARTING','pid':os.getpid(),'started_utc':previous.get('started_utc',dt.datetime.now(dt.timezone.utc).isoformat()),
            'cv_completed':previous.get('cv_completed',[]),'final_completed':previous.get('final_completed',[]),'search_budget':540,'final_budget':300}
    write_json(status_file,status)
    try:
        from mamba_resource_guard_own_safety import ResourceGuard
        guard=ResourceGuard(ROOT,OUT,fraction=.10,duty=.50)
        smoke(guard);data=DataCache()
        selected={};cv_records=[]
        for h in HORIZONS:
            for ticker in ('AAPL','TSLA'):
                for arm in ('A','B'):
                    for model in MODELS:
                        verify_code();scores=[]
                        for ci,config in enumerate(CONFIGS[model]):
                            fold_scores=[]
                            for block in FOLDS:
                                name=f'{ticker}_h{h}_{arm}_{model}_c{ci}_fold{block["name"]}'
                                folder=OUT/'cv'/f'h{h}'/ticker/arm/model/f'c{ci}_fold{block["name"]}'
                                status.update(status='SEARCH',current=name);write_json(status_file,status)
                                arrays,ids,meta=data.arrays(ticker,arm,h,block)
                                pred,info=fit_job(model,config,42,arrays,folder,{'ticker':ticker,'horizon':h,'arm':arm,'phase':'CV','block':block,'preprocessing':meta},guard)
                                score=brier(arrays['eval'][1],pred['eval']);fold_scores.append(score)
                                cv_records.append({'ticker':ticker,'horizon':h,'arm':arm,'model':model,'config_index':ci,'fold':block['name'],
                                    'outer_brier':score,'best_iteration':info['best_iteration'],'seconds':info['training_seconds']})
                                if name not in status['cv_completed']:status['cv_completed'].append(name)
                                write_json(status_file,status)
                            scores.append(float(np.mean(fold_scores)))
                        best=int(np.argmin(scores));key=f'{ticker}_h{h}_{arm}_{model}'
                        selected[key]={'config_index':best,'config':CONFIGS[model][best],'CV_mean_brier':scores}
                        write_json(OUT/'selected_configs.json',selected)
                        pd.DataFrame(cv_records).to_csv(OUT/'tables/CV_results.csv',index=False)
                        print('SEARCH complete',key,'selected',best,flush=True)
        verify_protected();write_json(OUT/'selection_locked.json',{'selected_sha256':sha(OUT/'selected_configs.json'),'no_test_used_for_selection':True,'CV_fits':len(cv_records)})
        baselines(data)
        for h in HORIZONS:
            for ticker in ('AAPL','TSLA'):
                data.frames[ticker].attrs['ticker']=ticker
                for arm in ('A','B'):
                    for model in MODELS:
                        verify_code();key=f'{ticker}_h{h}_{arm}_{model}';config=selected[key]['config']
                        arrays,ids,meta=data.arrays(ticker,arm,h,FINAL)
                        for seed in SEEDS:
                            name=key+f'_seed{seed}';status.update(status='TRAINING',current=name);write_json(status_file,status)
                            folder=OUT/'final'/f'h{h}'/ticker/arm/model/f'seed{seed}'
                            pred,info=fit_job(model,config,seed,arrays,folder,{'ticker':ticker,'horizon':h,'arm':arm,'phase':'FINAL','block':FINAL,'preprocessing':meta},guard)
                            calibrated,calinfo=calibrate(pred['cal'],arrays['cal'][1],pred['test'])
                            write_json(folder/'calibration.json',calinfo)
                            result=packet(data.frames[ticker],ids['test'],h,model,arm,seed,pred['test'],calibrated,'test')
                            result.to_csv(folder/'predictions.csv',index=False)
                            result.to_csv(OUT/'predictions'/f'{name}.csv',index=False)
                            packet(data.frames[ticker],ids['cal'],h,model,arm,seed,pred['cal'],np.full(len(pred['cal']),np.nan),'calibration_fit_raw').to_csv(folder/'calibration_predictions.csv',index=False)
                            if name not in status['final_completed']:status['final_completed'].append(name)
                            write_json(status_file,status)
                            print('FINAL complete',name,flush=True)
        guard.check(force=True);guard.close()
        shutil.copyfile(guard.log_path,OUT/'logs'/guard.log_path.name)
        verify_protected();verify_code()
        status.update(status='ANALYZING',current=None);write_json(status_file,status)
        cpuenv={**os.environ,'CUDA_VISIBLE_DEVICES':''}
        with (OUT/'logs/analysis.log').open('w') as f:
            subprocess.run([sys.executable,'-B','-u',str(ROOT/'scripts/analyze_e3b.py')],env=cpuenv,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
        verify_protected()
        status.update(status='COMPLETE',finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),archive=str(OUT/'e3b_complete_results.zip'))
        write_json(status_file,status);print('COMPLETE',status['archive'],flush=True)
    except BaseException:
        status.update(status='STOPPED',traceback=traceback.format_exc());write_json(status_file,status)
        print(status['traceback'],file=sys.stderr,flush=True);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--resume',action='store_true');args=p.parse_args()
    with (ROOT/'logs/mamba-suite.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.execute:execute(args.resume)
        else:prepare()
