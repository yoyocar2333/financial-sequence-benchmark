"""Supplement full-scan metadata with target-body quality and duplicate audits.

This never supplies features to E4c. Heuristics are diagnostics, not labels of
validated completeness. Reads only the already date-guarded AAPL/TSLA subset.
"""
import argparse
import collections
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
from e4c_protocol import OUT,sha,dump

def run(out):
    work=out/'fnspid_audit';m=json.loads((work/'COMPLETE.json').read_text());assert m['full_file_sha256']==m['expected_sha256'] and m['read_bytes']==m['expected_bytes']
    csv.field_size_limit(64*1024*1024);rows=[];datecounts=collections.Counter();quality=collections.Counter();target_totals={}
    for ticker in ('AAPL','TSLA'):
        n=0
        with gzip.open(work/f'{ticker}_all_retained_rows.csv.gz','rt',newline='') as f:
            for r in csv.DictReader(f):
                assert r['Date'][:10]<='2025-12-31';n+=1;year=int(r['Date'][:4]);body=r['Article'].strip();title=r['Article_title'].strip();lower=body[:1500].lower();datecounts[ticker,year,r['Date'][:10]]+=1
                flags={'rows':True,'body_nonempty':bool(body) and body.lower() not in ('nan','none','null','n/a'),
                  'body_under500_chars':len(body)<500,'body_under100_words':len(body.split())<100,'body_equals_title':body.casefold()==title.casefold(),
                  'possible_error_page':bool(re.match(r'\s*(?:access denied|403 forbidden|404 not found|page not found|just a moment|enable javascript|please enable javascript|subscribe to read)',lower)),
                  'possible_html_body':bool(re.search(r'<(?:html|body|script|div)\b',lower)),
                  'nonascii_characters':any(ord(c)>127 for c in body),'has_author':bool(r.get('Author','').strip())}
                for flag,b in flags.items():quality[ticker,year,flag]+=int(b)
        target_totals[ticker]=n
    for (t,y,flag),n in sorted(quality.items()):rows.append({'ticker':t,'year':y,'diagnostic':flag,'count':n,'denominator_rows':quality[t,y,'rows'],'fraction':n/quality[t,y,'rows']})
    pdays=[]
    for t,y in sorted(set((t,y) for t,y,_ in datecounts)):
        values=[v for (tt,yy,d),v in datecounts.items() if tt==t and yy==y];pdays.append({'ticker':t,'year':y,'distinct_publication_dates':len(values),'maximum_rows_one_date':max(values),'mean_rows_per_observed_date':sum(values)/len(values)})
    def save(name,rows):
        with (work/name).open('w',newline='') as f:
            cols=list(dict.fromkeys(k for r in rows for k in r));w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
    save('body_quality_heuristics.csv',rows);save('publication_date_density.csv',pdays)
    db=sqlite3.connect(f'file:{work.resolve()}/target_dedup.sqlite?mode=ro',uri=True)
    cross=[];sameyear=[]
    for column in ('url_hash','body_hash','title_date_hash'):
        pairs=db.execute(f'SELECT COUNT(*) FROM (SELECT {column} FROM news WHERE {column} IS NOT NULL GROUP BY {column} HAVING COUNT(DISTINCT ticker)=2)').fetchone()[0]
        cross.append({'key':column,'distinct_clusters_shared_AAPL_TSLA':pairs,'not_extra_independent_articles':True})
    # A URL with different body hashes is a potential version or scrape variation,
    # NOT evidence of a verified historical update sequence.
    for t in ('AAPL','TSLA'):
        nn=db.execute('SELECT COUNT(*) FROM (SELECT url_hash FROM news WHERE ticker=? AND url_hash IS NOT NULL GROUP BY url_hash HAVING COUNT(DISTINCT body_hash)>1)',(t,)).fetchone()[0]
        sameyear.append({'ticker':t,'URLs_with_multiple_nonempty_body_versions':nn,'historical_version_order_verified':False})
    save('cross_stock_duplicate_clusters.csv',cross);save('possible_article_versions.csv',sameyear)
    precision=db.execute('SELECT ticker,COUNT(DISTINCT rawdate),COUNT(DISTINCT date),SUM(precision="date_only"),SUM(precision LIKE "%midnight%"),SUM(precision="publisher_intraday_timezone_claimed") FROM news GROUP BY ticker').fetchall()
    save('date_precision_summary.csv',[{'ticker':t,'distinct_raw_timestamps':n,'distinct_publication_dates':d,'date_only':a,'midnight_unverified_precision':b,'intraday_timezone_claimed_not_firstseen':c} for t,n,d,a,b,c in precision]);db.close()
    composite={k:v for k,v in m['all_symbol_counts'].items() if k not in ('AAPL','TSLA') and re.search(r'(?:^|[^A-Z0-9])(?:AAPL|TSLA)(?:$|[^A-Z0-9])',k)}
    for t,n in target_totals.items():
        assert n==next(z['rows'] for z in m['target_summary'] if z['ticker']==t)
        assert n==m['all_symbol_counts'][t]-m['target_invalid_date_rows'].get(t,0)-m['target_post2025_metadata_only_skipped'].get(t,0)
    dump(work/'QUALITY_COMPLETE.json',{'status':'PASSED','full_scan_manifest_sha256':sha(work/'COMPLETE.json'),'target_export_counts_verified':target_totals,'composite_symbol_values_matching_targets':composite,'raw_exact_row_hash_includes_original_csv_index':True,'body_nonempty_not_claimed_fulltext_verified':True,'no_target_date_invalid_silently_counted':True,'diagnostic_heuristics_not_used_for_model_or_source_selection':True,'FNSPID_not_used_by_E4c':True})
    shutil.copy2(Path(__file__),out/'code'/Path(__file__).name);print('FNSPID QUALITY CHECKS PASSED',target_totals,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT);a=p.parse_args();run(a.out.resolve())
