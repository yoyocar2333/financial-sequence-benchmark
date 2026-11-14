"""Build an evidence-linked E9a synthesis from existing aggregate artifacts only.
No network, financial data loading, model fitting, score computation or new inference.
"""
import argparse,io,csv,hashlib,json,re,shutil,sys
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def writecsv(p,rows,fields=None):
 p.parent.mkdir(parents=True,exist_ok=True)
 if fields is None:fields=list(rows[0])
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
def mdtable(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
class Evidence:
 def __init__(self,root):self.root=root;self.records=[]
 def rows(self,path):return list(csv.DictReader(io.StringIO((self.root/path).read_text(encoding='utf-8'))))
 def one(self,path,**sel):
  found=[(i,r) for i,r in enumerate(self.rows(path),1) if all(r.get(k)==str(v) for k,v in sel.items())]
  if len(found)!=1:raise ValueError((path,sel,'nonunique',len(found)))
  i,r=found[0];return r,{'source_file':'research/'+path,'csv_record_1_based':i,'selector':sel,'source_sha256':sha(self.root/path),'source_row':r}
 def claim(self,id,claim,path,sel,fields,limit,scope='Exploratory; source-stage correction only',effect=''):
  row,prov=self.one(path,**sel)
  values={k:row[k] for k in fields}
  self.records.append(dict(claim_id=id,claim=claim,experiment=path.split('/')[0],source_file=prov['source_file'],source_table=Path(path).name,source_record=prov['csv_record_1_based'],selector=json.dumps(sel,sort_keys=True),fields=json.dumps(values,sort_keys=True),effect_definition=effect,effect_size=row.get('difference',row.get('brier_mean',row.get('brier',''))),significance=json.dumps({k:v for k,v in values.items() if 'holm' in k or k in ['hac_p','bootstrap_p','joint_significant','joint_positive_family']},sort_keys=True),sample_limitations=limit,evidence_status=scope,source_sha256=prov['source_sha256']))
  prov['claim_id']=id;self.provenance.append(prov);return row
 provenance=None

def build(repo,out):
 out.mkdir(parents=True,exist_ok=True)
 for f in ['tables','figures','audits','literature','code','checks']:(out/f).mkdir(exist_ok=True)
 src=out/'sources' if (out/'sources').exists() else repo/'research'
 e=Evidence(src);e.provenance=[]
 tables={}
 lim5='AAPL/TSLA; 482 dates per stock in repeatedly inspected 2024–2025; five seeds are not independent markets; 60-row sequences; source family correction does not cover the research history.'
 fields5=['n','difference','bootstrap_ci_low','bootstrap_ci_high','hac_holm_family','bootstrap_holm_family','joint_significant']
 rows=[]
 for stock in ['AAPL','TSLA']:
  for model in ['xgboost','lightgbm','lstm','mamba']:
   c=f'E5_{stock}_{model}'
   stat=e.claim(c,f'Technical-feature incremental Brier difference: {stock} {model}', 'E5/results/feature_gains.csv',dict(ticker=stock,candidate=model+'_T',reference=model+'_B'),fields5,lim5,effect='Brier(B) minus Brier(T), positive favors T; pointwise source bootstrap CI')
   vals=[]
   for arm in ['B','T']:
    r=e.claim(c+'_'+arm,f'{stock} {model} {arm} five-seed mean Brier','E5/results/metrics_comparison.csv',dict(ticker=stock,method=model+'_'+arm,version='calibrated',task='reversal'),['brier_mean','brier_std','log_loss_mean','roc_auc_mean'],lim5)
    vals.append(float(r['brier_mean']))
   rows.append(dict(ticker=stock,model=model,B_Brier=vals[0],T_Brier=vals[1],gain=float(stat['difference']),ci_low=float(stat['bootstrap_ci_low']),ci_high=float(stat['bootstrap_ci_high']),HAC_Holm=float(stat['hac_holm_family']),bootstrap_Holm=float(stat['bootstrap_holm_family']),claim_id=c))
 tables['E5_technical_increments.csv']=rows
 # Retain the strong simple baselines and controls; no post-hoc test.
 for stock in ['AAPL','TSLA']:
  for method in ['logistic_B','logistic_T','cal_prior','Hgate','Hsoft']:
   matches=[r for r in e.rows('E5/results/metrics_comparison.csv') if r['ticker']==stock and r['method']==method and r['version']=='calibrated' and r['task']=='reversal']
   if matches:e.claim('E5_'+stock+'_'+method,'Existing supplementary baseline; no new selection','E5/results/metrics_comparison.csv',dict(ticker=stock,method=method,version='calibrated',task='reversal'),['brier_mean','log_loss_mean','roc_auc_mean'],lim5)
 ctl=e.claim('E5_QQQ_control','TSLA XGBoost T versus QQQ-only augmentation C','E5/results/paired_tests.csv',dict(ticker='TSLA',candidate='xgboost_T',reference='xgboost_C',block_length=20),['difference','bootstrap_p','bootstrap_holm_family','hac_holm_family'],lim5,effect='Brier(C) minus Brier(T); exploratory secondary control, not causal attribution')
 lim6=lim5+' E6 P equals E5 T; F includes past-five-day direction and missingness/age; quarterly inputs repeated daily; lagged retrospective vintages not certified historical source PIT.'
 rows=[]
 for stock in ['AAPL','TSLA']:
  for model in ['logistic','xgboost','lightgbm','lstm','mamba']:
   r=e.claim(f'E6_FUSION_{stock}_{model}',f'{stock} {model}: source-stage reversal fusion comparison','E6/results/fusion_comparison.csv',dict(ticker=stock,model=model),['P','F_logistic','Early_PF','Late','same_weight_prior_blend','F_weight'],lim6,effect='Source reported calibrated Brier values; arithmetic differences are descriptive, not new estimates')
   rows.append(dict(ticker=stock,model=model,P=r['P'],F=r['F_logistic'],Early=r['Early_PF'],Late=r['Late'],constant_blend=r['same_weight_prior_blend'],F_weight=r['F_weight'],claim_id=f'E6_FUSION_{stock}_{model}'))
 tables['E6_fusion_controls.csv']=rows
 for i,r in enumerate(e.rows('E6/results/information_and_fusion_gains.csv')):
  e.claim(f'E6_MAIN_{i+1:02d}',r['ticker']+' '+r['candidate']+' versus '+r['reference'],'E6/results/information_and_fusion_gains.csv',dict(ticker=r['ticker'],target='reversal',lag_block=20,candidate=r['candidate'],reference=r['reference']),['n','difference','bootstrap_ci_low','bootstrap_ci_high','hac_p_holm_family','bootstrap_p_holm_family','hac_p_holm_global_primary','bootstrap_p_holm_global_primary','joint_positive_family'],lim6,effect='Brier(reference) minus Brier(candidate); H1 eight / H3 twenty; global twenty-eight')
 for method in ['logistic_P','logistic_Late','cal_prior']:
  e.claim('E6_UP_'+method,'Secondary AAPL direct-up task is not the primary reversal task','E6/results/metrics_comparison.csv',dict(ticker='AAPL',target='up_direct',method=method,probability='calibrated'),['n','brier_mean','AUC','log_loss'],lim6+' Direct-up secondary task; Late weight one means F alone.')
 e.claim('E6_UP_SIGNIFICANT','AAPL direct-up Late versus weak logistic P is significant within source correction','E6/results/paired_tests.csv',dict(ticker='AAPL',target='up_direct',lag_block=20,candidate='logistic_Late',reference='logistic_P'),['n','difference','bootstrap_ci_low','bootstrap_ci_high','bootstrap_p_holm_family','bootstrap_p_holm_global_primary','hac_p_holm_family'],lim6+' F weight=1; not evidence of complementary fusion.',effect='Brier(P) minus Brier(Late); secondary direct-up family/global twenty')
 lim4='AAPL-only retrospectively reconstructed issuer-selected Apple Newsroom; 2023 fit / 2024 selection+calibration / 2025 exploratory; 230 test dates, 65 overlapping extreme dates, 22 nonoverlapping five-day events; date proxy, not L3/L4.'
 rows=[]
 for method in ['lr_P','lr_D','lr_S','lr_T','hier_P','hier_S','hier_T','global']:
  r=e.claim('E4C_'+method,method+' calibrated event Brier in original cohort','E4c/results/metrics_comparison.csv',dict(timing='next_session',method=method,partition='test',version='calibrated',group='events'),['n','brier','log_loss','roc_auc','probability_sd','within_state_probability_sd'],lim4)
  rows.append(dict(method=method,n=r['n'],Brier=r['brier'],Log_loss=r['log_loss'],AUC=r['roc_auc'],claim_id='E4C_'+method))
 tables['E4c_event_models.csv']=rows
 contrasts=[('S_P','primary_LR_news2','lr_S','lr_P'),('T_S','primary_LR_news2','lr_T','lr_S'),('D_P','secondary_density_sentiment2','lr_D','lr_P'),('S_D','secondary_density_sentiment2','lr_S','lr_D'),('HIER_S_P','secondary_hier_news2','hier_S','hier_P')]
 rows=[]
 for tag,family,cand,ref in contrasts:
  r=e.claim('E4C_DIFF_'+tag,f'{cand} versus {ref}, {family}','E4c/results/paired_tests.csv',dict(timing='next_session',version='calibrated',block_length=20,group='events',metric='Brier',family=family,candidate=cand,reference=ref),['n','difference','hac_holm2','bootstrap_holm2','bootstrap_ci_low','bootstrap_ci_high'],lim4,effect='Brier(reference) minus Brier(candidate); correction within the named two-comparison family only')
  rows.append(dict(contrast=tag,family=family,gain=r['difference'],HAC_Holm=r['hac_holm2'],bootstrap_Holm=r['bootstrap_holm2'],ci_low=r['bootstrap_ci_low'],ci_high=r['bootstrap_ci_high'],claim_id='E4C_DIFF_'+tag))
 tables['E4c_event_contrasts.csv']=rows
 # Timing sensitivities for the significant secondary hierarchy finding.
 for timing in ['delay1','delay2']:
  a=[r['timing'] for r in e.rows('E4c/results/paired_tests.csv')]
  actual=next((x for x in set(a) if timing in x),None)
  if actual:
   e.claim('E4C_HIER_'+timing,'Fixed timing sensitivity, not selection','E4c/results/paired_tests.csv',dict(timing=actual,version='calibrated',block_length=20,group='events',metric='Brier',family='secondary_hier_news2',candidate='hier_S',reference='hier_P'),['n','difference','bootstrap_holm2','hac_holm2'],lim4)
 # Ranking in the originally specified cells; preserve its own multiplicity scope.
 for method in ['hier_S','lr_T','lr_S']:
  a=[r for r in e.rows('E4c/results/within_state_ranking.csv') if r['method']==method and r['timing']=='next_session' and r['version']=='calibrated' and r['block_length']=='20' and r['contrast']=='AUC_vs_half']
  if len(a)==1:
   e.claim('E4C_RANK_'+method,'Within-state event ranking, not marginal AUC','E4c/results/within_state_ranking.csv',dict(timing='next_session',method=method,version='calibrated',block_length=20,contrast='AUC_vs_half'),['estimate','n','same_state_pairs','bootstrap_p','bootstrap_holm5'],lim4)
 # Integrity findings use exact rows where available, document locators otherwise.
 docs=[('E5_METHODS','E5/README.md','Technical inputs, bounded CV, calibration and supplementary controls.','Repeatedly viewed sample; supplementary diagnostics are not causal identification.'),('E6_METHODS','E6/E6_SUMMARY.md','Tables in sections 2–4: 118 vintages, 45 training and 9 test vintages per stock; 8 new updates; frozen configuration and primary families.','Retrospective release-date proxy; repeated accounting values are not independent events.'),('E4C_METHODS','E4c/README.md','Original cohort, feature definitions, sample support and full-file FNSPID coverage audit.','Different cohort from E5/E6; timestamp proxy and rights limitations.'),('AUDIT_E7B','E7b/E7B_SUMMARY.md','Section 1 table: 20 companies / 4 groups; 21 indexes; 17 rendered pages / 10 companies / 90 displayed candidates; original SEC bytes 0, XBRL bytes 0, eligible quarters 0; manual QA 0/200.','Acquisition evidence is not a certified historical panel.'),('AUDIT_E8A','E8a/E8A_SUMMARY.md','Sections 2–5: 2,816 recovered news-stock-version rows; 3,316 feature views; 36 Gemini joins; L3=0,L4=0.','Not unique articles or proof of completeness.'),('AUDIT_E8A1','E8a1/HISTORICAL_PIT_PROVENANCE_AUDIT.md','Actual results: 0 real new raw samples; 0 L3; 0 L4; 0 independently reviewed samples.','No source contract or historical version evidence was created by code tests.'),('AUDIT_E8B','E8a1/E8B_READINESS_DECISION.md','Final decision NOT_READY; eight gates from fixed E8a contract.','Few qualified samples would not qualify the full experiment.'),('BACKGROUND_E1','E1_E2/README.md','Mamba five-seed MAE E1/E2b and 12 corrected comparisons.','Magnitude regression, different complete-case dates; no direct direction interpretation.'),('BACKGROUND_E3','E3c/README.md','Event evaluation and state-conditional ranking; final v1.1 recovery.','Two stocks, inspected 2024–2025; no new evidence generated.'),('POWER_E7A','E7a/STATISTICAL_POWER_ANALYSIS.md','Reference sigma=.0059531805226298; 200 stocks x16 quarters MDE .002184 moderate / .005027 strong; missing matched early-fusion variance.','Planning scenarios, not measured multi-sector dependence or demonstrated test size/power.'),('PROTOCOL_EXPOSURE','E8a/E8A_SUMMARY.md','Section 8: frozen E3c2026 SHA256 and earlier incidental 2026 news summaries/discovery exposure.','No claim of universally untouched 2026; E9a does not execute frozen verification.'),('E4_RECOVERY','E4b/README.md','Retrospective 448 Apple articles, rather than asserted complete recovery of about 450.','No historical first-seen proof or transfer of raw redistribution rights.')]
 for id,path,locator,limit in docs:
  if not (src/path).exists():raise FileNotFoundError(src/path)
  e.records.append(dict(claim_id=id,claim=locator,experiment=path.split('/')[0],source_file='research/'+path,source_table='document sections identified in claim',source_record='',selector='',fields='',effect_definition='',effect_size='',significance='Not a prediction test',sample_limitations=limit,evidence_status='Audit/background; not confirmatory inference',source_sha256=sha(src/path)))
 for name,rows in tables.items():writecsv(out/'tables'/name,rows)
 writecsv(out/'CLAIM_EVIDENCE_MATRIX.csv',e.records)
 dump(out/'audits/cell_provenance.json',e.provenance)
 dump(out/'audits/table_source_hashes.json',{p:sha(src/p) for p in sorted(set(x['source_file'].removeprefix('research/') for x in e.records))})
 dump(out/'audits/extraction_counts.json',{'claims':len(e.records),'exact_csv_rows':len(e.provenance),'new_models':0,'new_financial_metrics':0,'new_pvalues':0,'source_root':'existing frozen public aggregate sources'})
 # Retain all source-specific evidence values. No averaging across stages.
 return tables,e

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();t,e=build(a.repo,a.out);print('Evidence claims',len(e.records),'source rows',len(e.provenance))
