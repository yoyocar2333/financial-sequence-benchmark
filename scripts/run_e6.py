"""Finite CPU E6 benchmark; archived genuine neural price predictions reused."""
import argparse,datetime as dt,importlib.metadata as im,json,os,shutil,sys,traceback,gc
from pathlib import Path
import numpy as np
import pandas as pd
import e3b_protocol as bp
from e3b_models import fit_job,brier
from e6_core import ROOT,OUT,SOURCE,SEEDS,CPU,ALL,PLAN,load,arrays,existing_config
from e6_data import CORE,sha,dump,extract

def now():return dt.datetime.now(dt.timezone.utc).isoformat()

def prepare():
    if (OUT/'plan_locked.json').exists():raise FileExistsError('E6 already frozen')
    protected={}
    # Original immutable protocol and all E5 outputs are protected by file hashes.
    for p in (ROOT/'protocols/e3c_2026').rglob('*') if (ROOT/'protocols/e3c_2026').exists() else []:
        if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
    for name in ['E3C_2026_PROTOCOL.md','E5_CURRENT_RUN.json','E5_SUMMARY.md']:
        protected[name]=sha(ROOT/name)
    for p in SOURCE.rglob('*'):
        if p.is_file() and p.suffix not in ['.zip','.png','.pdf','.pt'] and 'logs' not in p.parts:protected[str(p.relative_to(ROOT))]=sha(p)
    dump(OUT/'audits/protected_previous_files.json',protected)
    for p in (SOURCE/'inputs').glob('*_through2025.csv'):shutil.copyfile(p,OUT/'inputs'/p.name)
    shutil.copyfile(SOURCE/'selected_configs.json',OUT/'inputs/e5_selected_configs.json')
    shutil.copyfile(SOURCE/'inputs/e3a_training_thresholds.json',OUT/'inputs/e3a_training_thresholds.json')
    reuse={}
    for t in ['AAPL','TSLA']:
        for m in ALL:
            ci=existing_config(t,m)['config_index']
            for b in bp.FOLDS:
                p=SOURCE/'cv'/t/'T'/m/f'c{ci}_fold{b["name"]}'/'raw_predictions.npz'
                dest=OUT/'reused_P/cv'/t/m/f'fold{b["name"]}.npz';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);reuse[str(p.relative_to(ROOT))]=sha(p)
            for seed in SEEDS:
                folder=OUT/'reused_P/final'/t/m/f'seed{seed}';folder.mkdir(parents=True,exist_ok=True)
                for p,dest in [(SOURCE/'predictions'/f'{t}_{m}_T_seed{seed}.csv',folder/'test.csv'),(SOURCE/'final'/t/'T'/m/f'seed{seed}'/'raw_predictions.npz',folder/'raw_predictions.npz')]:
                    shutil.copyfile(p,dest);reuse[str(p.relative_to(ROOT))]=sha(p)
    shutil.copyfile(SOURCE/'GPU_SMOKE.json',OUT/'audits/E5_GENUINE_MAMBA_SMOKE_REUSED.json')
    extract(OUT)
    audit=[];gate=[]
    for t in ['AAPL','TSLA']:
        f,a=load(t);a.to_csv(OUT/'inputs'/f'{t}_daily_fundamentals.csv',index=False)
        for arm in ['P','F','PF','M']:
            ar,ix,_=arrays(f,a,arm,bp.FINAL)
            for k,ii in ix.items():audit.append({'ticker':t,'arm':arm,'block':k,'n':len(ii),'start':str(f.index[ii[0]].date()),'end':str(f.index[ii[-1]].date()),'features':ar[k][0].shape[-1],'unique_vintages':a.iloc[ii].vintage.nunique(),'missing_any_core':int(a.iloc[ii][CORE].isna().any(axis=1).sum())})
            assert len(ix['test'])==482
        n=a.loc['2012-01-01':bp.FINAL['fit_end']].vintage.nunique();gate.append({'ticker':t,'distinct_training_vintages':int(n),'minimum_for_new_neural':100,'new_neural_supported':bool(n>=100),'implemented_neural':'reuse genuine archived E5 P for late fusion only'})
        if n>=100:raise RuntimeError('Unexpected neural gate; review frozen scope before any fits')
    pd.DataFrame(audit).to_csv(OUT/'tables/split_and_coverage_audit.csv',index=False);dump(OUT/'audits/neural_support_gate.json',gate)
    for name in ['e6_core.py','e6_data.py','run_e6.py','recover_e6_fundamentals.py','e3b_protocol.py','e3b_models.py','e3a_core.py','e5_core.py','analyze_e3b.py','analyze_e3c.py','e3c_core.py']:
        shutil.copyfile(ROOT/'scripts'/name,OUT/'code'/name)
    dump(OUT/'evaluation_plan.json',PLAN)
    files=[p for d in ['inputs','code','reused_P','raw'] for p in (OUT/d).rglob('*') if p.is_file()]
    dump(OUT/'frozen_manifest.json',{str(p.relative_to(OUT)):sha(p) for p in files})
    dump(OUT/'audits/reused_P_source_hashes.json',reuse)
    versions={n:im.version(n) for n in ['numpy','pandas','scipy','scikit-learn','xgboost-cpu','lightgbm','torch','mamba-ssm']}
    dump(OUT/'environment.json',{'python':sys.version,'prefix':sys.prefix,'packages':versions,'training_device':'CPU only; existing true CUDA Mamba predictions reused','new_neural_weights':False})
    dump(OUT/'plan_locked.json',{'at':now(),'plan_sha256':sha(OUT/'evaluation_plan.json'),'market_max':'2025-12-31','test_not_used_for_new_selection':True,'GPU_required':False})
    print('E6 PLAN LOCKED',gate,flush=True)

def verify():
    for rel,h in json.loads((OUT/'frozen_manifest.json').read_text()).items():
        if sha(OUT/rel)!=h:raise RuntimeError('Frozen input/code changed '+rel)
    for rel,h in json.loads((OUT/'audits/protected_previous_files.json').read_text()).items():
        if sha(ROOT/rel)!=h:raise RuntimeError('Prior result changed '+rel)
    if sha(OUT/'evaluation_plan.json')!=json.loads((OUT/'plan_locked.json').read_text())['plan_sha256']:raise RuntimeError('Plan changed')

def packet(f,ii,target,method,seed,raw,p,delay=2):
    y=f.y5.iloc[ii].to_numpy() if target=='reversal' else (f.nextopen_log5.iloc[ii].to_numpy()>0).astype(int)
    return pd.DataFrame({'ticker':f.attrs['ticker'],'date':f.index[ii].strftime('%Y-%m-%d'),'label_date':pd.to_datetime(f.label_date5.iloc[ii]).dt.strftime('%Y-%m-%d').to_numpy(),'target':target,'method':method,'seed':seed,'y':y,'p_raw':raw,'p':p,'reference_sign':f.reference_sign.iloc[ii].to_numpy(),'return5_pp':f.nextopen_log5.iloc[ii].to_numpy(),'fundamental_delay_sessions':delay})

def raw_P(t,m,seed):
    p=OUT/'reused_P/final'/t/m/f'seed{seed}'/'raw_predictions.npz'
    with np.load(p) as z:return {k:z[k].copy() for k in z.files}

def execute():
    verify();status={'status':'SEARCH','pid':os.getpid(),'started':now(),'fits':0};dump(OUT/'status.json',status)
    selected={};weights={};cvrows=[]
    def fit(t,arm,m,seed,b,config,folder,target='reversal',delay=2):
        f,a=load(t,delay);ar,ids,meta=arrays(f,a,arm,b,target)
        pred,info=fit_job(m,config,seed,ar,folder,{'study':'E6','ticker':t,'target':target,'block':b,'delay':delay,'preprocessing':meta})
        status.update(fits=status['fits']+1,current=f'{t}/{target}/{arm}/{m}/seed{seed}',updated=now());dump(OUT/'status.json',status)
        print('FIT',status['fits'],status['current'],'best',info['best_iteration'],flush=True)
        del ar;gc.collect();return pred,ids
    # Before any test probability generation: F searches and fusion weights.
    for t in ['AAPL','TSLA']:
        f,a=load(t)
        for m in CPU:
            means=[]
            for ci,c in enumerate(bp.CONFIGS[m]):
                scores=[]
                for b in bp.FOLDS:
                    pred,ix=fit(t,'F',m,42,b,c,OUT/'cv'/t/'F'/m/f'c{ci}_fold{b["name"]}')
                    score=brier(f.y5.iloc[ix['eval']],pred['eval']);scores.append(score);cvrows.append({'ticker':t,'model':m,'arm':'F','config_index':ci,'fold':b['name'],'raw_brier':score})
                means.append(float(np.mean(scores)))
            ci=int(np.argmin(means));selected[f'{t}_{m}']={'config_index':ci,'config':bp.CONFIGS[m][ci],'cv_means':means}
        for m in ALL:
            scores=[]
            for w in [0.,.25,.5,.75,1.]:
                loss=[]
                for b in bp.FOLDS:
                    ix=bp.indices(f,b['eval_start'],b['eval_end'])
                    with np.load(OUT/'reused_P/cv'/t/m/f'fold{b["name"]}.npz') as pz:pp=pz['eval']
                    ci=selected[f'{t}_logistic']['config_index']
                    with np.load(OUT/'cv'/t/'F/logistic'/f'c{ci}_fold{b["name"]}'/'raw_predictions.npz') as fz:fp=fz['eval']
                    if len(pp)!=len(ix) or len(fp)!=len(ix):raise RuntimeError('CV calendars mismatch')
                    loss.append(brier(f.y5.iloc[ix],(1-w)*pp+w*fp))
                scores.append(float(np.mean(loss)))
            wi=int(np.argmin(scores));weights[f'{t}_{m}']={'F_weight':[0.,.25,.5,.75,1.][wi],'grid_scores':scores}
    pd.DataFrame(cvrows).to_csv(OUT/'tables/CV_results.csv',index=False)
    dump(OUT/'selected_F_configs.json',selected);dump(OUT/'fusion_weights.json',weights)
    dump(OUT/'selection_locked.json',{'at':now(),'selected_sha':sha(OUT/'selected_F_configs.json'),'weights_sha':sha(OUT/'fusion_weights.json'),'new_test_probabilities_written':False,'neural_gate':'not supported per report-count, frozen neural Late only'})
    status['status']='TRAINING';dump(OUT/'status.json',status)
    output=[];calmetadata=[]
    for target in ['reversal','up_direct']:
        for t in ['AAPL','TSLA']:
            f,a=load(t);_,ids,_=arrays(f,a,'F',bp.FINAL,target)
            y=f.y5.to_numpy() if target=='reversal' else (f.nextopen_log5.to_numpy()>0).astype(int)
            prior=(y[ids['fit']].sum()+1)/(len(ids['fit'])+2)
            # Same calibration-label information as all calibrated pipelines.
            priorcal=(y[ids['cal']].sum()+1)/(len(ids['cal'])+2)
            output.append(packet(f,ids['test'],target,'cal_prior',-1,np.full(len(ids['test']),prior),np.full(len(ids['test']),priorcal)))
            sign=f.reference_sign.to_numpy();cp=np.empty(len(f))
            for s in [-1,1]:
                ii=ids['fit'][sign[ids['fit']]==s];cp[sign==s]=(y[ii].sum()+100*prior)/(len(ii)+100)
            cp[sign==0]=prior
            z,meta=bp.calibrate(cp[ids['cal']],y[ids['cal']],cp[ids['test']]);output.append(packet(f,ids['test'],target,'conditioned_prior',-1,cp[ids['test']],z))
            for seed in SEEDS:
                raw={}
                for m in CPU:
                    for arm in ['F','PF']+(['P'] if target!='reversal' else []):
                        c=selected[f'{t}_{m}']['config'] if arm=='F' else existing_config(t,m)['config']
                        pred,ix=fit(t,arm,m,seed,bp.FINAL,c,OUT/'final'/target/t/arm/m/f'seed{seed}',target)
                        raw[f'{m}_{arm}']=pred
                        p,meta=bp.calibrate(pred['cal'],y[ix['cal']],pred['test'])
                        output.append(packet(f,ix['test'],target,f'{m}_{arm}',seed,pred['test'],p));calmetadata.append({'ticker':t,'target':target,'method':f'{m}_{arm}','seed':seed,**meta})
                # Fixed metadata-only control separates values from missingness/age.
                pred,ix=fit(t,'M','logistic',seed,bp.FINAL,selected[f'{t}_logistic']['config'],OUT/'final'/target/t/'M/logistic'/f'seed{seed}',target)
                p,meta=bp.calibrate(pred['cal'],y[ix['cal']],pred['test']);output.append(packet(f,ix['test'],target,'logistic_metadata',seed,pred['test'],p))
                for m in (ALL if target=='reversal' else CPU):
                    pp=raw_P(t,m,seed) if target=='reversal' else raw[f'{m}_P']
                    if target=='reversal':
                        p,meta=bp.calibrate(pp['cal'],y[ids['cal']],pp['test']);old=pd.read_csv(OUT/'reused_P/final'/t/m/f'seed{seed}'/'test.csv')
                        np.testing.assert_array_equal(old.date.to_numpy(),f.index[ids['test']].strftime('%Y-%m-%d'))
                        np.testing.assert_allclose(p,old.p_calibrated,atol=1e-12)
                        output.append(packet(f,ids['test'],target,f'{m}_P',seed,pp['test'],p))
                    for label,w in [('Late',weights[f'{t}_{m}']['F_weight']),('Late50',.5),('PriorBlend',weights[f'{t}_{m}']['F_weight'])]:
                        fp=raw['logistic_F'];mix={k:(1-w)*pp[k]+w*(prior if label=='PriorBlend' else fp[k]) for k in ['cal','test']}
                        p,meta=bp.calibrate(mix['cal'],y[ids['cal']],mix['test']);output.append(packet(f,ids['test'],target,f'{m}_{label}',seed,mix['test'],p));calmetadata.append({'ticker':t,'target':target,'method':f'{m}_{label}','seed':seed,'F_weight':w,**meta})
            # Predeclared timing stress uses identical selected LR F/PF settings,
            # seed42 only; no hyperparameter or threshold re-selection.
            for arm in ['F','PF']:
                c=selected[f'{t}_logistic']['config'] if arm=='F' else existing_config(t,'logistic')['config']
                pred,ix=fit(t,arm,'logistic',42,bp.FINAL,c,OUT/'sensitivity'/target/t/arm/'delay5',target,5)
                p,meta=bp.calibrate(pred['cal'],y[ix['cal']],pred['test']);output.append(packet(f,ix['test'],target,f'logistic_{arm}_delay5',42,pred['test'],p,5))
    allpred=pd.concat(output,ignore_index=True);allpred.to_csv(OUT/'predictions/all_probabilities.csv.gz',index=False)
    pd.DataFrame(calmetadata).to_csv(OUT/'tables/calibration_parameters.csv',index=False)
    verify();status.update(status='TRAINING_COMPLETE',finished=now(),probability_rows=len(allpred),GPU_used=False);dump(OUT/'status.json',status)
    print('E6 ALL FITS COMPLETE',status['fits'],len(allpred),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--execute',action='store_true');args=ap.parse_args()
    if args.prepare:prepare()
    elif args.execute:
        try:execute()
        except BaseException:
            dump(OUT/'failure.json',{'at':now(),'traceback':traceback.format_exc(),'status':'STOPPED_NO_AUTORETRY'});raise
    else:ap.error('choose --prepare or --execute')
