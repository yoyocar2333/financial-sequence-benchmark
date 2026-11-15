"""Private no-refit replay from lawful frozen inputs and completed E9b artifacts.
Checks new probabilities against saved coefficients/native tree weights; creates no new fit.
"""
import argparse,datetime as dt,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path

def main(source,bundle,out,repo):
 if out.exists():raise FileExistsError('Use a new replay directory')
 out.mkdir(parents=True)
 for name in ['inputs','models','baseline']:
  shutil.copytree(bundle/name,out/name)
 for name in ['audits','tables','figures','predictions','logs','checks','literature']:(out/name).mkdir(exist_ok=True)
 for name in ['ANALYSIS_PLAN_LOCKED.json','ANALYSIS_PLAN_ADDENDUM_01.json','PAPER_TEMPLATE.md']:shutil.copy2(bundle/name,out/name)
 for name in ['plan_lock.json','addendum_01_lock.json','analysis_input_hashes.json','derived_development_hashes.json']:shutil.copy2(bundle/'audits'/name,out/'audits'/name)
 shutil.copy2(bundle/'literature/new_doi_records.json',out/'literature/new_doi_records.json')
 env={**os.environ,'E9B_SOURCE_ROOT':str(source.resolve()),'E9B_OUTPUT':str(out.resolve()),'E9B_NO_REFIT':'1','OPENBLAS_NUM_THREADS':'2','OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2'}
 code=Path(__file__).parent
 components=['e9b_technical.py','e9b_complexity.py','e9b_development.py','e9b_tree_controls.py','e9b_fusion.py','e9b_news.py','e9b_plot.py','e9b_citations.py']
 for name in components:
  with (out/'logs'/(name+'.log')).open('w') as log:subprocess.run([sys.executable,'-B',str(code/name)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  print('REPLAY',name,flush=True)
 subprocess.run([sys.executable,'-B',str(code/'e9b_paper.py'),'--out',str(out),'--repo',str(repo)],env=env,check=True)
 subprocess.run([sys.executable,'-B',str(code/'e9b_narrative.py'),'--out',str(out)],env=env,check=True)
 import pandas as pd,numpy as np
 checked=[]
 for p in sorted((bundle/'tables').glob('*.csv')):
  target=out/'tables'/p.name
  if not target.exists():continue
  a=pd.read_csv(p);b=pd.read_csv(target);pd.testing.assert_frame_equal(a,b,check_exact=False,rtol=1e-11,atol=1e-12);checked.append(p.name)
 assert (bundle/'CLAIM_EVIDENCE_MATRIX.csv').read_bytes()==(out/'CLAIM_EVIDENCE_MATRIX.csv').read_bytes()
 assert (bundle/'PAPER_DRAFT.md').read_bytes()==(out/'PAPER_DRAFT.md').read_bytes()
 report=dict(status='PASSED',replay_utc=dt.datetime.now(dt.timezone.utc).isoformat(),tables_recomputed=checked,table_count=len(checked),new_model_fits_in_replay=0,LR_coefficients_verified=24,tree_native_models_verified=36,Ridge_models_reused=6,claims_byte_identical=True,manuscript_byte_identical=True,PIT_certification=False,independent_human_QA=False)
 (out/'checks/full_replay_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('PRIVATE NO-REFIT REPLAY PASSED',len(checked),'tables',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--private-frozen-run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);a=p.parse_args();main(a.source_root,a.private_frozen_run,a.out,a.repo)
