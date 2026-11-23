"""Apply archived calibration coefficients and check frozen metrics; no estimator fitting."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd
from scipy.special import expit
from sklearn.metrics import roc_auc_score

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(root,repo,out):
 out.mkdir(parents=True,exist_ok=True)
 sys.path.insert(0,str(root/'scripts'))
 import e3b_protocol as bp,e5_core as e5
 from e9b_core import decomposition
 e6=root/'outputs/e6_20261106';e9=repo/'research/E9b/tables'
 inputs=[e6/'tables/calibration_parameters.csv',e6/'predictions/all_probabilities.csv.gz',e6/'fusion_weights.json',e6/'inputs/e3a_training_thresholds.json',e6/'audits/calibration_metadata_repair.json']
 meta=pd.read_csv(inputs[0]);z=pd.read_csv(inputs[1]);z=z[z.target.eq('reversal')&z.ticker.eq('AAPL')&z.method.isin([m+'_'+a for m in ['lstm','mamba'] for a in ['P','Late','PriorBlend']])].copy()
 assert z.date.le('2025-12-31').all() and z.label_date.le('2025-12-31').all()
 prior=pd.read_csv(e9/'fusion_probability_per_seed.csv');decold=pd.read_csv(e9/'fusion_decomposition_per_seed.csv');withinold=pd.read_csv(e6/'tables/within_state_ranking.csv')
 rows=[];decs=[];rawrank=[];sources=[];flat=[]
 # Use the same frozen price snapshot and the exact sign/eligibility rules; never parse2026 prices.
 frames={};e5.SOURCE=e6
 for stock in ['AAPL','TSLA']:
  f=e5.load(stock);frames[stock]=f
  needed=bp.BASE+[c for c in bp.EXTRA if c not in ('tail_up','tail_down','ztail_up','ztail_down','VIX_high','VXN_high')]
  finite=np.isfinite(f[needed].to_numpy(float)).all(axis=1);history=pd.Series(finite).rolling(60,min_periods=60).sum().eq(60).to_numpy()
  for label,start,end in [('train','2012-01-01','2022-12-31'),('stop','2023-01-01','2023-06-30'),('cal','2023-07-01','2023-12-31'),('test','2024-01-01','2025-12-31')]:
   calendar=(f.index>=start)&(f.index<=end);eligible=calendar&(f.end20<=end)&history;zero=f.reference_sign.to_numpy()==0
   ids=bp.indices(f,start,end)
   flat.append(dict(ticker=stock,partition=label,calendar_rows=int(calendar.sum()),exact_zero_past5_calendar=int((calendar&zero).sum()),eligible_before_direction=int(eligible.sum()),excluded_exact_zero_after_other_filters=int((eligible&zero).sum()),retained=len(ids),flat_rule='np.sign(100*(log(Close)-log(Close.shift(5)))) == 0; exact floating equality, no epsilon'))
  inputs.append(e6/'inputs'/f'{stock}_adjusted_through2025.csv')
 f=frames['AAPL'];ii=bp.indices(f,'2024-01-01','2025-12-31');ff=f.iloc[ii]
 threshold=json.loads(inputs[3].read_text())['AAPL'];cell=e5.states(ff,threshold)[2]
 for (method,seed),g in z.groupby(['method','seed']):
  g=g.sort_values('date');assert len(g)==482;np.testing.assert_array_equal(g.date,ff.index.strftime('%Y-%m-%d'));np.testing.assert_array_equal(g.y,ff.y5)
  mm=meta[meta.ticker.eq('AAPL')&meta.target.eq('reversal')&meta.method.eq(method)&meta.seed.eq(seed)];assert len(mm)==1;mm=mm.iloc[0]
  a,b=mm.coefficient,mm.intercept;p=g.p_raw.to_numpy();y=g.y.to_numpy();q=g.p.to_numpy();replay=expit(a*bp.logit(p)+b);error=float(np.max(abs(replay-q)));assert error<1e-12
  source_row=meta.index[(meta.ticker=='AAPL')&(meta.target=='reversal')&(meta.method==method)&(meta.seed==seed)][0]+1
  if method.endswith('_P'):
   model=method[:-2];artifact=root/'outputs/e5_20261102/final/AAPL/T'/model/f'seed{seed}/calibration.json';saved=json.loads(artifact.read_text());assert abs(saved['coefficient']-a)<1e-12 and abs(saved['intercept']-b)<1e-12;inputs.append(artifact);source_kind='Contemporaneous E5 calibration.json plus E6 named metadata'
  else:source_kind='E6 named metadata; historical name-collision repair documented; coefficients now applied without refit'
  entry=dict(ticker='AAPL',method=method,seed=int(seed),a=a,b=b,slope_sign='negative' if a<0 else 'positive' if a>0 else 'zero',n_calibration=int(mm.n_calibration),n_eval=len(g),calibrator_source_record=int(source_row),coefficient_status='VERIFIED_AGAINST_ARCHIVED_PROBABILITIES',coefficient_evidence=source_kind,max_probability_replay_error=error)
  for version,pp in [('raw',p),('calibrated',q)]:
   auc=roc_auc_score(y,pp);bs=float(np.mean((pp-y)**2));sd=float(np.std(pp))
   old=prior[prior.ticker.eq('AAPL')&prior.method.eq(method)&prior.seed.eq(seed)&prior.version.eq(version)].iloc[0]
   assert max(abs(bs-old.brier),abs(auc-old.AUC),abs(sd-old.sd_probability))<1e-12
   entry.update({version+'_Brier':bs,version+'_AUC':auc,version+'_SD':sd})
   pos=np.flatnonzero(y==1);neg=np.flatnonzero(y==0);same=cell[pos,None]==cell[None,neg];v=pp[pos,None];w=pp[None,neg];ws=float((((v>w)+.5*(v==w))*same).sum()/same.sum());entry[version+'_within_state_AUC']=ws;entry['within_state_pairs']=int(same.sum())
   for bins in [10,5]:
    result,_=decomposition(y,pp,bins);oldrow=decold[decold.ticker.eq('AAPL')&decold.method.eq(method)&decold.seed.eq(seed)&decold.version.eq(version)&decold.bins.eq(bins)].iloc[0]
    for key in ['brier','reliability','resolution','uncertainty','grouping_remainder']:assert abs(result[key]-oldrow[key])<1e-12
    decs.append(dict(ticker='AAPL',method=method,seed=int(seed),version=version,**result))
  expected=entry['raw_AUC'] if a>0 else 1-entry['raw_AUC'] if a<0 else .5
  entry['monotone_AUC_check_error']=abs(entry['calibrated_AUC']-expected);assert entry['monotone_AUC_check_error']<1e-12
  rows.append(entry)
 result=pd.DataFrame(rows);result.to_csv(out/'CALIBRATION_PER_SEED.csv',index=False,lineterminator='\n');pd.DataFrame(decs).to_csv(out/'CALIBRATION_DECOMPOSITION.csv',index=False,lineterminator='\n');pd.DataFrame(flat).to_csv(out/'FLAT_DIRECTION_COUNTS.csv',index=False,lineterminator='\n')
 summary=[]
 for method,g in result.groupby('method'):
  r=dict(ticker='AAPL',method=method,n_seeds=len(g),slope_min=g.a.min(),slope_max=g.a.max(),negative_slopes=int((g.a<0).sum()),negative_seed_list=','.join(map(str,g.loc[g.a<0,'seed'])),max_probability_replay_error=g.max_probability_replay_error.max())
  for key in ['Brier','AUC','SD','within_state_AUC']:
   for version in ['raw','calibrated']:r[version+'_'+key]=g[version+'_'+key].mean()
  old=withinold[withinold.ticker.eq('AAPL')&withinold.target.eq('reversal')&withinold.method.eq(method)&withinold.group.eq('all')&withinold.block.eq(20)]
  if len(old):assert abs(r['calibrated_within_state_AUC']-old.within_state_auc.iloc[0])<1e-12;r['within_state_reference']='Matches original same-cell seed-mean concordance; no new inference'
  else:r['within_state_reference']='Descriptive same-definition constant-control diagnostic; no preexisting test'
  summary.append(r)
 pd.DataFrame(summary).to_csv(out/'CALIBRATION_SUMMARY.csv',index=False,lineterminator='\n')
 for p in inputs+[e9/'fusion_probability_per_seed.csv',e9/'fusion_decomposition_per_seed.csv',e6/'tables/within_state_ranking.csv',root/'scripts/e3b_protocol.py',root/'scripts/e9b_technical.py',root/'scripts/e9b_core.py',root/'scripts/analyze_e6.py',root/'scripts/analyze_e3c.py']:
  base=root if root in p.resolve().parents else repo
  sources.append(dict(source_file=str(p.resolve().relative_to(base.resolve())),source_root='private_stock_prediction' if base==root else 'public_repository',sha256=sha(p)))
 pd.DataFrame(sources).drop_duplicates().to_csv(out/'CALIBRATION_SOURCE_MANIFEST.csv',index=False,lineterminator='\n')
 report=dict(status='PASSED',pipelines=6,per_seed_rows=len(result),slopes_replayed_without_refit=True,max_probability_error=float(result.max_probability_replay_error.max()),per_seed_Brier_AUC_SD_match_E9b=True,per_seed_decomposition_match_E9b=True,within_state_matches_source_where_available=True,strict_monotonic_auc_verified=True,new_financial_or_calibrator_fits=0,new_pvalues=0,latest_evaluation_label=str(z.label_date.max()))
 (out/'CALIBRATION_VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n');print(pd.DataFrame(summary).to_string(index=False));print(pd.DataFrame(flat).to_string(index=False));print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.root.resolve(),a.repo.resolve(),a.out.resolve())
