"""Read public conference/publisher format metadata only; never submits forms."""
import argparse,urllib.request,hashlib,json,base64
from pathlib import Path
from lxml import html

def main(out):
 repo=Path(__file__).resolve().parents[1]
 if (repo/'.git').exists() and (repo==out.resolve() or repo in out.resolve().parents):raise ValueError('Website HTML/templates require private output outside public Git')
 out.mkdir(parents=True,exist_ok=True);(out/'private_template').mkdir(exist_ok=True);records=[]
 for url,name in [('https://www.iceib.asia/','conference'),('https://www.mdpi.com/journal/engproc/instructions','publisher')]:
  try:
   raw=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Research manuscript format verification'}),timeout=20).read();(out/'private_template'/(name+'.html')).write_bytes(raw);tree=html.fromstring(raw)
   links=[dict(text=' '.join(a.text_content().split()),href=a.get('href')) for a in tree.xpath('//a[@href]') if any(w in a.text_content().lower() for w in ['submit','submission','template'])]

   for item in links:
    if item.get('href','').startswith('data:'):
     template_bytes=base64.b64decode(item['href'].split(',',1)[1]);(out/'private_template'/'conference_official_template.docx').write_bytes(template_bytes);item['href']='EMBEDDED_DOCUMENT_URI_OMITTED';item['decoded_template_sha256']=hashlib.sha256(template_bytes).hexdigest()
   records.append(dict(url=url,checked_date='2026-11-23',status='FETCHED_PUBLIC_METADATA',sha256=hashlib.sha256(raw).hexdigest(),links=links))
  except Exception as e:records.append(dict(url=url,checked_date='2026-11-23',status='NETWORK_CHECK_FAILED',error=str(e)))
 (out/'official_source_checks.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n');print(json.dumps(records,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
