"""Prepare, lock, fit and predict E4c. CPU only; existing studies are read-only."""
import argparse
import datetime as dt
import importlib.metadata
import json
import os
from pathlib import Path
import pickle
import platform
import shutil
import warnings
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from e4c_protocol import ROOT,OUT,SOURCE,SEEDS,TIMINGS,TYPES,FEATURES,PRICE,PLAN,sha,dump,load_frame,indices,logit,sigmoid
from e3c_core import state
from e3c_calibration_v1_1 import solve

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def savecsv(df,p):
    df.to_csv(p,index=False,compression={'method':'gzip','mtime':0} if str(p).endswith('.gz') else None)

def prepare(out):
    if (out/'plan_locked.json').exists():raise RuntimeError('Plan already locked; refusing prepare overwrite')
    for d in ('inputs','data','models','predictions','tables','figures','logs','code','protocol_2026_unchanged','audits'):(out/d).mkdir(parents=True,exist_ok=True)
    protected={}
    for p in sorted((SOURCE/'protocol_2026_unchanged').rglob('*')):
        if p.is_file():
            protected[str(p.relative_to(ROOT))]=sha(p)
            dest=out/'protocol_2026_unchanged'/p.relative_to(SOURCE/'protocol_2026_unchanged');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    for name in ('E4B_SUMMARY.md','E4C_EXPLORATORY_PROPOSAL.md','e4b_complete_results.zip'):
        p=SOURCE/name;protected[str(p.relative_to(ROOT))]=sha(p)
    for n in ('AAPL','QQQ','VIX','VXN'):
        p=SOURCE/'inputs'/f'{n}_adjusted_through2025.csv';shutil.copy2(p,out/'inputs'/p.name);protected[str(p.relative_to(ROOT))]=sha(p)
    shutil.copy2(SOURCE/'E4C_EXPLORATORY_PROPOSAL.md',out/'inputs/E4C_EXPLORATORY_PROPOSAL.md')
    a=pd.read_csv(SOURCE/'datasets/news_unified.csv.gz',keep_default_na=False)
    a=a[a.source_family.eq('apple_newsroom_recollected')&a.ticker.eq('AAPL')].copy()
    assert len(a)==448 and a.publication_date.between('2023-01-01','2025-12-31').all() and a.record_id.is_unique
    assert (~a.strict_PIT_eligible.astype(bool)).all()
    feats=pd.read_csv(SOURCE/'features/article_features.csv',keep_default_na=False)
    feats=feats[feats.record_id.isin(a.record_id)&feats.source.eq('full')].copy()
    assert len(feats)==448 and feats.record_id.is_unique
    ff=a[['record_id','text_sha256']].merge(feats[['record_id','text_sha256']],on='record_id',validate='one_to_one')
    assert ff.text_sha256_x.eq(ff.text_sha256_y).all()
    savecsv(a,out/'inputs/apple_newsroom_448.csv.gz');savecsv(feats,out/'inputs/apple_full_features.csv.gz')
    for n in ('model_registry.json','COMPLETE.json'):shutil.copy2(SOURCE/'features'/n,out/'inputs'/('e4b_features_'+n))
    f=load_frame('AAPL',out);st=state(f,'2022-12-31');calendar=f.index
    # Source collection covers the archive calendar from2023-01-01, not the
    # dates preceding the first actual retained article. Source completeness
    # remains unknown. Use common +2session delayed observation boundary.
    startidx=calendar.searchsorted(pd.Timestamp('2023-01-03'))+2
    common=np.arange(len(f))>=startidx+4
    idmap={n:indices(f,f'{y}-01-01',f'{y}-12-31') for n,y in [('train',2023),('validation',2024),('test',2025)]}
    idmap={k:v[common[v]] for k,v in idmap.items()}
    ids=np.concatenate(list(idmap.values()));part={int(i):p for p,ii in idmap.items() for i in ii}
    full=a.merge(feats,on=['record_id','text_sha256','publication_date'],validate='one_to_one').sort_values(['publication_date','record_id'])
    base_info=calendar.searchsorted(pd.to_datetime(full.publication_date),side='right')
    align=[];daily=[];links=[]
    for delay,timing in enumerate(TIMINGS):
        info=base_info+delay
        for j,r in enumerate(full.itertuples()):
            align.append({'record_id':r.record_id,'publication_date':r.publication_date,'timing':timing,'proxy_information_date':calendar[info[j]].strftime('%Y-%m-%d') if info[j]<len(calendar) else None,'strict_PIT_verified':False})
        for i in ids:
            dates=(info>=i-4)&(info<=i)
            nn=full.loc[dates].drop_duplicates('text_sha256');n=len(nn)
            signed=float((nn.sent_positive-nn.sent_negative).mean()) if n else 0.
            x={'ticker':'AAPL','date':calendar[i].strftime('%Y-%m-%d'),'partition':part[int(i)],'timing':timing,'target':int(f.y5.iloc[i]),'label_end5':str(f.label_date5.iloc[i].date()),'label_end20':str(f.end20.iloc[i].date()),
               'signed_reversal_amplitude_pp':float(-f.reference_sign.iloc[i]*f.nextopen_log5.iloc[i]),'executable_return5_log_pp':float(f.nextopen_log5.iloc[i]),'event':int(st['event'][i]),'direction':int(st['direction'][i]),'long_up':int(st['long'][i]),'VIX_high':int(st['vol'][i]),'VXN_high':int(st['vxn_high'][i]),'cell':int(st['cell'][i]),
               'conflict':float(st['direction'][i]*(2*st['long'][i]-1)<0),'news_count':n,'news_present':float(n>0),'news_log_count':float(np.log1p(n)),'news_signed_mean':signed,'news_signed_reference_interaction':signed*float(f.reference_sign.iloc[i]),'reconstructed_source_window_observed':True,'historical_source_completeness_verified':False,'strict_PIT_verified':False}
            for c in PRICE:
                if c!='conflict':x[c]=float(f[c].iloc[i])
            for typ in TYPES:x['raw_type_'+typ]=float(nn['event_type_'+typ].mean()) if n else 0.
            x['news_type_earnings']=x['raw_type_earnings'];x['news_type_product_launch']=x['raw_type_product_launch']
            x['news_type_legal_regulatory']=x['raw_type_litigation']+x['raw_type_regulation'];x['news_type_merger_acquisition']=x['raw_type_merger_acquisition']
            x['news_sentiment_bin']=0 if not n else 1 if signed<=-.1 else 3 if signed>=.1 else 2
            x['news_structure_bin']=4 if x['news_type_merger_acquisition']>0 else 3 if x['news_type_legal_regulatory']>0 else 2 if x['news_type_earnings']>0 else 1 if x['news_type_product_launch']>0 else 0
            daily.append(x)
            for rr in nn.itertuples():
                links.append({'date':x['date'],'partition':x['partition'],'timing':timing,'record_id':rr.record_id,'text_sha256':rr.text_sha256,'publication_date':rr.publication_date,'strict_PIT_verified':False})
    d=pd.DataFrame(daily);assert np.isfinite(d[FEATURES['T']+['target','signed_reversal_amplitude_pp']]).all().all()
    savecsv(d,out/'data/daily_features.csv.gz');savecsv(pd.DataFrame(align),out/'data/article_timing_manifest.csv');savecsv(pd.DataFrame(links),out/'data/article_daily_links.csv.gz')
    support=[]
    for (t,p),z in d.groupby(['timing','partition'],sort=False):
        e=z[z.event.eq(1)];support.append({'timing':t,'partition':p,'n_dates':len(z),'n_events':len(e),'event_reversals':int(e.target.sum()),'event_continuations':int((1-e.target).sum()),'events_with_retained_news':int(e.news_present.sum()),'date_min':z.date.min(),'date_max':z.date.max(),'last_label_end20':z.label_end20.max()})
    savecsv(pd.DataFrame(support),out/'tables/sample_support.csv')
    dump(out/'audits/thresholds.json',st['thresholds']);dump(out/'audits/protected_files.json',protected)
    versions={n:importlib.metadata.version(n) for n in ('numpy','pandas','scipy','scikit-learn')}
    dump(out/'environment.json',{'python':platform.python_version(),'executable':os.path.realpath(os.sys.executable),'versions':versions,'GPU_used':False,'BLAS_threads':2})
    codes=['e4c_protocol.py','run_e4c.py','analyze_e4c.py','audit_e4c_fnspid.py','finalize_e4c.py','e3a_core.py','e3b_protocol.py','e3c_core.py','e3c_calibration_v1_1.py','analyze_e3b.py','analyze_e3c.py']
    for n in codes:
        p=ROOT/'scripts'/n
        if not p.exists():raise RuntimeError('All code must exist before locking '+n)
        shutil.copy2(p,out/'code'/n)
    dump(out/'research_plan.json',PLAN)
    files=[p for p in out.rglob('*') if p.is_file() and (p.parent.name in ('inputs','code') or p.name in ('research_plan.json','daily_features.csv.gz','protected_files.json'))]
    dump(out/'plan_locked.json',{'locked_utc':now(),'before_any_E4c_model_fitting':True,'files':{str(p.relative_to(out)):sha(p) for p in files}})
    print(now(),'PREPARED and LOCKED',support,flush=True)

class Hierarchy:
    def __init__(self,arm):self.arm=arm
    def fit(self,df):
        self.data=df.copy();self.global_p=(df.target.sum()+1)/(len(df)+2);return self
    def predict(self,df):
        z=self.data;ans=[]
        for row in df.itertuples():
            q=self.global_p;use=z
            keys=['direction','long_up','VIX_high']+(['news_sentiment_bin'] if self.arm in ('S','T') else [])+(['news_structure_bin'] if self.arm=='T' else [])
            for key in keys:
                use=use[use[key].eq(getattr(row,key))];q=(use.target.sum()+30*q)/(len(use)+30)
            ans.append(q)
        return np.asarray(ans,float)

def verify(out):
    for name,h in json.loads((out/'plan_locked.json').read_text())['files'].items():
        if sha(out/name)!=h:raise RuntimeError('Locked input/code changed '+name)
    for name,h in json.loads((out/'audits/protected_files.json').read_text()).items():
        if (ROOT/name).exists() and sha(ROOT/name)!=h:raise RuntimeError('Protected original changed '+name)

def train(out):
    verify(out)
    if (out/'selection_locked.json').exists():raise RuntimeError('Models already locked; refusing retraining')
    d=pd.read_csv(out/'data/daily_features.csv.gz');selected=[];search=[];packs=[];coefs=[];calrows=[]
    warnings.filterwarnings('error',category=ConvergenceWarning)
    for timing,z in d.groupby('timing',sort=False):
        tr=z[z.partition.eq('train')];va=z[z.partition.eq('validation')]
        assert tr.date.max()<'2024-01-01' and va.date.max()<'2025-01-01'
        # Models are fit and selected without requesting test predictions.
        for arm,cols in FEATURES.items():
            scaler=StandardScaler().fit(tr[cols]);xt=scaler.transform(tr[cols]);xv=scaler.transform(va[cols]);candidates=[]
            for c in (.01,.1,1.):
                model=LogisticRegression(C=c,solver='lbfgs',tol=1e-10,max_iter=3000,random_state=42).fit(xt,tr.target)
                p=model.predict_proba(xv)[:,1];score=float(np.mean((p-va.target.to_numpy())**2))
                search.append({'timing':timing,'arm':arm,'C':c,'validation_all_Brier_raw':score,'validation_event_Brier_raw':float(np.mean((p[va.event.eq(1)]-va.loc[va.event.eq(1),'target'])**2)),'n_train':len(tr),'n_validation':len(va)})
                candidates.append((score,c))
            best=min(x[0] for x in candidates);c=min(c for s,c in candidates if s<=best+1e-12)
            selected.append({'timing':timing,'arm':arm,'C':c,'validation_Brier_raw':best,'columns':cols})
            check=[]
            for seed in SEEDS:
                model=LogisticRegression(C=c,solver='lbfgs',tol=1e-10,max_iter=3000,random_state=seed).fit(xt,tr.target)
                pv=model.predict_proba(xv)[:,1];check.append(pv)
                theta,diag=solve(pv,va.target);pack={'family':'lr','arm':arm,'timing':timing,'seed':seed,'columns':cols,'scaler':scaler,'model':model,'theta':theta,'C':c}
                packs.append(pack)
                calrows.append({'timing':timing,'method':'lr_'+arm,'seed':seed,'slope':theta[0],'intercept':theta[1],**diag})
                coefs.extend({'timing':timing,'arm':arm,'seed':seed,'feature':col,'scaled_coefficient':float(v),'C':c} for col,v in zip(cols,model.coef_[0]))
            if np.max(np.ptp(np.asarray(check),axis=0))>1e-12:raise RuntimeError('Unexpected seed-dependent LBFGS results; protocol assumes deterministic CPU fits')
        for method in ('global','event','hier_P','hier_S','hier_T'):
            prior=Hierarchy(method[-1]).fit(tr) if method.startswith('hier') else None
            pack={'family':'prior','method':method,'timing':timing,'seed':0,'model':prior,'global':float((tr.target.sum()+1)/(len(tr)+2)),'event':float((tr.loc[tr.event.eq(1),'target'].sum()+1)/(tr.event.sum()+2))}
            pv=predict_raw(pack,va);theta,diag=solve(pv,va.target);pack['theta']=theta;packs.append(pack)
            calrows.append({'timing':timing,'method':method,'seed':0,'slope':theta[0],'intercept':theta[1],**diag})
        print(now(),'FITTED',timing,'train',len(tr),'validation',len(va),'no test predictions yet',flush=True)
    savecsv(pd.DataFrame(search),out/'tables/validation_search.csv');savecsv(pd.DataFrame(coefs),out/'tables/logistic_coefficients.csv');savecsv(pd.DataFrame(calrows),out/'tables/calibration_parameters.csv')
    dump(out/'selected_configs.json',selected)
    with (out/'models/fitted_models.pkl').open('wb') as f:pickle.dump(packs,f,protocol=5)
    dump(out/'selection_locked.json',{'locked_utc':now(),'selected_configs_sha256':sha(out/'selected_configs.json'),'models_sha256':sha(out/'models/fitted_models.pkl'),'test_predictions_generated':False,'validation_reused_selection_and_calibration':True,'seeds_deterministic_verified':True})

def predict_raw(pack,z):
    if pack['family']=='lr':return pack['model'].predict_proba(pack['scaler'].transform(z[pack['columns']]))[:,1]
    if pack['method']=='global':return np.full(len(z),pack['global'])
    if pack['method']=='event':return np.where(z.event.eq(1),pack['event'],pack['global'])
    return pack['model'].predict(z)

def predict(out):
    verify(out);lock=json.loads((out/'selection_locked.json').read_text())
    assert sha(out/'models/fitted_models.pkl')==lock['models_sha256'] and sha(out/'selected_configs.json')==lock['selected_configs_sha256']
    if (out/'predictions/COMPLETE.json').exists():raise RuntimeError('Test predictions already exist; refusing overwrite')
    with (out/'models/fitted_models.pkl').open('rb') as f:packs=pickle.load(f)
    data=pd.read_csv(out/'data/daily_features.csv.gz');pred=[];cutoffs=[]
    for pack in packs:
        z=data[data.timing.eq(pack['timing'])].copy();raw=predict_raw(pack,z);a,b=pack['theta'];p=sigmoid(a*logit(raw)+b)
        method='lr_'+pack['arm'] if pack['family']=='lr' else pack['method']
        q=z[['ticker','date','partition','timing','target','label_end5','event','direction','long_up','VIX_high','VXN_high','cell','conflict','news_count','news_present','signed_reversal_amplitude_pp','executable_return5_log_pp']].copy()
        q['method']=method;q['seed']=pack['seed'];q['p_raw']=raw;q['p_calibrated']=p
        pred.append(q)
        cal=z.partition.eq('validation')&z.event.eq(1)
        cutoffs.append({'timing':pack['timing'],'method':method,'seed':pack['seed'],'validation_event_quartile_bounds':np.quantile(p[cal],[.25,.5,.75]).tolist()})
    p=pd.concat(pred,ignore_index=True);assert np.isfinite(p[['p_raw','p_calibrated']]).all().all()
    savecsv(p,out/'predictions/all_probabilities.csv.gz');savecsv(p[p.partition.eq('test')],out/'predictions/test_probabilities.csv.gz');dump(out/'models/validation_event_score_bins.json',cutoffs)
    dump(out/'predictions/COMPLETE.json',{'completed_utc':now(),'rows':len(p),'rows_test':int(p.partition.eq('test').sum()),'selection_lock_sha256':sha(out/'selection_locked.json'),'probabilities_sha256':sha(out/'predictions/all_probabilities.csv.gz'),'no_test_fit':True})
    print(now(),'PREDICTIONS COMPLETE',len(p),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','train','predict']);p.add_argument('--out',type=Path,default=OUT);a=p.parse_args()
    {'prepare':prepare,'train':train,'predict':predict}[a.phase](a.out.resolve())
if __name__=='__main__':main()
