"""Offline manuscript/source controls; no financial evaluation, network or template redistribution."""
import csv,hashlib,io,json,re
from pathlib import Path

def rows(p):return list(csv.DictReader(io.StringIO(p.read_text())))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(repo,bundle):
 assert json.loads((repo/'research/E9a/MANUSCRIPT_VERSION.json').read_text())['stage']=='E9b'
 records=rows(bundle/'audits/SOURCE_CLAIM_LEDGER.csv');assert len(records)==272
 for c in records:
  source=repo/c['source_file'];assert sha(source)==c['source_sha256'],c['source_file']
  values=rows(source);selector=json.loads(c['selector']);matches=[(i+1,r) for i,r in enumerate(values) if all(r.get(k)==str(v) for k,v in selector.items())]
  assert len(matches)==1,c['claim_id'];i,row=matches[0];assert i==int(c['source_record'])
  assert all(row[k]==v for k,v in json.loads(c['fields']).items()),c['claim_id']
 text=(bundle/'ICEIB2027_FULL_PAPER.md').read_text();abstract=(bundle/'ICEIB2027_ABSTRACT_DRAFT.md').read_text().split('## Abstract\n\n')[1].split('\n\n## Keywords')[0].strip()
 assert len(abstract.split())==100 and abstract in text
 assert not re.search(r'\bE[0-9]+[a-z]?\b|\[R\d+\]',abstract)
 assert '{{' not in text and '0.0240' in text and '0.0480' in text and '0.0744' in text
 assert '0.1512' in text and '0.028' in text and '0.1894/0.3714' in text and '0.004' in text
 assert 'incidental exposure to 2026' in text and 'unchanged and unexecuted' in text
 assert len(re.findall(r'^Table \d+\.',text,re.M))==3 and len(re.findall(r'^Figure \d+\.',text,re.M))==2 and text.count('` (')==3
 mapping=rows(bundle/'audits/REFERENCE_MAPPING.csv');cited=[]
 for n in re.findall(r'\[(\d+)\]',text.split('## References')[0]):
  if n not in cited:cited.append(n)
 assert cited==[str(i) for i in range(1,len(mapping)+1)] and len(mapping)==12
 original={r['id']:r for r in json.loads((repo/'research/E9a/literature/citation_catalog.json').read_text())}
 for r in mapping:assert r['doi']==original[r['original_id']].get('doi','')
 raw=rows(bundle/'tables/fusion_raw_identities.csv');assert len(raw)==10 and all(float(r['net_raw_F_beyond_constant'])<0 for r in raw)
 return dict(status='PASSED',source_cells=272,abstract_words=100,references=12,main_tables=3,main_figures=2,editable_equations=3,financial_model_fits=0,PIT_certification=False,independent_manual_QA=False,E3c2026_executed=False)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
 from iceib2027_active import resolve
 current=resolve(a.bundle)
 if current is not None:
  from iceib2027_r2_validate import validate as active
  r=active(a.repo,current)
 else:r=validate(a.repo,a.bundle)
 if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r,indent=2))
