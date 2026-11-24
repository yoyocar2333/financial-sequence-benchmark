"""Replay authored round2 source, deterministic arithmetic and original figures offline."""
import argparse,contextlib,io,json,shutil
from pathlib import Path

def main(repo,bundle,out,figures=False):
 from iceib2027_r2_validate import validate
 from iceib2027_r2_build import main as build
 validate(repo,bundle)
 if out.exists():raise FileExistsError('Choose a new replay directory')
 out.mkdir(parents=True)
 for name in ['REVISED_PAPER_TEMPLATE.md','ICEIB2027_REVISED_ABSTRACT.md']:shutil.copy2(bundle/name,out/name)
 with contextlib.redirect_stdout(io.StringIO()):build(repo,out)
 for name in ['ICEIB2027_REVISED_FULL_PAPER.md','RESULTS_SYNTHESIS_TABLE.md','SUPPLEMENTARY_RESULTS.md','tables/R2_SCORE_INTERPRETATION.csv','audits/R2_SOURCE_EVIDENCE.csv','audits/R2_MANUSCRIPT_METADATA.json']:assert (out/name).read_bytes()==(bundle/name).read_bytes(),name
 if figures:
  from iceib2027_r2_figures import main as plot
  plot(out)
  for p in (bundle/'figures').glob('*.png'):assert (out/'figures'/p.name).read_bytes()==p.read_bytes(),p.name
 result=dict(status='PASSED',source_tables_and_manuscript_byte_identical=True,figures_byte_identical=figures,network=False,financial_fits=0,new_inferential_tests=0,template_documents_excluded=True)
 (out/'audits/PUBLIC_REPLAY_REPORT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--figures',action='store_true');a=p.parse_args();main(a.repo,a.bundle,a.out,a.figures)
