"""Offline source-cell, plan, cohort and probability-accounting checks; no fitting."""
import csv,hashlib,io,json,re
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return list(csv.DictReader(io.StringIO(p.read_text())))
def validate(bundle,repo):
 supplemental=repo/'research/E9b'
 for name,lock in [('ANALYSIS_PLAN_LOCKED.json','plan_lock.json'),('ANALYSIS_PLAN_ADDENDUM_01.json','addendum_01_lock.json')]:
  assert sha(supplemental/name)==json.loads((supplemental/'audits'/lock).read_text())['sha256']
 for rel,h in json.loads((bundle/'audits/table_source_hashes.json').read_text()).items():assert sha(repo/'research'/rel)==h,rel
 claims=rows(bundle/'CLAIM_EVIDENCE_MATRIX.csv');baseline=rows(supplemental/'baseline/CLAIM_EVIDENCE_MATRIX.csv')
 assert len(claims)==319 and len({r['claim_id'] for r in claims})==319
 byid={r['claim_id']:r for r in claims}
 for old in baseline:assert all(byid[old['claim_id']][k]==v for k,v in old.items()),old['claim_id']
 for c in claims:
  if not c['selector']:continue
  source=repo/c['source_file'];data=rows(source);sel=json.loads(c['selector']);found=[(i+1,r) for i,r in enumerate(data) if all(r.get(k)==str(v) for k,v in sel.items())]
  assert len(found)==1,c['claim_id'];i,r=found[0];assert i==int(c['source_record'])
  assert all(r[k]==v for k,v in json.loads(c['fields']).items()),c['claim_id']
  assert sha(source)==c['source_sha256'],c['source_file']
 refs=json.loads((bundle/'literature/citation_catalog.json').read_text());paper=(bundle/'PAPER_DRAFT.md').read_text()
 assert len(refs)==40 and {r['id'] for r in refs}==set(re.findall(r'\[(R\d+)\]',paper))
 assert next(r for r in refs if r['id']=='R18')['doi']==''
 assert next(r for r in refs if r['id']=='R40')['doi']==''
 assert '{{' not in paper and '2023 / 2024 / 2025' in paper and 'P=T51' in paper
 for token in ['.1512','.028','.004','0.0240','.0744','.0480','grouping remainder','2024–2025','2026']:assert token in paper,token
 table=supplemental/'tables'
 for r in rows(table/'fusion_decomposition.csv'):
  residual=float(r['brier'])-(float(r['reliability'])-float(r['resolution'])+float(r['uncertainty'])+float(r['grouping_remainder']))
  assert abs(residual)<1e-12
 reconciliation=rows(table/'fusion_original_metric_reconciliation.csv');assert len(reconciliation)==88
 assert max(float(r['absolute_difference']) for r in reconciliation)<1e-12
 assert all(r['selection_uses_current_outer_labels']=='False' for r in rows(table/'development_prequential_weights.csv'))
 assert len(rows(table/'development_fit_audit.csv'))==24 and len(rows(table/'tree_control_fit_audit.csv'))==36
 assert all(r['last']<'2023-01-01' for r in rows(table/'technical_sample.csv'))
 assert len(rows(table/'development_all12_contrasts.csv'))==36
 # Public aggregates cannot certify raw-data PIT or replace the private no-refit replay.
 return dict(status='PASSED',claims=319,original_claim_fields_preserved=103,new_claims=216,references_checked=40,archived_Brier_reconciled=88,new_development_classification_fits=60,new_auxiliary_fits=6,financial_fits_in_this_validation=0,historical_PIT_certification=False,independent_manual_QA_performed=False,E3c2026_executed=False,merged=False)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--report',type=Path);a=p.parse_args();r=validate(a.bundle,a.repo)
 if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r,indent=2))
