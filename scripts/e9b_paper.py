"""Single current manuscript + evidence matrix from immutable original and new tables."""
import argparse,csv,io,json,hashlib,re
from pathlib import Path
import pandas as pd
from e9a_build import mdtable

def main(out,repo):
 def read(name):return pd.read_csv(out/'tables'/name)
 def fmt(x,n=6):return f'{float(x):.{n}f}' if pd.notna(x) else '—'
 oldroot=repo/'research'
 e5=pd.read_csv(oldroot/'E5/results/feature_gains.csv');e5m=pd.read_csv(oldroot/'E5/results/metrics_comparison.csv');e6=pd.read_csv(oldroot/'E6/results/fusion_comparison.csv');e4=pd.read_csv(oldroot/'E4c/results/metrics_comparison.csv');dev=read('development_six_contrasts.csv');dev=dev[dev.primary_block.eq(True)]
 cohort=mdtable(['Study','Fit / validation / evaluation','Sample and input','Task'],[
  ['Technical','2012–22 / 2023 / 2024–25','AAPL, TSLA; 482 dates each; B38→T51','5-session reversal'],
  ['Fundamentals','Same split','Same dates; P=T51, F16, Early66','Reversal; direct-up secondary'],
  ['Issuer news','2023 / 2024 / 2025','AAPL; 230 dates, 65 extreme dates; P8/D10/S12/T16','Event-conditioned reversal'],
  ['New development controls','Expanding fit; evaluate 2017–22','Two stocks; 1,450 dates each; fixed Logistic / XGB / LGBM','Raw-probability diagnostics']])
 rows=[]
 for row in e5.itertuples():
  def score(method):return e5m[e5m.ticker.eq(row.ticker)&e5m.method.eq(method)&e5m.version.eq('calibrated')&e5m.task.eq('reversal')].brier_mean.iloc[0]
  rows.append([row.ticker+' '+row.candidate.removesuffix('_T'),fmt(score(row.reference)),fmt(score(row.candidate)),fmt(row.difference),'['+fmt(row.bootstrap_ci_low)+', '+fmt(row.bootstrap_ci_high)+']',fmt(row.bootstrap_holm_family,4)])
 tech=mdtable(['Stock / model','B','T','Benefit','95% interval','Holm8 p'],rows)
 rows=[]
 for row in e6[e6.model.isin(['lstm','mamba'])].itertuples():rows.append([row.ticker+' '+row.model,fmt(row.P),fmt(row.same_weight_prior_blend),fmt(row.Late),fmt(row.F_weight,2)])
 fusion=mdtable(['Stock / price expert','P','Constant mixture','Late fusion','F weight'],rows)
 labels={'C1':('P+M+F','P+M+zero'),'C2':('P+M+F','P+M+duplicate'),'C3':('P+M+F','P'),'C4':('Sequential fusion','Same-weight constant'),'C5':('Sequential fusion','Prior-tuned constant'),'C6':('Sequential fusion','Prior-selected component')}
 rows=[]
 for row in dev.itertuples():
  can,ref=labels[row.contrast];rows.append([row.contrast+' '+can,ref,fmt(row.difference),'['+fmt(row.bootstrap_ci_low)+', '+fmt(row.bootstrap_ci_high)+']',fmt(row.bootstrap_holm6,4)])
 devtable=mdtable(['Contrast / candidate','Reference','Benefit','95% interval','Holm6 p'],rows)
 e4=e4[e4.timing.eq('next_session')&e4.partition.eq('test')&e4.version.eq('calibrated')&e4.group.eq('events')]
 methods=['lr_P','lr_D','lr_S','lr_T','hier_P','hier_S','hier_T','global'];nrows=[]
 for m in methods:
  row=e4[e4.method.eq(m)].iloc[0];nrows.append([m,fmt(row.brier),fmt(row.log_loss),fmt(row.roc_auc)])
 news=mdtable(['Model','Brier','Log loss','AUC'],nrows)
 replacements={'COHORT_TABLE':cohort,'TECHNICAL_TABLE':tech,'FUSION_TABLE':fusion,'DEVELOPMENT_TABLE':devtable,'NEWS_TABLE':news,'REFERENCES':(out/'literature/REFERENCES.md').read_text().strip()}
 text=(out/'PAPER_TEMPLATE.md').read_text()
 for key,value in replacements.items():text=text.replace('{{'+key+'}}',value)
 assert '{{' not in text;text=text.rstrip()+'\n';(out/'PAPER_DRAFT.md').write_text(text)
 # Preserve all103 original claim fields; append explicitly scoped new evidence.
 baseline=out/'baseline/CLAIM_EVIDENCE_MATRIX.csv'
 records=list(csv.DictReader(io.StringIO(baseline.read_text())));assert len(records)==103
 for row in records:row.update(origin='E9a_original',analysis_plan='original source-stage plan; supplementary plan does not replace it')
 def add(id,name,selection,fields,description,scope='E9b exploratory descriptive'):
  path=out/'tables'/name;rows=list(csv.DictReader(io.StringIO(path.read_text())));found=[(i+1,r) for i,r in enumerate(rows) if all(r.get(k)==str(v) for k,v in selection.items())];assert len(found)==1,(id,name,selection,len(found));i,row=found[0]
  values={k:row[k] for k in fields};effect=row.get('difference',row.get('Brier_gain',row.get('brier_mean','')))
  records.append(dict(claim_id=id,claim=description,experiment='E9b',source_file='research/E9b/tables/'+name,source_table=name,source_record=str(i),selector=json.dumps(selection,sort_keys=True),fields=json.dumps(values,sort_keys=True),effect_definition='Reference minus candidate where gain/difference is used; otherwise original table field',effect_size=effect,significance=json.dumps({k:v for k,v in values.items() if 'holm' in k or k in ['hac_p','bootstrap_p']},sort_keys=True),sample_limitations='Two observed stocks or one issuer corpus; original version/PIT limits remain. Development new fits use <=2022; 2024-2025 diagnostics are already-viewed exploratory data. Seeds are not independent market samples.',evidence_status=scope,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),origin='E9b_new',analysis_plan=('research/E9b/ANALYSIS_PLAN_ADDENDUM_01.json' if name.startswith(('tree_control','development_all12')) else 'research/E9b/ANALYSIS_PLAN_LOCKED.json')))
 a=read('technical_representation_joint.csv')
 for r in a.itertuples():add('E9B_REP_'+r.ticker+'_'+r.feature,'technical_representation_joint.csv',dict(ticker=r.ticker,feature=r.feature),['strongest_B','spearman','mean_R2','min_R2','max_R2','n'],'Training overlap and forward reconstruction; all thirteen targets retained')
 a=read('complexity_and_seed_stability.csv')
 for r in a.itertuples():add('E9B_COMPLEX_'+r.ticker+'_'+r.model+'_'+r.arm,'complexity_and_seed_stability.csv',dict(ticker=r.ticker,model=r.model,arm=r.arm),['flattened_columns','selected_config_index','configuration','parameter_count','Brier_seed_mean','Brier_seed_SD'],'Archived complexity/configuration and seed-stability metadata')
 a=read('fusion_raw_identities.csv')
 for r in a.itertuples():add('E9B_RAW_'+r.ticker+'_'+r.model,'fusion_raw_identities.csv',dict(ticker=r.ticker,model=r.model),['F_weight','alignment_term','deviation_penalty','net_raw_F_beyond_constant','archived_raw_gain','archive_rounding_max'],'Raw F deviation against matched constant; exact reconstructed algebra and archived rounding separated')
 for t in ['AAPL','TSLA']:
  for model in ['lstm','mamba']:
   for arm in ['P','Late','PriorBlend']:
    add('E9B_PROB_'+t+'_'+model+'_'+arm,'fusion_probability_summary.csv',dict(ticker=t,method=model+'_'+arm,version='calibrated'),['n_dates','n_seeds','brier_mean','brier_seed_SD','sd_probability_mean','calibration_bias','extreme_10_90','AUC_mean'],'Calibrated forecast concentration and seed stability')
    add('E9B_DECOMP_'+t+'_'+model+'_'+arm,'fusion_decomposition.csv',dict(ticker=t,method=model+'_'+arm,version='calibrated',bins=10),['brier','reliability','resolution','uncertainty','grouping_remainder','maximum_identity_error'],'Fixed-bin empirical decomposition with explicit grouping remainder')
 for cid in ['C1','C2','C3','C4','C5','C6']:
  for block in [60,20,120]:add(f'E9B_DEV_{cid}_{block}','development_six_contrasts.csv',dict(contrast=cid,block=block),['difference','bootstrap_ci_low','bootstrap_ci_high','hac_holm6','bootstrap_holm6','n_observed','calendar_sessions','stocks'],'Fixed-development contrast; principal block60, other blocks sensitivity','New exploratory six-comparison family; not original E6 tests')
 for t in ['AAPL','TSLA']:
  for method in ['logistic_P','PMzero','PMF','PMduplicate','metadata','F','logistic_Late','logistic_SameShrink','logistic_TunedShrink','logistic_BestSingle']:
   add('E9B_DEVMET_'+t+'_'+method,'development_metrics.csv',dict(ticker=t,method=method),['n','brier','AUC','mean_probability','sd_probability'],'New development-only raw-probability model diagnostic')
  for fold in [2016,2018,2020]:add(f'E9B_DEVWEIGHT_{t}_{fold}','development_prequential_weights.csv',dict(ticker=t,model='logistic',fold=fold),['F_weight','shrink_weight','best_single','n_previous_folds','selection_uses_current_outer_labels'],'Sequential allocation from previous folds only; fixed initial component')
 for part in ['train','validation','test']:
  for feature in ['signed_mean','absolute_mean']:
   add('E9B_NEWSCORR_'+part+'_'+feature,'news_density_sentiment_correlations.csv',dict(timing='next_session',partition=part,feature_y=feature),['n_with_retained_news','spearman','n_dates','historical_source_completeness_verified','strict_PIT_verified'],'Retained-source density and mean tone; full original split kept')
 for stratum in ['all','retained_0','retained_1_2','retained_3plus']:
  add('E9B_NEWSN_'+stratum,'news_density_support.csv',dict(timing='next_session',partition='test',group='events',stratum=stratum),['n','positive','negative','mean_signed_sentiment','historical_completeness_verified','strict_PIT_verified'],'Fixed2025 event-density stratum; zero retained articles is not verified no-news')
  for can,ref in [('lr_D','lr_P'),('lr_S','lr_D'),('lr_T','lr_S')]:add('E9B_NEWSGAIN_'+stratum+'_'+can,'news_attention_sentiment_contrasts.csv',dict(timing='next_session',partition='test',version='calibrated',group='events',stratum=stratum,candidate=can,reference=ref),['n','Brier_gain','mean_absolute_probability_change'],'Fixed density-conditioned descriptive contrast; no new hypothesis p-value')
 if (out/'tables/tree_control_contrasts.csv').exists():
  for model in ['xgboost','lightgbm']:
   for cid in ['C1','C2','C3']:
    for block in [60,20,120]:add(f'E9B_TREE_{model}_{cid}_{block}','tree_control_contrasts.csv',dict(model=model,contrast=cid,block=block),['difference','bootstrap_ci_low','bootstrap_ci_high','hac_holm6','bootstrap_holm6'],'Locked tree addendum; original config0, development-only, all controls retained','New exploratory tree6 family; original LR/E6 results unchanged')
   for ticker in ['AAPL','TSLA']:
    for arm in ['P','PMzero','PMF','PMduplicate']:add(f'E9B_TREEMET_{ticker}_{model}_{arm}','tree_control_metrics.csv',dict(ticker=ticker,model=model,arm=arm),['n','brier','AUC','sd_probability'],'Development-only stronger price/input control diagnostic')
  for row in read('development_all12_contrasts.csv').itertuples():
   add(f'E9B_ALL12_{row.model}_{row.contrast}_{row.block}','development_all12_contrasts.csv',dict(model=row.model,contrast=row.contrast,block=row.block),['difference','hac_holm12_supplementary','bootstrap_holm12_supplementary'],'Combined multiplicity sensitivity across original LR6 and addendum tree6; local p-values kept')
 fields=list(records[0]);
 with (out/'CLAIM_EVIDENCE_MATRIX.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(records)
 meta=dict(stage='E9b',manuscript_title='Understanding the Sources of Apparent Predictive Gains in Financial Machine Learning',subtitle='Representation, Probability Shrinkage, News Density, and Temporal Data Integrity',date='15 November 2026',version='2.0',figures=['F1_representation.png','F2_fusion_calibration.png','F3_attention_sentiment.png'],old_claims=103,new_claims=len(records)-103,total_claims=len(records),references=40,new_classification_fits=60,new_LR_fits=24,new_tree_fits=36,new_auxiliary_fits=6,financial_fit_latest='2020-06-30',development_eval_latest='2022-12-31',GPU=False)
 (out/'MANUSCRIPT_VERSION.json').write_text(json.dumps(meta,indent=2)+'\n')
 print('Paper words',len(text.split()),'claims',len(records),'new',len(records)-103)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);a=p.parse_args();main(a.out,a.repo)
