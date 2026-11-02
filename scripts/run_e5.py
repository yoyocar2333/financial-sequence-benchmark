"""Prepare and run a finite E5 suite without modifying prior results."""
import argparse,datetime as dt,gc,importlib.metadata,json,os,shutil,subprocess,sys,traceback
from pathlib import Path
import numpy as np
import pandas as pd
import e3b_protocol as bp
from e3b_models import fit_job,brier,neural_model
from e5_core import *

def now():return dt.datetime.now(dt.timezone.utc).isoformat()

def prepare():
    if (OUT/'prepared.json').exists():raise FileExistsError('Prepared E5 already exists; no implicit overwrite')
    for name in ['inputs','code','logs','tables','predictions','figures','audits']: (OUT/name).mkdir(parents=True,exist_ok=True)
    bp.write_json(OUT/'evaluation_plan.json',PLAN)
    files={}
    for n in ['e5_core.py','run_e5.py','e3b_protocol.py','e3b_models.py','e3a_core.py','analyze_e3b.py','analyze_e3c.py','e3c_core.py','mamba_resource_guard.py','mamba_resource_guard_own_safety.py']:
        p=ROOT/'scripts'/n;shutil.copy2(p,OUT/'code'/n);files[str(p.relative_to(ROOT))]=bp.sha(p)
    files[str((OUT/'evaluation_plan.json').relative_to(ROOT))]=bp.sha(OUT/'evaluation_plan.json')
    protected=json.loads((ROOT/'outputs/e4c_20261026/audits/protected_files.json').read_text())
    for n in ['E3C_2026_PROTOCOL.md','RESEARCH_REPORT_CURRENT.json','RESEARCH_REPORT_CONDENSED_CURRENT.json']:
        protected[n]=bp.sha(ROOT/n)
    inputs={}
    for p in (SOURCE/'inputs').glob('*_through2025.csv'):
        shutil.copy2(p,OUT/'inputs'/p.name);inputs[str(p.relative_to(ROOT))]=bp.sha(p)
    for p in [SOURCE/'selected_configs.json',SOURCE/'selection_locked.json',SOURCE/'evaluation_plan.json',SOURCE/'tables/CV_results.csv',SOURCE/'inputs/e3a_training_thresholds.json']:
        shutil.copy2(p,OUT/'inputs'/p.name);inputs[str(p.relative_to(ROOT))]=bp.sha(p)
    # Record all B h5 source artifacts, not just aggregate metrics.
    for ticker in ['AAPL','TSLA']:
        for model in MODELS:
            for seed in SEEDS:
                folder=SOURCE/'final/h5'/ticker/'B'/model/f'seed{seed}'
                for name,h in json.loads((folder/'COMPLETE.json').read_text())['files'].items():
                    if bp.sha(folder/name)!=h:raise RuntimeError('Changed B fit '+str(folder/name))
                for name in ['COMPLETE.json','predictions.csv','calibration_predictions.csv','raw_predictions.npz','config.json','fit_info.json']:
                    p=folder/name;protected[str(p.relative_to(ROOT))]=bp.sha(p)
    bp.write_json(OUT/'code_manifest.json',files);bp.write_json(OUT/'audits/protected_files.json',protected);bp.write_json(OUT/'input_manifest.json',inputs)
    versions={p:importlib.metadata.version(p) for p in ['torch','mamba_ssm','causal_conv1d','triton','xgboost-cpu','lightgbm','numpy','pandas','scipy','scikit-learn']}
    bp.write_json(OUT/'environment.json',{'python':sys.version,'prefix':sys.prefix,'versions':versions})
    (OUT/'environment.lock.txt').write_text(subprocess.check_output([sys.executable,'-B','-m','pip','freeze'],text=True))
    audit=[]
    for t in ['AAPL','TSLA']:
        f=load(t);f.to_csv(OUT/'inputs'/f'{t}_technical_and_labels.csv',index_label='Date')
        for arm in ['T','C','H','H0']:
            arrays,ids,_=block_arrays(f,arm,FINAL)
            for k,ii in ids.items():
                audit.append({'ticker':t,'arm':arm,'block':k,'n':len(ii),'start':str(f.index[ii[0]].date()),'end':str(f.index[ii[-1]].date()),'label20_max':str(f.end20.iloc[ii[-1]].date()),'dims':arrays[k][0].shape[-1]})
            assert len(ids['test'])==482
        for b in FOLDS:block_arrays(f,'T',b)
    pd.DataFrame(audit).to_csv(OUT/'tables/split_audit.csv',index=False)
    bp.write_json(OUT/'prepared.json',{'status':'READY','new_CV':162,'new_final':90,'reused_B':50,'GPU_used':False,'at':now()})
    print('E5 PLAN LOCKED:162 CV +90 final;50 reused B; no2026',flush=True)


def verify():
    for fn in ['code_manifest.json','input_manifest.json','audits/protected_files.json']:
        for p,h in json.loads((OUT/fn).read_text()).items():
            if bp.sha(ROOT/p)!=h:raise RuntimeError('Protected input/code changed: '+p)


def packet(f,ii,method,seed,raw,p):
    return pd.DataFrame({'ticker':f.attrs['ticker'],'date':f.index[ii].strftime('%Y-%m-%d'),'label_date':pd.to_datetime(f.label_date5.iloc[ii]).dt.strftime('%Y-%m-%d').to_numpy(),
        'method':method,'seed':seed,'target_reversal':f.y5.iloc[ii].to_numpy(),'executable_log_return_pp':f.nextopen_log5.iloc[ii].to_numpy(),'reference_sign':f.reference_sign.iloc[ii].to_numpy(),
        'p_raw':raw,'p_calibrated':p,'p_up':np.where(f.reference_sign.iloc[ii].to_numpy()<0,p,1-p)})


def baselines(frames):
    thresholds=json.loads((OUT/'inputs/e3a_training_thresholds.json').read_text())
    for ticker,f in frames.items():
        ii={k:bp.indices(f,*ab) for k,ab in {'fit':('2012-01-01',FINAL['fit_end']),'cal':(FINAL['cal_start'],FINAL['cal_end']),'test':(FINAL['test_start'],FINAL['test_end'])}.items()}
        for model in MODELS:
            for seed in SEEDS:
                source=SOURCE/'final/h5'/ticker/'B'/model/f'seed{seed}'
                z=pd.read_csv(source/'predictions.csv');np.testing.assert_array_equal(z.date,f.index[ii['test']].strftime('%Y-%m-%d'))
                out=OUT/'predictions'/f'{ticker}_{model}_B_seed{seed}.csv'
                packet(f,ii['test'],model+'_B',seed,z.p_raw,z.p_calibrated).to_csv(out,index=False)
                # Preserve source calibration probabilities and true source identity.
                shutil.copy2(source/'calibration_predictions.csv',OUT/'predictions'/f'{ticker}_{model}_B_seed{seed}_cal_source.csv')
        scores=rule_scores(f)
        for model in RULES:
            raw={}
            for name,ids in ii.items():
                up=bp.sigmoid(2*scores[model].iloc[ids].to_numpy());side=f.reference_sign.iloc[ids].to_numpy()
                raw[name]=np.where(side<0,up,1-up)
            p,meta=bp.calibrate(raw['cal'],f.y5.iloc[ii['cal']],raw['test'])
            packet(f,ii['test'],model,-1,raw['test'],p).to_csv(OUT/'predictions'/f'{ticker}_{model}.csv',index=False)
            bp.write_json(OUT/'predictions'/f'{ticker}_{model}_calibration.json',meta)
        # Fair same-calibration-period constants and published soft baselines.
        for name in ['cal_prior','momentum20','mean_reversion5']:
            z=pd.read_csv(SOURCE/'predictions'/f'{ticker}_h5_{name}.csv')
            packet(f,ii['test'],name,-1,z.p_raw,z.p_calibrated).to_csv(OUT/'predictions'/f'{ticker}_{name}.csv',index=False)
        _,_,cell=states(f,thresholds[ticker]);y=f.y5.to_numpy();prior=float((y[ii['fit']].sum()+1)/(len(ii['fit'])+2))
        probabilities=np.full(len(f),prior)
        for c in range(8):
            ix=ii['fit'][cell[ii['fit']]==c]
            probabilities[cell==c]=(y[ix].sum()+100*prior)/(len(ix)+100)
        p,meta=bp.calibrate(probabilities[ii['cal']],y[ii['cal']],probabilities[ii['test']])
        packet(f,ii['test'],'state_prior',-1,probabilities[ii['test']],p).to_csv(OUT/'predictions'/f'{ticker}_state_prior.csv',index=False)
        bp.write_json(OUT/'predictions'/f'{ticker}_state_prior_calibration.json',meta)


def smoke(guard):
    import torch,mamba_ssm,selective_scan_cuda
    records=[]
    for name in ['lstm','mamba']:
        for width in [32,64]:
            net=neural_model(name,51,{'width':width}).cuda();x=torch.ones((64,60,51),device='cuda')
            loss=net(x).square().mean();loss.backward();torch.cuda.synchronize()
            assert torch.isfinite(loss) and all(torch.isfinite(p.grad).all() for p in net.parameters() if p.grad is not None)
            records.append({'model':name,'width':width,'loss':float(loss.detach()),'peak_bytes':torch.cuda.max_memory_allocated()})
            del net,x,loss;gc.collect();torch.cuda.empty_cache()
    bp.write_json(OUT/'GPU_SMOKE.json',{'status':'PASSED','gpu':torch.cuda.get_device_name(0),'torch':torch.__version__,'CUDA':torch.version.cuda,'mamba_ssm':mamba_ssm.__version__,'selective_scan':selective_scan_cuda.__file__,'checks':records})


def execute(resume=False):
    verify();statuspath=OUT/'status.json'
    if statuspath.exists():
        old=json.loads(statuspath.read_text())
        if not resume or old['status']!='STOPPED':raise RuntimeError('Refuse duplicate/completed E5 execution')
    status={'status':'STARTING','pid':os.getpid(),'started':now(),'cv_completed':0,'final_completed':0}
    bp.write_json(statuspath,status)
    guard=None
    try:
        from mamba_resource_guard_own_safety import ResourceGuard
        guard=ResourceGuard(ROOT,OUT,fraction=.10,duty=.50);smoke(guard)
        frames={t:load(t) for t in ['AAPL','TSLA']};selected={};cv=[]
        jobs=[('T',m,m,CONFIGS[m]) for m in MODELS]+[('C',m,m,CONFIGS[m]) for m in ['logistic','xgboost']]+[(a,'hybrid' if a=='H' else 'ungated','logistic',CONFIGS['logistic']) for a in ['H','H0']]
        for ticker,f in frames.items():
            for arm,label,model,configs in jobs:
                cache={b['name']:block_arrays(f,arm,b) for b in FOLDS};means=[]
                for ci,config in enumerate(configs):
                    scores=[]
                    for b in FOLDS:
                        verify();arrays,ids,meta=cache[b['name']]
                        name=f'{ticker}_{label}_{arm}_c{ci}_fold{b["name"]}'
                        status.update(status='SEARCH',current=name);bp.write_json(statuspath,status)
                        folder=OUT/'cv'/ticker/arm/label/f'c{ci}_fold{b["name"]}'
                        pred,info=fit_job(model,config,42,arrays,folder,{'study':'E5','ticker':ticker,'arm':arm,'block':b,'preprocessing':meta},guard)
                        score=brier(arrays['eval'][1],pred['eval']);scores.append(score)
                        cv.append({'ticker':ticker,'arm':arm,'model':label,'candidate':ci,'fold':b['name'],'brier':score,'seconds':info['training_seconds']})
                        status['cv_completed']+=1;bp.write_json(statuspath,status)
                    means.append(float(np.mean(scores)))
                best=int(np.argmin(means));key=f'{ticker}_{label}_{arm}'
                selected[key]={'config_index':best,'config':configs[best],'cv_means':means,'fitting_model':model}
                bp.write_json(OUT/'selected_configs.json',selected)
                pd.DataFrame(cv).to_csv(OUT/'tables/CV_results.csv',index=False)
                print('SEARCH',key,'selected',best,'completed',status['cv_completed'],flush=True)
                del cache;gc.collect()
        assert status['cv_completed']==162
        bp.write_json(OUT/'selection_locked.json',{'sha256':bp.sha(OUT/'selected_configs.json'),'locked_at':now(),'new_test_predictions_written':False,'CV_completed':162})
        baselines(frames)
        for ticker,f in frames.items():
            for arm,label,model,_ in jobs:
                arrays,ids,meta=block_arrays(f,arm,FINAL);key=f'{ticker}_{label}_{arm}';config=selected[key]['config']
                for seed in SEEDS:
                    verify();guard.check(force=True)
                    name=key+f'_seed{seed}';status.update(status='TRAINING',current=name);bp.write_json(statuspath,status)
                    folder=OUT/'final'/ticker/arm/label/f'seed{seed}'
                    pred,info=fit_job(model,config,seed,arrays,folder,{'study':'E5','ticker':ticker,'arm':arm,'phase':'final','block':FINAL,'preprocessing':meta},guard)
                    calibrated,calinfo=bp.calibrate(pred['cal'],arrays['cal'][1],pred['test'])
                    bp.write_json(folder/'calibration.json',calinfo)
                    method=label+'_'+arm
                    packet(f,ids['test'],method,seed,pred['test'],calibrated).to_csv(OUT/'predictions'/f'{ticker}_{method}_seed{seed}.csv',index=False)
                    packet(f,ids['cal'],method,seed,pred['cal'],pred['cal']).to_csv(folder/'calibration_predictions.csv',index=False)
                    status['final_completed']+=1;bp.write_json(statuspath,status)
                    print('FINAL',name,'completed',status['final_completed'],flush=True)
                del arrays;gc.collect()
        assert status['final_completed']==90
        guard.close();guard=None;verify()
        status.update(status='TRAINING_COMPLETE',finished_training=now(),current=None);bp.write_json(statuspath,status)
        print('E5 TRAINING_COMPLETE:162CV+90final; waiting CPU analysis',flush=True)
    except BaseException:
        status.update(status='STOPPED',traceback=traceback.format_exc());bp.write_json(statuspath,status);raise
    finally:
        if guard is not None:guard.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--execute',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args()
    if a.prepare:prepare()
    elif a.execute:execute(a.resume)
    else:p.error('Specify --prepare or --execute')
