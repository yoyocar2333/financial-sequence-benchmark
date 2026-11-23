"""Diagnostics of frozen E6 forecasts: concentration, grouping-aware Brier and shrinkage."""
import json
import numpy as np,pandas as pd
from e9b_core import R,O,start,save,dump,metrics,decomposition,inference
EXPERTS=['logistic','xgboost','lightgbm','lstm','mamba']
def main():
 inputs=['outputs/e6_20261106/predictions/all_probabilities.csv.gz','outputs/e6_20261106/fusion_weights.json','outputs/e6_20261106/tables/metrics_comparison.csv']
 start('fusion',inputs);z=pd.read_csv(R/inputs[0]);z=z[z.target.eq('reversal')].copy();assert z.date.le('2025-12-31').all() and z.label_date.le('2025-12-31').all()
 methods=['cal_prior','conditioned_prior','logistic_F','logistic_metadata']+[m+'_'+a for m in EXPERTS for a in ['P','Late','PriorBlend']]+[m+'_PF' for m in ['logistic','xgboost','lightgbm']]
 z=z[z.method.isin(methods)];old=pd.read_csv(R/inputs[2]);weights=json.loads((R/inputs[1]).read_text());dist=[];dec=[];bins=[];ens=[];identities=[];contrasts=[];reuse=[];datepred=[]
 for (t,m,s),g in z.groupby(['ticker','method','seed']):
  g=g.sort_values('date');assert len(g)==482
  for version,col in [('raw','p_raw'),('calibrated','p')]:
   stats=metrics(g.y,g[col]);dist.append(dict(ticker=t,method=m,seed=s,version=version,**stats))
   for k in [10,5]:
    d,bs=decomposition(g.y,g[col],k);dec.append(dict(ticker=t,method=m,seed=s,version=version,**d))
    for b in bs:bins.append(dict(ticker=t,method=m,seed=s,version=version,bins=k,estimator='individual_seed',**b))
 for (t,m),g in z.groupby(['ticker','method']):
  y=g.groupby('date').y.first();pivot=g.pivot(index='date',columns='seed',values='p').sort_index();assert pivot.notna().all().all();pp=pivot.mean(axis=1);y=y.reindex(pp.index)
  ens.append(dict(ticker=t,method=m,estimator='mean_probability_ensemble',**metrics(y,pp)))
  d,bs=decomposition(y,pp,10)
  for b in bs:bins.append(dict(ticker=t,method=m,seed=-999,version='calibrated',bins=10,estimator='probability_ensemble',**b))
  for date,yy,q in zip(pp.index,y,pp):datepred.append(dict(ticker=t,date=date,method=m,y=int(yy),p=q,estimator='mean_probability_ensemble'))
 dist=pd.DataFrame(dist);dec=pd.DataFrame(dec)
 agg=dist.groupby(['ticker','method','version'],as_index=False).agg(n_dates=('n','first'),n_seeds=('seed','nunique'),brier_mean=('brier','mean'),brier_seed_SD=('brier','std'),brier_seed_min=('brier','min'),brier_seed_max=('brier','max'),AUC_mean=('AUC','mean'),log_loss_mean=('log_loss','mean'),mean_probability=('mean_probability','mean'),sd_probability_mean=('sd_probability','mean'),extreme_10_90=('extreme_10_90','mean'),extreme_25_75=('extreme_25_75','mean'),calibration_bias=('calibration_bias','mean'),mean_abs_from_half=('mean_abs_from_half','mean'))
 for r in agg.itertuples():
  source=old[old.ticker.eq(r.ticker)&old.target.eq('reversal')&old.method.eq(r.method)&old.probability.eq(r.version)];assert len(source)==1
  error=float(r.brier_mean-source.brier_mean.iloc[0]);assert abs(error)<1e-12
  reuse.append(dict(ticker=r.ticker,method=r.method,version=r.version,original_brier=source.brier_mean.iloc[0],recomputed_brier=r.brier_mean,absolute_difference=abs(error),same_frozen_result=True))
 decagg=dec.groupby(['ticker','method','version','bins'],as_index=False).agg(n_seeds=('seed','nunique'),brier=('brier','mean'),reliability=('reliability','mean'),resolution=('resolution','mean'),uncertainty=('uncertainty','mean'),grouping_remainder=('grouping_remainder','mean'),binned_brier=('binned_brier','mean'),maximum_identity_error=('identity_residual',lambda x:abs(x).max()))
 for t in ['AAPL','TSLA']:
  sub=z[z.ticker.eq(t)];calendar=pd.to_datetime(sub.date.unique()).sort_values();n=len(calendar)
  def array(method,col):
   a=sub[sub.method.eq(method)].pivot(index='date',columns='seed',values=col).sort_index();assert len(a)==n and not a.isna().any().any();return a.to_numpy().T
  y=sub.groupby('date').y.first().sort_index().to_numpy();f=array('logistic_F','p_raw');c=array('cal_prior','p_raw')[0]
  delta=[];tags=[]
  for m in EXPERTS:
   w=weights[t+'_'+m]['F_weight'];p=array(m+'_P','p_raw');q=array(m+'_Late','p_raw');q0=array(m+'_PriorBlend','p_raw')
   qr=(1-w)*p+w*f;q0r=(1-w)*p+w*c
   rounding=max(float(np.max(abs(q-qr))),float(np.max(abs(q0-q0r))))
   np.testing.assert_allclose(q,qr,rtol=0,atol=4*np.finfo(np.float32).eps);np.testing.assert_allclose(q0,q0r,rtol=0,atol=4*np.finfo(np.float32).eps)
   alignment=2*w*(f-c)*(y-q0r);penalty=w*w*(f-c)**2;gain=(q0r-y)**2-(qr-y)**2
   np.testing.assert_allclose(gain,alignment-penalty,atol=1e-12)
   diversity=w*(1-w)*np.mean((p-f)**2);mixed=(1-w)*np.mean((p-y)**2)+w*np.mean((f-y)**2)-diversity
   np.testing.assert_allclose(np.mean((qr-y)**2),mixed,rtol=0,atol=1e-12)
   identities.append(dict(ticker=t,model=m,F_weight=w,raw_P_Brier=np.mean((p-y)**2),raw_F_Brier=np.mean((f-y)**2),raw_Late_Brier=np.mean((q-y)**2),raw_Shrink_Brier=np.mean((q0-y)**2),reconstructed_Late_Brier=np.mean((qr-y)**2),reconstructed_Shrink_Brier=np.mean((q0r-y)**2),archive_rounding_max=rounding,archived_raw_gain=np.mean((q0-y)**2-(q-y)**2),alignment_term=alignment.mean(),deviation_penalty=penalty.mean(),net_raw_F_beyond_constant=gain.mean(),diversity_term=diversity,identity_max_error=np.max(abs(gain-(alignment-penalty))),P_raw_SD=np.mean(np.std(p,axis=1)),F_raw_SD=np.mean(np.std(f,axis=1))))
   for version,col in [('raw','p_raw'),('calibrated','p')]:
    candidate=array(m+'_Late',col)
    for ref in ['P','PriorBlend']:
     d=np.mean((array(m+'_'+ref,col)-y)**2-(candidate-y)**2,axis=0);delta.append(d);tags.append(dict(ticker=t,model=m,version=version,candidate=m+'_Late',reference=m+'_'+ref))
  result=inference(np.stack(delta,axis=1)[None,:,:],np.ones((1,n)),60,20261115+60+200)
  for tag,r in zip(tags,result):contrasts.append({**tag,**{k:v for k,v in r.items() if k not in ['hac_p','bootstrap_p']},'scope':'new exploratory pointwise interval; no new hypothesis p-value'})
 save(dist,O/'tables/fusion_probability_per_seed.csv');save(agg,O/'tables/fusion_probability_summary.csv');save(dec,O/'tables/fusion_decomposition_per_seed.csv');save(decagg,O/'tables/fusion_decomposition.csv');save(pd.DataFrame(bins),O/'tables/fusion_reliability_bins.csv');save(pd.DataFrame(ens),O/'tables/fusion_probability_ensembles.csv');save(pd.DataFrame(identities),O/'tables/fusion_raw_identities.csv');save(pd.DataFrame(contrasts),O/'tables/fusion_pointwise_intervals.csv');save(pd.DataFrame(reuse),O/'tables/fusion_original_metric_reconciliation.csv');save(pd.DataFrame(datepred),O/'predictions/fusion_ensemble_visualization.csv.gz')
 dump(O/'audits/fusion_complete.json',dict(reused_prediction_rows=len(z),new_financial_fits=0,all_original_mean_Briers_reconciled=True,grouping_remainder_explicit=True,per_seed_primary=True,raw_mixture_identities_passed=True,bins=[10,5],future_data_after2025_used=False))
 print('FUSION COMPLETE',len(agg),'metric groups,',len(identities),'raw identities',flush=True)
if __name__=='__main__':main()
