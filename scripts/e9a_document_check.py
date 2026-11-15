"""Technical document checks; not independent scientific or human-data QA.
Needs existing PyMuPDF and pdffonts. Reads only the authored E9a documents.
"""
import argparse,json,re,subprocess,zipfile
from pathlib import Path

def main(bundle):
 if (bundle/'MANUSCRIPT_VERSION.json').exists() and __import__('json').loads((bundle/'MANUSCRIPT_VERSION.json').read_text()).get('stage')=='E9b':
  from e9b_document_check import main as current; return current(bundle)
 import fitz
 d=fitz.open(bundle/'PAPER_DRAFT.pdf');texts=[p.get_text() for p in d];joined='\n'.join(texts)
 fonts=subprocess.check_output(['pdffonts',str(bundle/'PAPER_DRAFT.pdf')],text=True)
 assert all(re.search(r'\s+yes\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$',l) for l in fonts.splitlines()[2:]),fonts
 assert all(len(t)>100 for t in texts),'blank page'
 assert '\ufffd' not in joined and '繁體中文重點摘要' in joined
 assert 'Update field' not in joined
 assert '0.1512' in joined and '0.028' in joined
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
 result=dict(status='PASSED',pages=len(d),embedded_fonts=True,Chinese_extractable=True,replacement_characters=0,unintended_blank_pages=0,outside_page_text_blocks=0,unique_image_resources=len(imgs),DOCX_images=media,external_file_paths=False,embedded_attachments_or_active_scripts=False,visual_review='Representative rendered pages checked by author agent; not independent scientific QA')
 (bundle/'checks/document_quality.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);main(p.parse_args().bundle)
