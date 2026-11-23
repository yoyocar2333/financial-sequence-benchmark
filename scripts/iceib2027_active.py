"""Resolve the active conference manuscript without overwriting preserved editorial baselines."""
import json,shutil
from pathlib import Path

def resolve(bundle):
 bundle=Path(bundle)
 if (bundle/'REVISED_PAPER_TEMPLATE.md').exists():return bundle
 path=bundle/'ACTIVE_MANUSCRIPT.json'
 if path.exists():return bundle/json.loads(path.read_text())['source_directory']
 return None

def build(repo,out):
 from iceib2027_r2_build import main
 current=resolve(Path(repo)/'research/ICEIB2027')
 if current is None:raise ValueError('No active round2 source registered')
 if Path(out).resolve()!=(current.resolve()):
  if Path(out).exists():raise FileExistsError('Choose a new output directory; original conference baseline is preserved')
  Path(out).mkdir(parents=True)
  for name in ['REVISED_PAPER_TEMPLATE.md','ICEIB2027_REVISED_ABSTRACT.md']:shutil.copy2(current/name,Path(out)/name)
 main(Path(repo),Path(out))
