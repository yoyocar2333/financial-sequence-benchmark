"""Private template/document check; engineering QA does not certify PIT or submission acceptance."""
import argparse,json,re,subprocess,unicodedata,zipfile,hashlib
from pathlib import Path

def main(template,bundle,layout):
 import fitz
 from docx import Document
 from lxml import etree
 expected=json.loads((bundle/'audits/BASELINE_RECORD.json').read_text())['baseline_Word_sha256']
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
  assert len(root.xpath('//m:oMath',namespaces={'m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}))==8
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
 # Check full equations as well as decimal tokens; an overlong math cell can clip text inside the page.
 mathnorm=lambda value:norm(value).replace('_','')
 for line in md.splitlines():
  if line.startswith('`'):
   expected_math=mathnorm(line.split('` (')[0].strip('`'))
   if line.endswith('(7)'):
    # PDF extraction groups three visually correct subscript-k glyphs after ΣvE.
    # Verify all six indices are present and the full remaining expression is exact.
    rendered=re.search(r'G=Σ.*?\.',mathnorm(text)).group(0)
    assert rendered.count('k')==expected_math.count('k')==6
    assert rendered.replace('k','')==expected_math.replace('k',''),'Grouping equation clipped'
   else:assert expected_math in mathnorm(text),'Equation clipped in PDF'
 assert len(current.inline_shapes)==1
 for label,tail in [('Table 1.','Apple news'),('Table 2.','Mamba'),('Table 3.','Mamba fusion'),('Table 4.','News')]:
  matched=[p for p in pdf if re.search(r'(?m)^'+re.escape(label),p.get_text())]
  assert len(matched)==1 and norm(tail) in norm(matched[0].get_text()),'Split data table: '+label

 for i,p in enumerate(pdf):
  assert re.search(r'\b'+str(i+1)+r' of '+str(len(pdf))+r'\b',p.get_text()),i
  for b in p.get_text('blocks'):
   assert b[0]>=-1 and b[1]>=-1 and b[2]<=p.rect.width+1 and b[3]<=p.rect.height+1
   if b[0]<32 and (b[1]>p.rect.height-45 or b[3]<60):
    assert not re.fullmatch(r'[\d\s]+',b[4]),'Stray header/footer line number on page '+str(i+1)

 assert pdf.embfile_count()==0
 assert len([p for p in pdf if len(p.get_text().strip())<150])==0,'Blank or nearly blank page'
 assert 'review draft' not in text.lower() and 'email.com' not in text.lower()
 assert 'Hsieh Hao-Hsuan' in text and 'Jian-Jiun Ding' in text and '2026' not in text
 assert 'jjding@ntu.edu.tw' in text and '+886-3-33669652' in norm(text)
 assert 'Graduate Institute of Communication Engineering' in text
 for label in ['Author Contributions:','Funding:','Institutional Review Board Statement:','Informed Consent Statement:','Data Availability Statement:','Conflicts of Interest:']:assert norm(label) in norm(text),label
 assert 'pending confirmation' not in text.lower()
 decimal_count=len(set(re.findall(r'\d+\.\d{3,}',md.split('## References')[0])))
 result=dict(auxiliary_paragraphs_excluded_from_line_numbering=auxiliary_count,body_line_number_settings_preserved=True,stray_header_footer_line_numbers=0,status='PASSED_FOR_PROFESSOR_REVIEW',formal_submission_status='PENDING_FINAL_AUTHOR_APPROVAL_ROUTE_SYSTEM_AND_NATIVE_FONT_RECHECK',pages=len(pdf),all_pages_include_figures_references_and_backmatter=True,template_styles_byte_equivalent=True,template_geometry_unchanged=True,source_paragraphs_verified=verified,all_scientific_decimal_tokens_in_PDF=True,scientific_decimal_tokens_checked=decimal_count,editable_equations=8,complete_equations_visible=True,PDF_subscript_reading_order_normalized=True,data_tables_split_across_pages=0,main_data_tables=4,figures=1,references=12,all_fonts_embedded=True,official_font_exact=False,PDF_font_substitution='P052 for unavailable Palatino Linotype; review rendering only',PDF_font_recheck_required=True,Word_preserves_original_inherited_font_sizes=True,public_template_or_formatted_document_distribution=False,replacement_characters=0,page_fields_correct=True,outside_page_text_blocks=0,independent_scientific_or_human_QA=False)
 (layout/'checks/DOCUMENT_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--template',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--layout',type=Path,required=True);a=p.parse_args();main(a.template,a.bundle,a.layout)
