"""E4b provenance utilities. New retrospective text never receives PIT certification."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import re
import time
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/e4b_20261026'
PRIOR=ROOT/'outputs/e4a_20261026_phase7a'
VENDOR=ROOT/'vendor/stockllm-pit-news/fdf6103ff22035a6cd9e6a7e946430f0c2b2e33d'
FINBERT_REV='0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031'


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def now(): return dt.datetime.now(dt.timezone.utc).isoformat()


def dump(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False,default=str)+'\n');tmp.replace(p)


def fetch(url,out=OUT):
    # Only deliberately selected historical news URLs are accepted.
    if 'apple.com/newsroom/' in url:
        if not re.search(r'/newsroom/(?:archive/)?(?:201[2-9]|202[0-5])/',url):
            raise ValueError('Historical-year news URL required: '+url)
    key=hashlib.sha256(url.encode()).hexdigest();body=out/'raw/http'/(key+'.html');meta=body.with_suffix('.json')
    body.parent.mkdir(parents=True,exist_ok=True)
    if body.exists() and meta.exists():
        z=json.loads(meta.read_text())
        if sha(body)!=z['sha256']:raise RuntimeError('HTTP cache changed')
        return body.read_bytes(),z
    for attempt in range(3):
        try:
            r=requests.get(url,headers={'User-Agent':'University financial-news research; historical2023-2025 only'},timeout=35)
            if r.status_code==429:
                time.sleep(min(30,float(r.headers.get('Retry-After',10))));continue
            r.raise_for_status();payload=r.content
            if len(payload)>8_000_000:raise ValueError('Unexpectedly large page')
            body.write_bytes(payload);z={'requested_url':url,'response_url':r.url,'retrieved_utc':now(),'status':r.status_code,
                'sha256':sha(body),'bytes':len(payload),'http_last_modified':r.headers.get('Last-Modified'),'http_etag':r.headers.get('ETag'),
                'historical_text_revision_verified':False}
            dump(meta,z);time.sleep(.3);return payload,z
        except (requests.RequestException,ValueError):
            if attempt==2:raise
            time.sleep(2**attempt)
    raise RuntimeError('Rate limit not resolved')
