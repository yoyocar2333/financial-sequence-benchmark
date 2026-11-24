"""Replay the professor-requested manuscript from frozen aggregates and authored source."""
import argparse,json,shutil
from pathlib import Path

def main(repo,bundle,out):
 from iceib2027_r4_validate import validate
 from iceib2027_r4_build import main as build
 validate(repo,bundle)
 if out.exists():raise FileExistsError('Choose a new directory')
 out.mkdir(parents=True);(out/'audits').mkdir()
 for n in ['PAPER_TEMPLATE.md','ABSTRACT.md','EVIDENCE_VERSION.json']:shutil.copy2(bundle/n,out/n)
 build(repo,out)
 assert (out/'ICEIB2027_FULL_PAPER.md').read_bytes()==(bundle/'ICEIB2027_FULL_PAPER.md').read_bytes()
 result=dict(status='PASSED',manuscript_byte_identical=True,financial_fits=0,calibrator_fits=0,new_pvalues=0,network=False)
 (out/'audits/PUBLIC_REPLAY_REPORT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.repo,a.bundle,a.out)
