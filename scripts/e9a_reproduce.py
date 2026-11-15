"""Offline aggregate replay. Does not download data, train or evaluate a new model."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path

def main(repo,bundle,out,figures):
 if out.exists():raise FileExistsError('Use a fresh output directory; never overwrite the frozen paper bundle.')
 hashes=json.loads((bundle/'audits/table_source_hashes.json').read_text())
 for rel,digest in hashes.items():assert hashlib.sha256((repo/'research'/rel).read_bytes()).hexdigest()==digest,rel
 out.mkdir(parents=True)
 for d in ['audits','literature','checks']:(out/d).mkdir()
 for path in ['PAPER_TEMPLATE.md','literature/verified_doi_records.json']:
  shutil.copy2(bundle/path,out/path)
 code=Path(__file__).parent
 subprocess.run([sys.executable,'-B',str(code/'e9a_build.py'),'--repo',str(repo),'--out',str(out)],check=True)
 subprocess.run([sys.executable,'-B',str(code/'e9a_citations.py'),'--out',str(out)],check=True)
 if figures:
  subprocess.run([sys.executable,'-B',str(code/'e9a_paper.py'),'--out',str(out)],check=True)
 else:
  shutil.copy2(bundle/'PAPER_DRAFT.md',out/'PAPER_DRAFT.md')
 subprocess.run([sys.executable,'-B',str(code/'e9a_validate.py'),'--repo',str(repo),'--bundle',str(out),'--report',str(out/'checks/evidence_validation.json')],check=True)
 names=['CLAIM_EVIDENCE_MATRIX.csv']+[str(p.relative_to(bundle)) for p in sorted((bundle/'tables').glob('*.csv'))]
 for name in names:assert (bundle/name).read_bytes()==(out/name).read_bytes(),name
 if figures:assert (bundle/'PAPER_DRAFT.md').read_bytes()==(out/'PAPER_DRAFT.md').read_bytes()
 print('Replayed aggregate tables and source links; historical source qualification was not performed.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--figures',action='store_true');a=p.parse_args();main(a.repo,a.bundle,a.out,a.figures)
