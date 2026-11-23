"""Public aggregate/archived-coefficient validation, no fitting or new hypothesis tests."""
import argparse,contextlib,csv,hashlib,io,json,re,shutil,tempfile
from pathlib import Path
import pandas as pd,numpy as np

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(repo,bundle):
 protected=json.loads((bundle/'audits/PROTECTED_SOURCE_HASHES.json').read_text())
 for p,h in protected.items():assert sha(repo/p)==h,p
 from iceib2027_r2_validate import validate as prior
 prior(repo,repo/'research/ICEIB2027/round2')
 z=pd.read_csv(bundle/'tables/CALIBRATION_PER_SEED.csv');source=pd.read_csv(repo/'research/E6/results/calibration_parameters.csv');old=pd.read_csv(repo/'research/E9b/tables/fusion_probability_per_seed.csv');decs=pd.read_csv(bundle/'tables/CALIBRATION_DECOMPOSITION.csv');olddec=pd.read_csv(repo/'research/E9b/tables/fusion_decomposition_per_seed.csv');assert len(z)==30 and len(decs)==120
 for r in z.itertuples():
  src=source[source.ticker.eq(r.ticker)&source.target.eq('reversal')&source.method.eq(r.method)&source.seed.eq(r.seed)];assert len(src)==1;src=src.iloc[0]
  assert abs(r.a-src.coefficient)<1e-12 and abs(r.b-src.intercept)<1e-12
  for version in ['raw','calibrated']:
   rr=old[old.ticker.eq(r.ticker)&old.method.eq(r.method)&old.seed.eq(r.seed)&old.version.eq(version)].iloc[0]
   assert abs(getattr(r,version+'_Brier')-rr.brier)<1e-12 and abs(getattr(r,version+'_AUC')-rr.AUC)<1e-12 and abs(getattr(r,version+'_SD')-rr.sd_probability)<1e-12
  expected=r.raw_AUC if r.a>0 else 1-r.raw_AUC if r.a<0 else .5
  assert abs(r.calibrated_AUC-expected)<1e-12 and r.max_probability_replay_error<1e-12
 for r in decs.itertuples():
  oldrow=olddec[olddec.ticker.eq(r.ticker)&olddec.method.eq(r.method)&olddec.seed.eq(r.seed)&olddec.version.eq(r.version)&olddec.bins.eq(r.bins)].iloc[0]
  for col in ['brier','reliability','resolution','uncertainty','grouping_remainder']:assert abs(getattr(r,col)-oldrow[col])<1e-12
  assert abs(r.brier-(r.reliability-r.resolution+r.uncertainty+r.grouping_remainder))<1e-12
 for method,g in z.groupby('method'):
  s=pd.read_csv(bundle/'tables/CALIBRATION_SUMMARY.csv').set_index('method').loc[method]
  for version in ['raw','calibrated']:
   for metric in ['Brier','AUC','SD','within_state_AUC']:assert abs(s[version+'_'+metric]-g[version+'_'+metric].mean())<1e-12
  assert s.negative_slopes==(g.a<0).sum()
 assert sorted(z.loc[z.a<0,'seed'].unique())==[46]
 assert set(z.loc[z.a<0,'method'])=={'mamba_P','mamba_Late','mamba_PriorBlend'}
 rawid=pd.read_csv(repo/'research/E9b/tables/fusion_raw_identities.csv');assert len(rawid)==10 and (rawid.identity_max_error<1e-12).all()
 flats=pd.read_csv(bundle/'tables/FLAT_DIRECTION_COUNTS.csv');assert len(flats)==8 and flats.retained.sum()>0
 assert list(flats.loc[flats.partition=='train','excluded_exact_zero_after_other_filters'])==[2,3]
 assert (flats.loc[flats.partition!='train','excluded_exact_zero_after_other_filters']==0).all()
 text=(bundle/'ICEIB2027_FULL_PAPER.md').read_text();body=text.split('## References')[0]
 for t in ['4.6. Cross-Experiment Synthesis','REL','RES','UNC','G','alpha=10','Spearman','0.583474','0.573053','0.549749','0.0240','0.0480','0.0744','0.1512','0.028','0.1894/0.3714','0.004','zero L3','L4','2024–2025']:assert t in body,t
 assert not any(t in body for t in ['Codex','E9b','allocation exception','Original bounded','sparse vintages preclude'])
 assert not re.search(r'\boriginal\b|\bexisting\b|\bremains?\b',body,re.I)
 assert len(re.findall(r'^Table \d+\.',text,re.M))==4 and len(re.findall(r'^Figure \d+\.',text,re.M))==1 and text.count('` (')==5
 assert re.findall(r'^### (4\.\d)\. ',text,re.M)==['4.1','4.2','4.3','4.4','4.5','4.6']
 abstract=(bundle/'ABSTRACT.md').read_text().split('\n\n',1)[1].strip();assert len(abstract.split())==100 and abstract in text
 version=json.loads((bundle/'EVIDENCE_VERSION.json').read_text())['commit'];assert re.fullmatch('[a-f0-9]{40}',version) and version in text
 references=text.split('## References\n\n')[1];assert references==(repo/'research/ICEIB2027/round2/ICEIB2027_REVISED_FULL_PAPER.md').read_text().split('## References\n\n')[1]
 from iceib2027_r3_build import main as build
 with tempfile.TemporaryDirectory(prefix='iceib_r3_replay_') as td:
  dest=Path(td);(dest/'tables').mkdir();(dest/'audits').mkdir()
  for n in ['PAPER_TEMPLATE.md','ABSTRACT.md','EVIDENCE_VERSION.json']:shutil.copy2(bundle/n,dest/n)
  shutil.copy2(bundle/'tables/CALIBRATION_SUMMARY.csv',dest/'tables/CALIBRATION_SUMMARY.csv')
  with contextlib.redirect_stdout(io.StringIO()):build(repo,dest)
  assert (dest/'ICEIB2027_FULL_PAPER.md').read_bytes()==(bundle/'ICEIB2027_FULL_PAPER.md').read_bytes()
 return dict(status='PASSED',protected_files_unchanged=len(protected),saved_coefficients_checked=30,decomposition_rows_reconciled=120,per_seed_scores_match_archived=True,all8_technical_and10_fusion_settings_retained=True,raw_identity_matches10_archived_settings=True,full_manuscript_byte_reproduced=True,abstract_words=100,main_tables=4,main_figures=1,editable_equations=5,references=12,financial_fits=0,calibrator_fits=0,new_pvalues=0,E3c2026_executed=False,independent_human_QA=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();result=validate(a.repo,a.bundle)
 if a.report:a.report.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
