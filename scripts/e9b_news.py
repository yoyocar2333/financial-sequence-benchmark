"""Frozen Apple-corpus density/sentiment diagnostics, with missingness kept distinct."""
import numpy as np,pandas as pd
from e9b_core import R,O,start,save,dump,metrics
METHODS=['lr_P','lr_D','lr_S','lr_T','hier_P','hier_S','hier_T','global']

def stratum(count):return np.select([count.eq(0),count.between(1,2)],['retained_0','retained_1_2'],default='retained_3plus')
def state_auc(y,p,cell):
 y=np.asarray(y,int);p=np.asarray(p,float);cell=np.asarray(cell);pairs=0;concord=0.
 for value in np.unique(cell):
  m=cell==value;a=p[m&(y==1)];b=p[m&(y==0)];pairs+=len(a)*len(b)
  if len(a) and len(b):concord+=np.sum(a[:,None]>b)+.5*np.sum(a[:,None]==b)
 enough=len(y)>=20 and y.sum()>=10 and (1-y).sum()>=10 and pairs>=20
 return dict(within_state_AUC=concord/pairs if enough else np.nan,same_state_pairs=pairs,ranking_status='descriptive_support_passed' if enough else 'suppressed_sparse_class_or_cell_support')

def main():
 inputs=['outputs/e4c_20261026/data/daily_features.csv.gz','outputs/e4c_20261026/predictions/all_probabilities.csv.gz','outputs/e4c_20261026/tables/paired_tests.csv']
 start('news',inputs);d=pd.read_csv(R/inputs[0]);z=pd.read_csv(R/inputs[1]);assert d.date.le('2025-12-31').all() and d.label_end20.le('2025-12-31').all()
 keys=['ticker','date','timing','partition'];assert not d.duplicated(keys).any();z=z[z.method.isin(METHODS)];rows=[];gains=[];corr=[];support=[];nondeterminism=[]
 for name,g in z.groupby(keys+['method']):
  a=g[['p_raw','p_calibrated']].std(ddof=0);nondeterminism.append(float(a.max()))
 assert max(nondeterminism)<1e-12
 p=z.groupby(keys+['method'],as_index=False).agg(p_raw=('p_raw','mean'),p_calibrated=('p_calibrated','mean'),target=('target','first'),source_seeds=('seed','nunique'))
 merged=p.merge(d,on=keys,validate='many_to_one',suffixes=('','_features'));np.testing.assert_array_equal(merged.target,merged.target_features);merged=merged.drop(columns=['target_features']);merged['stratum']=stratum(merged.news_count);d['stratum']=stratum(d.news_count)
 for (timing,part),g in d.groupby(['timing','partition']):
  positive=g[g.news_count.gt(0)]
  for what,v in [('signed_mean',positive.news_signed_mean),('absolute_mean',positive.news_signed_mean.abs())]:
   corr.append(dict(timing=timing,partition=part,n_with_retained_news=len(positive),feature_y=what,spearman=positive.news_log_count.corr(v,method='spearman'),n_dates=len(g),retained_coverage=float(g.news_present.mean()),historical_source_completeness_verified=bool(g.historical_source_completeness_verified.all()),strict_PIT_verified=bool(g.strict_PIT_verified.all()),sample='retained-news days only; representation diagnostic'))
  for group,mask in [('all',np.ones(len(g),bool)),('events',g.event.eq(1).to_numpy())]:
   gg=g[mask]
   for name in ['all','retained_0','retained_1_2','retained_3plus']:
    h=gg if name=='all' else gg[gg.stratum.eq(name)]
    support.append(dict(timing=timing,partition=part,group=group,stratum=name,n=len(h),positive=int(h.target.sum()),negative=int((1-h.target).sum()),retained_articles_mean=h.news_count.mean(),mean_signed_sentiment=h.loc[h.news_count.gt(0),'news_signed_mean'].mean(),mean_absolute_mean_sentiment=h.loc[h.news_count.gt(0),'news_signed_mean'].abs().mean(),source_window_observed=int(h.reconstructed_source_window_observed.sum()),historical_completeness_verified=int(h.historical_source_completeness_verified.sum()),strict_PIT_verified=int(h.strict_PIT_verified.sum())))
 for (timing,part,method),g in merged.groupby(['timing','partition','method']):
  for group,mask in [('all',np.ones(len(g),bool)),('events',g.event.eq(1).to_numpy())]:
   gg=g[mask]
   for name in ['all','retained_0','retained_1_2','retained_3plus']:
    h=gg if name=='all' else gg[gg.stratum.eq(name)]
    for version,col in [('raw','p_raw'),('calibrated','p_calibrated')]:
     row=dict(timing=timing,partition=part,method=method,group=group,stratum=name,version=version,n=len(h))
     if len(h):
      stat=metrics(h.target,h[col]);stat['AUC']=stat['AUC'] if stat['positive']>=10 and stat['negative']>=10 else np.nan
      row.update(stat);row.update(state_auc(h.target,h[col],h.cell));row.update(mean_signed_reversal_amplitude=h.signed_reversal_amplitude_pp.mean(),mean_abs_executable_return=h.executable_return5_log_pp.abs().mean())
     else:row.update(ranking_status='empty_fixed_stratum')
     rows.append(row)
 for (timing,part),g in merged.groupby(['timing','partition']):
  for version,col in [('raw','p_raw'),('calibrated','p_calibrated')]:
   wide=g.pivot(index='date',columns='method',values=col);meta=d[d.timing.eq(timing)&d.partition.eq(part)].set_index('date').reindex(wide.index);assert not wide.isna().any().any()
   for group,mask in [('all',np.ones(len(meta),bool)),('events',meta.event.eq(1).to_numpy())]:
    for name in ['all','retained_0','retained_1_2','retained_3plus']:
     m=mask if name=='all' else mask&meta.stratum.eq(name).to_numpy()
     for candidate,reference in [('lr_D','lr_P'),('lr_S','lr_D'),('lr_T','lr_S'),('lr_S','lr_P'),('hier_S','hier_P')]:
      q=wide[candidate].to_numpy()[m];p0=wide[reference].to_numpy()[m];yy=meta.target.to_numpy()[m]
      gains.append(dict(timing=timing,partition=part,version=version,group=group,stratum=name,candidate=candidate,reference=reference,n=int(m.sum()),Brier_gain=np.mean((p0-yy)**2-(q-yy)**2) if len(q) else np.nan,mean_absolute_probability_change=np.mean(abs(q-p0)) if len(q) else np.nan,mean_probability_change=np.mean(q-p0) if len(q) else np.nan,exploratory_descriptive=True))
 save(pd.DataFrame(rows),O/'tables/news_density_conditioned_metrics.csv');save(pd.DataFrame(gains),O/'tables/news_attention_sentiment_contrasts.csv');save(pd.DataFrame(corr),O/'tables/news_density_sentiment_correlations.csv');save(pd.DataFrame(support),O/'tables/news_density_support.csv')
 old=pd.read_csv(R/inputs[2]);old=old[old.version.eq('calibrated')&old.block_length.eq(20)&old.group.eq('events')&old.metric.eq('Brier')&old.family.isin(['primary_LR_news2','secondary_hier_news2','secondary_density_sentiment2'])]
 save(old,O/'tables/news_original_timing_tests.csv')
 # Original primary and locally significant secondary results must remain numerically identical.
 assert float(old[old.timing.eq('next_session')&old.candidate.eq('lr_S')&old.reference.eq('lr_P')].bootstrap_holm2.iloc[0])==.1512
 assert float(old[old.timing.eq('next_session')&old.candidate.eq('hier_S')&old.reference.eq('hier_P')].bootstrap_holm2.iloc[0])==.028
 dump(O/'audits/news_complete.json',dict(new_models=0,maximum_LR_seed_probability_SD=max(nondeterminism),strata_fixed=['0','1-2','3+'],no_recollection=True,source_absence_not_verified_market_absence=True,new_pvalues=0,original_families_preserved=True))
 print('NEWS COMPLETE',len(rows),'conditional rows',len(gains),'paired descriptive contrasts',flush=True)
if __name__=='__main__':main()
