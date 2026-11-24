"""Reuse the preserved template styles; add a separate professor-review abstract file."""
import argparse, json, shutil, tempfile
from pathlib import Path
from docx import Document
from docx.shared import Cm
from docx.oxml.ns import qn
from iceib2027_r4_docx import main as previous_main


def main(template, bundle, out):
    with tempfile.TemporaryDirectory(prefix='iceib_r5_docx_') as tmp:
        work=Path(tmp)
        for name in ['ICEIB2027_FULL_PAPER.md','audits/BASELINE_RECORD.json']:
            (work/name).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(bundle/name,work/name)
        original=(work/'ICEIB2027_FULL_PAPER.md').read_text()
        original=original.replace('(../round4/figures/control_design.png)',
                                  '('+str((bundle/'../round4/figures/control_design.png').resolve())+')')
        (work/'ICEIB2027_FULL_PAPER.md').write_text(original)
        previous_main(template,work,out)
    destination=out/'ICEIB2027_FULL_PAPER.docx';doc=Document(destination)
    table=[t for t in doc.tables if t.cell(0,0).text=='Price expert'][0]
    widths=[2.05,2.05,3.85,2.05,3.85];scale=13.86/sum(widths)
    for j,width in enumerate(widths):
        table.columns[j].width=Cm(width*scale)
        for row in table.rows:row.cells[j].width=Cm(width*scale)
    doc.save(destination)
    abstractdoc=Document(destination);body=abstractdoc.element.body;remove=False
    for child in list(body):
        if child.tag==qn('w:sectPr'):continue
        if child.tag==qn('w:p'):
            from docx.text.paragraph import Paragraph
            paragraph=Paragraph(child,abstractdoc._body)
            if paragraph.text=='1. Introduction and Related Work':remove=True
        if remove:body.remove(child)
    abstractdoc.core_properties.subject='Standalone ICEIB 2027 abstract for professor review'
    abstractdoc.save(out/'ICEIB2027_ABSTRACT_ONLY.docx')
    (out/'ICEIB2027_ABSTRACT_ONLY.txt').write_text(
        (bundle/'ABSTRACT.md').read_text().split('\n\n',1)[1].strip()+'\n')
    recordpath=out/'checks/template_generation.json'
    record=json.loads(recordpath.read_text());record.pop('baseline_is_current_round3_Word',None)
    record.update(baseline_stage='ICEIB2027_R4',standalone_abstract=True,
                  local_table_column_widths_adjusted=True)
    recordpath.write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--template',type=Path,required=True)
    p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();main(a.template,a.bundle,a.out)
