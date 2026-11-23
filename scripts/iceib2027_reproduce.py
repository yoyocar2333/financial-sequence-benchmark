"""Public offline aggregate replay; private templates and financial model fits are excluded."""
import argparse,json,shutil
from pathlib import Path

def main(repo,bundle,out,figures=False):
 from iceib2027_validate import validate
 from iceib2027_build import main as build
 validate(repo,bundle)
 if out.exists():raise FileExistsError('Use a new output directory')
 out.mkdir(parents=True)
 for name in ['FULL_PAPER_TEMPLATE.md','ICEIB2027_ABSTRACT_DRAFT.md']:shutil.copy2(bundle/name,out/name)
 build(repo,out)
 for name in ['ICEIB2027_FULL_PAPER.md','audits/SOURCE_CLAIM_LEDGER.csv','audits/REFERENCE_MAPPING.csv','audits/MANUSCRIPT_METADATA.json']:
  assert (out/name).read_bytes()==(bundle/name).read_bytes(),name
 if figures:
  from iceib2027_figures import main as plot
  plot(out)
  for p in (bundle/'figures').glob('*.png'):assert p.read_bytes()==(out/'figures'/p.name).read_bytes(),p.name
 result=dict(status='PASSED',manuscript_claims_references_byte_identical=True,figure_bytes_identical=figures,new_models=0,network=False,template_documents_distributed=False)
 (out/'audits/PUBLIC_REPLAY_REPORT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--figures',action='store_true');a=p.parse_args()
 from iceib2027_active import resolve
 current=resolve(a.bundle)
 if current is not None:
  if (current/'PAPER_TEMPLATE.md').exists():
   from iceib2027_r3_reproduce import main as active
  else:
   from iceib2027_r2_reproduce import main as active
  if (current/'PAPER_TEMPLATE.md').exists():active(a.repo,current,a.out)
  else:active(a.repo,current,a.out,a.figures)
 else:main(a.repo,a.bundle,a.out,a.figures)
