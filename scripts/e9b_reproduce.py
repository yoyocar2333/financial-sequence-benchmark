"""Offline publication replay from public aggregates; no raw-data refit or network."""
import argparse,csv,hashlib,json,shutil
from pathlib import Path

def main(repo,bundle,out,figures=False):
 from e9b_validate import validate
 validate(bundle,repo)
 if out.exists():raise FileExistsError('Use a fresh output directory')
 supplemental=repo/'research/E9b';out.mkdir(parents=True)
 for directory in ['tables','baseline']:
  shutil.copytree(supplemental/directory,out/directory)
 shutil.copytree(bundle/'literature',out/'literature');shutil.copytree(bundle/'audits',out/'audits')
 (out/'figures').mkdir();(out/'checks').mkdir()
 shutil.copy2(bundle/'PAPER_TEMPLATE.md',out/'PAPER_TEMPLATE.md')
 from e9b_citations import main as citations
 from e9b_paper import main as paper
 citations(out);paper(out,repo)
 for name in ['CLAIM_EVIDENCE_MATRIX.csv','PAPER_DRAFT.md','MANUSCRIPT_VERSION.json']:
  assert (out/name).read_bytes()==(bundle/name).read_bytes(),name
 assert (out/'literature/citation_catalog.json').read_bytes()==(bundle/'literature/citation_catalog.json').read_bytes()
 if figures:
  from e9b_plot import main as plot
  plot(out)
 result=dict(status='PASSED',scope='Public aggregate manuscript/table replay; private source-prediction replay is separate',claims=319,manuscript_byte_identical=True,new_fits=0,network=False,figure_regeneration=figures,PIT_certification=False)
 (out/'checks/public_replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--figures',action='store_true');a=p.parse_args();main(a.repo,a.bundle,a.out,a.figures)
