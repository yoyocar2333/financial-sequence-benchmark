"""Freeze and execute CPU-only event-conditioned benchmark; never alter E3a/E3b."""
import argparse
import datetime as dt
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from e3c_core import (ROOT,OUT,SOURCE,SEEDS,FOLDS,FINAL,GRIDS,PLAN,Prior,load_frame,indices,
                     features,state,blocks,masks,shrink_calibrate,sha,write_json,sigmoid,logit)

CODE=('e3c_core.py','run_e3c.py','analyze_e3c.py','plot_e3c.py','test_e3c.py','e3c_status.py')


def verify():
    for manifest in ('protected_previous_files.json','code_manifest.json'):
        for name,h in json.loads((OUT/manifest).read_text()).items():
            if sha(ROOT/name)!=h:raise RuntimeError('Protected/frozen file changed: '+name)


def prepare():
    if (OUT/'prepared.json').exists():verify();return
    if OUT.exists():raise FileExistsError('Preserve incomplete E3c preparation; refusing overwrite')
    OUT.mkdir(parents=True)
    for name in ('inputs','code','cv','final','predictions','tables','figures','logs'):(OUT/name).mkdir()
    if (ROOT/'logs/e3c_preflight.log').exists():shutil.copyfile(ROOT/'logs/e3c_preflight.log',OUT/'logs/preflight.log')
    protected=json.loads((SOURCE/'protected_previous_files.json').read_text())
    for study in (ROOT/'outputs/e3a_20261021',SOURCE):
        for name,h in json.loads((study/'archive_manifest.json').read_text())['files'].items():
            protected[str((study/name).relative_to(ROOT))]=h
        for name in ('archive_manifest.json','status.json','e3b_complete_results.zip','e3b_complete_results.zip.sha256'):
            p=study/name
            if p.exists():protected[str(p.relative_to(ROOT))]=sha(p)
    for name in ('E3B_SUMMARY.md','README_E3B.md'):
        protected[name]=sha(ROOT/name)
    write_json(OUT/'protected_previous_files.json',protected)
    for p in (SOURCE/'inputs').glob('*through2025.csv'):shutil.copyfile(p,OUT/'inputs'/p.name)
    for name in ('e3a_training_thresholds.json','original_snapshot_provenance.json','e3a_data_audit.csv'):
        shutil.copyfile(SOURCE/'inputs'/name,OUT/'inputs'/name)
    shutil.copyfile(SOURCE/'E3B_SUMMARY.md',OUT/'inputs/E3B_SUMMARY_original.md')
    shutil.copyfile(SOURCE/'GPU_SMOKE.json',OUT/'inputs/E3B_GPU_SMOKE_original.json')
    hashes={}
    for name in CODE+('e3b_protocol.py','e3a_core.py','analyze_e3b.py'):
        p=ROOT/'scripts'/name;shutil.copyfile(p,OUT/'code'/name);hashes[str(p.relative_to(ROOT))]=sha(p)
    shutil.copyfile(ROOT/'README_E3C.md',OUT/'README_E3C.md');hashes['README_E3C.md']=sha(ROOT/'README_E3C.md')
    write_json(OUT/'evaluation_plan.json',{**PLAN,'frozen_utc':dt.datetime.now(dt.timezone.utc).isoformat()})
    hashes[str((OUT/'evaluation_plan.json').relative_to(ROOT))]=sha(OUT/'evaluation_plan.json')
    write_json(OUT/'code_manifest.json',hashes)
    env={n:importlib.metadata.version(n) for n in ('numpy','pandas','scipy','scikit-learn','xgboost-cpu','torch','mamba_ssm')}
    write_json(OUT/'environment.json',{'python':sys.version,'executable':sys.executable,'versions':env,'GPU_used':False})
    (OUT/'environment.lock.txt').write_text(subprocess.check_output([sys.executable,'-B','-m','pip','freeze'],text=True))
    audit=[]
    for ticker in ('AAPL','TSLA'):
        f=load_frame(ticker,OUT);f.to_csv(OUT/'inputs'/f'{ticker}_labels_and_causal_features.csv')
        for block in FOLDS+[dict(name='FINAL',**FINAL)]:
            _,s,meta=features(f,block['fit_end']);ids=blocks(f,block)
            if block['name']=='FINAL':ids['unused_stop2023H1']=indices(f,block['stop_start'],block['stop_end'])
            for name,i in ids.items():
                e=s['event'][i];y=f.y5.iloc[i].to_numpy();mask=masks(f,s,i)
                audit.append({'ticker':ticker,'block':block['name'],'partition':name,'n':len(i),'events':int(e.sum()),
                    'reversals':int(y[e].sum()),'continuations':int(e.sum()-y[e].sum()),
                    'nonoverlap5':int(mask['nonoverlap5'].sum()),'nonoverlap20':int(mask['nonoverlap20'].sum()),
                    'first':str(f.index[i[0]].date()),'last':str(f.index[i[-1]].date()),'label_end20':str(f.end20.iloc[i[-1]].date())})
            if block['name']=='FINAL':
                expected=json.loads((OUT/'inputs/e3a_training_thresholds.json').read_text())[ticker]
                np.testing.assert_allclose(meta['thresholds']['past5'],[expected['past5']['0.1'],expected['past5']['0.9']],atol=1e-12)
                write_json(OUT/'inputs'/f'{ticker}_preprocessing.json',meta)
    pd.DataFrame(audit).to_csv(OUT/'tables/sample_support_audit.csv',index=False)
    write_json(OUT/'neural_support_decision.json',{'new_neural_event_networks':'NOT_TRAINED','reason':'Both final train event counts<1000, thinned5 counts202<300; calibration events19/22<50; earlier folds have4-10-event calibration blocks. Existing E3b weights and one-parameter heads evaluated instead','decision_uses':'training/validation support only, no test-performance selection'})
    write_json(OUT/'prepared.json',{'status':'READY','CPU_only':True,'new_neural_training':False,'CV_raw_model_fits':72,'final_raw_model_fits':40})
    verify();print('E3c protocol/data/source frozen; CPU-only READY',flush=True)


def brier(y,p):return float(np.mean((np.asarray(y)-np.asarray(p))**2))


def fit(name,config,seed,x,y,evals,folder):
    folder.mkdir(parents=True,exist_ok=True)
    complete=folder/'COMPLETE.json'
    if complete.exists():
        z=json.loads(complete.read_text())
        for n,h in z['files'].items():
            if sha(folder/n)!=h:raise RuntimeError('Completed job changed '+str(folder/n))
        z=np.load(folder/'raw_predictions.npz');return {k:z[k] for k in z.files}
    write_json(folder/'config.json',{'model':name,'config':config,'seed':seed,'train_n':len(y),'train_class_counts':np.bincount(y,minlength=2).tolist()})
    started=time.monotonic()
    if name=='lr':
        from sklearn.exceptions import ConvergenceWarning
        import warnings
        m=LogisticRegression(**config,solver='lbfgs',max_iter=2000,random_state=seed)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always',ConvergenceWarning);m.fit(x,y)
        write_json(folder/'warnings.json',{'warnings':[str(a.message) for a in w]})
        if w:raise RuntimeError('LR convergence warning: retained in job log')
        history=[{'iteration':int(m.n_iter_[0]),'train_brier':brier(y,m.predict_proba(x)[:,1])}]
        joblib.dump(m,folder/'model.joblib')
    else:
        from xgboost import XGBClassifier
        m=XGBClassifier(**config,objective='binary:logistic',tree_method='hist',max_bin=64,eval_metric='logloss',
            n_jobs=2,subsample=.8,colsample_bytree=.8,random_state=seed,verbosity=0)
        m.fit(x,y,eval_set=[(x,y)],verbose=False);m.save_model(folder/'model.ubj')
        history=[{'iteration':i+1,'train_log_loss':v} for i,v in enumerate(m.evals_result()['validation_0']['logloss'])]
    pred={n:m.predict_proba(z)[:,1] for n,z in evals.items()}
    importance=m.coef_[0] if name=='lr' else m.feature_importances_
    pd.DataFrame({'feature_index':np.arange(x.shape[1]),'value':importance,'type':'standardized_logit_coefficient' if name=='lr' else 'training_gain_fraction'}).to_csv(folder/'feature_importance.csv',index=False)
    if not all(np.isfinite(v).all() for v in pred.values()):raise RuntimeError('Non-finite probability')
    np.savez_compressed(folder/'raw_predictions.npz',**pred);pd.DataFrame(history).to_csv(folder/'training_history.csv',index=False)
    write_json(folder/'fit_info.json',{'seconds':time.monotonic()-started,'train_n':len(y),'features':x.shape[1]})
    write_json(complete,{'files':{p.name:sha(p) for p in folder.iterdir() if p.is_file() and p.name!='COMPLETE.json'}})
    return pred


def calibrated(raw,calraw,y,s,ids):
    return shrink_calibrate(raw,s['event'][ids['eval']],calraw,y[ids['cal']],s['event'][ids['cal']])


def prior_predictions(method,alpha,y,s,ids):
    m=Prior(method,alpha).fit(y,s,ids['fit'],ids['cal']);cr=m.predict(ids['cal']);raw=m.predict(ids['eval'])
    if method=='recent_event_prior':return raw,raw,{'method':'cal event counts +20 pseudo-observations at historical event prior'}
    p,c=calibrated(raw,cr,y,s,ids);return p,raw,c


def save_prediction(f,ids,st,name,seed,raw,p,calp,info,folder):
    i=ids['eval'];amp=-f.reference_sign.iloc[i].to_numpy()*f.nextopen_log5.iloc[i].to_numpy()
    z=pd.DataFrame({'ticker':f.attrs['ticker'],'date':f.index[i].strftime('%Y-%m-%d'),'label_date':pd.to_datetime(f.label_date5.iloc[i]).dt.strftime('%Y-%m-%d').to_numpy(),
        'method':name,'seed':seed,'target':f.y5.iloc[i].to_numpy(),'p_raw':raw,'p':p,'event':st['event'][i].astype(int),
        'event_direction':st['direction'][i],'long_up':st['long'][i],'VIX_high':st['vol'][i],'cell':st['cell'][i],
        'signed_reversal_amplitude_pp':amp,'executable_log_return_pp':f.nextopen_log5.iloc[i].to_numpy()})
    if not np.isfinite(z[['p','p_raw']]).all().all():raise RuntimeError('Invalid final probability')
    z.to_csv(OUT/'predictions'/f'{f.attrs["ticker"]}_{name}_seed{seed}.csv',index=False)
    # Fixed score bins are determined on historical calibration EVENTS, never test quantiles.
    e=st['event'][ids['cal']];bounds=np.quantile(np.asarray(calp)[e],[.2,.4,.6,.8]).tolist()
    metadata={'calibration':info,'event_score_quintile_bounds':bounds,'test_labels_not_used_for_fit':True}
    write_json(folder/'prediction_metadata.json',metadata)
    write_json(OUT/'predictions'/f'{f.attrs["ticker"]}_{name}_seed{seed}.json',metadata)
    pd.DataFrame({'date':f.index[ids['cal']].strftime('%Y-%m-%d'),'target':f.y5.iloc[ids['cal']].to_numpy(),
        'event':e.astype(int),'p':calp}).to_csv(folder/'calibration_probabilities.csv',index=False)


def execute():
    prepare();statusfile=OUT/'status.json'
    if statusfile.exists():raise FileExistsError('Existing study status; preserve rather than auto-retry')
    status={'status':'SEARCH','pid':os.getpid(),'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'cv_raw_fits':0,'final_raw_fits':0,'current':None}
    write_json(statusfile,status)
    try:
        frames={t:load_frame(t,OUT) for t in ('AAPL','TSLA')};selected={};records=[]
        for ticker,f in frames.items():
            for family in ('lr','xgb'):
                scores=[]
                for ci,config in enumerate(GRIDS[family]):
                    parts=[]
                    for block in FOLDS:
                        status['current']=f'{ticker}_{family}_c{ci}_fold{block["name"]}';write_json(statusfile,status)
                        x,s,meta=features(f,block['fit_end']);ids=blocks(f,block);y=f.y5.to_numpy()
                        pred={}
                        for scope in ('all','event'):
                            tr=ids['fit'] if scope=='all' else ids['fit'][s['event'][ids['fit']]]
                            folder=OUT/'cv'/ticker/family/f'c{ci}'/block['name']/scope
                            pred[scope]=fit(family,config,42,x[tr],y[tr],{n:x[v] for n,v in ids.items() if n!='fit'},folder)
                            write_json(folder/'preprocessing.json',meta)
                            status['cv_raw_fits']+=1;write_json(statusfile,status)
                        for variant in ('all','event'):
                            raw={n:pred['all'][n] if variant=='all' else np.where(s['event'][ids[n]],pred['event'][n],pred['all'][n]) for n in ('cal','eval')}
                            p,c=calibrated(raw['eval'],raw['cal'],y,s,ids);e=s['event'][ids['eval']]
                            score=brier(y[ids['eval']][e],p[e]);parts.append(score)
                            records.append({'ticker':ticker,'family':family,'config_index':ci,'fold':block['name'],'variant':variant,'event_n':int(e.sum()),'calibrated_event_brier':score})
                    scores.append(float(np.mean(parts)))
                selected[ticker+'_'+family]={'index':int(np.argmin(scores)),'joint_CV_brier':scores,'config':GRIDS[family][int(np.argmin(scores))]}
                print('SEARCH',ticker,family,'selected',selected[ticker+'_'+family]['index'],flush=True)
            for method in ('direction_prior','state_prior'):
                scores=[]
                for alpha in GRIDS['prior']:
                    v=[]
                    for block in FOLDS:
                        s=state(f,block['fit_end']);ids=blocks(f,block);y=f.y5.to_numpy();p,_,_=prior_predictions(method,alpha,y,s,ids);e=s['event'][ids['eval']]
                        value=brier(y[ids['eval']][e],p[e]);v.append(value)
                        records.append({'ticker':ticker,'family':method,'config_index':alpha,'fold':block['name'],'variant':'prior','event_n':int(e.sum()),'calibrated_event_brier':value})
                    scores.append(float(np.mean(v)))
                selected[ticker+'_'+method]={'alpha':GRIDS['prior'][int(np.argmin(scores))],'CV_brier':scores}
        pd.DataFrame(records).to_csv(OUT/'tables/CV_results.csv',index=False);write_json(OUT/'selected_configs.json',selected)
        write_json(OUT/'selection_locked.json',{'sha256':sha(OUT/'selected_configs.json'),'no_E3c_test_predictions_generated_yet':True,'CV_raw_fits':status['cv_raw_fits']})
        verify();status['status']='TRAINING';write_json(statusfile,status)
        for ticker,f in frames.items():
            f.attrs['ticker']=ticker;x,s,meta=features(f,FINAL['fit_end']);ids=blocks(f,FINAL);ids['eval']=ids.pop('test');y=f.y5.to_numpy()
            for family in ('lr','xgb'):
                config=selected[ticker+'_'+family]['config']
                for seed in SEEDS:
                    status['current']=f'{ticker}_{family}_seed{seed}';write_json(statusfile,status)
                    pred={}
                    for scope in ('all','event'):
                        tr=ids['fit'] if scope=='all' else ids['fit'][s['event'][ids['fit']]]
                        folder=OUT/'final'/ticker/family/f'seed{seed}'/scope
                        pred[scope]=fit(family,config,seed,x[tr],y[tr],{n:x[v] for n,v in ids.items() if n!='fit'},folder)
                        write_json(folder/'preprocessing.json',meta);status['final_raw_fits']+=1;write_json(statusfile,status)
                    for variant in ('all','event'):
                        raw={n:pred['all'][n] if variant=='all' else np.where(s['event'][ids[n]],pred['event'][n],pred['all'][n]) for n in ('cal','eval')}
                        p,c=calibrated(raw['eval'],raw['cal'],y,s,ids)
                        cp,_=shrink_calibrate(raw['cal'],s['event'][ids['cal']],raw['cal'],y[ids['cal']],s['event'][ids['cal']])
                        save_prediction(f,ids,s,family+'_'+variant,seed,raw['eval'],p,cp,c,OUT/'final'/ticker/family/f'seed{seed}'/variant)
                    print('FINAL',status['current'],flush=True)
            for method in ('global_prior','event_prior','direction_prior','state_prior','recent_event_prior'):
                alpha=selected.get(ticker+'_'+method,{}).get('alpha',30.)
                p,raw,c=prior_predictions(method,alpha,y,s,ids)
                m=Prior(method,alpha).fit(y,s,ids['fit'],ids['cal']);cr=m.predict(ids['cal'])
                cp=cr if method=='recent_event_prior' else shrink_calibrate(cr,s['event'][ids['cal']],cr,y[ids['cal']],s['event'][ids['cal']])[0]
                folder=OUT/'final'/ticker/method;folder.mkdir(parents=True)
                write_json(folder/'prior.json',{'alpha':alpha,'train_global_rate':m.global_p,'train_event_rate':m.event_p,'fit_end':FINAL['fit_end'],'formula':PLAN['priors']})
                save_prediction(f,ids,s,method,-1,raw,p,cp,c,folder)
            # Reuse ALL E3b A/B models and simple baselines without training or selecting them again.
            for model in ('logistic','xgboost','lightgbm','lstm','mamba'):
                for arm in ('A','B'):
                    for seed in SEEDS:
                        old=SOURCE/'final/h5'/ticker/arm/model/f'seed{seed}'
                        zz=pd.read_csv(old/'predictions.csv');cc=pd.read_csv(old/'calibration_predictions.csv');ci=json.loads((old/'calibration.json').read_text())
                        np.testing.assert_array_equal(zz.date,f.index[ids['eval']].strftime('%Y-%m-%d'))
                        np.testing.assert_array_equal(cc.date,f.index[ids['cal']].strftime('%Y-%m-%d'))
                        np.testing.assert_array_equal(zz.target_reversal,y[ids['eval']])
                        np.testing.assert_array_equal(cc.target_reversal,y[ids['cal']])
                        cp=sigmoid(ci['coefficient']*logit(cc.p_raw)+ci['intercept'])
                        name=f'e3b_{model}_{arm}';folder=OUT/'final'/ticker/name/f'seed{seed}';folder.mkdir(parents=True)
                        save_prediction(f,ids,s,name,seed,zz.p_raw.to_numpy(),zz.p_calibrated.to_numpy(),cp,{'reused_from':str(old.relative_to(ROOT)),**ci},folder)
                        shutil.copyfile(old/'predictions.csv',OUT/'inputs'/f'{ticker}_{name}_seed{seed}_original.csv')
                        provenance=OUT/'inputs/e3b_models'/ticker/arm/model/f'seed{seed}';provenance.mkdir(parents=True)
                        for fn in ('calibration.json','calibration_predictions.csv','fit_info.json','config.json'):
                            shutil.copyfile(old/fn,provenance/fn)
                        if model in ('lstm','mamba') and arm=='B':
                            p,c=shrink_calibrate(zz.p_calibrated.to_numpy(),s['event'][ids['eval']],cp,y[ids['cal']],s['event'][ids['cal']],event_head=True)
                            ccp,_=shrink_calibrate(cp,s['event'][ids['cal']],cp,y[ids['cal']],s['event'][ids['cal']],event_head=True)
                            folder=OUT/'final'/ticker/f'recal_{model}_B'/f'seed{seed}';folder.mkdir(parents=True)
                            save_prediction(f,ids,s,f'recal_{model}_B',seed,zz.p_calibrated.to_numpy(),p,ccp,c,folder)
            for model in ('cal_prior','momentum20','mean_reversion5'):
                zz=pd.read_csv(SOURCE/'predictions'/f'{ticker}_h5_{model}.csv');name='e3b_'+model
                folder=OUT/'final'/ticker/name;folder.mkdir(parents=True)
                if model=='cal_prior':cp=np.full(len(ids['cal']),(y[ids['cal']].sum()+1)/(len(ids['cal'])+2))
                else:
                    past=20 if model=='momentum20' else 5;z=f.iloc[ids['cal']]
                    standardized=z[f'past{past}'].to_numpy()/(z[f'RV{past}'].to_numpy()/np.sqrt(252)*np.sqrt(past))
                    pup=sigmoid(standardized if model=='momentum20' else -standardized)
                    cp=np.where(z.reference_sign.to_numpy()<0,pup,1-pup)
                    ci=json.loads((SOURCE/'predictions'/f'{ticker}_h5_{model}_calibration.json').read_text())
                    cp=sigmoid(ci['coefficient']*logit(cp)+ci['intercept'])
                save_prediction(f,ids,s,name,-1,zz.p_raw.to_numpy(),zz.p_calibrated.to_numpy(),cp,{'reused_E3b_baseline':model},folder)
        verify();status.update(status='ANALYZING',current=None);write_json(statusfile,status)
        subprocess.run([sys.executable,'-B','-u',str(ROOT/'scripts/analyze_e3c.py')],cwd=ROOT,check=True)
        verify();status.update(status='COMPLETE',finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),archive=str(OUT/'e3c_complete_results.zip'))
        write_json(statusfile,status);print('COMPLETE',status['archive'],flush=True)
    except BaseException:
        status.update(status='STOPPED',traceback=traceback.format_exc());write_json(statusfile,status);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');args=p.parse_args()
    with (ROOT/'logs/e3c-suite.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.execute:execute()
        else:prepare()
