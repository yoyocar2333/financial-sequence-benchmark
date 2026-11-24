"""Export full paper and standalone abstract using the unchanged isolated renderer."""
import argparse, shutil
from pathlib import Path
from iceib2027_r4_render_pdf import main as render


def main(out, program, registry):
    render(out,program,registry)
    standalone=out/'abstract_only';standalone.mkdir(exist_ok=True)
    shutil.copy2(out/'ICEIB2027_ABSTRACT_ONLY.docx',standalone/'ICEIB2027_FULL_PAPER.docx')
    render(standalone,program,registry)
    shutil.copy2(standalone/'ICEIB2027_FULL_PAPER.pdf',out/'ICEIB2027_ABSTRACT_ONLY.pdf')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--program',type=Path,required=True);p.add_argument('--registry',type=Path)
    a=p.parse_args();main(a.out,a.program,a.registry)
