"""Primary-source citation additions; metadata lookup only, no financial data."""
import argparse,json,urllib.request,urllib.parse,hashlib,datetime as dt
from pathlib import Path
CANDIDATES=[
 ('R33','Combining probability forecasts','10.1111/j.1467-9868.2009.00726.x'),
 ('R34','The forecast combination puzzle: A simple theoretical explanation','10.1016/j.ijforecast.2015.12.005'),
 ('R35','Some Remarks on the Reliability of Categorical Probability Forecasts','10.1175/2008MWR2329.1'),
 ('R36','Stable reliability diagrams for probabilistic classifiers','10.1073/pnas.2016191118'),
 ('R37','Time Machine GPT','10.18653/v1/2024.findings-naacl.208'),
 ('R39','Stock Movement Prediction from Tweets and Historical Prices','10.18653/v1/P18-1183')]

def lookup(out):
 records=[]
 for id,title,doi in CANDIDATES:
  url='https://api.crossref.org/works/'+urllib.parse.quote(doi,safe='');req=urllib.request.Request(url,headers={'User-Agent':'Academic citation metadata verification E9b; no content collection'})
  try:
   with urllib.request.urlopen(req,timeout=30) as f:raw=f.read()
   m=json.loads(raw)['message'];row=dict(id=id,expected_title=title,doi=doi,title=m.get('title',[''])[0],authors=m.get('author',[]),venue=m.get('container-title',[''])[0],volume=m.get('volume',''),issue=m.get('issue',''),pages=m.get('page',''),dates={k:m[k].get('date-parts') for k in ['published','published-print','published-online','issued'] if k in m},status='DOI_METADATA_FOUND_NEEDS_PRIMARY_TITLE_MATCH',checked_date='2026-11-15',metadata_url=url,response_sha256=hashlib.sha256(raw).hexdigest(),original_HTTP_body_retained=False)
  except Exception as e:row=dict(id=id,expected_title=title,doi=doi,status='LOOKUP_FAILED',error=str(e),checked_date='2026-11-15')
  records.append(row);print(id,row['status'],row.get('title'),flush=True)
 (out/'literature/new_doi_records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);lookup(p.parse_args().out)
