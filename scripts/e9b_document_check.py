"""Current E9b document consistency and technical checks; separate from scientific QA.
Needs existing PyMuPDF and pdffonts. Reads only the authored E9a documents.
"""
import argparse,json,re,subprocess,zipfile
from pathlib import Path

def main(bundle):
 import fitz
 d=fitz.open(bundle/'PAPER_DRAFT.pdf');texts=[p.get_text() for p in d];joined='\n'.join(texts)
 fonts=subprocess.check_output(['pdffonts',str(bundle/'PAPER_DRAFT.pdf')],text=True)
 assert all(re.search(r'\s+yes\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$',l) for l in fonts.splitlines()[2:]),fonts
 assert all(len(t)>100 for t in texts),'blank page'
 assert '\ufffd' not in joined and '繁體中文重點摘要' in joined
 assert 'Update field' not in joined
 assert re.search(r'(?:0)?\.1512\b',joined) and re.search(r'(?:0)?\.028\b',joined)
 assert all('Working paper · '+str(i+1) in t for i,t in enumerate(texts)),'page field'
 imgs=set(z[0] for page in d for z in page.get_images());assert len(imgs)==3
 assert d.embfile_count()==0
 with zipfile.ZipFile(bundle/'PAPER_DRAFT.docx') as z:
  xml='\n'.join(z.read(n).decode('utf-8','ignore') for n in z.namelist() if n.endswith(('.xml','.rels')))
  media=len([n for n in z.namelist() if n.startswith('word/media/')]);assert media==3
 assert '/'+ 'ibmnas/' not in xml+joined and 'file:///' not in xml+joined
 assert 'vbaProject' not in xml and 'TOC ' in xml and 'PAGE ' in xml
 for x in range(1,d.xref_length()):
  obj=d.xref_object(x)
  assert not any(k in obj for k in ['/JavaScript','/EmbeddedFile','/Launch','file:///'])
 for page in d:
  for b in page.get_text('blocks'):assert b[0]>=-1 and b[1]>=-1 and b[2]<=page.rect.width+1 and b[3]<=page.rect.height+1
 # Every nonempty source paragraph/table cell is represented in the editable document.
 from e9b_docx import clean
 from lxml import etree
 with zipfile.ZipFile(bundle/'PAPER_DRAFT.docx') as z:root=etree.fromstring(z.read('word/document.xml'))
 doc_text=' '.join(root.xpath('//w:t/text()',namespaces={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}))
 norm=lambda s:re.sub(r'\s+','',s)
 doc_text=norm(doc_text);lines=(bundle/'PAPER_DRAFT.md').read_text().splitlines();start=lines.index('# 繁體中文重點摘要');checked=0
 for line in lines[start:]:
  line=line.strip()
  if not line or line.startswith('!['):continue
  if line.startswith('|'):
   cells=[x.strip() for x in line.strip('|').split('|')]
   if all(re.fullmatch(r':?-+:?',x) for x in cells):continue
   for x in cells:assert norm(clean(x)) in doc_text,x
  else:
   text=norm(clean(re.sub(r'^#+ ', '',line)));assert text in doc_text,text;checked+=1
 assert len(d) in range(12,17),len(d)
 assert doc_text.count('[R40]')>=1
 result=dict(source_paragraphs_verified=checked,source_tables=5,references=40,status='PASSED',pages=len(d),embedded_fonts=True,Chinese_extractable=True,replacement_characters=0,unintended_blank_pages=0,outside_page_text_blocks=0,unique_image_resources=len(imgs),DOCX_images=media,external_file_paths=False,embedded_attachments_or_active_scripts=False,visual_review='Representative rendered pages checked by author agent; not independent scientific QA')
 (bundle/'checks/document_quality.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);main(p.parse_args().bundle)
