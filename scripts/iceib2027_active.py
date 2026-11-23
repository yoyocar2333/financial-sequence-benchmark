"""Resolve the active conference manuscript without overwriting preserved editorial baselines."""
import json,shutil
from pathlib import Path

def resolve(bundle):
 bundle=Path(bundle)
 if (bundle/'PAPER_TEMPLATE.md').exists() or (bundle/'REVISED_PAPER_TEMPLATE.md').exists():return bundle
 path=bundle/'ACTIVE_MANUSCRIPT.json'
 if path.exists():return bundle/json.loads(path.read_text())['source_directory']
 return None

def build(repo,out):
 current=resolve(Path(repo)/'research/ICEIB2027')
 if current is None:raise ValueError('No active conference source registered')
 third=(current/'PAPER_TEMPLATE.md').exists()
 if third:
  from iceib2027_r3_build import main
 else:
  from iceib2027_r2_build import main
 if Path(out).resolve()!=(current.resolve()):
  if Path(out).exists():raise FileExistsError('Choose a new output directory; original conference baseline is preserved')
  Path(out).mkdir(parents=True)
  names=['PAPER_TEMPLATE.md','ABSTRACT.md','EVIDENCE_VERSION.json'] if third else ['REVISED_PAPER_TEMPLATE.md','ICEIB2027_REVISED_ABSTRACT.md']
  for name in names:shutil.copy2(current/name,Path(out)/name)
  if third:
   (Path(out)/'tables').mkdir();(Path(out)/'audits').mkdir();shutil.copy2(current/'tables/CALIBRATION_SUMMARY.csv',Path(out)/'tables/CALIBRATION_SUMMARY.csv')
 main(Path(repo),Path(out))
