"""Complete, bounded-memory scan of the fixed 23.23 GB FNSPID Nasdaq CSV.

No rows are sent to E4c models. Download is resumable in verified HTTP ranges;
the complete byte SHA256 and EOF are required before claiming a full scan.
"""
import argparse
import collections
import concurrent.futures
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import unicodedata
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

ROOT=Path(__file__).resolve().parents[1]
REV='bf9189c41527198897d1af3e17b1a0095279fc45'
SIZE=23232979597
EXPECTED='1a7a3eb8e6b97ec19f286f2cfca3371542bddb272ab1eb8f36e33ad98fa5c4da'
URL=f'https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/{REV}/Stock_news/nasdaq_exteral_data.csv'

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def dump(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n');t.replace(p)
def digest(s):return hashlib.sha256(s.encode()).hexdigest()

def download(path,work):
    import requests
    path.parent.mkdir(parents=True,exist_ok=True);work.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.stat().st_size!=SIZE:raise RuntimeError('Existing source has unexpected size; refusing overwrite')
        return
    part=path.with_suffix('.csv.partial');state=work/'download_ranges.json';step=32*1024*1024
    old=json.loads(state.read_text()) if state.exists() else {'revision':REV,'size':SIZE,'step':step,'complete':{}}
    assert (old['revision'],old['size'],old['step'])==(REV,SIZE,step)
    if not part.exists() and old['complete']:raise RuntimeError('Range manifest exists but partial source is missing')
    fd=os.open(part,os.O_CREAT|os.O_RDWR,0o644);os.ftruncate(fd,SIZE)
    def get(i):
        begin=i*step;end=min(SIZE,begin+step)-1;err=None
        for attempt in range(4):
            try:
                with requests.get(URL+f'?e4c_full_range={begin}&try={attempt}',headers={'Range':f'bytes={begin}-{end}'},stream=True,timeout=(40,120)) as r:
                    if r.status_code!=206 or r.headers.get('Content-Range')!=f'bytes {begin}-{end}/{SIZE}':
                        raise RuntimeError(f'Range mismatch: {r.status_code} {r.headers.get("Content-Range")}')
                    data=r.content
                if len(data)!=end-begin+1:raise RuntimeError('Short range')
                n=os.pwrite(fd,data,begin)
                if n!=len(data):raise RuntimeError('Short local write')
                return i,{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
            except Exception as e:
                err=e;time.sleep(min(20,2**attempt))
        raise RuntimeError(f'Download block {i} failed: {err}')
    todo=[i for i in range((SIZE+step-1)//step) if str(i) not in old['complete']]
    start=time.monotonic()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for future in concurrent.futures.as_completed([pool.submit(get,i) for i in todo]):
                i,info=future.result();old['complete'][str(i)]=info
                dump(state,old)
                if len(old['complete'])%10==0 or len(old['complete'])==(SIZE+step-1)//step:
                    done=sum(z['bytes'] for z in old['complete'].values())
                    print(now(),'DOWNLOAD',done,'/',SIZE,'elapsed_s',round(time.monotonic()-start),flush=True)
        os.fsync(fd)
    finally:os.close(fd)
    assert sum(x['bytes'] for x in old['complete'].values())==SIZE
    part.replace(path)

class HashReader(io.RawIOBase):
    def __init__(self,f):self.f=f;self.h=hashlib.sha256();self.n=0
    def readable(self):return True
    def readinto(self,b):
        n=self.f.readinto(b)
        if n:self.h.update(memoryview(b)[:n]);self.n+=n
        return n

def norm(s):return ' '.join(unicodedata.normalize('NFKC',s).split()).casefold()
def normurl(s):
    try:
        z=urlsplit(s.strip());query=[(k,v) for k,v in parse_qsl(z.query,keep_blank_values=True) if not k.lower().startswith(('utm_','fbclid','gclid'))]
        return urlunsplit((z.scheme.lower(),z.netloc.lower(),z.path.rstrip('/'),urlencode(sorted(query)),''))
    except ValueError:return s.strip()
def missing(s):return not s.strip() or s.strip().casefold() in ('nan','none','null','n/a')

def scan(path,out):
    work=out/'fnspid_audit';work.mkdir(parents=True,exist_ok=True)
    if (work/'COMPLETE.json').exists():
        m=json.loads((work/'COMPLETE.json').read_text())
        if m.get('full_file_sha256')==EXPECTED and path.stat().st_size==SIZE:
            print('Previously completed scan retained',flush=True);return
    csv.field_size_limit(64*1024*1024)
    dbpath=work/'target_dedup.sqlite'
    if dbpath.exists():raise RuntimeError('Incomplete audit database exists; use a new output directory to preserve it')
    db=sqlite3.connect(dbpath)
    db.execute('CREATE TABLE news (row_no INTEGER PRIMARY KEY,ticker TEXT,year INTEGER,date TEXT,rawdate TEXT,publisher TEXT,body_chars INTEGER,body_words INTEGER,body_missing INTEGER,body_ge1000 INTEGER,url_missing INTEGER,title_missing INTEGER,precision TEXT,midnight INTEGER,raw_hash TEXT,url_hash TEXT,title_date_hash TEXT,body_hash TEXT)')
    db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=NORMAL')
    outputs={};writers={};header=None;total=0;bad=[];tickers=collections.Counter();future=collections.Counter();invalid_dates=collections.Counter();started=time.monotonic()
    for ticker in ('AAPL','TSLA'):
        outputs[ticker]=gzip.open(work/f'{ticker}_all_retained_rows.csv.gz','wt',newline='',encoding='utf8')
    with path.open('rb',buffering=0) as base:
        raw=HashReader(base);text=io.TextIOWrapper(io.BufferedReader(raw,buffer_size=4*1024*1024),encoding='utf-8-sig',errors='strict',newline='')
        reader=csv.reader(text,strict=True);header=next(reader);expected=len(header)
        required=['Date','Stock_symbol','Article','Article_title','Url','Publisher']
        if not all(c in header for c in required):raise RuntimeError('Unexpected CSV schema')
        ix={k:header.index(k) for k in required}
        for t in outputs:
            writers[t]=csv.writer(outputs[t]);writers[t].writerow(['source_csv_row',*header])
        for row in reader:
            total+=1
            if len(row)!=expected:
                if len(bad)<50:bad.append({'csv_row':total,'physical_line':reader.line_num,'columns':len(row)})
                continue
            symbol=row[ix['Stock_symbol']].strip();tickers[symbol]+=1
            if symbol not in ('AAPL','TSLA'):continue
            rd=row[ix['Date']].strip();match=re.match(r'^(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}:\d{2})(?:\.\d+)?(?:\s*(UTC|Z|[+-]\d{2}:?\d{2}))?)?$',rd)
            if not match:
                invalid_dates[symbol]+=1;continue
            ds,clock,zone=match.groups()
            try:dt.date.fromisoformat(ds)
            except ValueError:invalid_dates[symbol]+=1;continue
            # No post-2025 headline/body normalization, export, or modelling.
            if ds>'2025-12-31':future[symbol]+=1;continue
            body=row[ix['Article']];bm=missing(body);bn='' if bm else norm(body)
            title=row[ix['Article_title']];url=row[ix['Url']];publisher=row[ix['Publisher']]
            precision='date_only' if not clock else ('UTC_midnight_unverified' if clock=='00:00:00' and zone else 'naive_midnight_unverified' if clock=='00:00:00' else 'publisher_clock_timezone_unverified' if not zone else 'publisher_intraday_timezone_claimed')
            db.execute('INSERT INTO news VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(total,symbol,int(ds[:4]),ds,rd,publisher,len(body) if not bm else 0,len(bn.split()),int(bm),int(len(body)>=1000 and not bm),int(missing(url)),int(missing(title)),precision,int(clock=='00:00:00'),digest(json.dumps(row,ensure_ascii=False,separators=(',',':'))),None if missing(url) else digest(normurl(url)),digest(norm(title)+'|'+ds),None if bm else digest(bn)))
            writers[symbol].writerow([total,*row])
            if total%10000==0:db.commit()
            if total%100000==0:
                print(now(),'SCAN rows',total,'bytes',raw.n,'targets',db.execute('SELECT ticker,COUNT(*) FROM news GROUP BY ticker').fetchall(),flush=True)
        # csv.reader must reach actual EOF, not an inferred final ticker block.
        text.read();bytecount=raw.n;fullsha=raw.h.hexdigest();physical_lines=reader.line_num
    for f in outputs.values():f.close()
    db.commit()
    if bytecount!=SIZE or fullsha!=EXPECTED:raise RuntimeError(f'Full-file integrity failed: {bytecount} {fullsha}')
    db.execute('CREATE INDEX ticker_year ON news(ticker,year)');db.commit()
    rows=[]
    for ticker in ('AAPL','TSLA'):
        years=[r[0] for r in db.execute('SELECT DISTINCT year FROM news WHERE ticker=? ORDER BY year',(ticker,))]
        for year in sorted(set(years)|set(range(2012,2026))):
            w='ticker=? AND year=?';params=(ticker,year)
            n,b,large,bchars,bwords,urlm,titlem,mn,mx=db.execute(f'SELECT COUNT(*),SUM(1-body_missing),SUM(body_ge1000),AVG(body_chars),AVG(body_words),SUM(url_missing),SUM(title_missing),MIN(date),MAX(date) FROM news WHERE {w}',params).fetchone()
            rec={'ticker':ticker,'year':year,'article_rows':n,'body_nonempty':b or 0,'body_nonempty_fraction':b/n if n else None,'body_ge1000_characters':large or 0,'mean_body_characters_all_rows':bchars,'mean_normalized_body_words_all_rows':bwords,'missing_urls':urlm or 0,'missing_titles':titlem or 0,'date_min':mn,'date_max':mx,'historical_first_seen_verified':0,'historical_text_version_verified':0,'strict_PIT_verified_rows':0}
            for label,column in [('exact_row','raw_hash'),('normalized_url','url_hash'),('normalized_title_date','title_date_hash'),('normalized_body','body_hash')]:
                nonempty,distinct=db.execute(f'SELECT COUNT({column}),COUNT(DISTINCT {column}) FROM news WHERE {w}',params).fetchone()
                rec[label+'_nonmissing']=nonempty;rec[label+'_unique']=distinct;rec[label+'_duplicate_excess']=nonempty-distinct;rec[label+'_duplicate_fraction_nonmissing']=(nonempty-distinct)/nonempty if nonempty else None
            rows.append(rec)
    def save(name,rows):
        with (work/name).open('w',newline='') as f:
            fields=list(dict.fromkeys(k for r in rows for k in r));w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    save('yearly_coverage.csv',rows)
    save('timestamp_precision_by_year.csv',[{'ticker':t,'year':y,'precision':p,'n':n} for t,y,p,n in db.execute('SELECT ticker,year,precision,COUNT(*) FROM news GROUP BY ticker,year,precision ORDER BY ticker,year,precision')])
    save('publisher_by_year.csv',[{'ticker':t,'year':y,'publisher':p,'n':n,'body_nonempty':b} for t,y,p,n,b in db.execute('SELECT ticker,year,publisher,COUNT(*),SUM(1-body_missing) FROM news GROUP BY ticker,year,publisher ORDER BY ticker,year,COUNT(*) DESC')])
    summary=[]
    for t in ('AAPL','TSLA'):
        n,b,lo,hi=db.execute('SELECT COUNT(*),SUM(1-body_missing),MIN(date),MAX(date) FROM news WHERE ticker=?',(t,)).fetchone()
        z={'ticker':t,'rows':n,'body_nonempty':b,'date_min':lo,'date_max':hi,'midnight_rows':db.execute('SELECT COUNT(*) FROM news WHERE ticker=? AND midnight=1',(t,)).fetchone()[0]}
        for c in ('raw_hash','url_hash','title_date_hash','body_hash'):
            nn,nu=db.execute(f'SELECT COUNT({c}),COUNT(DISTINCT {c}) FROM news WHERE ticker=?',(t,)).fetchone();z[c+'_nonmissing']=nn;z[c+'_unique']=nu;z[c+'_duplicate_excess']=nn-nu
        summary.append(z)
    duplicate_examples=[]
    for column in ('url_hash','title_date_hash','body_hash'):
        for t,h,n in db.execute(f'SELECT ticker,{column},COUNT(*) FROM news WHERE {column} IS NOT NULL GROUP BY ticker,{column} HAVING COUNT(*)>1 ORDER BY COUNT(*) DESC LIMIT 30'):
            duplicate_examples.append({'key':column,'ticker':t,'hash':h,'n':n,'source_rows':','.join(str(z[0]) for z in db.execute(f'SELECT row_no FROM news WHERE ticker=? AND {column}=? ORDER BY row_no',(t,h)))})
    save('duplicate_cluster_examples.csv',duplicate_examples)
    db.execute('PRAGMA wal_checkpoint(TRUNCATE)');db.close()
    manifest={'status':'COMPLETE_FULL_FILE_EOF_VERIFIED','completed_utc':now(),'source_path':str(path.resolve()),'source_url':URL,'dataset_revision':REV,'expected_bytes':SIZE,'read_bytes':bytecount,'expected_sha256':EXPECTED,'full_file_sha256':fullsha,'csv_data_records':total,'physical_csv_lines':physical_lines,'columns':header,'column_count_errors_first50':bad,'unique_symbol_values':len(tickers),'all_symbol_counts':dict(tickers),'target_invalid_date_rows':dict(invalid_dates),'target_post2025_metadata_only_skipped':dict(future),'target_summary':summary,'elapsed_s':time.monotonic()-started,'strict_PIT_claim':False,'used_in_E4c_models':False,'complete_file_not_claim_of_complete_publisher_archive':True}
    dump(work/'COMPLETE.json',manifest)
    if bad:raise RuntimeError('Full EOF reached but malformed record columns found; see audit')
    print(json.dumps({k:v for k,v in manifest.items() if k!='all_symbol_counts'},indent=2),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--source',type=Path,default=ROOT/'data/fnspid_bf9189c41527198897d1af3e17b1a0095279fc45/nasdaq_exteral_data.csv');p.add_argument('--download',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    if a.download:download(a.source,a.out/'fnspid_audit')
    scan(a.source,a.out)
if __name__=='__main__':main()
