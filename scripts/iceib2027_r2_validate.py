"""Offline round2 evidence, arithmetic and source-replay checks; never financial training."""
import argparse,csv,hashlib,io,json,re,tempfile,contextlib
from decimal import Decimal as D,localcontext
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return list(csv.DictReader(io.StringIO(p.read_text())))
def validate(repo,bundle):
 evidence=rows(bundle/'audits/R2_SOURCE_EVIDENCE.csv');assert len(evidence)==596
 cache={};digests={}
 for r in evidence:
  name=r['source_file']
  if name not in cache:cache[name]=rows(repo/name);digests[name]=sha(repo/name)
  assert digests[name]==r['sha256'],name
  values=cache[name];selector=json.loads(r['selector']);found=[(i+1,x) for i,x in enumerate(values) if all(x.get(k)==str(v) for k,v in selector.items())]
  assert len(found)==1 and found[0][0]==int(r['source_record'])
  assert found[0][1]==json.loads(r['fields'])
 arithmetic=rows(bundle/'tables/R2_SCORE_INTERPRETATION.csv');assert len(arithmetic)==73
 for r in arithmetic:
  a,b,d=map(D,[r['reference_Brier'],r['candidate_Brier'],r['delta_Brier']]);assert abs((a-b)-d)<D('2e-12')
  with localcontext() as ctx:
   ctx.prec=40;assert str(100*d/a)==r['relative_percent']
  assert a>0
  if r['adjusted_p']:assert D(0)<=D(r['adjusted_p'])<=D(1)
  if r['CI_low']:assert D(r['CI_low'])<=d<=D(r['CI_high'])
  if 'vs_global' in r['comparison_id']:assert not r['CI_low'] and not r['adjusted_p'] and 'DESCRIPTIVE' in r['correction_family']
 ids=[r['comparison_id'] for r in arithmetic];assert len(ids)==len(set(ids))
 assert sum(x.startswith('technical_') for x in ids)==8
 assert sum(x.startswith('fusion_') for x in ids)==20
 assert sum(x.startswith('development_') for x in ids)==36
 assert sum(x.startswith('news_') for x in ids)==9
 assert all(D(r['delta_Brier'])<0 for r in arithmetic if r['comparison_id'].startswith('fusion_') and r['comparison_id'].endswith('_raw'))
 text=(bundle/'ICEIB2027_REVISED_FULL_PAPER.md').read_text();meta=json.loads((bundle/'audits/R2_MANUSCRIPT_METADATA.json').read_text())
 headings=re.findall(r'^### (4\.\d)\. ',text,re.M);assert headings==['4.1','4.2','4.3','4.4','4.5','4.6']
 assert '{{' not in text and '2026' not in text and 'review draft' not in text.lower()
 for bad in ['B38','T51','C39','P8','Holm6','Holm12','PriorBlend','C1–C6','analyst-consensus vintages']:assert bad not in text,bad
 for value in ['0.395%','0.482%','0.251%','0.0240','0.0480','0.0744','2017–2018','0.1512','0.028','0.1894/0.3714','0.256489','0.259011','0.004','repeatedly inspected','unconstrained slope','0.4032']:
  assert value in text,value
 abstract=(bundle/'ICEIB2027_REVISED_ABSTRACT.md').read_text().split('## Abstract\n\n')[1].split('\n\n## Keywords')[0].strip();assert abstract in text and len(abstract.split())==100
 assert len(re.findall(r'^Table \d+\.',text,re.M))==3 and len(re.findall(r'^Figure \d+\.',text,re.M))==2 and text.count('` (')==3
 references=text.split('## References\n\n')[1];old=(repo/'research/ICEIB2027/ICEIB2027_FULL_PAPER.md').read_text().split('## References\n\n')[1];assert references==old
 cited=[]
 for sequence in re.findall(r'\[([0-9,–-]+)\]',text.split('## References')[0]):
  for item in sequence.split(','):
   ns=re.split('[–-]',item);cited.extend(range(int(ns[0]),int(ns[-1])+1))
 assert set(cited)==set(range(1,13))
 assert len(re.findall(r'^\d+\. ',references,re.M))==12
 protected=json.loads((bundle/'audits/PROTECTED_SCIENTIFIC_SOURCE_HASHES.json').read_text())
 for name,digest in protected.items():assert sha(repo/name)==digest,name
 # Recreate manuscript, evidence, relative arithmetic and complete source families from frozen inputs.
 from iceib2027_r2_build import main as build
 with tempfile.TemporaryDirectory(prefix='iceib_r2_verify_') as temporary:
  target=Path(temporary)
  import shutil
  for name in ['REVISED_PAPER_TEMPLATE.md','ICEIB2027_REVISED_ABSTRACT.md']:shutil.copy2(bundle/name,target/name)
  with contextlib.redirect_stdout(io.StringIO()):build(repo,target)
  for name in ['ICEIB2027_REVISED_FULL_PAPER.md','RESULTS_SYNTHESIS_TABLE.md','SUPPLEMENTARY_RESULTS.md','tables/R2_SCORE_INTERPRETATION.csv','audits/R2_SOURCE_EVIDENCE.csv','audits/R2_MANUSCRIPT_METADATA.json']:assert (target/name).read_bytes()==(bundle/name).read_bytes(),name
 return dict(status='PASSED',exact_original_source_rows=len(evidence),descriptive_arithmetic_rows=len(arithmetic),protected_scientific_sources=len(protected),all_8_technical_20_fusion_36_development_9_news_rows_retained=True,manuscript_and_tables_byte_reproduced=True,original_CIs_and_pvalues_unchanged=True,relative_percentage_new_inference=False,cohorts_and_multiplicity_families_separate=True,abstract_words=100,main_tables=3,main_figures=2,references=12,financial_fits=0,new_pvalues=0,E3c2026_executed=False,independent_human_scientific_QA=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();r=validate(a.repo,a.bundle)
 if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r,indent=2))
