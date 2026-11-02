"""Offline E4b validation, source coverage, figures, feasibility and result archive."""
import argparse
import gzip
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
import zipfile
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from e4b_core import ROOT,OUT,PRIOR,sha,dump,now,FINBERT_REV

SOURCES=[
 ('Apple Newsroom','Reconstructed2023-2025','AAPL; corporate source only','full prose, date only','public pages; no historical version/first-seen proof','copyrighted; private research archive, not an open redistribution license','ACTUALLY_RECONSTRUCTED','https://www.apple.com/newsroom/archive/2023/'),
 ('Phase7A AlphaVantage','Provided January2025 only','AAPL52 summaries','publisher timestamp, summary,36 Gemini outputs','historical delivery/version unverified; relevance and partial annotation issues','user-supplied original; third-party distribution unverified','ACTUALLY_INTEGRATED','https://www.alphavantage.co/documentation/'),
 ('FNSPID','Advertised1999-2023; ticker-specific coverage NOT guaranteed','AAPL/TSLA tagging requires empirical audit','CSV publisher UTC strings; many missing ticker/body fields','public filter returned500; raw29GB files; missing first-seen; release2025 not strict PIT','HF card/LICENSE CC BY-NC4.0; Github2025 commercial-release statement conflicts, preserve both; underlying publisher rights separate','PUBLIC_METADATA_AND_BOUNDED_PROBES','https://huggingface.co/datasets/Zihan1004/FNSPID'),
 ('Benzinga','Vendor advertises history since2009','US equities including ticker-linked news; verify AAPL/TSLA years','created/updated and full body option','API entitlement and historical per-version delivery audit required','subscription/contract; full text and redistribution rights depend on license','NOT_AUTHENTICATED_NO_PURCHASE','https://www.benzinga.com/apis/blog/mastering-the-benzinga-newsfeed-api/'),
 ('LSEG News Archive/MRN','Reuters from1996; MRN archive from2003','company-coded global news; verify entitlements','story and take timestamps, version identifiers/text','candidate for2012-2025; verify historical takes, latency and source entitlements','licensed archive, separate content/source and redistribution conditions','NOT_AUTHENTICATED_NO_PURCHASE','https://developers.lseg.com/en/article-catalog/article/machine-readable-news-mrn-n2_ubms-comparison-and-migration-guide'),
 ('RavenPack','Official API describes history from2000','company/entity analytics; documents separate','analytics timestamps, entities, relevance/novelty','historical analytics version and document rights must be checked','licensed; institutional/WRDS access varies, not free fulltext','NOT_AUTHENTICATED_NO_PURCHASE','https://github.com/RavenPack/r-api'),
 ('Massive ticker news','Oldest2016-06-22, sparse before2021; insights from2024-07-02','ticker news; cannot fill2012-2015','published_utc, summaries, insights','published time is not arrival/insight creation time; not historical as-of API','plan-dependent history; separate Benzinga product/license','PUBLIC_DOCUMENTATION_ONLY','https://massive.com/knowledge-base/article/how-far-back-does-massives-news-and-sentiment-data-go'),
 ('GDELT2 GKG','2.0 starts2015-02-19','global media; company matching must be rebuilt','URLs/entities/themes/tone metadata, not licensed article bodies','monitoring time is not necessarily first publisher release; GDELT1 older events do not supply equivalent ticker fulltext','open metadata access; publisher article rights remain separate','PUBLIC_DOCUMENTATION_ONLY','https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/'),
 ('SEC EDGAR','historical filings can cover2012-2025','AAPL/TSLA filings and8-K exhibits, not general financial news','filing acceptance/dissemination metadata and original documents','useful separate corporate-disclosure track; not a complete news replacement','public filing access under SEC fair-access rules; third-party exhibit rights require care','PUBLIC_DOCUMENTATION_ONLY','https://www.sec.gov/search-filings/edgar-application-programming-interfaces')]


def validate(out,verify_previous=True):
    input_path=out/'datasets/news_unified_feature_input.csv.gz'
    if not input_path.exists():input_path=out/'datasets/news_unified.csv.gz'
    data=pd.read_csv(input_path,keep_default_na=False)
    ft=pd.read_csv(out/'features/article_features.csv',float_precision='round_trip')
    complete=json.loads((out/'features/COMPLETE.json').read_text())
    for name,h in complete['files'].items():
        if sha(out/name)!=h:raise RuntimeError('Feature artifact changed '+name)
    expected_views=int((data.representation.ne('title_only_no_body').astype(int)+1).sum())
    assert len(ft)==expected_views and data.record_id.is_unique
    assert sha(input_path)==json.loads((out/'features/model_registry.json').read_text())['news_sha256']
    assert (data.publication_date<='2025-12-31').all()
    assert set(ft.record_id)==set(data.record_id) and ft.primary_view.sum()==len(data)
    assert ft.truncated_tokens.eq(0).all() and np.isfinite(ft[['sent_positive','sent_negative','sent_neutral']]).all().all()
    np.testing.assert_allclose(ft[['sent_positive','sent_negative','sent_neutral']].sum(axis=1),1,atol=1e-6)
    chunk=pd.DataFrame([json.loads(line) for line in (out/'features/finbert_chunks.jsonl').read_text().splitlines()])
    assert chunk.tokens.between(1,510).all()
    grouping=chunk.groupby(['record_id','source'],sort=True)
    totals=grouping.tokens.sum();ff=ft.set_index(['record_id','source']).sort_index()
    np.testing.assert_array_equal(totals,ff.finbert_tokens)
    for k in ('positive','negative','neutral'):
        mean=(chunk.assign(w=chunk[k]*chunk.tokens).groupby(['record_id','source']).w.sum()/totals)
        np.testing.assert_allclose(mean,ff['sent_'+k],atol=1e-12,rtol=1e-12)
    gg=pd.read_csv(out/'features/gemini_original36_exact_version_join.csv')
    assert len(gg)==36 and gg.record_id.is_unique
    assert all(data.set_index('record_id').loc[r.record_id,'text_sha256']==r.text_sha256 for r in gg.itertuples())
    if verify_previous:
        for p,h in json.loads((out/'protected_previous_files.json').read_text()).items():
            if sha(ROOT/p)!=h:raise RuntimeError('Previous research changed '+p)
    expected='9ffe3c31bbfabb6609ee69dde1deab7a13729b43511a9c045d945b5b03453940'
    assert sha(out/'protocol_2026_unchanged/E3C_2026_PROTOCOL.json')==expected
    result={'status':'PASSED','articles':len(data),'feature_rows':len(ft),'chunks':len(chunk),'all_tokens_accounted':True,
        'probabilities_valid':True,'exact_Gemini_version_joins':36,'previous_results_unchanged':True,
        'protocol2026_sha256':expected,'2026_validation_executed':False,'2026_rows_in_research':False,'new_news_predictors_trained':0}
    dump(out/'audits/validation.json',result)
    return data,ft


def finalize_metadata(out,data):
    # Preserve exactly what the extractor hashed, then normalize source lineage.
    original=out/'datasets/news_unified_feature_input.csv.gz'
    if not original.exists():shutil.copyfile(out/'datasets/news_unified.csv.gz',original)
    z=data.copy();fn=z.source_family.eq('fnspid_bounded_headlines')
    probe=json.loads((out/'audits/fnspid_bounded_recovery.json').read_text())
    z.loc[fn,'record_origin']='E4B_FNSPID_FIXED_REV_BOUNDED_BLOCK'
    z.loc[fn,'retrieved_utc']=probe['created_utc']
    z['source_dataset_revision']=np.where(fn,probe['revision'],'')
    z['claimed_publisher_timestamp_is_midnight']=z.published_utc.astype(str).str.contains('T00:00:00',regex=False)
    z['timestamp_precision_raw']=z.timestamp_precision
    z.loc[fn & z.claimed_publisher_timestamp_is_midnight,'timestamp_precision']='UTC_midnight_precision_unverified'
    z['exact_historical_timestamp_accuracy_verified']=False
    np.testing.assert_array_equal(z.record_id,data.record_id);np.testing.assert_array_equal(z.text_sha256,data.text_sha256)
    z.to_csv(out/'datasets/news_unified.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    z.drop(columns=['title','content']).to_csv(out/'datasets/news_unified_manifest.csv',index=False)
    dump(out/'audits/dataset_lineage.json',{'feature_input_snapshot':'datasets/news_unified_feature_input.csv.gz','feature_input_sha256':sha(original),
        'final_normalized_dataset':'datasets/news_unified.csv.gz','normalized_sha256':sha(out/'datasets/news_unified.csv.gz'),
        'metadata_only_normalization':'FNSPID source lineage and midnight precision uncertainty; all record IDs,text hashes and text features unchanged',
        'unique_document_URLs':int(z.url.nunique()),'article_entity_version_records':len(z),'headline_only_records':int(fn.sum())})
    return z


def canonical(url):
    u=urlsplit(url);query=urlencode([(k,v) for k,v in parse_qsl(u.query) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')])
    return urlunsplit(('https',u.netloc.lower(),u.path.rstrip('/')+'/',query,''))


def quality(out,data,ft):
    z=data[['record_id','document_id','url','text_sha256','source_family','publication_date','representation']].copy();z['canonical_url']=z.url.map(canonical)
    z['canonical_document_id']=z.canonical_url.map(lambda s:__import__('hashlib').sha256(s.encode()).hexdigest()[:24])
    z['exact_text_cluster_size']=z.groupby('text_sha256').record_id.transform('size')
    z['versions_or_representations_per_canonical_url']=z.groupby('canonical_url').record_id.transform('size')
    z.to_csv(out/'tables/document_version_dedup_map.csv',index=False)
    vector=TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),min_df=1).fit_transform(data.title.str.casefold())
    similarity=cosine_similarity(vector);pairs=[]
    for a,b in zip(*np.where(np.triu(similarity>=.90,1))):
        pairs.append({'record_id_a':data.record_id.iloc[a],'record_id_b':data.record_id.iloc[b],'title_cosine_similarity':similarity[a,b],
            'automatically_merged':False,'note':'candidate related/duplicate/update title, requires review; title similarity is not event identity'})
    pd.DataFrame(pairs,columns=['record_id_a','record_id_b','title_cosine_similarity','automatically_merged','note']).to_csv(out/'tables/near_title_duplicate_review.csv',index=False)
    q=pd.read_csv(out/'tables/event_extraction_quality_flags.csv')
    agg=q.groupby('source')[['syntactic_records','missing_actor_or_object','target_role_other_or_unknown','arguments_over20_words']].sum().reset_index()
    for c in ('missing_actor_or_object','target_role_other_or_unknown','arguments_over20_words'):agg[c+'_fraction_of_syntactic_records']=agg[c]/agg.syntactic_records
    agg['independent_human_gold_available']=False;agg['fractions_are_error_rates']=False
    agg.to_csv(out/'tables/extraction_quality_summary.csv',index=False)
    both=pd.read_csv(out/'features/unified_finbert_events_gemini.csv');both=both[both.sentiment.notna()].copy()
    both['finbert_signed_sentiment']=both.sent_positive-both.sent_negative
    def sign(a):return np.where(a>.1,1,np.where(a<-.1,-1,0))
    both['sentiment_bins_disagree']=sign(both.finbert_signed_sentiment)!=sign(both.sentiment)
    both[['record_id','finbert_signed_sentiment','sentiment','sentiment_bins_disagree','market_relevance']].to_csv(out/'tables/finbert_gemini_same36_comparison.csv',index=False)
    corr=spearmanr(both.finbert_signed_sentiment,both.sentiment).statistic
    dump(out/'audits/model_output_comparison.json',{'same_exact_text_articles':36,'signed_sentiment_Spearman':float(corr),
        'fixed_bin_disagreement_fraction':float(both.sentiment_bins_disagree.mean()),'no_accuracy_or_superiority_claim':True,'no_human_sentiment_gold':True})
    catalog=pd.DataFrame(SOURCES,columns=['source','historical_coverage','entity_scope','content_and_times','quality_or_PIT_limit','license_and_access','access_status','primary_reference'])
    catalog.loc[catalog.source.eq('FNSPID'),'access_status']='OBTAINED_BOUNDED_BLOCKS_AAPL441_TSLA1875_HEADLINES_ONLY_NO_COMPLETE_ARCHIVE'
    catalog.to_csv(out/'tables/data_source_comparison.csv',index=False)
    times=[]
    for fam,z in data.groupby('source_family'):
        times.append({'source_family':fam,'article_entity_version_records':len(z),'date_only_or_unverified_midnight_precision':int(z.timestamp_precision.isin(['date_only','UTC_midnight_precision_unverified']).sum()),
            'claimed_publisher_timestamps':int(z.published_utc.astype(bool).sum()),'midnight_publisher_time_rows':int(z.claimed_publisher_timestamp_is_midnight.sum()),
            'historical_first_seen_verified':0,'historical_text_version_verified':0})
    pd.DataFrame(times).to_csv(out/'tables/news_time_quality.csv',index=False)
    dump(out/'datasets/SCHEMA.json',{'identity':'record_id is exact version+representation+source identity; canonical_document_id and text cluster in dedup map',
        'availability':['publication_date','published_utc nullable','timestamp_precision','retrieved_utc nullable','historical_available_utc nullable','historical_text_revision_verified'],
        'source_versions':'new Apple full prose and old Phase7A summaries are separate, not interchangeable original bodies',
        'features':'FinBERT positive/negative/neutral are text sentiment; Gemini direction_probability is NOT5day reversal probability; event syntactic counts are not independent financial events',
        'joins':'features require exact record_id AND text_sha256; no date-only article feature joins',
        'dedup':'raw observations preserved; exact text dedup within a source/ticker/window before aggregation; near-title pairs only flagged, updates/version timing never silently merged',
        'missingness':'uncollected stock/year/source UNKNOWN; zero permitted only as known count in this reconstructed source universe, not whole-market no-news',
        'rights':'private research result; no public redistribution of third-party fulltext or assumption all sources share a license'})
    return z,agg


def align(out,data,ft):
    market=pd.read_csv(out/'inputs/market_news_alignment.csv.gz');full=ft[ft.source.eq('full')].set_index('record_id')
    articles=data.copy();info=[]
    for ticker in ('AAPL','TSLA'):
        sessions=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(out/'inputs'/f'{ticker}_adjusted_through2025.csv').Date))
        part=articles[articles.ticker.eq(ticker)].copy()
        for r in part.itertuples():
            if r.timestamp_precision in ('date_only','UTC_midnight_precision_unverified'):i=sessions.searchsorted(pd.Timestamp(r.publication_date),side='right')
            else:
                cut=(sessions+pd.Timedelta(hours=17)).tz_localize('America/New_York').tz_convert('UTC')
                i=cut.searchsorted(pd.Timestamp(r.published_utc),side='left')
            info.append({'record_id':r.record_id,'publisher_proxy_information_date':sessions[i].strftime('%Y-%m-%d') if i<len(sessions) else None,
                'publisher_proxy_defer1_date':sessions[i+1].strftime('%Y-%m-%d') if i+1<len(sessions) else None,
                'publisher_proxy_defer2_date':sessions[i+2].strftime('%Y-%m-%d') if i+2<len(sessions) else None,
                'alignment_tier':'RETROSPECTIVE_PUBLISHER_PROXY_NOT_VERIFIED_PIT'})
    articles=articles.merge(pd.DataFrame(info),on='record_id',validate='one_to_one')
    articles.drop(columns=['title','content']).to_csv(out/'datasets/news_market_timing_manifest.csv',index=False)
    source_rows=[];source_event_rows=[];source_links=[]
    for ticker in ('AAPL','TSLA'):
        sessions=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(out/'inputs'/f'{ticker}_adjusted_through2025.csv').Date))
        for family in sorted(data.source_family.unique()):
            nn=articles[articles.ticker.eq(ticker)&articles.source_family.eq(family)].copy();nn['_date']=pd.to_datetime(nn.publisher_proxy_information_date)
            for year in range(2012,2026):
                yy=nn[nn.publication_date.str.startswith(str(year))]
                source_rows.append({'ticker':ticker,'year':year,'source_family':family,'retrieved_article_entity_records':len(yy),
                    'full_prose_records':int(yy.representation.eq('title_plus_full_prose').sum()),'headline_only_records':int(yy.representation.eq('title_only_no_body').sum()),
                    'publisher_timestamps_claimed':int(yy.published_utc.astype(bool).sum()),'midnight_publisher_timestamps':int(yy.claimed_publisher_timestamp_is_midnight.sum()),
                    'complete_market_news_coverage':np.nan,'historical_delivery_verified':False,'zero_is_no_retrieved_record_not_no_news':True})
            if nn.empty:continue
            lower=nn._date.min();upper=nn._date.max()
            for rr in market[market.ticker.eq(ticker)&market.event.eq(1)].itertuples():
                day=pd.Timestamp(rr.date);i=sessions.get_loc(day);start=sessions[max(0,i-4)]
                inspan=start>=lower and day<=upper
                found=nn[nn._date.between(start,day)].drop_duplicates('text_sha256')
                for art in found.itertuples():source_links.append({'ticker':ticker,'event_date':rr.date,'source_family':family,'record_id':art.record_id,
                    'proxy_information_date':art.publisher_proxy_information_date,'exact_text_sha256':art.text_sha256,'strict_model_input':False})
                if inspan or len(found):source_event_rows.append({'ticker':ticker,'event_date':rr.date,'year':day.year,'source_family':family,
                    'within_retrieved_timestamp_span':inspan,'event_direction':rr.event_direction,'conflict':rr.conflict,'VIX_high':rr.VIX_high,
                    'known_retained_articles_last5':len(found),'source_completeness_verified':False,'strict_PIT_verified':False})
    pd.DataFrame(source_rows).to_csv(out/'tables/source_coverage_by_stock_year.csv',index=False)
    pd.DataFrame(source_event_rows).to_csv(out/'datasets/source_specific_market_event_coverage.csv',index=False)
    pd.DataFrame(source_links).to_csv(out/'datasets/source_specific_event_article_links.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    daily=[];links=[]
    for ticker in ('AAPL','TSLA'):
        sessions=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(out/'inputs'/f'{ticker}_adjusted_through2025.csv').Date))
        stocks=market[market.ticker.eq(ticker)]
        news=articles[articles.ticker.eq(ticker)&articles.source_family.eq('apple_newsroom_recollected')].copy()
        for timing,col in [('next_session_date_proxy','publisher_proxy_information_date'),('defer1','publisher_proxy_defer1_date'),('defer2','publisher_proxy_defer2_date')]:
            news['_date']=pd.to_datetime(news[col])
            for r in stocks.itertuples():
                d=pd.Timestamp(r.date);i=sessions.get_loc(d);a=sessions[max(0,i-4)]
                valid=ticker=='AAPL' and a>=pd.Timestamp('2023-01-03') and d<=pd.Timestamp('2025-12-31')
                rows=news[news._date.between(a,d)].sort_values(['publication_date','record_id']).drop_duplicates('text_sha256') if valid else news.iloc[:0]
                ff=full.loc[rows.record_id] if len(rows) else full.iloc[:0]
                rec={'ticker':ticker,'date':r.date,'year':d.year,'partition':r.partition,'timing_assumption':timing,'event':r.event,'event_direction':r.event_direction,
                    'conflict':r.conflict,'VIX_high':r.VIX_high,'cell':r.cell,'future_y5':r.future_y5,
                    'future_signed_reversal_amplitude_pp':r.future_signed_reversal_amplitude_pp,
                    'reconstructed_source_window_observed':valid,'historical_source_completeness_verified':False,
                    'archive_known_articles_last5':len(rows) if valid else np.nan,
                    'archive_FinBERT_signed_mean':float((ff.sent_positive-ff.sent_negative).mean()) if len(ff) else np.nan,
                    'strict_PIT_features_available':False}
                for typ in ('litigation','earnings','product_launch','merger_acquisition','regulation','other'):
                    rec['has_type_'+typ]=bool((ff['event_type_'+typ]>0).any()) if valid else None
                daily.append(rec)
                if r.event and valid and timing=='next_session_date_proxy':
                    for art in rows.itertuples():links.append({'ticker':ticker,'event_date':r.date,'partition':r.partition,'event_direction':r.event_direction,'conflict':r.conflict,'record_id':art.record_id,
                        'publication_date':art.publication_date,'proxy_information_date':getattr(art,col),'strict_model_input':False})
    daily=pd.DataFrame(daily);daily.to_csv(out/'datasets/daily_news_market_alignment.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    pd.DataFrame(links).to_csv(out/'datasets/apple_market_event_article_links.csv',index=False)
    primary=daily[daily.timing_assumption.eq('next_session_date_proxy')]
    yearly=[];bytype=[];outcomes=[]
    for (ticker,year),z in primary.groupby(['ticker','year']):
        valid=z[z.reconstructed_source_window_observed];e=valid[valid.event.eq(1)];covered=e[e.archive_known_articles_last5.gt(0)]
        count=int(((data.ticker==ticker)&data.publication_date.str.startswith(str(year))&data.source_family.eq('apple_newsroom_recollected')).sum())
        yearly.append({'ticker':ticker,'year':year,'eligible_market_dates':len(z),'price_events':int(z.event.sum()),'Apple_recollected_articles':count if ticker=='AAPL' and year>=2023 else np.nan,
            'proxy_window_observed_dates':len(valid),'proxy_window_observed_events':len(e),'events_with_known_archive_news_last5':len(covered),
            'event_overlap_rate_in_reconstructed_universe':len(covered)/len(e) if len(e) else np.nan,
            'whole_market_news_coverage':np.nan,'historical_source_completeness_verified':False,
            'status':'RECONSTRUCTED_APPLE_SOURCE_ONLY' if len(valid) else 'UNOBSERVED_NOT_NO_NEWS'})
        if len(e):
            groups={'all_events':e,'surge':e[e.event_direction.eq(1)],'crash':e[e.event_direction.eq(-1)],'conflict':e[e.conflict.eq(1)],'aligned':e[e.conflict.eq(0)],'VIX_high':e[e.VIX_high.eq(1)],'VIX_low':e[e.VIX_high.eq(0)]}
            for name,g in groups.items():bytype.append({'ticker':ticker,'year':year,'price_event_type':name,'event_n':len(g),'with_known_archive_news_last5':int(g.archive_known_articles_last5.gt(0).sum()),
                'overlap_rate_source_only':g.archive_known_articles_last5.gt(0).mean() if len(g) else np.nan})
    for timing,z in daily[daily.event.eq(1)&daily.reconstructed_source_window_observed].groupby('timing_assumption'):
        news=z[z.archive_known_articles_last5.gt(0)]
        groups={'all_source_observed_events':z,'known_archive_news':news,'no_retained_archive_article':z[z.archive_known_articles_last5.eq(0)]}
        for k in ('litigation','earnings','product_launch','merger_acquisition','regulation','other'):groups['news_type_'+k]=news[news['has_type_'+k].eq(True)]
        for name,g in groups.items():outcomes.append({'timing_assumption':timing,'group':name,'event_n':len(g),'reversals':int(g.future_y5.sum()),
            'reversal_fraction':g.future_y5.mean() if len(g) else np.nan,'signed_amplitude_mean_pp':g.future_signed_reversal_amplitude_pp.mean() if len(g) else np.nan,
            'status':'DESCRIPTIVE_RETROSPECTIVE_SOURCE_SELECTION_NOT_PREDICTIVE_OR_CAUSAL','p_value':np.nan})
    pd.DataFrame(yearly).to_csv(out/'tables/coverage_by_stock_year.csv',index=False)
    pd.DataFrame(bytype).to_csv(out/'tables/coverage_by_market_event_type.csv',index=False)
    pd.DataFrame(outcomes).to_csv(out/'tables/source_conditioned_outcomes_descriptive.csv',index=False)
    return primary,pd.DataFrame(yearly)


def proposal(out,primary):
    support=[]
    boundary=pd.read_csv(out/'inputs/market_news_alignment.csv.gz')[['ticker','date','label_end20']]
    for year in (2023,2024,2025):
        z=primary[primary.ticker.eq('AAPL')&primary.year.eq(year)&primary.reconstructed_source_window_observed]
        z=z.merge(boundary,on=['ticker','date'],validate='one_to_one')
        z=z[z.label_end20<=f'{year}-12-31']
        e=z[z.event.eq(1)];news=e[e.archive_known_articles_last5.gt(0)]
        support.append({'year':year,'eligible_dates':len(z),'event_n':len(e),'event_reversals':int(e.future_y5.sum()),'event_continuations':len(e)-int(e.future_y5.sum()),'events_with_retained_Apple_news':len(news),'max_label_end20':z.label_end20.max()})
    pd.DataFrame(support).to_csv(out/'tables/proposed_2023_2025_split_support.csv',index=False)
    text='''# E4c candidate: same-source2023-2025 retrospective exploratory study

This is a new limited exploratory protocol proposal, not execution or an independent test. The original2012-2022/2023/2024-2025 E3c design and2026one-shot protocol remain unchanged.

Use AAPL Apple Newsroom ONLY to avoid training on media summaries and testing on corporate releases. Train2023, validation/calibration2024, report2025 once under frozen settings; all these years have already been viewed. Keep the existing2012-2022event thresholds/price cells, same next-open5-session reversal target,20-session split purge and causal price history. Drop the initial source-lookback boundary where pre2023news was not collected. Freeze the newly reconstructed text snapshot, features and hashes; describe it as retrospective publication-proxy text, not strict historical PIT.

The provided yearly support CSV governs complexity. Event-only deep networks and XGBoost are not justified by approximately one year of a few dozen training events. Start with train-only Beta-Binomial global/event priors, hierarchical direction/long-trend/VIX cell shrinkage, then at most a low-dimensional all-date ridge LogisticRegression. Restrict price inputs to a predeclared compact summary, news to log-count/observation flag plus signed sentiment and a few broad event-type indicators. Compare P/S/T on identical source-observed dates; missing/uncollected differs from a zero in the retained Apple-source universe.

Use at most C=.01/.1/1 selected by2024Brier with a deterministic tie-break; avoid a separate event-only calibrator on a tiny sample. A fixed identity-prior calibration on all validation dates may be declared before evaluation, with all other tuning held fixed. If2024is used for selection and calibration, explicitly record the reuse and report uncalibrated results too; prefer a split within2024only if each partition retains support. Do not use2025to change source selection, sentiment/event thresholds or hyperparameters.

Primary: paired Brier, P->S and S->T; full common-calendar HAC20/block20bootstrap with60-session sensitivity and Holm2. Secondary: log loss and same-state AUC; average seed losses, never treat seeds as extra dates. At least20 event dates,10/class and20 within-state positive-negative pairs are required for ranking inference. Sensitivity: publication-next-session,+1,+2information sessions and5-session event thinning. Keep subgroup analyses descriptive when support is small. No trade-profit assertion and no assumption sentiment is a return probability.

Report exact source overlap and base rates by crash/surge, conflicting long trend and VIX. A Brier gain without within-state ranking gain supports calibration/average-probability improvement only. A corporate-source positive-news bias is not a general-financial-news result. TSLA comparison requires the SAME media population/period and extraction procedure first; never use AAPL corporate articles as TSLA no-news controls.

For the original2012-2025two-stock design, first obtain institutionally licensed timestamp/version archives (e.g. LSEG/Benzinga/RavenPack) or an empirically audited complete academic corpus. Verify actual ticker-year counts, publisher/arrival/update timestamps, missing body and tag rates and usable test source continuity before training. FNSPID's advertised dates alone do not establish per-stock availability, nor does a publication timestamp prove first seen. SEC8-Kdisclosures can form a separate event track, not replace missing general news.

Do not open2026to compensate for missing historical news. Any later truly independent news validation needs a separately preregistered unseen period and a prospective immutable collection/version log; the existing E3c2026price-only protocol cannot be repurposed or augmented with news.
'''
    (out/'E4C_EXPLORATORY_PROPOSAL.md').write_text(text)
    dump(out/'audits/model_feasibility.json',{'original2012_2022_news_predictor_fit':'NOT_READY','reason':'No demonstrated same-source sufficiently complete2012-2025AAPL/TSLA archive; Apple starts2023, recovered FNSPID blocks only2019-2020 with missing bodies and mostly midnight times',
        'AAPL2023_2025':'feasible source-limited retrospective data/low-dimensional pilot; event-only complex models not supported','TSLA':'1875 recovered2019-2020headlines, no same-source2023-2025fulltext test cohort',
        'models_trained':0,'2026_protocol_changed':False,'proposal_only':True})
    return support


def plots(out,data,ft,coverage):
    os.environ.setdefault('MPLCONFIGDIR',str(out/'.matplotlib'))
    for p in (Path.home()/'.local/lib/python3.10/site-packages',Path('/usr/local/lib/python3.10/dist-packages'),Path('/usr/lib/python3/dist-packages')):
        if p.exists():sys.path.append(str(p))
    import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    def save(fig,name):
        for ext in ('png','pdf'):fig.savefig(out/'figures'/f'{name}.{ext}',bbox_inches='tight',dpi=180)
        plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(11,4.5));years=[2023,2024,2025]
    new=data[data.source_family.eq('apple_newsroom_recollected')].publication_date.str[:4].value_counts()
    ax[0].bar(np.arange(3)-.18,[152,158,140],width=.36,color='#bac9d1',label='Old reported corpus')
    ax[0].bar(np.arange(3)+.18,[new[str(y)] for y in years],width=.36,color='#2a7775',label='Actually recollected')
    ax[0].set(xticks=np.arange(3),xticklabels=years,ylabel='Full-prose Apple articles',title='Original report vs current reconstruction');ax[0].legend(fontsize=8)
    c=coverage[coverage.ticker.eq('AAPL')&coverage.year.isin(years)]
    ax[1].bar(c.year,c.proxy_window_observed_events,color='#bac9d1',label='Eligible price events')
    ax[1].bar(c.year,c.events_with_known_archive_news_last5,color='#2a7775',width=.45,label='Known Apple-source news in past5')
    ax[1].set(xticks=years,ylabel='Price-event dates (overlapping)',title='Source overlap, not whole-market news coverage');ax[1].legend(fontsize=8)
    fig.tight_layout();save(fig,'01_reconstruction_and_event_support')
    joined=data[['record_id','source_family']].merge(ft[ft.primary_view],on='record_id')
    fig,ax=plt.subplots(1,2,figsize=(11,4.5))
    for fam,color in [('apple_newsroom_recollected','#2a7775'),('phase7a_original_summary','#bd7e45')]:
        z=joined[joined.source_family.eq(fam)];ax[0].hist(z.sent_positive-z.sent_negative,bins=np.linspace(-1,1,21),alpha=.55,label=fam,color=color)
    ax[0].set(xlabel='FinBERT positive minus negative',ylabel='Articles',title='Different sources/representations have different distributions');ax[0].legend(fontsize=7)
    paired=pd.read_csv(out/'tables/finbert_gemini_same36_comparison.csv');ax[1].scatter(paired.finbert_signed_sentiment,paired.sentiment,color='#2a7775',alpha=.7)
    ax[1].plot([-1,1],[-1,1],ls='--',color='#aaa');ax[1].set(xlabel='FinBERT signed sentiment',ylabel='Original Gemini sentiment',title='Same36 summaries; disagreement is not an error rate')
    fig.tight_layout();save(fig,'02_sentiment_and_source_shift')
    cv=pd.read_csv(out/'tables/coverage_by_market_event_type.csv');cv=cv[cv.price_event_type.isin(['surge','crash','conflict','aligned'])]
    fig,ax=plt.subplots(figsize=(10,4.5))
    for name,color in [('surge','#5a9c7e'),('crash','#bd6858'),('conflict','#6484a5'),('aligned','#bd9b4d')]:
        z=cv[cv.price_event_type.eq(name)];ax.plot(z.year,z.overlap_rate_source_only,'o-',label=name,color=color)
    ax.set(xticks=years,ylim=(-.03,1.05),ylabel='Fraction with retained Apple article in past5',title='Coverage within price-event types; publication proxies only');ax.legend();ax.grid(axis='y',alpha=.2)
    fig.tight_layout();save(fig,'03_event_type_news_overlap')
    fig,ax=plt.subplots(figsize=(10,4.5));labels=['Recollected Apple full prose','Original provider summaries','FNSPID headline-only entity records','FinBERT feature views','Gemini exact-version joins','Historical PIT certified articles','News predictors trained']
    vals=[448,52,2316,len(ft),36,0,0];ax.barh(labels[::-1],vals[::-1],color='#2a7775')
    for i,v in enumerate(vals[::-1]):ax.text(v+8,i,str(v),va='center')
    ax.set(xlim=(0,len(ft)*1.12),xlabel='Records / feature views (as labeled)',title='What E4b actually produced and what remains unverified');fig.tight_layout();save(fig,'04_verified_outputs')
    html='<!doctype html><meta charset="utf-8"><title>E4b figures</title><style>body{font:16px sans-serif;max-width:1100px;margin:auto}img{width:100%}</style><h1>E4b dataset recovery</h1><p>Retrospective reconstruction; no strict historical PIT or prediction-superiority claim.</p>'
    for p in sorted((out/'figures').glob('*.png')):html+=f'<h2>{p.stem}</h2><a href="{p.stem}.pdf">PDF</a><img src="{p.name}">'
    (out/'figures/index.html').write_text(html)


def report(out,support,coverage):
    collection=json.loads((out/'audits/collection_summary.json').read_text());inference=json.loads((out/'audits/finbert_inference.json').read_text())
    comparison=json.loads((out/'audits/model_output_comparison.json').read_text())
    c=coverage[coverage.ticker.eq('AAPL')&coverage.year.ge(2023)]
    tab='| 年份 | 重建全文 | 可評估價格事件 | 有已知Apple新聞的事件 | 來源內重合率 |\n|---|---:|---:|---:|---:|\n'
    for r in c.itertuples():tab+=f'| {r.year} | {int(r.Apple_recollected_articles)} | {r.proxy_window_observed_events} | {r.events_with_known_archive_news_last5} | {r.event_overlap_rate_in_reconstructed_universe:.2%} |\n'
    fns='公開filter端點HTTP500；小範圍取樣發現大量股票代號空白，未據此宣稱兩檔有完整歷史。'
    if (out/'audits/fnspid_bounded_recovery.json').exists():fns+='另取得的連續ticker區塊見該稽核檔；區塊不是全庫掃描或完整市場新聞證明。'
    text=f'''# E4b — Historical Financial News Dataset Recovery & Integration

**完成可取得資料的重建、真實FinBERT／V1事件特徵、統一版本資料集、來源／覆蓋／品質稽核與後續可行性方案。**這是資料基礎研究，未訓練新聞反轉模型；未取得足以證明2012–2025AAPL與TSLA完整同來源新聞的資料。2026價格模型協定逐位元不變，未執行驗證。

## 重建結果與原始快照的差別

從只含指定年份的Apple英文存檔重抓 **448篇全文**：2023年152、2024年156、2025年140。全部候選文章解析成功，失敗{collection['failures']}筆。舊研究報表是152／158／140，共450；本次2024少2篇。舊450篇的完整URL清單／HTTP／文章特徵沒有找回，無法指認這2篇或判斷是刪頁、存檔異動或舊收集差異，不補造文章。

研究分支保留的100篇2023URL均成功抓回，**100/100文字雜湊與舊清單完全吻合**。這證明此子樣本與先前2026回溯收集的擷取結果一致；不證明2023當時的頁面版本或first_seen。全部新頁面保留HTTP、回應雜湊、文字雜湊及UTC取得時間，標記`E4B_CURRENT_REDOWNLOAD`、`historical_text_revision_verified=false`。發布日期與實際可得時間分欄，不把現在抓取時間偽裝成歷史first_seen。

另完整保留原Phase7A **52篇2025年1月摘要、36篇原存Gemini輸出**，與重抓全文分開，未重抓或改寫原摘要。另從固定FNSPID版本的已標記連續區塊取得 **AAPL441筆、TSLA1,875筆純標題**；AAPL僅2020年3–6月，TSLA僅2019年7月至2020年6月，內文全部缺失。共整合 **2,816筆新聞—股票版本紀錄**；多股票同一URL及文字cluster另存，不把它們當獨立新聞。沒有把100篇來源核對清單再加算一次。全文、供應商摘要和純標題明確分欄，不能混稱全文語料。

其中 **2,296/2,316筆FNSPID時間為00:00:00 UTC（99.14%）**。這不能視為已核實的秒級發布時間，可能只有日期精度；原值保留，precision標成未確認，主要保守對齊改用所列日期之後第一個觀測交易日。此規則只依時間品質制定，未依反轉結果挑選。跨來源共有2,783個不同URL，URL去重與多股票關聯分開保留。

![重建及市場事件支援](figures/01_reconstruction_and_event_support.png)

## 特徵抽取確實完成

- 真正`ProsusAI/finbert`，固定舊研究revision `{FINBERT_REV}`。448篇全文＋52篇摘要有兩種視圖，另2,316筆純標題只做一種視圖，合計 **3,316列特徵**，不偽造缺失內文。
- 共 **{inference['chunk_rows']}個chunk**；每段510內容token加CLS/SEP，使用所有內容token，以原token數加權，**截斷token=0**。逐chunk重建加權機率與特徵檔一致。
- 保留舊V1英文spaCy規則、`en_core_web_sm3.8.0`及53維事件特徵，保存每筆語法事件和品質旗標。未將尚未通過獨立人工核對的V2放行。
- 36篇Gemini只能依**同文章ID＋同text_sha256**接到原摘要版本，不能直接移接到新抓網頁。原存prompt/cache身份核對沿用E4a；未呼叫新Gemini或付費API。
- 新增標題的單一RTX4090前向推論約{inference['seconds']:.1f}秒，PyTorch峰值allocator約{inference['max_allocator_MiB']:.1f}MiB；先前500篇推論另約17.6秒。兩次依序執行，batch8、10%allocator，沒有GPU訓練，沒有處理或終止他人程序。事件解析用CPU。新spaCy依賴只裝在`.venv-e4b`，舊環境未修改。

固定權重不等於原900列特徵逐位元恢復：目前Python3.10／torch2.6／transformers4.48.3與舊報表環境不同；目前tokenizer實作及完整版本另存。舊逐篇輸出不在，不能驗證所有文章原特徵完全相同。

FinBERT為文本positive／negative／neutral，Gemini方向機率亦非5日反轉機率。相同36篇的signed情緒Spearman={comparison['signed_sentiment_Spearman']:.4f}，固定±.1分箱不一致率={comparison['fixed_bin_disagreement_fraction']:.2%}；沒有人工情緒gold，這些差異不是準確率，也不證明哪個模型更好。

![情緒分布與來源差異](figures/02_sentiment_and_source_shift.png)

## 統一資料、版本與重複處理

`news_unified.csv.gz`包含ID、來源、股票、URL、發布日期／時間精度、取得時間、全文／摘要／純標題、文字版本hash及PIT狀態。特徵抽取時的輸入快照另留`news_unified_feature_input.csv.gz`，最終資料補正來源lineage及午夜時間品質旗標，文字、record_id及特徵不變。`article_features.csv`與`unified_finbert_events_gemini.csv`以record_id及text_sha256接合。文件身份、canonical URL、版本與精確文字cluster保存在dedup表；不同版本／全文與摘要不默默合併。新聞窗口內相同文字只計一次；近似標題只標為人工複查候選，不自動認定為同一金融事件。

V1抽的是語法動詞紀錄，可能缺角色、包含AUX／普通動詞、品牌與公司角色混淆、未處理否定／情態／共指。`extraction_quality_summary.csv`報這些結構旗標；它們不是錯誤率或Precision／Recall。**尚無獨立人工事件gold。**建議先在固定100篇審查樣本完成真正人工核對，再決定事件結構能否進入主要預測比較。

## 新聞與市場事件覆蓋

行情、5日next-open反轉標籤、2012–2022門檻、長期趨勢／VIX狀態均沿用E4a／E3c，沒有下載新價格。日期型Apple新聞用發布日期後第一個實際股票交易日；17:00ET截止、過去5資訊交易日含當日。這是**回溯發布時間proxy**，不符合已證實的嚴格歷史PIT。另提供延後1／2資訊日敏感性。最早來源窗口不完整的日期不當作無新聞。

{tab}

上表只描述「目前可重建的Apple企業來源」；不是全部金融新聞覆蓋。跨來源兩檔年別清單在`source_coverage_by_stock_year.csv`，已保留TSLA2019／2020與AAPL2020標題數，以及大量午夜時間旗標；`source_specific_market_event_coverage.csv`另外列出這些標題與價格事件的已知重合。2012–2022未取得的年份、TSLA的Apple來源等保留UNKNOWN／NA，不能因沒抓到資料就當市場沒有新聞。各年surge／crash、長短期衝突／一致、高低VIX的Apple來源分母在`coverage_by_market_event_type.csv`；新聞類型與5日反轉率／signed幅度另有描述表，不用來挑特徵或宣稱因果／預測提升。

上表是原E3c共同樣本按年描述。新E4c方案另要求每年的t+20不跨界，因此2024驗證支援數須看`proposed_2023_2025_split_support.csv`，不能直接拿原2024–2025共同測試區段的2024全部日期當新驗證年。初版支援表及修正原因已保存；沒有訓練或重挑模型。

![各事件類型的來源重合](figures/03_event_type_news_overlap.png)

## 2012–2025兩檔長期來源調查

詳見`data_source_comparison.csv`及保存的公開API／授權稽核。以下是來源的可能範圍，**不是本輪已取得的股票年別完整語料**：

- [FNSPID資料卡](https://huggingface.co/datasets/Zihan1004/FNSPID)：宣稱1999–2023；原CSV5.73GB與23.23GB。{fns} 未補上2024–2025，也沒有歷史first_seen。HF資料卡及LICENSE仍標CC BY-NC4.0，GitHub較新的商用釋出文字與之不一致，應保存版本並釐清，不能假設第三方文章全文已獲相同再散布授權。
- [Benzinga官方](https://www.benzinga.com/apis/)：歷史資料自2009；API可提供created／updated及全文選項。可望涵蓋原時間架構，但本輪無授權登入，AAPL／TSLA實際逐年量、完整版本與交付時間須取得樣本後驗證。
- [LSEG官方MRN文件](https://developers.lseg.com/en/article-catalog/article/machine-readable-news-mrn-n2_ubms-comparison-and-migration-guide)：提供story／take時間；[News Archive](https://solutions.lseg.com/30yearTickHistory)說明Reuters自1996，MRN等產品歷史範圍另依合約。適合優先詢問校內既有授權，仍須核對來源、版本及全文權利。
- [RavenPack官方API](https://github.com/RavenPack/r-api)：歷史analytics自2000，全文Document API另有範圍。需確認學校／WRDS合約，不能把analytics授權視為任意全文授權。
- [Massive官方](https://massive.com/knowledge-base/article/how-far-back-does-massives-news-and-sentiment-data-go)：ticker news最早2016、2021前稀疏，insights自2024；發布時間不是到達／情緒產生時間，無法直接補2012–2015。
- [GDELT官方](https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/)2.0自2015；提供全球新聞metadata，非完整財經全文／ticker映射，較早GDELT事件數不能冒充同格式歷史新聞。
- [AlphaVantage文件](https://www.alphavantage.co/documentation/)有time_from/time_to與limit，但日期參數本身不證明AAPL／TSLA自2012都有完整資料；本輪未使用任何私人key或購買方案。
- [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)可做兩檔長期8-K／公告附檔的獨立公司揭露支線，並有發布／受理證據；它不取代一般財經新聞。

本輪沒有購買訂閱、申請他人權限、繞過登入或付費牆；未宣稱已取得這些商業完整archive。Apple全文及原供應商摘要保存在私有研究結果中，**不得把ZIP視為可公開轉售／散布的授權證明**。[Apple內容條款](https://www.apple.com/legal/internet-services/terms/site.html)

## 下一步可行模型與驗證

原2012–2022訓練設計仍缺同來源、充分完整、可信版本時間的兩檔新聞，**尚不適合正式News-Conditioned Reversal Prediction benchmark**。

可行的獨立分支是`E4C_EXPLORATORY_PROPOSAL.md`：只用同一Apple來源，2023訓練、2024選模／校準、2025探索性評估，保持既有市場事件定義與next-open5日標籤。各年可用事件數已算出，訓練期只有數十個事件，不足以支持事件專家深度網路。先做train-only歷史／階層收縮機率與低維全日期ridge LogisticRegression；P／S／T用完全相同日期、固定小搜尋及相同校準。XGBoost、LSTM、Mamba暫緩。

主要以配對Brier、HAC20／日期區塊20 bootstrap、block60敏感性與Holm評估；同狀態AUC要有至少20事件、10／10標籤及20配對才推論。區分機率校準／平均機率與真正時機排序。所有2023–2025已檢視，只能探索性。這份方案本輪未執行模型。

## 保留與可重現

E1–E4a成果及2026協定hash均核對不變，2026驗證未執行。延續E4a已公開的舊ZIP盤點意外接觸紀錄，不重新宣稱2026完全未被看過；本輪僅蒐集、抽取、統計<=2025資料。

產物包含原始HTTP／新全文、舊摘要及FNSPID標題分區、統一資料／特徵、{inference['chunk_rows']}chunk cache、每筆V1事件、版本核對／重複候選、股票年別與事件組別覆蓋、來源與授權稽核、四組PNG／PDF、環境／模型版本、程式與完整ZIP。模型權重約440MB保留在專用快取，不重複塞入結果ZIP；固定revision與權重hash、下載方法均保存。離線分析可用保存的chunk／事件與特徵重播，不需API或GPU。
'''
    (out/'E4B_SUMMARY.md').write_text(text)


def archive(out):
    skip={'e4b_complete_results.zip','e4b_complete_results.zip.sha256','archive_manifest.json','status.json'}
    files=[p for p in out.rglob('*') if p.is_file() and p.name not in skip and not p.name.endswith('.tmp') and '.matplotlib' not in p.parts]
    dump(out/'archive_manifest.json',{'algorithm':'sha256','files':{str(p.relative_to(out)):sha(p) for p in sorted(files)}})
    files.append(out/'archive_manifest.json');zp=out/'e4b_complete_results.zip'
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED,compresslevel=5,allowZip64=True) as z:
        for p in sorted(files):z.write(p,str(Path(out.name)/p.relative_to(out)))
    with zipfile.ZipFile(zp) as z:assert z.testzip() is None
    (out/'e4b_complete_results.zip.sha256').write_text(sha(zp)+'  '+zp.name+'\n');return zp


def run(out,replay=False):
    data,ft=validate(out,verify_previous=not replay);data=finalize_metadata(out,data);quality(out,data,ft);primary,coverage=align(out,data,ft);support=proposal(out,primary)
    plots(out,data,ft,coverage);report(out,support,coverage)
    if not replay:
        for name in ('e4b_core.py','recover_e4b_news.py','extract_e4b_features.py','finalize_e4b_features.py','probe_e4b_fnspid.py','analyze_e4b.py','test_e4b.py'):
            shutil.copyfile(ROOT/'scripts'/name,out/'code'/name)
        env={'python':sys.version,'executable':sys.executable,'packages':{n:importlib.metadata.version(n) for n in ('torch','transformers','spacy','en-core-web-sm','numpy','pandas','scipy','scikit-learn')},'new_environment':'.venv-e4b','previous_environments_modified':False}
        dump(out/'environment.json',env);(out/'environment.lock.txt').write_text(subprocess.check_output([sys.executable,'-B','-m','pip','freeze'],text=True))
        shutil.copyfile(ROOT/'README_E4B.md',out/'README_E4B.md')
        own=subprocess.check_output([sys.executable,'-B','-m','pip','list','--path',str(ROOT/'.venv-e4b/lib/python3.10/site-packages'),'--format=freeze'],text=True)
        own=re.sub(r'(?im)^en[-_]core[-_]web[-_]sm==[^\n]+','en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl',own)
        (out/'requirements-e4b-extra.lock.txt').write_text(own)
        for src,dst in [('logs/e4b_collect.log','collection.log'),('logs/e4b_features.log','feature_inference.log'),('logs/e4b_features_additional.log','additional_feature_inference_and_join_failure.log'),('logs/e4b_tests_final.log','dataset_tests.log'),('logs/e4b_environment.log','environment_setup.log'),('logs/e4b_fnspid.log','fnspid_initial_failure.log'),('logs/e4b_fnspid_revised_parser.log','fnspid_parser_diagnostic.log'),('logs/e4b_fnspid_blank_ticker_audit.log','fnspid_bounded_audit.log')]:
            if (ROOT/src).exists():shutil.copyfile(ROOT/src,out/'logs'/dst)
        dump(out/'code_manifest.json',{str(p.relative_to(out)):sha(p) for p in (out/'code').rglob('*') if p.is_file()})
        dump(out/'input_manifest.json',{str(p.relative_to(out)):sha(p) for folder in ('inputs','raw','features') for p in (out/folder).rglob('*') if p.is_file()})
        dump(out/'COMPLETION.json',{'status':'COMPLETE_DATA_RECOVERY','news_records':len(data),'news_predictors_trained':0,'strict_historical_PIT_claim':False,'2026_validation_run':False})
        zp=archive(out);shutil.copyfile(out/'E4B_SUMMARY.md',ROOT/'E4B_SUMMARY.md')
        dump(ROOT/'E4B_CURRENT_RUN.json',{'status':'COMPLETE_DATA_RECOVERY','output':str(out),'zip':str(zp),'zip_sha256':sha(zp),'summary':str(out/'E4B_SUMMARY.md'),'2026_validation_run':False})
    print('E4b ANALYSIS COMPLETE',out)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);p.add_argument('--replay',action='store_true');a=p.parse_args();run(a.out.resolve(),a.replay)
