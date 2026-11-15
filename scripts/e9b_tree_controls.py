"""All pre-existing CPU tree architectures, fixed candidate0, development-only addendum."""
import json,os
import numpy as np,pandas as pd
import e3b_protocol as bp,e5_core as ec,e6_core as fc
from e3b_models import fit_cpu
from e9b_core import R,O,load_dev,start,save,dump,sha,metrics,inference,holm
DUP=['past5','past20','past60','past120','RV5','RV20','Close']

def main():
 plan=O/'ANALYSIS_PLAN_ADDENDUM_01.json';assert sha(plan)==json.loads((O/'audits/addendum_01_lock.json').read_text())['sha256']
 start('tree_controls',['outputs/e9b_20261115/ANALYSIS_PLAN_ADDENDUM_01.json'])
 output=[];fits=[];calendar=None
 for t in ['AAPL','TSLA']:
  f=load_dev(t);a=pd.read_csv(O/'inputs'/f'{t}_fundamentals_development.csv');a.index=pd.to_datetime(a.date);a=a.reindex(f.index)
  if calendar is None:calendar=f.loc['2017-01-01':'2022-12-31'].index
  for block in bp.FOLDS:
   fold=block['name'];P,pm=ec.transform(f,'T',block['fit_end']);F,_=fc.fundamental_matrix(f,a,block['fit_end']);M=F[:,7:-1];dup=P[:,[pm['base']['columns'].index(k) for k in DUP]]
   indices={'fit':bp.indices(f,'2012-01-01',block['fit_end']),'stop':bp.indices(f,block['stop_start'],block['stop_end']),'eval':bp.indices(f,block['eval_start'],block['eval_end'])};y=f.y5.to_numpy()
   assert f.index[indices['eval']].max()<=pd.Timestamp('2022-12-31') and (f.end20.iloc[indices['eval']]<=block['eval_end']).all()
   for model in ['xgboost','lightgbm']:
    with np.load(R/f'outputs/e5_20261102/cv/{t}/T/{model}/c0_fold{fold}/raw_predictions.npz') as z:archived=z['eval'].copy()
    assert len(archived)==len(indices['eval'])
    for date,yy,q in zip(f.index[indices['eval']],y[indices['eval']],archived):output.append(dict(ticker=t,date=str(date.date()),fold=fold,model=model,arm='P',y=int(yy),p=float(q)))
    for arm,x in [('PMzero',np.column_stack([P,M,np.zeros((len(f),7),np.float32)])),('PMF',np.column_stack([P,M,F[:,:7]])),('PMduplicate',np.column_stack([P,M,dup]))]:
     assert x.shape[1]==66;folder=O/'models/tree_controls'/t/fold/model/arm;folder.mkdir(parents=True,exist_ok=True);signature={'model':model,'config':bp.CONFIGS[model][0],'arm':arm,'ticker':t,'fold':fold,'seed':42,'addendum_sha256':sha(plan)}
     if (folder/'fit_complete.json').exists():
      meta=json.loads((folder/'fit_complete.json').read_text());assert meta['signature']==signature
      with np.load(folder/'predictions.npz') as z:archived_p=z['eval'].copy()
      info=meta['info'];Xeval=bp.windows(x,indices['eval']).reshape(len(indices['eval']),-1)
      if model=='xgboost':
       import xgboost as xgb
       loaded=xgb.Booster(params={'nthread':2,'device':'cpu'});loaded.load_model(folder/'model.ubj');pred=loaded.predict(xgb.DMatrix(Xeval),iteration_range=(0,info['best_iteration']))
      else:
       import lightgbm as lgb
       loaded=lgb.Booster(model_file=str(folder/'model.txt'));pred=loaded.predict(Xeval,num_iteration=info['best_iteration'],num_threads=2)
      np.testing.assert_allclose(pred,archived_p,rtol=0,atol=1e-12)
     else:
      if os.environ.get('E9B_NO_REFIT')=='1':raise RuntimeError('No-refit replay missing completed tree artifact: '+str(folder))
      X={k:bp.windows(x,v) for k,v in indices.items()};Y={k:y[v] for k,v in indices.items()}
      predictions,info=fit_cpu(model,bp.CONFIGS[model][0],42,X['fit'],Y['fit'],X['stop'],Y['stop'],{'eval':X['eval']},folder);pred=predictions['eval'];np.savez_compressed(folder/'predictions.npz',eval=pred);dump(folder/'fit_complete.json',{'signature':signature,'info':info})
     fits.append(dict(ticker=t,fold=fold,model=model,arm=arm,n_train=len(indices['fit']),n_stop=len(indices['stop']),n_eval=len(indices['eval']),best_iteration=info['best_iteration'],features_per_session=66,configuration=json.dumps(bp.CONFIGS[model][0],sort_keys=True)))
     for date,yy,q in zip(f.index[indices['eval']],y[indices['eval']],pred):output.append(dict(ticker=t,date=str(date.date()),fold=fold,model=model,arm=arm,y=int(yy),p=float(q)))
     print('TREE',t,fold,model,arm,info['best_iteration'],flush=True)
 z=pd.DataFrame(output);save(z,O/'predictions/tree_control_probabilities.csv.gz');save(pd.DataFrame(fits),O/'tables/tree_control_fit_audit.csv')
 rows=[]
 for (t,m,arm),g in z.groupby(['ticker','model','arm']):rows.append(dict(ticker=t,model=m,arm=arm,**metrics(g.y,g.p)))
 save(pd.DataFrame(rows),O/'tables/tree_control_metrics.csv')
 tags=[(m,c,ref) for m in ['xgboost','lightgbm'] for c,ref in [('C1','PMzero'),('C2','PMduplicate'),('C3','P')]];arrays=[];masks=[]
 for t in ['AAPL','TSLA']:
  one=z[z.ticker.eq(t)];wide=one.pivot(index='date',columns=['model','arm'],values='p');yy=one.groupby('date').y.first();d=pd.DataFrame({m+'_'+c:(wide[(m,ref)]-yy)**2-(wide[(m,'PMF')]-yy)**2 for m,c,ref in tags});d.index=pd.to_datetime(d.index);aligned=d.reindex(calendar);arrays.append(aligned.fillna(0).to_numpy());masks.append(aligned.notna().all(axis=1).to_numpy())
 rows=[]
 for block in [60,20,120]:
  result=inference(np.stack(arrays),np.stack(masks),block,20261115+block+400);hp=holm([r['hac_p'] for r in result]);bpv=holm([r['bootstrap_p'] for r in result])
  for i,((model,cid,ref),r) in enumerate(zip(tags,result)):rows.append(dict(model=model,contrast=cid,candidate='PMF',reference=ref,block=block,**r,hac_holm6=hp[i],bootstrap_holm6=bpv[i],exploratory_addendum=True))
 tree=pd.DataFrame(rows);save(tree,O/'tables/tree_control_contrasts.csv');original=pd.read_csv(O/'tables/development_six_contrasts.csv');original['model']='logistic';original['family']='initial_LR6';tree['family']='addendum_tree6';combined=pd.concat([original,tree],ignore_index=True)
 for block,ids in combined.groupby('block').groups.items():
  combined.loc[ids,'hac_holm12_supplementary']=holm(combined.loc[ids,'hac_p']);combined.loc[ids,'bootstrap_holm12_supplementary']=holm(combined.loc[ids,'bootstrap_p'])
 save(combined,O/'tables/development_all12_contrasts.csv');dump(O/'audits/tree_controls_complete.json',dict(new_tree_fits=len(fits),new_GPU_fits=0,original_LR_results_unchanged=True,new_six_tree_family=True,all_twelve_correction_also_reported=True,data_latest='2022-12-31'))
 print('TREE CONTROLS COMPLETE',len(fits),'fits',flush=True)
if __name__=='__main__':main()
