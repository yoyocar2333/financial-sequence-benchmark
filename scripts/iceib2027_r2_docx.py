"""Private submission-layout DOCX from a user-supplied Engineering Proceedings template.
The template and template-formatted outputs must not be posted online under MDPI's terms.
"""
import argparse,copy,hashlib,json,re
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm,Twips

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def add_field(p,instruction,rpr=None):
 r=p.add_run()
 if rpr is not None:r._r.insert(0,copy.deepcopy(rpr))
 for tag,kind in [('begin','fldChar'),('instruction','instrText'),('separate','fldChar'),('end','fldChar')]:
  e=OxmlElement('w:'+kind)
  if kind=='fldChar':e.set(qn('w:fldCharType'),tag)
  else:e.set(qn('xml:space'),'preserve');e.text=' '+instruction+' '
  r._r.append(e)
def suppress_auxiliary_line_numbers(doc):
 """Headers/footers are excluded; keep the section's body line-number setting."""
 for sec in doc.sections:
  for name in ['header','even_page_header','first_page_header','footer','even_page_footer','first_page_footer']:
   for p in getattr(sec,name)._element.iter(qn('w:p')):
    pr=p.get_or_add_pPr();flag=pr.find(qn('w:suppressLineNumbers'))
    if flag is None:
     flag=OxmlElement('w:suppressLineNumbers');pr.insert_element_before(flag,'w:pBdr','w:shd','w:tabs','w:spacing','w:ind','w:jc','w:rPr')
    flag.set(qn('w:val'),'1')

def main(template,bundle,out):
 repo=Path(__file__).resolve().parents[1]
 if (repo/'.git').exists() and (repo==out.resolve() or repo in out.resolve().parents):raise ValueError('Template documents require private output outside this public Git checkout')
 expected=json.loads((bundle/'audits/BASELINE_RECORD.json').read_text())['Word_sha256']
 if sha(template)!=expected:raise ValueError('Use the preserved user six-page Word baseline specified in BASELINE_RECORD.json')
 out.mkdir(parents=True,exist_ok=True);(out/'checks').mkdir(exist_ok=True)
 doc=Document(template);styles=doc.styles.element.xml
 original_geometry=doc.sections[0]._sectPr.xml
 sample_table=copy.deepcopy(next(t._tbl for t in doc.tables if t.cell(0,0).paragraphs[0].style.name=='MDPI_4.2_table_body'));sample_equation=copy.deepcopy(next(t._tbl for t in doc.tables if t.cell(0,0).paragraphs[0].style.name=='MDPI_3.9_equation'))
 for child in list(doc.element.body):
  if child.tag!=qn('w:sectPr'):doc.element.body.remove(child)
 # Keep template styles, section geometry, line numbering, logos and first-page design.
 # Remove unreachable sample images/links/comments from the editable submission document.
 for id,rel in list(doc.part.rels.items()):
  if rel.reltype.endswith(('/image','/hyperlink','/comments','/people')):doc.part.drop_rel(id)
 doc.core_properties.title='Diagnosing Apparent Predictive Gains in Financial Machine Learning'
 doc.core_properties.author='Author names pending confirmation';doc.core_properties.subject='ICEIB2027 revised manuscript; publication metadata pending'
 doc.core_properties.last_modified_by='Research team'
 # Editorial assignment/copyright are publisher-controlled; pending status is in the footer and back matter.
 from docx.table import Table
 # Replace sample publication year/DOI with explicit pending status; no invented identifier.
 for sec in doc.sections:
  reference=sec.header.paragraphs[0];rpr=copy.deepcopy(reference.runs[0]._r.rPr) if reference.runs else None
  for header in [sec.header,sec.even_page_header]:
   p=header.paragraphs[0];p.clear();r=p.add_run('ICEIB 2027\t')
   if rpr is not None:r._r.insert(0,copy.deepcopy(rpr))
   add_field(p,'PAGE',rpr);p.add_run(' of ');add_field(p,'NUMPAGES',rpr)
  for footer in [sec.footer,sec.even_page_footer]:
   for p in footer.paragraphs:p.clear()
  for p in sec.first_page_footer.paragraphs:p.clear()
  p=sec.first_page_footer.paragraphs[-1];p.add_run('ICEIB 2027\t');add_field(p,'PAGE',rpr);p.add_run(' of ');add_field(p,'NUMPAGES',rpr)
 lines=(bundle/'ICEIB2027_REVISED_FULL_PAPER.md').read_text().splitlines();i=0;references=False;counts={'tables':0,'figures':0,'equations':0,'references':0}
 while i<len(lines):
  line=lines[i].strip();i+=1
  if not line:continue
  if line.startswith('# '):
   doc.add_paragraph('Proceeding Paper','MDPI_1.1_article_type');doc.add_paragraph(line[2:],'MDPI_1.2_title');continue
  if line=='Hsieh Hao-Hsuan' or line.startswith('[Author names'):
   doc.add_paragraph(line,'MDPI_1.3_authornames');continue
  if line.startswith('[Affiliation'):
   doc.add_paragraph(line,'MDPI_1.6_affiliation');doc.add_paragraph('* Correspondence: [Name and e-mail pending confirmation]','MDPI_1.6_affiliation');doc.add_paragraph('† [Conference presentation details pending confirmation]','MDPI_1.6_affiliation');continue
  if line.startswith('## '):
   title=line[3:]
   if title=='Abstract':doc.add_paragraph('Abstract','MDPI_1.7_abstract');mode='abstract';continue
   if title=='Back Matter':mode='back';continue
   mode='references' if title=='References' else 'body';references=title=='References';p=doc.add_paragraph(title,'MDPI_2.1_heading1');p.paragraph_format.keep_with_next=True;continue
  if line.startswith('### '):
   p=doc.add_paragraph(line[4:],'MDPI_2.2_heading2');p.paragraph_format.keep_with_next=True;continue
  if line.startswith('Keywords:'):doc.add_paragraph(line,'MDPI_1.8_keywords');continue
  if line.startswith('!['):
   image=bundle/re.search(r'\]\(([^)]+)\)',line).group(1);p=doc.add_paragraph(style='MDPI_3.3_text_space_after');p.paragraph_format.keep_with_next=True;p.add_run().add_picture(str(image),width=Cm(13.8));counts['figures']+=1;continue
  if line.startswith('Table '):
   p=doc.add_paragraph(line,'MDPI_4.1_table_caption');p.paragraph_format.keep_with_next=True;continue
  if line.startswith('Figure '):doc.add_paragraph(line,'MDPI_5.1_figure_caption');continue
  if line.startswith('|'):
   block=[line]
   while i<len(lines) and lines[i].strip().startswith('|'):block.append(lines[i].strip());i+=1
   rows=[[c.strip() for c in x.strip('|').split('|')] for x in block];rows=[r for r in rows if not all(re.fullmatch(r':?-+:?',v) for v in r)]
   cols=len(rows[0]);t=doc.add_table(rows=0,cols=cols);pr=t._tbl.tblPr
   for c in list(pr):pr.remove(c)
   for c in sample_table.tblPr:pr.append(copy.deepcopy(c))
   widths=([2.7,2.0,2.0,1.7,3.5] if counts['tables']==0 else [5.0,2.0,2.0,1.7,2.1] if cols==5 else [3.1,3.4,7.35] if cols==3 else [13.86/cols]*cols)
   scale=13.86/sum(widths);widths=[w*scale for w in widths]
   for c,w in zip(t.columns,widths):c.width=Cm(w)
   for row in rows:
    cells=t.add_row().cells
    for j,(cell,text) in enumerate(zip(cells,row)):
     cell.width=Cm(widths[j]);p=cell.paragraphs[0];p.style=doc.styles['MDPI_4.2_table_body'];p.text=text
   header=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(header)
   for row in t.rows:row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
   # Keep compact data tables together, rather than splitting the interpretation across pages.
   for row in t.rows[:-1]:
    for cell in row.cells:
     for p in cell.paragraphs:p.paragraph_format.keep_with_next=True
   counts['tables']+=1;continue
  if line.startswith('`'):
   expression,number=line.split('` (',1)[0].strip('`'),line.rsplit('(',1)[1].strip(')')
   x=copy.deepcopy(sample_equation);doc.element.body.insert(len(doc.element.body)-1,x);t=Table(x,doc._body)
   for j,c in enumerate(t.rows[0].cells):
    p=c.paragraphs[0]
    for child in list(p._p):
     if child.tag!=qn('w:pPr'):p._p.remove(child)
    if j==0:
     math=OxmlElement('m:oMath');r=OxmlElement('m:r');txt=OxmlElement('m:t');txt.text=expression;r.append(txt);math.append(r);p._p.append(math)
    else:p.add_run('('+number+')')
   counts['equations']+=1;continue
  if references:
   line=re.sub(r'^\d+\.\s*','',line);p=doc.add_paragraph(line,'MDPI_8.1_references');counts['references']+=1;continue
  style='MDPI_1.7_abstract' if mode=='abstract' else 'MDPI_6.2_back_matter' if mode=='back' else 'MDPI_3.1_text'
  doc.add_paragraph(line,style)
 suppress_auxiliary_line_numbers(doc)
 assert doc.styles.element.xml==styles,'Do not modify template font or paragraph style definitions'
 # Header/footer references may be renumbered by python-docx, but page/column geometry stays unchanged.
 setting=OxmlElement('w:updateFields');setting.set(qn('w:val'),'true');doc.settings.element.append(setting)
 destination=out/'ICEIB2027_REVISED_FULL_PAPER.docx';doc.save(destination)
 record=dict(baseline_is_user_edited_Word=True,status='GENERATED_FROM_USER_TEMPLATE',template_sha256=sha(template),template_styles_unchanged=True,template_geometry_unchanged=True,body_font='Palatino Linotype; original inherited Latin size unchanged (LibreOffice effective10pt); native Word validation pending',headings='12pt H1; inherited H2 unchanged',references_font='9pt original style',figures=counts['figures'],tables=counts['tables'],equations=counts['equations'],references=counts['references'],public_distribution_allowed=False)
 (out/'checks/template_generation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--template',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.template,a.bundle,a.out)
