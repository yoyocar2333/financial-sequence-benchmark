"""Editable academic DOCX from E9a Markdown; no remote document service."""
import argparse,re
from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt,Cm,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE

def setfont(style,name='Times New Roman',size=11):
 style.font.name=name;style.font.size=Pt(size)
 style.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'Noto Serif TC')
def field(p,instruction):
 r=p.add_run();b=OxmlElement('w:fldChar');b.set(qn('w:fldCharType'),'begin');r._r.append(b)
 i=OxmlElement('w:instrText');i.set(qn('xml:space'),'preserve');i.text=instruction;r._r.append(i)
 sep=OxmlElement('w:fldChar');sep.set(qn('w:fldCharType'),'separate');r._r.append(sep)
 t=OxmlElement('w:t');t.text='Update field';r._r.append(t)
 e=OxmlElement('w:fldChar');e.set(qn('w:fldCharType'),'end');r._r.append(e)
def clean(t):
 t=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'\1 (\2)',t)
 return t.replace('**','').replace('`','')
def main(out):
 if (out/'MANUSCRIPT_VERSION.json').exists() and __import__('json').loads((out/'MANUSCRIPT_VERSION.json').read_text()).get('stage')=='E9b':
  from e9b_docx import main as current; return current(out)
 doc=Document();sec=doc.sections[0];sec.page_width=Cm(21);sec.page_height=Cm(29.7)
 sec.top_margin=sec.bottom_margin=Cm(2.1);sec.left_margin=sec.right_margin=Cm(2.2)
 normal=doc.styles['Normal'];setfont(normal);normal.paragraph_format.line_spacing=1.12;normal.paragraph_format.space_after=Pt(7)
 for s,size in [('Title',24),('Subtitle',15),('Heading 1',16),('Heading 2',12),('Heading 3',11),('Caption',9)]:
  setfont(doc.styles[s],size=size);doc.styles[s].font.color.rgb=RGBColor.from_string('17324D')
  doc.styles[s].paragraph_format.keep_with_next=True
 doc.styles['Caption'].paragraph_format.keep_with_next=False
 for name in ['TOC 1','TOC 2']:
  st=doc.styles[name] if name in doc.styles else doc.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
  setfont(st,size=9);st.paragraph_format.space_before=Pt(0);st.paragraph_format.space_after=Pt(0);st.paragraph_format.line_spacing=1.0
 sec.header.paragraphs[0].text='E9a  |  Exploratory working paper  |  14 November 2026';setfont(doc.styles['Header'],size=8)
 fp=sec.footer.paragraphs[0];fp.alignment=WD_ALIGN_PARAGRAPH.CENTER
 fp.add_run('Working paper · ');field(fp,' PAGE ');setfont(doc.styles['Footer'],size=9)
 doc.core_properties.title='Auditing Incremental Predictive Value in Financial Machine Learning'
 doc.core_properties.subject='Exploratory evidence, probability shrinkage and point-in-time data audit'
 doc.core_properties.author='Research team — authorship to be confirmed'
 doc.core_properties.keywords='E9a; H1; H3; reproducibility; PIT; exploratory'
 p=doc.add_paragraph();p.paragraph_format.space_before=Pt(100)
 p=doc.add_paragraph('Auditing Incremental Predictive Value in Financial Machine Learning','Title')
 doc.add_paragraph('Information Redundancy, Probability Shrinkage,\nand Point-in-Time Data Integrity','Subtitle')
 doc.add_paragraph('E9a · Publication Draft & Data Access Decision Package\n14 November 2026 · Version 1.0')
 doc.add_paragraph('Authors and institutional affiliation: to be confirmed by the research team.')
 doc.add_paragraph('Exploratory synthesis of E0–E8a.1\nNo new financial training or confirmation test')
 doc.add_paragraph('https://github.com/yoyocar2333/financial-sequence-benchmark')
 doc.add_page_break();doc.add_paragraph('Contents','Title');field(doc.add_paragraph(),' TOC \\o "1-2" \\h \\z \\u ')
 doc.add_page_break()
 lines=(out/'PAPER_DRAFT.md').read_text().splitlines();i=next(i for i,l in enumerate(lines) if l=='# 繁體中文重點摘要')
 tables=0;images=0;in_references=False
 while i<len(lines):
  line=lines[i].strip()
  if not line:i+=1;continue
  if line.startswith('|'):
   block=[]
   while i<len(lines) and lines[i].strip().startswith('|'):
    row=[clean(x.strip()) for x in lines[i].strip().strip('|').split('|')]
    if not all(re.fullmatch(r':?-+:?',x) for x in row):block.append(row)
    i+=1
   table=doc.add_table(rows=1,cols=len(block[0]));table.style='Light Shading Accent 1';table.alignment=WD_TABLE_ALIGNMENT.CENTER;table.autofit=False
   if len(block[0])==7:widths=[3.2]+[2.2]*6
   elif len(block[0])==6:widths=[2.6,1.5,1.5,1.8,4.1,4.1]
   elif len(block[0])==4 and tables==0:widths=[1.7,4.3,3.4,7.2]
   elif len(block[0])==4 and tables==4:widths=[6.0,1.8,4.0,4.8]
   else:widths=[16.6/len(block[0])]*len(block[0])
   for j,v in enumerate(block[0]):table.rows[0].cells[j].text=v
   trpr=table.rows[0]._tr.get_or_add_trPr();rep=OxmlElement('w:tblHeader');rep.set(qn('w:val'),'true');trpr.append(rep)
   for row in block[1:]:
    cells=table.add_row().cells
    for j,v in enumerate(row):cells[j].text=v
   for row in table.rows:
    pr=row._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
    for j,cell in enumerate(row.cells):
     cell.width=Cm(widths[j]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
     for p in cell.paragraphs:
      p.paragraph_format.space_after=Pt(4);p.paragraph_format.line_spacing=1.0;p.paragraph_format.keep_with_next=True
      for r in p.runs:r.font.size=Pt(8.5)
   tables+=1;doc.add_paragraph();continue
  if line.startswith('!['):
   path=re.search(r'\]\(([^)]+)\)',line).group(1);p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_with_next=True;p.add_run().add_picture(str(out/path),width=Cm(16.2));images+=1;i+=1;continue
  if line.startswith('#'):
   m=re.match(r'^(#+) (.*)',line);level=min(len(m[1]),3);title=m[2]
   if title in ['Abstract','1. Introduction','References']:doc.add_page_break()
   doc.add_heading(title,level=level)
   if title=='References':in_references=True
   i+=1;continue
  style='Caption' if re.match(r'^(Table|Figure) \d+\.',line) else None
  p=doc.add_paragraph(clean(line),style=style)
  if not style:p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
  if in_references:
   p.paragraph_format.space_after=Pt(5);p.paragraph_format.line_spacing=1.0;p.paragraph_format.keep_together=True
   for r in p.runs:r.font.size=Pt(10)
  if line.startswith('`'):
   for r in p.runs:r.font.name='Liberation Mono';r.font.size=Pt(9)
  i+=1
 # Force fields to refresh in compatible editors as well as the PDF renderer.
 st=doc.settings.element;upd=OxmlElement('w:updateFields');upd.set(qn('w:val'),'true');st.append(upd)
 doc.save(out/'PAPER_DRAFT.docx')
 print('DOCX tables',tables,'embedded figures',images)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
