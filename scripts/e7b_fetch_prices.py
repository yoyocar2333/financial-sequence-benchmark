"""Bounded historical-price accessibility audit, never an as-traded certification.

Yahoo envelopes can contain unsolicited current quotes. Original responses are
quarantined locally; only explicit historical arrays and identity metadata enter
sanitized inputs. No raw envelope or current quote is published or modelled.
"""
import datetime as dt,hashlib,json,time
from pathlib import Path
import requests
from e7b_setup import OUT,dump
MAPPING={'CHK_legacy':'CHK','DELL_legacy':'DELL','SHLD_legacy':'SHLDQ','YHOO_legacy':'YHOO'}

def main():
 rows=[];(OUT/'raw/quarantine/price_responses').mkdir(parents=True,exist_ok=True)
 cohort=list(__import__('csv').DictReader((OUT/'cohort_locked.csv').open()))
 for item in cohort:
  ident=item['prototype_id'];symbol=MAPPING.get(ident,ident)
  dest=OUT/'raw/prices'/f'{ident}_historical_sanitized.json'
  if dest.exists():raise FileExistsError('Preserve response '+str(dest))
  u=f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1=1325376000&period2=1672531200&interval=1d&events=div%2Csplits&includeAdjustedClose=true'
  row={'prototype_id':ident,'queried_symbol':symbol,'url':u,'retrieved_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'security_link_verified':False,'as_traded_verified':False}
  try:
   # Existing probe is reused, not downloaded again.
   probe=OUT/'raw/prices/yahoo_AAPL_2012_2022_response.bin'
   if ident=='AAPL' and probe.exists():
    payload=probe.read_bytes();old=json.loads((OUT/'audits/yahoo_price_accessibility_probe.json').read_text());row.update(http_status=200,reused_prior_probe=True,copied_to_bundle_at_utc=row['retrieved_at_utc'],retrieved_at_utc=old['retrieved_at_utc'])
   else:
    time.sleep(1.05);r=requests.get(u,headers={'User-Agent':'FinancialSequenceBenchmark academic historical-data audit'},timeout=30);payload=r.content;row['http_status']=r.status_code
   raw=OUT/'raw/quarantine/price_responses'/f'{ident}.bin';raw.write_bytes(payload)
   row.update(bytes=len(payload),response_sha256=hashlib.sha256(payload).hexdigest(),quarantined_response_path=str(raw.relative_to(OUT)),original_not_in_public_release=True)
   if row['http_status']==200:
    j=json.loads(payload);results=j.get('chart',{}).get('result')
    if not results:raise ValueError('No historical result: '+str(j.get('chart',{}).get('error')))
    x=results[0];times=x.get('timestamp',[])
    if any(not (1325376000<=v<1672531200) for v in times):raise ValueError('Unexpected out-of-bound historical timestamps; refuse entire input')
    keep=['symbol','currency','exchangeName','instrumentType','timezone','exchangeTimezoneName','firstTradeDate','shortName']
    events={}
    for kind,vals in x.get('events',{}).items():events[kind]={k:v for k,v in vals.items() if 1325376000<=int(v.get('date',k))<1672531200}
    safe={'prototype_id':ident,'source':'Yahoo chart historical-only sanitized response','identity_metadata_is_current_not_historical':True,'identity_metadata':{k:v for k,v in x.get('meta',{}).items() if k in keep},'timestamp':times,'indicators':x.get('indicators',{}),'events':events,'unsolicited_current_quote_fields_excluded':True,'not_as_traded_or_PIT_certified':True}
    dump(dest,safe);row.update(historical_rows=len(times),first_date=dt.datetime.fromtimestamp(min(times),dt.timezone.utc).date().isoformat() if times else None,last_date=dt.datetime.fromtimestamp(max(times),dt.timezone.utc).date().isoformat() if times else None,sanitized_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),sanitized_path=str(dest.relative_to(OUT)),split_events=len(events.get('splits',{})),dividend_events=len(events.get('dividends',{})),status='HISTORICAL_ARRAY_ACQUIRED_QUARANTINED_UNVERIFIED_IDENTITY_AND_ADJUSTMENT')
   else:row['status']='HTTP_FAILURE_NO_RETRY'
  except (requests.RequestException,ValueError,KeyError) as e:row.update(status='UNAVAILABLE_OR_INVALID',error=str(e))
  rows.append(row);dump(OUT/'audits/price_fetch_manifest.json',rows)
  print(ident,row['status'],row.get('historical_rows',0),flush=True)
 print('PRICE ACCESSIBILITY AUDIT FINISHED',len(rows),flush=True)
if __name__=='__main__':main()
