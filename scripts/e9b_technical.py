"""Development-only representation reconstruction and rank redundancy."""
import os
import numpy as np,pandas as pd
from scipy.cluster.hierarchy import linkage,leaves_list
from scipy.spatial.distance import squareform
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
import e3b_protocol as bp,e5_core as ec
from e9b_core import R,O,save,dump,start,load_dev

def main():
 files=[f'outputs/e5_20261102/inputs/{t}_adjusted_through2025.csv' for t in ['AAPL','TSLA','QQQ','VIX','VXN']]
 start('technical',files);summary=[];predictrows=[];cv=[];correlations=[];clusters=[];sample=[]
 for ticker in ['AAPL','TSLA']:
  f=load_dev(ticker);B,meta=bp.feature_matrix(f,'B','2022-12-31');cols=meta['columns'];extras=ec.TECH+[ec.RELATIVE]
  allx=np.column_stack([B,f[extras].to_numpy()]);mask=(f.index>='2012-01-01')&np.isfinite(allx).all(axis=1)
  x=pd.DataFrame(allx[mask],columns=cols+extras,index=f.index[mask]);corr=x.corr(method='spearman')
  sample.append(dict(ticker=ticker,n=len(x),first=str(x.index.min().date()),last=str(x.index.max().date()),B_dimensions=38,T_dimensions=51,flattened_B=2280,flattened_T=3060))
  for a in corr:
   for b in corr:correlations.append(dict(ticker=ticker,feature_a=a,feature_b=b,spearman=corr.loc[a,b],sample='2012-2022 training calendar'))
  distance=1-corr.abs().fillna(0).to_numpy();distance=(distance+distance.T)/2;np.fill_diagonal(distance,0)
  tree=linkage(squareform(distance,checks=True),method='average');order=leaves_list(tree)
  for rank,index in enumerate(order):clusters.append(dict(ticker=ticker,rank=rank,feature=x.columns[index]))
  save(pd.DataFrame(tree,columns=['left','right','distance','members']),O/'tables'/f'technical_linkage_{ticker}.csv')
  for a in extras:
   c=corr.loc[a,cols].abs();best=c.idxmax();summary.append(dict(ticker=ticker,technical_feature=a,strongest_B=best,spearman=corr.loc[a,best],absolute_spearman=c.loc[best],n=len(x)))
  for block in bp.FOLDS:
   bx,bm=bp.feature_matrix(f,'B',block['fit_end']);ii=bp.indices(f,'2012-01-01',block['fit_end']);jj=bp.indices(f,block['eval_start'],block['eval_end'])
   ys=f[extras].to_numpy();validfit=np.isfinite(bx[ii]).all(axis=1)&np.isfinite(ys[ii]).all(axis=1);assert validfit.all()
   sx=StandardScaler().fit(bx[ii]);sy=StandardScaler().fit(ys[ii]);artifact=O/'models'/f'{ticker}_feature_ridge_{block["name"]}.npz'
   if os.environ.get('E9B_NO_REFIT')=='1':
    with np.load(artifact) as z:
     np.testing.assert_allclose(sx.mean_,z['x_mean'],rtol=0,atol=1e-12);np.testing.assert_allclose(sy.mean_,z['y_mean'],rtol=0,atol=1e-12)
     model=Ridge(alpha=10);model.coef_=z['coef'].copy();model.intercept_=z['intercept'].copy();model.n_features_in_=bx.shape[1]
   else:model=Ridge(alpha=10).fit(sx.transform(bx[ii]),sy.transform(ys[ii]))
   pred=sy.inverse_transform(model.predict(sx.transform(bx[jj])))
   np.savez_compressed(O/'models'/f'{ticker}_feature_ridge_{block["name"]}.npz',coef=model.coef_,intercept=model.intercept_,x_mean=sx.mean_,x_scale=sx.scale_,y_mean=sy.mean_,y_scale=sy.scale_)
   for k,col in enumerate(extras):
    actual=ys[jj,k];estimate=pred[:,k];rr=r2_score(actual,estimate) if np.var(actual)>0 else np.nan
    cv.append(dict(ticker=ticker,fold=block['name'],feature=col,n_fit=len(ii),n_eval=len(jj),R2=rr,normalized_RMSE=float(np.sqrt(np.mean((actual-estimate)**2))/sy.scale_[k]),target_train_SD=sy.scale_[k],alpha=10))
    for date,act,est in zip(f.index[jj],actual,estimate):predictrows.append(dict(ticker=ticker,fold=block['name'],date=str(date.date()),feature=col,observed_feature=act,predicted_feature=est))
   print('TECH',ticker,block['name'],len(ii),len(jj),flush=True)
 save(pd.DataFrame(correlations),O/'tables/technical_spearman_matrix.csv');save(pd.DataFrame(clusters),O/'tables/technical_cluster_order.csv');save(pd.DataFrame(summary),O/'tables/technical_redundancy.csv');save(pd.DataFrame(cv),O/'tables/technical_forward_reconstruction.csv');save(pd.DataFrame(predictrows),O/'predictions/feature_reconstruction.csv.gz');save(pd.DataFrame(sample),O/'tables/technical_sample.csv')
 agg=pd.DataFrame(cv).groupby(['ticker','feature'],as_index=False).agg(mean_R2=('R2','mean'),min_R2=('R2','min'),max_R2=('R2','max'),mean_normalized_RMSE=('normalized_RMSE','mean'))
 save(agg,O/'tables/technical_reconstruction_summary.csv');dump(O/'audits/technical_complete.json',dict(auxiliary_fits=6,financial_model_fits=0,max_date='2022-12-31',all_features_retained=True))
if __name__=='__main__':main()
