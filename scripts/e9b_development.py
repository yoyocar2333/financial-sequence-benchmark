"""Fixed-config development-only information and shrinkage controls.
All financial fits end at2020-06-30 at latest; evaluation ends2022.
"""
import csv,json,time,warnings,os
import numpy as np,pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
import e3b_protocol as bp,e5_core as ec,e6_core as fc
from e9b_core import R,O,save,dump,start,load_dev,metrics,inference,holm,sha

DUP=['past5','past20','past60','past120','RV5','RV20','Close'];EXPERTS=['logistic','xgboost','lightgbm','lstm','mamba']

def fit_once(ticker,fold,arm,X,y,ii,jj):
 folder=O/'models/development'/ticker/str(fold)/arm;folder.mkdir(parents=True,exist_ok=True)
 predfile=folder/'predictions.npz';metafile=folder/'fit.json'
 signature=dict(ticker=ticker,fold=fold,arm=arm,plan_sha=sha(O/'ANALYSIS_PLAN_LOCKED.json'),shape=list(X.shape),n_train=len(ii),n_eval=len(jj),C=.001,max_iter=500,tol=.0001,seed=42)
 if predfile.exists() and metafile.exists():
  meta=json.loads(metafile.read_text());assert meta['signature']==signature,'Invalid resume'
  with np.load(predfile) as z:
   from scipy.special import expit
   recalculated=expit(X[jj]@z['coef'].T+z['intercept']).ravel()
   np.testing.assert_allclose(recalculated,z['p'],rtol=0,atol=1e-12)
   return recalculated,meta
 if os.environ.get('E9B_NO_REFIT')=='1':raise RuntimeError('No-refit replay missing completed LR artifact: '+str(folder))
 attempts=[];model=None
 for maxiter in [500,2000]:
  started=time.monotonic();model=LogisticRegression(C=.001,solver='lbfgs',max_iter=maxiter,tol=.0001,random_state=42)
  with warnings.catch_warnings(record=True) as caught:
   warnings.simplefilter('always',ConvergenceWarning);model.fit(X[ii],y[ii])
  messages=[str(w.message) for w in caught];failed=any(issubclass(w.category,ConvergenceWarning) for w in caught)
  attempts.append(dict(max_iter=maxiter,iterations=int(model.n_iter_[0]),warnings=messages,converged=not failed,seconds=time.monotonic()-started))
  if not failed:break
 if failed:raise RuntimeError('Predeclared convergence stop: '+str(signature))
 p=model.predict_proba(X[jj])[:,1];np.savez_compressed(predfile,p=p,coef=model.coef_,intercept=model.intercept_)
 meta=dict(signature=signature,attempts=attempts,information_end=fold+'-06-30',evaluation_max='2022-12-31',converged=True);dump(metafile,meta)
 print('FIT',ticker,fold,arm,attempts[-1]['iterations'],round(attempts[-1]['seconds'],2),flush=True);return p,meta

def choose(previous,candidate):
 if not previous:return .5
 scores=[]
 for w in [0.,.25,.5,.75,1.]:
  scores.append(np.mean([np.mean(((1-w)*a['P']+w*(a['constant'] if candidate=='constant' else a['F'])-a['y'])**2) for a in previous]))
 return [0.,.25,.5,.75,1.][int(np.argmin(scores))]

def main():
 inputs=[]
 for ticker in ['AAPL','TSLA']:
  for block in bp.FOLDS:
   for model in EXPERTS:inputs.append(f'outputs/e5_20261102/cv/{ticker}/T/{model}/c0_fold{block["name"]}/raw_predictions.npz')
   inputs.append(f'outputs/e6_20261106/cv/{ticker}/F/logistic/c0_fold{block["name"]}/raw_predictions.npz')
 start('development',inputs);predrows=[];weightrows=[];fitrows=[];calendar=None;vintagecounts=[]
 for ticker in ['AAPL','TSLA']:
  f=load_dev(ticker);a=pd.read_csv(O/'inputs'/f'{ticker}_fundamentals_development.csv');a.index=pd.to_datetime(a.date);a=a.reindex(f.index)
  assert a.index.max()<=pd.Timestamp('2022-12-31')
  # Historical producer labels are independently checked before reusing its forecasts.
  label_rows=[]
  with (R/f'outputs/e5_20261102/inputs/{ticker}_technical_and_labels.csv').open() as source:
   for row in csv.DictReader(source):
    if row['Date']>'2022-12-31':break
    label_rows.append({k:row[k] for k in ['Date','y5','label_date5','end20']})
  old_labels=pd.DataFrame(label_rows).set_index('Date')
  calendar=f.loc['2017-01-01':'2022-12-31'].index if calendar is None else calendar
  histories={m:[] for m in EXPERTS}
  for block in bp.FOLDS:
   fold=block['name'];P,pm=ec.transform(f,'T',block['fit_end']);F,fm=fc.fundamental_matrix(f,a,block['fit_end']);M=F[:,7:-1]
   assert P.shape[1]==51 and F.shape[1]==16 and M.shape[1]==8
   ii=bp.indices(f,'2012-01-01',block['fit_end']);jj=bp.indices(f,block['eval_start'],block['eval_end']);y=f.y5.to_numpy();dates=f.index[jj]
   assert dates.max()<=pd.Timestamp('2022-12-31') and (f.end20.iloc[jj]<=block['eval_end']).all()
   for ids in [ii,jj]:
    old=old_labels.loc[f.index[ids].strftime('%Y-%m-%d')]
    np.testing.assert_array_equal(old.y5.astype(int).to_numpy(),y[ids])
    np.testing.assert_array_equal(old.label_date5.to_numpy(),pd.to_datetime(f.label_date5.iloc[ids]).dt.strftime('%Y-%m-%d').to_numpy())
   bcols=pm['base']['columns'];dup=P[:,[bcols.index(k) for k in DUP]]
   inputs_mat={'PMzero':np.column_stack([P,M,np.zeros((len(f),7),np.float32)]),'PMF':np.column_stack([P,M,F[:,:7]]),'PMduplicate':np.column_stack([P,M,dup])}
   outputs={}
   for arm,values in inputs_mat.items():
    assert values.shape[1]==66
    X=bp.windows(values,jj).reshape(len(jj),-1);Xfit=bp.windows(values,ii).reshape(len(ii),-1)
    # Compact combined buffer makes the no-test training/evaluation boundary explicit.
    Xall=np.concatenate([Xfit,X]);yall=np.concatenate([y[ii],y[jj]]);trainidx=np.arange(len(ii));evalidx=np.arange(len(ii),len(ii)+len(jj))
    prediction,meta=fit_once(ticker,fold,arm,Xall,yall,trainidx,evalidx);outputs[arm]=prediction;fitrows.append(dict(ticker=ticker,fold=fold,arm=arm,n_train=len(ii),n_eval=len(jj),input_features=Xfit.shape[1],iterations=meta['attempts'][-1]['iterations'],converged=meta['converged']))
   X=F[:,7:];prediction,meta=fit_once(ticker,fold,'metadata',X,y,ii,jj);outputs['metadata']=prediction;fitrows.append(dict(ticker=ticker,fold=fold,arm='metadata',n_train=len(ii),n_eval=len(jj),input_features=9,iterations=meta['attempts'][-1]['iterations'],converged=True))
   prior=float((y[ii].sum()+1)/(len(ii)+2))
   with np.load(R/f'outputs/e6_20261106/cv/{ticker}/F/logistic/c0_fold{fold}/raw_predictions.npz') as z:fp=z['eval'].copy()
   assert fp.shape==(len(jj),);outputs['F']=fp;outputs['constant']=np.full(len(jj),prior)
   vintagecounts.append(dict(ticker=ticker,fold=fold,n_train_vintages=int(a.vintage.iloc[ii].nunique()),n_eval_vintages=int(a.vintage.iloc[jj].nunique()),n_train_days=len(ii),n_eval_days=len(jj)))
   for model in EXPERTS:
    with np.load(R/f'outputs/e5_20261102/cv/{ticker}/T/{model}/c0_fold{fold}/raw_predictions.npz') as z:pp=z['eval'].copy()
    assert pp.shape==fp.shape
    history=histories[model];w=choose(history,'F');u=choose(history,'constant')
    best='P' if not history or np.mean([np.mean((h['P']-h['y'])**2) for h in history])<=np.mean([np.mean((h['F']-h['y'])**2) for h in history]) else 'F'
    outputs[model+'_P']=pp;outputs[model+'_Late']=(1-w)*pp+w*fp;outputs[model+'_SameShrink']=(1-w)*pp+w*prior;outputs[model+'_TunedShrink']=(1-u)*pp+u*prior;outputs[model+'_BestSingle']=pp if best=='P' else fp
    weightrows.append(dict(ticker=ticker,fold=fold,model=model,F_weight=w,shrink_weight=u,best_single=best,n_previous_folds=len(history),selection_uses_current_outer_labels=False))
    history.append(dict(P=pp,F=fp,constant=prior,y=y[jj]))
   for name,p in outputs.items():
    for d,yy,q in zip(dates,y[jj],p):predrows.append(dict(ticker=ticker,date=d.strftime('%Y-%m-%d'),fold=fold,method=name,y=int(yy),p=float(q),stage='development_only',config=0))
 z=pd.DataFrame(predrows);save(z,O/'predictions/development_probabilities.csv.gz');save(pd.DataFrame(weightrows),O/'tables/development_prequential_weights.csv');save(pd.DataFrame(fitrows),O/'tables/development_fit_audit.csv');save(pd.DataFrame(vintagecounts),O/'tables/development_vintage_support.csv')
 metric=[]
 for (t,m),g in z.groupby(['ticker','method']):metric.append(dict(ticker=t,method=m,**metrics(g.y,g.p)))
 save(pd.DataFrame(metric),O/'tables/development_metrics.csv')
 contrasts=[('C1','PMF','PMzero'),('C2','PMF','PMduplicate'),('C3','PMF','logistic_P'),('C4','logistic_Late','logistic_SameShrink'),('C5','logistic_Late','logistic_TunedShrink'),('C6','logistic_Late','logistic_BestSingle')]
 arrays=[];masks=[];quarter=[];contrasts_daily={}
 for t in ['AAPL','TSLA']:
  pivot=z[z.ticker.eq(t)].pivot(index='date',columns='method',values='p');yy=z[z.ticker.eq(t)].groupby('date').y.first();pivot.index=pd.to_datetime(pivot.index);yy.index=pd.to_datetime(yy.index)
  assert not pivot.isna().any().any();d=pd.DataFrame({cid:(pivot[ref]-yy)**2-(pivot[can]-yy)**2 for cid,can,ref in contrasts});contrasts_daily[t]=d
  aligned=d.reindex(calendar);mask=aligned.notna().all(axis=1).to_numpy();arrays.append(aligned.fillna(0).to_numpy());masks.append(mask)
  for period,g in d.groupby(d.index.to_period('Q')):
   for col in d:quarter.append(dict(ticker=t,quarter=str(period),contrast=col,n_dates=len(g),difference=float(g[col].mean())))
 arr=np.stack(arrays);mask=np.stack(masks);rows=[]
 for block in [60,20,120]:
  inf=inference(arr,mask,block,20261115+block+400)
  hp=holm([r['hac_p'] for r in inf]);bpv=holm([r['bootstrap_p'] for r in inf])
  for i,((cid,can,ref),r) in enumerate(zip(contrasts,inf)):rows.append(dict(contrast=cid,candidate=can,reference=ref,block=block,primary_block=block==60,**r,hac_holm6=hp[i],bootstrap_holm6=bpv[i],exploratory=True))
 save(pd.DataFrame(rows),O/'tables/development_six_contrasts.csv');q=pd.DataFrame(quarter);save(q,O/'tables/development_quarterly_differences.csv');v=[]
 for cid,can,ref in contrasts:
  wide=q[q.contrast.eq(cid)].pivot(index='quarter',columns='ticker',values='difference')
  for t in ['AAPL','TSLA']:v.append(dict(contrast=cid,ticker=t,n_calendar_quarters=wide[t].count(),SD_quarter_mean=wide[t].std(ddof=1),lag1_autocorrelation=wide[t].autocorr(1),cross_stock_quarter_correlation=wide.AAPL.corr(wide.TSLA),certified_population_dependence=False))
 save(pd.DataFrame(v),O/'tables/development_variance_diagnostics.csv');dump(O/'audits/development_complete.json',dict(classification_fits=len(fitrows),archived_P_F_reused=True,evaluation_end='2022-12-31',latest_training_end='2020-06-30',new_GPU_fits=0,current_outer_labels_used_for_selection=False,conditional_on_two_stocks=True,source_version_PIT='retrospective_proxy_unchanged'))
 print('DEVELOPMENT COMPLETE',len(fitrows),'classification fits',len(z),'forecast rows',flush=True)
if __name__=='__main__':main()
