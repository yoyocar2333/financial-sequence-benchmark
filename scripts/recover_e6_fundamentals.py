"""Recover public issuer-vintage financial documents; never fetch 2026 reports.

SEC HTTP failures are evidence, not permission to bypass a block. The fallback
is original issuer releases with date-only, conservatively lagged availability.
"""
import argparse, datetime as dt, hashlib, json, re, subprocess, time
from pathlib import Path
from urllib.parse import urljoin, urlparse
import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/e6_20261106'
UA='E6AcademicResearch/1.0 (https://github.com/yoyocar2333/financial-sequence-benchmark)'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n')

class Fetcher:
    def __init__(self,out):self.out=out;self.audit=[];self.s=requests.Session();self.s.headers['User-Agent']=UA
    def get(self,url,key,kind='html'):
        if re.search(r'(?:2026|2027)',url):raise ValueError('Holdout URL forbidden '+url)
        p=self.out/'raw'/f'{key}.{kind}'
        if p.exists():return p
        time.sleep(.55)
        r=self.s.get(url,timeout=60)
        record={'url':url,'retrieved_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'http_status':r.status_code,'bytes':len(r.content),'response_sha256':hashlib.sha256(r.content).hexdigest(),'path':str(p.relative_to(self.out)) if r.status_code==200 else None,'last_modified':r.headers.get('Last-Modified'),'etag':r.headers.get('ETag')}
        with (self.out/'audits/http.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
        if r.status_code!=200:print('UNAVAILABLE',r.status_code,url,flush=True);return None
        p.write_bytes(r.content)
        if kind=='pdf':
            if not r.content.startswith(b'%PDF'):raise ValueError('Not PDF '+url)
            subprocess.run(['pdftotext','-layout',str(p),str(p.with_suffix('.txt'))],check=True)
        return p

def apple(out,get):
    # Public issuer-site index has no numeric 2026 facts. Keep only <=2025 rows.
    idx=Path('/tmp/e6-apple-reports-all.json')
    if not idx.exists():raise FileNotFoundError('Discover issuer public financial-report index first; see README_E6.md')
    items=[x for x in json.loads(idx.read_text())['GetFinancialReportListResult'] if x['ReportYear']<=2025 and x['ReportSubType'] in ['First Quarter','Second Quarter','Third Quarter','Fourth Quarter']]
    dump(out/'raw/apple_report_directory_pre2026.json',items)
    urls={}
    for x in items:
        docs={z['DocumentCategory']:z['DocumentPath'].strip() for z in x['Documents']}
        q=['First Quarter','Second Quarter','Third Quarter','Fourth Quarter'].index(x['ReportSubType'])+1
        urls[docs['news']]={'fiscal_year':x['ReportYear'],'quarter':q,'statement_url':docs.get('statement'),'filing_url':docs.get('tenq',docs.get('tenk')),'directory_revision':x['RevisionNumber'],'directory_reportdate_not_release':x['ReportDate']}
    # Scan only historical archive pages, not the unfiltered current homepage.
    for year in range(2011,2016):
        page=1
        while True:
            u=f'https://www.apple.com/newsroom/archive/{year}/?page={page}'
            p=get(u,f'apple_archive_{year}_{page}')
            if not p:break
            s=BeautifulSoup(p.read_text(),'html.parser')
            for a in s.select('a[href]'):
                link=urljoin('https://www.apple.com',a['href'])
                if re.search(fr'/newsroom/{year}/\d\d/.*Apple-Reports-',link,re.I):urls.setdefault(link,{})
            nums=[int(x) for x in re.findall(r'(?:of|共)\s*(\d+)',s.get_text(' ',strip=True))]
            total=max(nums) if nums else page
            print('APPLE ARCHIVE',year,page,total,flush=True)
            if page>=total or page>=20:break
            page+=1
    rows=[]
    for i,(u,meta) in enumerate(sorted(urls.items())):
        p=get(u,f'apple_release_{i:03d}')
        if not p:continue
        s=BeautifulSoup(p.read_text(),'html.parser');article=s.select_one('article') or s
        text=article.get_text(' ',strip=True)
        (p.with_suffix('.txt')).write_text(text)
        date=None
        for z in s.select('meta'):
            if z.get('property') in ['article:published_time','og:published_time'] or z.get('name') in ['date','pubdate','Date']:
                date=z.get('content','')[:10]
        date_node=s.select_one('time')
        if not date and date_node:date=date_node.get('datetime') or date_node.get_text(strip=True)
        if not date:
            m=re.search(r'([A-Z][a-z]+\s+\d{1,2},\s+20\d{2})',text)
            if m:date=str(pd.Timestamp(m.group(1)).date())
        if not date:raise ValueError('No release date '+u)
        date=str(pd.Timestamp(date).date())
        if date>'2025-12-31':raise ValueError('Holdout release')
        if not meta.get('quarter'):
            m=re.search(r'fiscal (20\d\d) (first|second|third|fourth) quarter',text,re.I)
            if not m:print('Not quarterly release',u,flush=True);continue
            meta.update(fiscal_year=int(m.group(1)),quarter=['first','second','third','fourth'].index(m.group(2).lower())+1)
        for a in article.select('a[href]'):
            au=urljoin(u,a['href'])
            if '.pdf' in au.lower() and any(k in (a.get_text(' ',strip=True)+' '+au).lower() for k in ['financial','data summary','datasum','fin_stat','earnings','consolidated']):
                if not meta.get('statement_url') or 'financial' in (a.get_text(' ',strip=True)+' '+au).lower():meta['statement_url']=au
        key=f"AAPL_FY{meta['fiscal_year']}_Q{meta['quarter']}"
        pdf=get(meta['statement_url'],key,'pdf') if meta.get('statement_url') else None
        filing=get(meta['filing_url'],key+'_filing','pdf') if meta.get('filing_url','').lower().endswith('.pdf') else None
        rows.append({'ticker':'AAPL','release_date':date,'release_url':u,'release_path':str(p.relative_to(out)),'document_path':str(pdf.relative_to(out)) if pdf else None,'filing_path':str(filing.relative_to(out)) if filing else None,**meta})
        print('APPLE',key,date,bool(pdf),flush=True)
    return rows

def tesla(out,get):
    # An independently retrieved copy is discovery ONLY. Numerical observations
    # must come from the official Tesla asset URLs, verified against PDF dates.
    source=Path('/tmp/e6-discovery-tesla.html')
    if not source.exists():raise FileNotFoundError('Tesla link-discovery page absent')
    soup=BeautifulSoup(source.read_text(),'html.parser');year=None;rows=[]
    for tr in soup.select('tr'):
        yn=tr.select_one('.ir-year')
        if yn:year=int(yn.get_text(strip=True))
        if not year or not 2011<=year<=2025:continue
        cells=tr.find_all('td',recursive=False)
        if len(cells)<4 or not re.fullmatch('Q[1-4]',cells[0].get_text(strip=True)):continue
        q=int(cells[0].get_text(strip=True)[1]);date=str(pd.Timestamp(cells[1].get_text(strip=True)).date())
        if date>'2025-12-31':continue
        asset=tr.select_one('a.ir-pdf')
        if not asset:continue
        u=asset['href']
        if urlparse(u).hostname not in ['digitalassets.tesla.com','assets-ir.tesla.com','www.tesla.com']:raise ValueError('Nonissuer source '+u)
        key=f'TSLA_FY{year}_Q{q}';p=get(u,key,'pdf')
        if not p:continue
        links=[a['href'] for a in tr.select('a[href]') if 'www.sec.gov/' in a['href']]
        rows.append({'ticker':'TSLA','fiscal_year':year,'quarter':q,'release_date_directory':date,'release_date':date,'document_url':u,'document_path':str(p.relative_to(out)),'filing_url':links[0] if links else None,'date_evidence':'issuer directory cross-check pending PDF; discovery copy not source of numerical facts'})
        print('TESLA',key,date,flush=True)
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=OUT);a=ap.parse_args();out=a.out
    for d in ['raw','audits','tables','inputs','code','logs','predictions','figures']: (out/d).mkdir(parents=True,exist_ok=True)
    get=Fetcher(out).get
    rows=apple(out,get)+tesla(out,get)
    pd.DataFrame(rows).to_csv(out/'tables/document_inventory.csv',index=False)
    dump(out/'audits/document_hashes.json',{str(p.relative_to(out)):sha(p) for p in (out/'raw').iterdir() if p.is_file()})
    print('RECOVERED',len(rows),flush=True)

if __name__=='__main__':main()
