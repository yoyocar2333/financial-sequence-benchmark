"""Professor-revision source/metadata/evidence checks; no fitting or financial evaluation."""
import argparse,contextlib,hashlib,io,json,re,shutil,tempfile
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(repo,bundle):
 protected=json.loads((bundle/'audits/PROTECTED_SOURCE_HASHES.json').read_text())
 for name,h in protected.items():assert sha(repo/name)==h,name
 from iceib2027_r3_validate import validate as previous
 previous(repo,repo/'research/ICEIB2027/round3')
 text=(bundle/'ICEIB2027_FULL_PAPER.md').read_text();old=(repo/'research/ICEIB2027/round3/ICEIB2027_FULL_PAPER.md').read_text()
 assert text.splitlines()[0]=='# Diagnosing apparent predictive gains in financial machine learning'
 metadata=json.loads((bundle/'audits/AUTHOR_METADATA_AND_DECLARATIONS.json').read_text())
 for key in ['authors','affiliation','correspondence','conference']:assert metadata[key] in text,key
 assert '### 2.4. Development Controls and Statistical Evaluation' in text
 assert re.findall(r'^## ([1-5])\. ',text,re.M)==['1','2','3','4','5']
 assert re.findall(r'^### (3\.\d)\. ',text,re.M)==['3.1','3.2','3.3','3.4','3.5','3.6']
 assert re.findall(r'` \((\d)\)',text)==list('12345678')
 abstract=(bundle/'ABSTRACT.md').read_text().split('\n\n',1)[1].strip();assert abstract in text and 100<len(abstract.split())<=200
 intro=text.split('## 1. Introduction and Related Work\n\n')[1].split('\n## 2.')[0];oldintro=old.split('## 1. Introduction and Related Work\n\n')[1].split('\n## 2.')[0];assert len(intro.split())>2*len(oldintro.split())
 methods=text.split('## 2. Methods and Experimental Setup\n\n')[1].split('### 2.1.')[0];assert 'contribution' in methods and 'controls' in methods
 back=text.split('## Back Matter\n\n')[1].split('\n## References')[0]
 required=['Author Contributions:','Funding:','Institutional Review Board Statement:','Informed Consent Statement:','Data Availability Statement:','Conflicts of Interest:'];assert [back.index(k) for k in required]==sorted(back.index(k) for k in required)
 assert 'This research received no external funding.' in back and 'The authors declare no conflicts of interest.' in back
 assert 'Institutional Review Board Statement: Not applicable.' in back and 'Informed Consent Statement: Not applicable.' in back
 assert 'All authors have read and agreed' not in back and 'NSTC' not in back
 refs=text.split('## References\n\n')[1];original=old.split('## References\n\n')[1]
 for a,b in [('Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)','Proc. ACL (Vol. 1: Long Papers)'),('Proceedings of the National Academy of Sciences','Proc. Natl. Acad. Sci. USA'),('Scandinavian Journal of Statistics','Scand. J. Stat.')]:original=original.replace(a,b)
 original=original.replace(' https://www.jstor.org/stable/4615733','');assert refs==original
 assert len(re.findall(r'^\d+\. ',refs,re.M))==12
 for value in ['0.000980','0.001198','0.0240','0.0480','0.0744','0.1512','0.028','0.1894/0.3714','0.004','zero L3','L4']:assert value in text,value
 # All four unmodified neural score/reference/interval rows survive in panel A.
 for row in old.splitlines():
  if row.startswith('| AAPL LSTM |') or row.startswith('| AAPL Mamba |') or row.startswith('| TSLA LSTM |') or row.startswith('| TSLA Mamba |'):assert row in text,row
 assert len(re.findall(r'^Table \d+\.',text,re.M))==4 and len(re.findall(r'^Figure \d+\.',text,re.M))==1
 from iceib2027_r4_build import main as build
 with tempfile.TemporaryDirectory(prefix='iceib_r4_') as tmp:
  out=Path(tmp);(out/'audits').mkdir()
  for n in ['PAPER_TEMPLATE.md','ABSTRACT.md','EVIDENCE_VERSION.json']:shutil.copy2(bundle/n,out/n)
  with contextlib.redirect_stdout(io.StringIO()):build(repo,out)
  assert (out/'ICEIB2027_FULL_PAPER.md').read_bytes()==(bundle/'ICEIB2027_FULL_PAPER.md').read_bytes()
 return dict(status='PASSED',protected_scientific_and_prior_revision_files=len(protected),abstract_words=len(abstract.split()),prior_abstract_words=100,introduction_words=len(intro.split()),prior_introduction_words=len(oldintro.split()),author_metadata_user_confirmed=True,six_required_declarations_present=True,senior_example_grant_or_roles_reused=False,main_tables=4,main_figures=1,equations=8,references=12,all_scientific_results_unchanged=True,source_byte_reproduced=True,financial_fits=0,calibrator_fits=0,new_pvalues=0,E3c2026_executed=False,independent_human_QA=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();result=validate(a.repo,a.bundle)
 if a.report:a.report.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
