"""Rebuild2023-2025Apple Newsroom, retaining retrieval-version evidence and failures."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import pandas as pd
from bs4 import BeautifulSoup
from e4b_core import ROOT,OUT,PRIOR,VENDOR,sha,dump,fetch,now


def prepare(out):
    if (out/'prepared.json').exists():return
    if out.exists():raise FileExistsError('Preserve preexisting study')
    for n in ('raw/http','inputs','code','tables','figures','logs','datasets','features','audits'): (out/n).mkdir(parents=True)
    protected={}
    for n in ('E4A_CURRENT_RUN.json','E4A_SUMMARY.md','E3C_CURRENT_RUN.json'):
        protected[n]=sha(ROOT/n)
    for p in (PRIOR/'protocol').rglob('*'):
        if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
    for study in ('mamba_multiseed_20261020','e3a_20261021','e3b_20261026','e3c_20261026_v1_1','e4a_20261026_v1_1','e4a_20261026_phase7a'):
        for p in (ROOT/'outputs'/study).glob('*complete*.zip*'):protected[str(p.relative_to(ROOT))]=sha(p)
    dump(out/'protected_previous_files.json',protected)
    dump(out/'DATASET_PROTOCOL.json',{'version':'E4b-recovery-v1','frozen_utc':now(),'purpose':'Dataset recovery and feasibility, no news predictor fit',
        'collect_years':[2023,2024,2025],'historical_end':'2025-12-31','Apple_universe':'all links on year-filtered English archive pages; reconcile against old100 URL/hash list, no forced450 count',
        'source_versions':'current re-download != original historical body; preserve HTTP/text hashes,retrieved timestamp and release date separately',
        'text_models':'exact prior FinBERT revision; every content token in510-token chunks with token-weighted pooling; originalV1spaCy3.8.0 language model and event rules retained; noV2 promotion',
        'news_gemini':'reuse original36 cache-backed outputs only; no paid inference; join by exact text-version hash, never by date alone',
        'market_data':'reuse E4a frozen through2025; original2012-2022/2023/2024-2025 partitions, t+20 purge and60-session complete history',
        'PIT':'strict historical availability stays unknown unless independent historical version/first-seen evidence; publication-date next-session proxy separate',
        'dedup':'canonical URL identity+text version; exact-text cluster; retain source andbody-vs-summary representation; near-title similarity flags only, no automated merging of updates',
        'news_coverage':'known-source article/event overlap, not complete market-news coverage; unobserved source years remain unknown, no false no-news zeros',
        'statistics':'coverage and extraction quality only; no news-predictor hyperparameter tuning or significance claim; source-stratified descriptive event outcomes; block estimates only with enough event support',
        '2026':'no real2026article/price/label collection; prior2026protocol bytes unchanged and validation not run',
        'resources':'max2 concurrentHTTP requests, token inference batch8; CPU initially; one genuine GPU inference process only if needed/available, no training; do not alter prior venvs'})
    for p in (PRIOR/'inputs').glob('*through2025.csv'):shutil.copyfile(p,out/'inputs'/p.name)
    for n in ('market_news_alignment.csv.gz','event_news_features.csv'):
        shutil.copyfile(PRIOR/'aligned'/n,out/'inputs'/n)
    for n in ('AAPL_news_historical_smoke.csv','AAPL_llm_historical_resume.csv','prompt_original.txt'):
        shutil.copyfile(PRIOR/'inputs/phase7a'/n,out/'inputs'/n)
    review=ROOT/'vendor/stockllm-pit-news/e5a0767415a9123f0a338a73068aa564fac90585/reports/apple_extraction_audit_v1/blind_review_manifest.csv'
    shutil.copyfile(review,out/'inputs/original100_article_manifest.csv')
    shutil.copyfile(VENDOR/'reports/apple_public_v1/collection_summary.json',out/'inputs/old_collection_summary.json')
    shutil.copyfile(VENDOR/'reports/apple_public_v1/model_registry.json',out/'inputs/old_model_registry.json')
    shutil.copytree(PRIOR/'protocol',out/'protocol_2026_unchanged')
    shutil.copytree(VENDOR/'event_extraction',out/'code/upstream_event_extraction')
    shutil.copyfile(VENDOR/'experiments/infer_apple_public.py',out/'code/upstream_infer_apple_public.py')
    shutil.copyfile(VENDOR/'experiments/collect_apple_newsroom.py',out/'code/upstream_collector.py')
    dump(out/'prepared.json',{'status':'PREPARED','created_utc':now()})


def collect(out):
    prepare(out);archive=[];urlset=set()
    for year in (2023,2024,2025):
        for page in range(1,51):
            url=f'https://www.apple.com/newsroom/archive/{year}/?page={page}'
            content,meta=fetch(url,out);soup=BeautifulSoup(content,'html.parser')
            links=sorted(set('https://www.apple.com'+a['href'] for a in soup.select('a[href]')
                if re.fullmatch(fr'/newsroom/{year}/\d{{2}}/[^/?]+/?',a['href'])))
            if not links:raise RuntimeError('No historical article links: '+url)
            text=' '.join(x.get_text(' ',strip=True) for x in soup.select('[class*=pagination]'))
            matches=re.findall(r'of\s+(\d+)',text);total=int(matches[0]) if matches else None
            if total is None:raise RuntimeError('Pagination count unavailable; fail closed')
            archive.append({'year':year,'page':page,'total_pages':total,'article_links':len(links),'url':url,'sha256':meta['sha256']})
            urlset.update(links);print('ARCHIVE',year,page,'/',total,'URLs',len(urlset),flush=True)
            if page>=total:break
        else:raise RuntimeError('Archive page cap reached')
    pd.DataFrame(archive).to_csv(out/'tables/apple_archive_scan.csv',index=False)
    old=pd.read_csv(out/'inputs/original100_article_manifest.csv');urlset.update(old.url)
    pd.DataFrame({'url':sorted(urlset)}).to_csv(out/'inputs/reconstructed_candidate_urls.csv',index=False)
    spec=importlib.util.spec_from_file_location('frozen_collector',out/'code/upstream_collector.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    def one(url):
        try:
            content,meta=fetch(url,out);soup=BeautifulSoup(content,'html.parser');date=soup.select_one('.category-eyebrow__date')
            if date is None:raise ValueError('Missing date')
            published=pd.to_datetime(date.get_text(' ',strip=True),format='%B %d, %Y')
            if not 2023<=published.year<=2025:raise ValueError('Published date outside2023-2025; body not parsed')
            row=mod.parse_article(content.decode('utf-8'),url)
            row.update(retrieved_utc=meta['retrieved_utc'],http_sha256=meta['sha256'],record_origin='E4B_CURRENT_REDOWNLOAD',
                text_version_origin='current_page_not_original_snapshot',historical_available_utc=None,
                published_utc=None,publication_timezone=None,collection_completeness='retrievable English Apple-source archive only')
            return row,None
        except Exception as e:return None,{'url':url,'error_type':type(e).__name__,'error':str(e)}
    rows=[];fail=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(one,u):u for u in sorted(urlset)}
        for j,f in enumerate(as_completed(futures),1):
            row,error=f.result()
            if error:fail.append(error)
            else:rows.append(row)
            if j%20==0 or j==len(futures):print('ARTICLES',j,'/',len(futures),'accepted',len(rows),'failed',len(fail),flush=True)
    frame=pd.DataFrame(rows).sort_values(['publication_date','article_id']);assert frame.article_id.is_unique
    frame.to_csv(out/'raw/apple_newsroom_articles_recollected.csv',index=False)
    frame.drop(columns=['title','content']).to_csv(out/'datasets/apple_article_manifest_recollected.csv',index=False)
    dump(out/'audits/collection_failures.json',fail)
    joined=old.merge(frame[['article_id','text_sha256']],on='article_id',how='left',suffixes=('_old','_new'))
    joined['retrieved']=joined.text_sha256_new.notna();joined['exact_original_text_hash_match']=joined.text_sha256_old.eq(joined.text_sha256_new)
    joined.to_csv(out/'tables/original100_version_reconciliation.csv',index=False)
    summary={'status':'COLLECTED','retrieved_utc':now(),'articles':len(frame),'by_year':frame.publication_date.str[:4].value_counts().sort_index().to_dict(),
        'archive_candidate_urls':len(urlset),'failures':len(fail),'old100_retrieved':int(joined.retrieved.sum()),'old100_exact_text_hash_matches':int(joined.exact_original_text_hash_match.sum()),
        'old_snapshot_recovered':False,'strict_historical_PIT_verified':False,'2026_collected':False}
    dump(out/'audits/collection_summary.json',summary);print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);a=p.parse_args();collect(a.out.resolve())
