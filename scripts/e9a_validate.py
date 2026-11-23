"""Offline source-cell, cohort, citation and claim-boundary validation; no refitting."""
import argparse,io,csv,hashlib,json,re
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(bundle,repo):
 if (bundle/'MANUSCRIPT_VERSION.json').exists() and __import__('json').loads((bundle/'MANUSCRIPT_VERSION.json').read_text()).get('stage')=='E9b':
  from e9b_validate import validate as current; return current(bundle,repo)
 hashes=json.loads((bundle/'audits/table_source_hashes.json').read_text());root=repo/'research'
 for rel,digest in hashes.items():
  assert sha(root/rel)==digest, 'Source changed: '+rel
 records=list(csv.DictReader(io.StringIO((bundle/'CLAIM_EVIDENCE_MATRIX.csv').read_text())))
 assert len(records)==103 and len({r['claim_id'] for r in records})==103
 for r in records:
  if not r['selector']:continue
  rows=list(csv.DictReader(io.StringIO((repo/r['source_file']).read_text())));sel=json.loads(r['selector']);found=[(i+1,x) for i,x in enumerate(rows) if all(x.get(k)==str(v) for k,v in sel.items())]
  assert len(found)==1,(r['claim_id'],'selector')
  i,x=found[0];assert i==int(r['source_record'])
  assert all(x[k]==v for k,v in json.loads(r['fields']).items()),r['claim_id']
  assert sha(repo/r['source_file'])==r['source_sha256']
 p=(bundle/'PAPER_DRAFT.md').read_text();refs=json.loads((bundle/'literature/citation_catalog.json').read_text());ids={r['id'] for r in refs}
 assert ids==set(re.findall(r'\[(R\d+)\]',p)) and len(ids)==32
 assert next(r for r in refs if r['id']=='R18')['doi']==''
 assert next(r for r in refs if r['id']=='R27')['status']=='DOI_AND_AUTHOR_PRIMARY_PAGE_VERIFIED'
 assert '{{' not in p and '2023 / 2024 / 2025' in p and 'P=E5 T' in p
 assert '0.1512' in p and '0.028' in p and 'secondary' in p and '0.004' in p
 assert 'not an equivalence result' in p and 'not an externally registered' in p
 for name in ['E5_technical_increments.csv','E6_fusion_controls.csv','E4c_event_models.csv']:
  rows=list(csv.DictReader(io.StringIO((bundle/'tables'/name).read_text())))
  for row in rows:
   field='B_Brier' if name.startswith('E5') else 'P' if name.startswith('E6') else 'Brier'
   assert f'{float(row[field]):.6f}' in p,(name,row)
 result={'status':'PASSED','claims':len(records),'exact_source_csv_rows':sum(bool(r['selector']) for r in records),'source_files_hash_checked':len(hashes),'references_checked':len(refs),'new_financial_estimates':0,'historical_PIT_certification':False,'independent_manual_QA_performed':False,'E3c2026_executed':False,'merged':False}
 return result
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--bundle',type=Path,required=True);a.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);a.add_argument('--report',type=Path);x=a.parse_args();r=validate(x.bundle,x.repo)
 if x.report:x.report.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r,indent=2))
