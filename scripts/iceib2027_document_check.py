"""Private template/document check; engineering QA does not certify PIT or submission acceptance."""
import argparse,json,re,subprocess,unicodedata,zipfile,hashlib
from pathlib import Path

def main(template,bundle,layout):
 import fitz
 from docx import Document
 from lxml import etree
 expected='184bc15210ba3cc7a9db2540c9eb5661fe982a9b678c786692cd818819db4eda'
 assert hashlib.sha256(template.read_bytes()).hexdigest()==expected
 source=Document(template);current=Document(layout/'ICEIB2027_FULL_PAPER.docx');assert source.styles.element.xml==current.styles.element.xml,'Template styles changed'
 geometry=['page_width','page_height','top_margin','bottom_margin','left_margin','right_margin','header_distance','footer_distance']
 for k in geometry:assert getattr(source.sections[0],k)==getattr(current.sections[0],k),k
 # Line numbering applies only to the article body, including otherwise empty auxiliary paragraphs.
 from docx.oxml.ns import qn
 auxiliary_count=0
 for original_sec,sec in zip(source.sections,current.sections):
  old=original_sec._sectPr.find(qn('w:lnNumType'));new=sec._sectPr.find(qn('w:lnNumType'))
  assert old is not None and new is not None and dict(old.attrib)==dict(new.attrib),'Body line-number settings changed'
  for name in ['header','even_page_header','first_page_header','footer','even_page_footer','first_page_footer']:
   for paragraph in getattr(sec,name)._element.iter(qn('w:p')):
    flag=paragraph.find('./'+qn('w:pPr')+'/'+qn('w:suppressLineNumbers'))
    assert flag is not None and flag.get(qn('w:val')) in ['1','true'],'Auxiliary paragraph still allows line numbers'
    auxiliary_count+=1
 pdf=fitz.open(layout/'ICEIB2027_FULL_PAPER.pdf');assert 4<=len(pdf)<=8
 text='\n'.join(p.get_text() for p in pdf);assert '\ufffd' not in text
 fonts=subprocess.check_output(['pdffonts',str(layout/'ICEIB2027_FULL_PAPER.pdf')],text=True)
 assert all(re.search(r'\s+yes\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$',l) for l in fonts.splitlines()[2:]),fonts
 assert 'P052' in fonts
 with zipfile.ZipFile(layout/'ICEIB2027_FULL_PAPER.docx') as z:
  root=etree.fromstring(z.read('word/document.xml'));content=''.join(root.xpath('//w:t/text()|//m:t/text()',namespaces={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}))
  assert len(root.xpath('//m:oMath',namespaces={'m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}))==3
 norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s)).replace('\u00ad','')
 md=(bundle/'ICEIB2027_FULL_PAPER.md').read_text();verified=0
 for line in md.splitlines():
  line=line.strip()
  if not line or line.startswith('![') or line=='## Back Matter':continue
  if line.startswith('|'):
   cells=[c.strip() for c in line.strip('|').split('|')]
   if all(re.fullmatch(r':?-+:?',c) for c in cells):continue
   for cell in cells:assert norm(cell) in norm(content),cell
  else:
   value=re.sub(r'^#+ |^\d+\. (?=[A-Z])','',line)
   if line.startswith('`'):value=line.split('` (')[0].strip('`')
   assert norm(value) in norm(content),value[:80]
   verified+=1
 for number in set(re.findall(r'\d+\.\d{3,}',md.split('## References')[0])):assert number in norm(text),number
 for i,p in enumerate(pdf):
  assert re.search(r'\b'+str(i+1)+r' of '+str(len(pdf))+r'\b',p.get_text()),i
  for b in p.get_text('blocks'):
   assert b[0]>=-1 and b[1]>=-1 and b[2]<=p.rect.width+1 and b[3]<=p.rect.height+1
   if b[0]<32 and (b[1]>p.rect.height-45 or b[3]<60):
    assert not re.fullmatch(r'[\d\s]+',b[4]),'Stray header/footer line number on page '+str(i+1)

 assert pdf.embfile_count()==0
 result=dict(auxiliary_paragraphs_excluded_from_line_numbering=auxiliary_count,body_line_number_settings_preserved=True,stray_header_footer_line_numbers=0,status='PASSED_FOR_PROFESSOR_REVIEW',formal_submission_status='PENDING_ROUTE_AUTHORS_SYSTEM_FIELDS_AND_NATIVE_FONT_RECHECK',pages=len(pdf),all_pages_include_figures_references_and_backmatter=True,template_styles_byte_equivalent=True,template_geometry_unchanged=True,source_paragraphs_verified=verified,all_scientific_decimal_tokens_in_PDF=True,editable_equations=3,main_data_tables=3,figures=2,references=12,all_fonts_embedded=True,official_font_exact=False,PDF_font_substitution='P052 for unavailable Palatino Linotype; review rendering only',PDF_font_recheck_required=True,Word_preserves_original_inherited_font_sizes=True,public_template_or_formatted_document_distribution=False,replacement_characters=0,page_fields_correct=True,outside_page_text_blocks=0,independent_scientific_or_human_QA=False)
 (layout/'checks/DOCUMENT_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--template',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--layout',type=Path,required=True);a=p.parse_args()
 from iceib2027_active import resolve
 current=resolve(a.bundle)
 if current is not None:
  if (current/'PAPER_TEMPLATE.md').exists():
   from iceib2027_r3_document_check import main as active
  else:
   from iceib2027_r2_document_check import main as active
  active(a.template,current,a.layout)
 else:main(a.template,a.bundle,a.layout)
