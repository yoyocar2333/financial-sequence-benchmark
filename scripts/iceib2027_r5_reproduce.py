"""Replay current authored prose and frozen model-score tables without model training."""
import argparse, json, shutil
from pathlib import Path
from iceib2027_r5_validate import validate
from iceib2027_r5_build import main as build


def main(repo,bundle,out):
    validate(repo,bundle)
    if out.exists():raise FileExistsError('Choose a new output directory')
    out.mkdir(parents=True);(out/'audits').mkdir()
    for name in ['PAPER_TEMPLATE.md','ABSTRACT.md','EVIDENCE_VERSION.json']:shutil.copy2(bundle/name,out/name)
    build(repo,out)
    assert (out/'ICEIB2027_FULL_PAPER.md').read_bytes()==(bundle/'ICEIB2027_FULL_PAPER.md').read_bytes()
    v=dict(status='PASSED',manuscript_byte_identical=True,new_fits=0,network=False)
    (out/'audits/PUBLIC_REPLAY_REPORT.json').write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();main(a.repo,a.bundle,a.out)
