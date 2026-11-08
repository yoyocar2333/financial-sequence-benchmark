"""Append the user-located Phase7A52-article pilot without altering frozen studies.

Only three explicitly dated historical CSV members and the36 matching cache
members are read. No2026 article, market CSV, credentials or arbitrary ZIP code.
"""
import argparse
import csv
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import hashlib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from e4a_core import ROOT,sha,dump,now,strict_availability,cutoff_utc,map_available,TYPES
from run_e4a import archive,verify_previous
from freeze_e3c_2026 import check

BASE=ROOT/'outputs/e4a_20261026_v1_1'
ZIP=ROOT/'data/market_20261019/raw/StockLLM_phase7A.zip'
OUT=ROOT/'outputs/e4a_20261026_phase7a'
FILES=['data/processed/AAPL_news_historical_smoke.csv','data/processed/AAPL_llm_historical_resume.csv','data/processed/AAPL_llm_historical_smoke.csv']
REQUESTED=['data/raw/apple_public_v1/apple_newsroom_articles.csv','outputs/apple_public_v1/article_manifest.csv','outputs/apple_public_v1/article_features.csv','outputs/apple_public_v1/finbert_chunks.jsonl']


def initialize(out):
    if out.exists(): raise FileExistsError('Preserve existing delivery')
    manifest=json.loads((BASE/'archive_manifest.json').read_text())['files']
    for p,h in manifest.items():
        if sha(BASE/p)!=h: raise RuntimeError('Base result changed: '+p)
    shutil.copytree(BASE,out,ignore=shutil.ignore_patterns('e4a_complete_results.zip','e4a_complete_results.zip.sha256','archive_manifest.json','status.json','.matplotlib'))
    shutil.copyfile(BASE/'E4A_SUMMARY.md',out/'inputs/E4A_GITHUB_ONLY_SUMMARY.md')
    shutil.copyfile(BASE/'input_manifest.json',out/'inputs/E4A_GITHUB_ONLY_INPUT_MANIFEST.json')
    shutil.copyfile(BASE/'evaluation_plan.json',out/'inputs/E4A_ORIGINAL_DESIGN_LOCK.json')
    shutil.copyfile(ROOT/'scripts/extend_e4a_phase7a.py',out/'code/extend_e4a_phase7a.py')
    plan={'version':'E4a-1.1-Phase7A-coverage-extension','created_utc':now(),'status':'LOCKED_BEFORE_EVENT_OUTCOME_ALIGNMENT',
        'reason':'User identified additional local ZIP after GitHub-only feasibility study; original outputs and2026protocol preserved',
        'base_archive_sha256':sha(BASE/'e4a_complete_results.zip'),'source_zip_sha256':sha(ZIP),'allowed_members':FILES,
        'analysis_end':'2025-12-31','original_train_cal_test_and_complexity_gates':'unchanged; no news training if2012-2022 support=0',
        'news_universe':'52 historical AAPL rows,36 annotated outputs; no assumption that this is a complete provider/news sample',
        'timing_tiers':['strict version availability: still unverified','publisher timestamp proxy available by fixed17:00ET cutoff, not certified PIT'],
        'sensitivity':['publisher+60minutes','publisher proxy deferred1 observed information session'],
        'aggregation':'past5 information sessions inclusive event date; equal mean of AVAILABLE Gemini sentiment only, report annotation fraction; missing !=neutral; no direction_probability as reversal forecast',
        'polarity_bins':'negative < -.1, neutral/mixed [-.1,.1], positive > .1; event-aligned if event_direction*mean_sentiment>.1; opposed if<-.1',
        'types':'fixed6 broad types: regulation if regulation/regulatory; else litigation if legal/lawsuit/litigation; else earnings if earnings/results; else M&A if merger/acquisition/M&A; else product_launch if product/launch; else other. Original unconstrained type strings preserved; no gold accuracy claim',
        'summaries':'all event reversals/signed log-pp amplitude, positive-only magnitude, same price-state cells; descriptive only unless independent support gates met',
        'inference':'Keep original8Brier+4ranking hypotheses NOT_ESTIMABLE without train support. Proxy sentiment association requires >=20 dates per contrast side,10/class overall,20 within-state pairs and block20/60 analysis; otherwise rates only, no p or binomial IID CIs',
        'model_fit':'none; reuse E3c predictions as contextual error audit only, no news-vs-price predictive superiority claim',
        '2026_protocol':'exact original9ffe3c31bbfabb6609ee69dde1deab7a13729b43511a9c045d945b5b03453940 bytes; no refreeze, retraining or validation',
        'text_scope':'Alpha Vantage summary content, not certified full article body; no Gemini calls/FinBERT download'}
    dump(out/'PHASE7A_EXTENSION_LOCK.json',plan)
    dump(out/'holdout_handling_audit.json',{'recorded_utc':now(),'incident':'ZIP inventory date-column heuristic matched sentiment and displayed aggregate2026sentiment distributions from legacy CSVs before filtering was tightened',
        'exposed':'2026 file/date metadata and aggregate sentiment counts; no article body/title, market-price values, return/target labels or forecast accuracy inspected',
        'research_use':'No2026rows enter any E4a dataset, label, statistic, model, choice or plot;2026validation not executed',
        'mitigation':'Only explicit historical file whitelist; date filtering before converting/printing non-date columns; read cache only after matching2025article hashes; do not read the other ZIP datasets',
        'protocol_relation':'Price-only2026protocol was hash-locked BEFORE the incident and remains byte-identical. Cannot claim no2026news-feature exposure; final independent-period eligibility requires team access audit/attestation. No rule/model adjustment based on exposed aggregates.'})


def extract_historical(out):
    d=out/'inputs/phase7a';d.mkdir()
    hashes={};raws={}
    with zipfile.ZipFile(ZIP) as z:
        names=set(z.namelist());presence={p:any(n.endswith(p) for n in names) for p in REQUESTED}
        for rel in FILES:
            name='StockLLM_phase7A/'+rel;content=z.read(name)
            rows=list(csv.DictReader(io.StringIO(content.decode('utf-8-sig'))))
            assert rows and all(r['timestamp'][:10]<='2025-12-31' for r in rows)
            assert all(r['ticker']=='AAPL' for r in rows)
            p=d/Path(rel).name;p.write_bytes(content);hashes[rel]=sha(p);raws[Path(rel).name]=pd.read_csv(p)
        prompt=z.read('StockLLM_phase7A/prompts/llm_only.txt').decode()
        (d/'prompt_original.txt').write_text(prompt)
        client=z.read('StockLLM_phase7A/llm/client.py').decode().splitlines()
        (d/'cache_key_algorithm.txt').write_text('\n'.join(client[33:38])+'\n')
        source=z.read('StockLLM_phase7A/data/extract_news_alpha_vantage.py').decode()
        # This source uses env/argument credentials; no credential values exported.
        (d/'historical_extractor_source.py.txt').write_text(source)
        anno=raws['AAPL_llm_historical_resume.csv'];proof=[];cache=d/'matched2025_cache';cache.mkdir()
        for row in anno.to_dict('records'):
            article={k:row[k] for k in ('ticker','timestamp','information_date','title','content','source','url')}
            encoded=json.dumps({'prompt':prompt,'article':article,'model':'gemini-3.5-flash'},sort_keys=True,ensure_ascii=False).encode()
            key=hashlib.sha256(encoded).hexdigest();member='StockLLM_phase7A/data/processed/llm_cache/'+key+'.json'
            if member not in names: raise RuntimeError('Historical cache proof missing '+row['article_id'])
            content=z.read(member);signal=json.loads(content)
            for k in ('sentiment','confidence','importance','market_relevance','direction_probability'):
                np.testing.assert_allclose(float(signal[k]),float(row[k]),atol=1e-12)
            for k in ('event_type','reason','time_horizon','risk_level'): assert signal[k]==row[k]
            p=cache/(key+'.json');p.write_bytes(content)
            proof.append({'article_id':row['article_id'],'cache_key':key,'cache_sha256':sha(p),'model_string_proven_by_key':'gemini-3.5-flash','server_revision_verified':False,'prompt_sha256':sha(d/'prompt_original.txt'),'output_matches_csv':True})
        pd.DataFrame(proof).to_csv(out/'tables/phase7a_cache_identity_audit.csv',index=False)
    raw=raws['AAPL_news_historical_smoke.csv'];anno=raws['AAPL_llm_historical_resume.csv'];smoke=raws['AAPL_llm_historical_smoke.csv']
    assert len(raw)==52 and len(anno)==36 and len(smoke)==18
    assert raw.article_id.is_unique and anno.article_id.is_unique and set(anno.article_id)<=set(raw.article_id)
    a=raw.set_index('article_id');b=anno.set_index('article_id')
    for c in ('title','content','timestamp','source','url'):
        np.testing.assert_array_equal(a.loc[b.index,c],b[c])
    for row in smoke.itertuples(): np.testing.assert_allclose(row.sentiment,b.loc[row.article_id,'sentiment'],atol=1e-12)
    dump(out/'phase7a_source_audit.json',{'zip_path_relative_to_project':str(ZIP.relative_to(ROOT)),'zip_sha256':sha(ZIP),'requested_public_v1_members_found':presence,
        'historical_news_rows':52,'Gemini_rows':36,'smoke_rows':18,'smoke_rows_are_subset_not_additional':True,'matching_historical_cache_files':36,
        'FinBERT_features_present':False,'Gemini_model_string':'gemini-3.5-flash','server_revision_or_training_cutoff_verified':False,
        'prompt_text_only':True,'recovered_outputs_status':'cache-key/CSV identity verified, not independent proof of server inference/absence of model contamination',
        'content_field':'historical extractor uses Alpha Vantage summary, not full article scraping','members_sha256':hashes,
        'preserved_raw_zip_unmodified':True,'no_other_raw_market_or_news_members_loaded_for_analysis':True})
    return raw,anno


def mapped_type(value):
    s=str(value).casefold()
    if 'regulat' in s: return 'regulation'
    if any(x in s for x in ('legal','lawsuit','litigat')): return 'litigation'
    if any(x in s for x in ('earnings','results')): return 'earnings'
    if any(x in s for x in ('merger','acquisition','m&a')): return 'merger_acquisition'
    if any(x in s for x in ('product','launch')): return 'product_launch'
    return 'other'


def align(out,raw,anno):
    market=pd.read_csv(out/'aligned/market_news_alignment.csv.gz');old_events=pd.read_csv(out/'aligned/event_news_features.csv')
    price=pd.read_csv(out/'inputs/AAPL_adjusted_through2025.csv');sessions=pd.DatetimeIndex(pd.to_datetime(price.Date))
    ann=anno.set_index('article_id');rows=[];audit=[]
    for row in raw.to_dict('records'):
        pub=pd.Timestamp(row['timestamp']);assert pub.tzinfo is not None and pub.year<=2025
        original=pd.Timestamp(row['information_date']);proxy=map_available(pub,sessions)
        legacy=row['article_id'] in ann.index
        score=float(ann.loc[row['article_id'],'sentiment']) if legacy else np.nan
        typ=str(ann.loc[row['article_id'],'event_type']) if legacy else None
        r={k:row[k] for k in ('article_id','ticker','title','content','source','url')}
        r.update(publication_date=pub.tz_convert('America/New_York').strftime('%Y-%m-%d'),published_utc=pub.isoformat(),version_seen_utc=None,availability_evidence=None,
            historical_text_revision_verified=False,text_sha256=hashlib.sha256((row['title']+'\n\n'+row['content']).encode()).hexdigest(),
            original_information_date=row['information_date'],publisher_proxy_date=proxy.strftime('%Y-%m-%d'),
            proxy_plus60_date=map_available(pub+pd.Timedelta(minutes=60),sessions).strftime('%Y-%m-%d'),
            proxy_defer1_date=sessions[sessions.get_loc(proxy)+1].strftime('%Y-%m-%d'),
            Gemini_annotated=legacy,Gemini_sentiment=score,Gemini_original_type=typ,Gemini_mapped_type=mapped_type(typ) if legacy else None,
            Gemini_relevance=float(ann.loc[row['article_id'],'market_relevance']) if legacy else np.nan,
            Gemini_confidence=float(ann.loc[row['article_id'],'confidence']) if legacy else np.nan,
            strict_eligible=False,annotation_scope='partial36/52, temporally truncated, not random')
        assert strict_availability(r)[0] is None
        rows.append(r)
        audit.append({'article_id':row['article_id'],'published_utc':pub.isoformat(),'legacy_information_date':row['information_date'],
            'legacy_information_date_is_observed_session':original in sessions,'repaired_legacy_session':sessions[sessions.searchsorted(original)].strftime('%Y-%m-%d'),
            'publisher_proxy_17ET_session':proxy.strftime('%Y-%m-%d'),'old_16ET_vs_new17ET_rule_differ':row['information_date']!=proxy.strftime('%Y-%m-%d'),
            'strict_PIT_verified':False})
    news=pd.DataFrame(rows);news.drop(columns=['content','title']).to_csv(out/'aligned/phase7a_article_features_provenance.csv',index=False)
    pd.DataFrame(audit).to_csv(out/'tables/phase7a_timing_audit.csv',index=False)
    frames=[];joins=[]
    for timing,column in [('publisher_proxy','publisher_proxy_date'),('plus60minutes','proxy_plus60_date'),('defer1session','proxy_defer1_date')]:
        n=news.copy();n['_date']=pd.to_datetime(n[column])
        for event in old_events.itertuples():
            d=pd.Timestamp(event.date)
            if event.ticker!='AAPL': continue
            i=sessions.get_loc(d);start=sessions[max(0,i-4)]
            included=n[n._date.between(start,d)];labeled=included[included.Gemini_annotated]
            sentiment=float(labeled.Gemini_sentiment.mean()) if len(labeled) else np.nan
            polarity='unavailable' if not len(labeled) else 'positive' if sentiment>.1 else 'negative' if sentiment<-.1 else 'neutral_mixed'
            aligned='unavailable' if not len(labeled) else 'aligned' if event.event_direction*sentiment>.1 else 'opposed' if event.event_direction*sentiment<-.1 else 'neutral_mixed'
            rec={'ticker':'AAPL','date':event.date,'partition':event.partition,'timing_assumption':timing,'cell':event.cell,'event_direction':event.event_direction,
                'conflict':event.conflict,'VIX_high':event.VIX_high,'future_y5':event.future_y5,'future_signed_reversal_amplitude_pp':event.future_signed_reversal_amplitude_pp,
                'known52_articles_last5':len(included),'annotated36_articles_last5':len(labeled),'annotation_fraction_of_known52':len(labeled)/len(included) if len(included) else np.nan,
                'Gemini_sentiment_mean':sentiment,'sentiment_polarity':polarity,'sentiment_vs_event':aligned,'strict_model_eligible':False,'source_collection_complete':False}
            for typ in TYPES: rec['type_'+typ+'_present']=bool((labeled.Gemini_mapped_type==typ).any())
            frames.append(rec)
            if timing=='publisher_proxy':
                for art in n.itertuples():
                    j=sessions.get_loc(pd.Timestamp(art.publisher_proxy_date));lag=j-i
                    if -5<=lag<=5:
                        joins.append({'ticker':'AAPL','event_date':event.date,'partition':event.partition,'article_id':art.article_id,'published_utc':art.published_utc,
                            'publisher_proxy_date':art.publisher_proxy_date,'relative_information_session':lag,'prediction_window_last5':-4<=lag<=0,
                            'post_event':lag>0,'Gemini_annotated':art.Gemini_annotated,'Gemini_sentiment':art.Gemini_sentiment,
                            'Gemini_original_type':art.Gemini_original_type,'Gemini_mapped_type':art.Gemini_mapped_type,'strict_model_input':False,
                            'alignment_tier':'PUBLISHER_TIMESTAMP_PROXY_NO_VERSION_EVIDENCE'})
    e=pd.DataFrame(frames);e.to_csv(out/'aligned/phase7a_event_features.csv',index=False)
    pd.DataFrame(joins).to_csv(out/'aligned/phase7a_news_event_alignment.csv',index=False)
    # Main alignment remains explicit about unavailable strict news. New proxy columns
    # have their own scope; no false replacement of strict count or missing FinBERT.
    main=e[e.timing_assumption.eq('publisher_proxy')]
    cols=['ticker','date','known52_articles_last5','annotated36_articles_last5','annotation_fraction_of_known52','Gemini_sentiment_mean','sentiment_polarity','sentiment_vs_event']
    events=old_events.merge(main[cols],on=['ticker','date'],how='left',validate='one_to_one')
    events.to_csv(out/'aligned/event_news_features.csv',index=False)
    market=market.merge(main[cols],on=['ticker','date'],how='left',validate='one_to_one')
    market.to_csv(out/'aligned/market_news_alignment.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    old_meta=pd.read_csv(out/'aligned/news_metadata_normalized.csv')
    new_meta=news.drop(columns=['content','title']).copy();new_meta['timestamp_precision']='timezone_aware_published_only';new_meta['eligible_for_model']=False
    pd.concat([old_meta,new_meta],ignore_index=True).to_csv(out/'aligned/news_metadata_normalized.csv',index=False)
    return news,e,pd.DataFrame(audit)


def describe(out,news,events):
    results=[];sensitivity=[]
    for timing,e in events.groupby('timing_assumption',sort=False):
        known=e[e.known52_articles_last5.gt(0)];ann=e[e.annotated36_articles_last5.gt(0)]
        thinning=0;last=-10**9
        dates=pd.to_datetime(pd.read_csv(out/'inputs/AAPL_adjusted_through2025.csv').Date)
        for d in pd.to_datetime(ann.date):
            i=int(np.searchsorted(dates,d))
            if i-last>=5: thinning+=1;last=i
        sensitivity.append({'timing_assumption':timing,'known_news_events':len(known),'annotated_news_events':len(ann),'five_session_thinned_annotated_events':thinning,
            'annotated_reversals':int(ann.future_y5.sum()),'annotated_reversal_rate':ann.future_y5.mean() if len(ann) else np.nan,
            'status':'DESCRIPTIVE_PUBLISHED_TIME_PROXY_NOT_STRICT_PIT'})
        groups={'all_annotated':ann,'surge':ann[ann.event_direction.eq(1)],'crash':ann[ann.event_direction.eq(-1)],
            'conflict':ann[ann.conflict.eq(1)],'aligned_trend':ann[ann.conflict.eq(0)],'high_VIX':ann[ann.VIX_high.eq(1)],'low_VIX':ann[ann.VIX_high.eq(0)]}
        for p in ('positive','negative','neutral_mixed'): groups['sentiment_'+p]=ann[ann.sentiment_polarity.eq(p)]
        for p in ('aligned','opposed','neutral_mixed'): groups['sentiment_vs_event_'+p]=ann[ann.sentiment_vs_event.eq(p)]
        for typ in TYPES: groups['type_'+typ]=ann[ann['type_'+typ+'_present']]
        for label,z in groups.items():
            amp=z.future_signed_reversal_amplitude_pp
            results.append({'ticker':'AAPL','timing_assumption':timing,'group':label,'event_n':len(z),'reversals':int(z.future_y5.sum()),
                'reversal_probability':z.future_y5.mean() if len(z) else np.nan,'signed_amplitude_mean_pp':amp.mean() if len(z) else np.nan,
                'reversal_only_magnitude_mean_pp':amp[amp>0].mean() if (amp>0).any() else np.nan,
                'status':'DESCRIPTIVE_SMALL_SAMPLE_NON_PIT','p_value':np.nan,'ci_low':np.nan,'ci_high':np.nan})
    stats=pd.DataFrame(results);stats.to_csv(out/'tables/phase7a_conditional_outcomes.csv',index=False)
    pd.DataFrame(sensitivity).to_csv(out/'tables/phase7a_timing_sensitivity.csv',index=False)
    main=events[events.timing_assumption.eq('publisher_proxy')&events.annotated36_articles_last5.gt(0)].copy()
    main.groupby(['cell','sentiment_vs_event']).agg(event_n=('future_y5','size'),reversals=('future_y5','sum'),reversal_probability=('future_y5','mean'),signed_amplitude_mean_pp=('future_signed_reversal_amplitude_pp','mean')).reset_index().to_csv(out/'tables/phase7a_within_state_support.csv',index=False)
    # The whole pilot, not just fitted outputs, is audited for company relevance.
    news.groupby(['Gemini_annotated','Gemini_mapped_type'],dropna=False).size().rename('articles').reset_index().to_csv(out/'tables/phase7a_article_types.csv',index=False)
    news[['article_id','Gemini_annotated','Gemini_relevance','Gemini_confidence']].to_csv(out/'tables/phase7a_annotation_relevance.csv',index=False)
    pred=pd.read_csv(out/'aligned/existing_price_predictions.csv.gz');records=[]
    for (method,seed),z in pred[pred.ticker.eq('AAPL')].groupby(['method','seed']):
        a=main[['date','future_y5']].merge(z,on='date',validate='one_to_one')
        if not len(a): continue
        np.testing.assert_array_equal(a.future_y5,a.target)
        p=a.p.to_numpy();y=a.target.to_numpy()
        records.append({'ticker':'AAPL','method':method,'seed':seed,'known_annotated_proxy_event_dates':len(a),'mean_predicted_reversal_probability':p.mean(),
            'observed_reversal_rate':y.mean(),'Brier':np.mean((p-y)**2),'ROC_AUC':roc_auc_score(y,p) if len(np.unique(y))==2 else np.nan,
            'status':'LEGACY_PRICE_ONLY_MODEL_CONTEXT_NOT_NEWS_INTEGRATION'})
    pd.DataFrame(records).to_csv(out/'tables/phase7a_existing_price_error_audit.csv',index=False)
    dump(out/'PHASE7A_INFERENCE_STATUS.json',{'news_model_training':False,'2012_2022_news_feature_train_events':0,'TSLA_news_articles':0,
        'FinBERT_scored_articles':0,'Gemini_scored_articles':36,'strict_verified_articles':0,'news_effect_test_status':'NOT_ESTIMABLE',
        'association_status':'Descriptive only; few event dates, clustered overlapping5day outcomes, missing16 annotations, no source-version availability proof',
        'no_new_predictor_or_news_effect_claim':True})
    return stats,pd.DataFrame(sensitivity)


def plots(out,news,events,stats):
    import os
    os.environ.setdefault('MPLCONFIGDIR',str(out/'.matplotlib'))
    for p in (Path.home()/'.local/lib/python3.10/site-packages',Path('/usr/local/lib/python3.10/dist-packages'),Path('/usr/lib/python3/dist-packages')):
        if p.exists(): sys.path.append(str(p))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    def save(fig,name):
        for ext in ('png','pdf'): fig.savefig(out/'figures'/(name+'.'+ext),bbox_inches='tight',dpi=180)
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,5))
    labels=['Real metadata: GitHub2023 + Phase7A2025','Phase7A2025 news summaries','Phase7A Gemini outputs/cache verified','FinBERT article features recovered','Strict historical version availability','2012-2022 news-feature training events']
    values=[152,52,36,0,0,0];ys=np.arange(len(values));ax.barh(ys,values,color=['#296c70','#52879c','#d59653']+['#ccc']*3);ax.invert_yaxis();ax.set_yticks(ys,labels)
    for i,v in enumerate(values): ax.text(v+2,i,str(v),va='center')
    ax.set(xlim=(0,175),xlabel='Supplied / verified records (not total market-news activity)',title='E4a updated feasibility after recovering Phase7A ZIP')
    save(fig,'03_feasibility_gates')
    fig,ax=plt.subplots(2,1,figsize=(11,6.5),sharex=True)
    dates=pd.to_datetime(news.publisher_proxy_date);a=news.assign(date=dates).groupby('date').agg(known=('article_id','size'),annotated=('Gemini_annotated','sum'))
    ax[0].bar(a.index,a.known,width=.8,color='#588395',label='Known52 article universe');ax[0].bar(a.index,a.annotated,width=.45,color='#d59653',label='Gemini36 annotated subset');ax[0].legend(fontsize=9)
    ax[0].set(ylabel='Articles per assumed information session',title='Phase7A: partial Gemini annotation and overlapping event windows')
    e=events[events.timing_assumption.eq('publisher_proxy')&events.known52_articles_last5.gt(0)]
    ann=e[e.annotated36_articles_last5.gt(0)]
    ax[1].scatter(pd.to_datetime(ann.date),ann.Gemini_sentiment_mean,c='#296c70',s=45,label='Past5-session mean available Gemini sentiment')
    missing=e[e.annotated36_articles_last5.eq(0)]
    ax[1].scatter(pd.to_datetime(missing.date),np.zeros(len(missing)),marker='x',color='#999',label='No annotation (position is placeholder, not neutral)')
    ax[1].axhline(0,color='#aaa',lw=.8);ax[1].set(ylabel='Text sentiment, NOT reversal probability',xlabel='AAPL price-event date / publisher-time proxy');ax[1].legend(fontsize=8)
    for a in ax: a.grid(axis='y',alpha=.15)
    fig.autofmt_xdate();fig.tight_layout();save(fig,'05_phase7a_annotation_timeline')
    z=stats[stats.timing_assumption.eq('publisher_proxy')&stats.group.isin(['all_annotated','sentiment_positive','sentiment_negative','sentiment_neutral_mixed','sentiment_vs_event_aligned','sentiment_vs_event_opposed'])].copy()
    fig,ax=plt.subplots(figsize=(10,4.8));x=np.arange(len(z));ax.scatter(x,z.reversal_probability,color='#296c70',s=60)
    for i,r in enumerate(z.itertuples()): ax.text(i,(r.reversal_probability if np.isfinite(r.reversal_probability) else .5)+.05,f'n={r.event_n}',ha='center')
    ax.set(xticks=x,xticklabels=[s.replace('sentiment_vs_event_','vs event: ').replace('sentiment_','').replace('all_annotated','all annotated') for s in z.group],ylim=(-.05,1.2),ylabel='Observed5-session reversal fraction',title='Tiny event-conditioned Gemini subset: descriptive, no significance claim')
    ax.grid(axis='y',alpha=.15);fig.tight_layout();save(fig,'06_phase7a_conditional_reversal')
    html=(out/'figures/index.html').read_text()
    html+='<h2>Phase7A extension: publisher-time proxies, not verified PIT</h2>'
    for name in ('05_phase7a_annotation_timeline','06_phase7a_conditional_reversal'): html+=f'<a href="{name}.pdf">PDF</a><img src="{name}.png" alt="{name}">'
    (out/'figures/index.html').write_text(html)


def report(out,news,events,audit,stats,sensitivity):
    original=(out/'inputs/E4A_GITHUB_ONLY_SUMMARY.md').read_text()
    main=sensitivity[sensitivity.timing_assumption.eq('publisher_proxy')].iloc[0]
    assoc=stats[stats.timing_assumption.eq('publisher_proxy')&stats.group.isin(['all_annotated','sentiment_positive','sentiment_negative','sentiment_neutral_mixed','sentiment_vs_event_aligned','sentiment_vs_event_opposed'])]
    tab='| 新聞條件 | 事件數 | 反轉數 | 反轉率 | 平均signed反轉幅度(log百分點) |\n|---|---:|---:|---:|---:|\n'
    for r in assoc.itertuples():
        rate=f'{r.reversal_probability:.2%}' if np.isfinite(r.reversal_probability) else 'NA'
        amp=f'{r.signed_amplitude_mean_pp:.4f}' if np.isfinite(r.signed_amplitude_mean_pp) else 'NA'
        tab+=f'| {r.group} | {r.event_n} | {r.reversals} | {rate} | {amp} |\n'
    bad=int((~audit.legacy_information_date_is_observed_session).sum())
    text=f'''# E4a — News-Conditioned Reversal Study（Phase7A資料補查完成）

**完成資料覆蓋、時間對齊、部分Gemini新聞條件描述、價格模型誤差稽核與可重現封裝。仍無足夠資料估計新聞的新增預測能力。**本輪沒有訓練新聞模型，也沒有使用2026列計算任何模型或研究結果。E1–E3c、前一份GitHub-only E4a、原始ZIP及已固定2026協定均保留。

## 找到的資料與未找到的資料

依使用者提示，找到 `data/market_20261019/raw/StockLLM_phase7A.zip`（SHA256 `6455aaf1302bc68e4b61cd9204f5f5c01024683613d022f83a3684b24909fb87`）。ZIP內**沒有**指定的四個apple_public_v1檔案：apple_newsroom_articles.csv、article_manifest.csv、article_features.csv、finbert_chunks.jsonl。

但確實有另一批可用歷史資料：

| 來源 | 可逐篇核對資料 | 時段／限制 |
|---|---:|---|
| GitHub抽取審查清單 | 100篇metadata | AAPL2023，152篇母體的固定隨機子樣本；無逐篇情緒 |
| Phase7A historical_smoke | 52篇新聞摘要 | AAPL2025-01-02至01-31；不是全年語料 |
| Phase7A Gemini resume | 36篇逐篇輸出 | 52篇中的前段子集，69.23%；16篇未完成，不可當中立 |
| Phase7A Gemini smoke | 18篇 | 已含於36篇，不能加總成54篇 |
| 真正FinBERT逐篇輸出 | 0篇 | 不是FinBERT計算失敗，而是此ZIP未提供 |
| 2012–2022新聞訓練／TSLA語料 | 0篇提供 | 仍無法沿用原分割訓練新聞模型 |

GitHub450篇AAPL企業新聞及900列特徵仍只有公開彙總，完整原文及特徵未找到。本輪實際來源是100篇2023metadata＋52篇2025摘要，不能聲稱找回450篇。Phase7A extractor把Alpha Vantage `summary`放進`content`，並不是已核實的完整新聞本文；provider/ticker關聯亦不保證文章主要討論Apple。

原ZIP保持不動；只讀取明確的2025歷史CSV與可匹配的36個cache，不執行舊程式、不安裝套件、不呼叫付費API、不用舊市場CSV／舊Target。使用者原始資料是私有研究輸入，僅此本機結果ZIP收錄白名單2025輸入，不重新發布到GitHub。

## Gemini輸出身份與PIT限制

36篇的prompt、完整文章字典及model字串重建SHA256，均命中原cache，逐一與CSV的機率、情緒、事件類型及reason核對一致。可證明cache key使用 `gemini-3.5-flash`，但**不能獨立證明當年服務端精確revision、訓練截止或推論來源**。上游沒有歷史first_seen、內文版本可核對證據或推論時戳，仍屬回溯抽取，不是已證明當時可部署的模型。

這批52篇有具時區的發布時間，可改善日期精度，卻仍缺實際取得時間與歷史版本證據；100篇2023清單則只有日期。嚴格PIT已驗證文章仍為0，表示證據不足，不代表市場沒有新聞。`strict_news_count`維持NA，不能把缺資料填0。

固定17:00 America/New_York cutoff，沿用E3c次交易日Open至t+5Close的反轉標籤。發布時間proxy只是假設可用，不是first_seen證明。敏感性固定為發布+60分鐘與延後1個資訊交易日，不以結果挑最佳規則。原`information_date`有{bad}筆不是實際股票交易日；本輪以凍結行情的觀測交易日重新映射，保留舊日期、修復日期及16時／17時規則差異供稽核。未把舊10日／2%目標、次日方向機率或Gemini direction_probability當5日反轉機率。

![更新後新聞可行性](figures/03_feasibility_gates.png)

## 新聞條件下的5日反轉：僅小樣本描述

沿用2012–2022訓練門檻、長期context120_ex5及VIX狀態、2012–2022／2023／2024–2025時間架構；測試482日期與E3c一致。事件新聞窗口固定過去5資訊交易日含當日。52篇已知新聞與{int(main.known_news_events)}個AAPL價格事件有重合，其中{int(main.annotated_news_events)}個事件可計算部分Gemini摘要情緒；按5日間隔取首事件後只剩{int(main.five_session_thinned_annotated_events)}個事件。

{tab}

sentiment_positive/negative依窗口平均情緒>.1／<-.1；其餘neutral_mixed。vs_event aligned表示情緒與急漲跌同向，opposed表示逆向；這些是**新聞與已知過去趨勢的關係**，不使用未來標籤分組。signed幅度正值代表反轉、負值代表延續；反轉發生者的條件幅度另存CSV，不與反轉概率混淆。

這些事件大量重疊、來自單一短月份，未完成的16篇位於較後日期，缺失不是隨機；同一篇摘要也可能進多個事件窗口。不同組別同時混有價格狀態與時間段差異。**不能據此判定情緒有效、無效或因果解釋反轉，更不能將表內比例當預測成績。**不報IID二項信賴區間，不對小樣本湊顯著性。

![部分標註時間與事件](figures/05_phase7a_annotation_timeline.png)

![小樣本條件反轉比例](figures/06_phase7a_conditional_reversal.png)

36篇產生多種自由文字event_type，本輪保留原字串並依固定規則映射到regulation/litigation/earnings/M&A/product_launch/other六類；不是人工核實的事件真值，也不能把M&A speculation等同已發生收購。逐類反轉率、幅度、同價格狀態的樣本量均保存；沒有依測試報酬改分類規則。上游事件抽取V2仍未通過獨立人工標註關卡，未擅自放行。

## 模型增益與統計判斷

價格基準仍用E3c歷史事件／狀態機率、LR與XGBoost。原新聞比較計畫P（38維價格）、S（P＋情緒）、T（S＋事件結構）與原訓練／校準分割不變。2012–2022新聞特徵支援仍0，所以**新新聞模型訓練0組，主要8個Brier與次要4個within-state ranking比較仍NOT_ESTIMABLE**，效果量／p／CI留NA。

`phase7a_existing_price_error_audit.csv`只描述既有價格模型在這幾個已知摘要事件上的誤差，不是新聞融合模型成績。`phase7a_within_state_support.csv`顯示每個方向×長期趨勢×VIX cell的可用樣本；不足以建立可靠同狀態新增排序檢定。發布+60分鐘／延後1交易日的完整樣本數及反轉率存在`phase7a_timing_sensitivity.csv`，不拿最佳一列當結論。原同日期配對HAC20／block20、block60敏感性及Holm規格保留，待資料支持才執行。

目前最可靠的研究結論是：**已找回一段可稽核的部分Gemini新聞資料，但它不能回答新聞是否解釋了價格模型無法區分的反轉／延續。**問題在歷史年份支援、來源完整性、語意標註未完成及可得時間證據，而非已證明新聞無訊號。既有波動幅度Mamba亦不能當成方向模型。

## 2026固定協定與接觸紀錄

`protocol/E3C_2026_PROTOCOL.json`的SHA256仍為 `9ffe3c31bbfabb6609ee69dde1deab7a13729b43511a9c045d945b5b03453940`，與補查前逐位元相同，**未訓練、未執行2026驗證**。同一XGBoost family、38特徵、固定門檻、fit2012–2024／cal2025H2、seeds42–46、4個Brier／2個同狀態AUC假設，以及最早2027-01-15全年度資料齊備後的一次性規則，均未依新聞補查改動。參見[固定協定](protocol/E3C_2026_PROTOCOL.md)。

須如實記錄：ZIP初次盤點用過寬的日期欄判定，意外顯示舊2026檔案的**情緒分數彙總**與日期；未查看2026新聞本文／標題、行情數值、報酬／target或成績。這些列未納入任何研究統計或模型選擇。協定早於該次接觸已鎖定，沒有修改；但不能聲稱研究團隊完全未接觸任何2026新聞特徵。正式獨立性仍須核對所有既有接觸紀錄；若保留期曾影響規則，須依原協定改用另行預先登錄的更晚未見期間。詳見`holdout_handling_audit.json`，不能隱藏此限制。

## 完整產物與可重現性

- `aligned/`：6,915市場日期、1,397價格事件、152篇實際metadata／摘要身份資料、100篇日期推定對齊、52篇發布時間proxy對齊及三種時間敏感性；future_標籤與可用特徵分開命名。
- `tables/phase7a_*`：36筆cache身份核對、時間／假日稽核、類型／標註覆蓋、條件反轉概率與幅度、同狀態樣本、既有價格模型誤差；原覆蓋表及NOT_ESTIMABLE預定檢定保留。
- `inputs/phase7a/`：只白名單2025原始52篇、36／18篇輸出、原prompt、匹配36cache及摘要欄來源程式；原ZIP以hash指認，不把其2026或憑證檔包進結果。
- `code/`、輸入／程式SHA256、環境lock、圖表PNG/PDF／HTML、完整結果ZIP。GitHub-only報告留在`inputs/E4A_GITHUB_ONLY_SUMMARY.md`，舊結果目錄完全保留。

可重跑本輪：見`README_E4A_PHASE7A.md`，不需要API、GPU或2026。先前15份GitHub-only CSV已離線重現，擴充版另核對白名單新聞、cache一致性與保留期隔離。E1–E3c原成果hash未改。

下一步是找回真正的450篇`apple_public_v1`原始／特徵檔，並確認是否另有2012–2022與TSLA新聞及來源首次可見／版本日誌；單靠補完16篇或重抓當前網站，都無法補上原訓練年份。只有2023–2025語料時，應另立受限回溯研究，不暗改本輪分割，也不開啟2026補樣本。
'''
    (out/'E4A_SUMMARY.md').write_text(text)
    (out/'README_E4A_PHASE7A.md').write_text('''# E4a Phase7A extension

The complete source ZIP is preserved outside the result. Only3 whitelisted historical2025 CSVs, their matching36 caches and the text-only prompt are extracted. No old code is executed. No2026 rows enter analysis; the inventory exposure incident is documented separately.

From stock_prediction with the original ZIP and GitHub-only delivery present:

```bash
PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv-e3b/bin/python -B scripts/extend_e4a_phase7a.py
```

Existing output directories are never overwritten. For portable replay using only the packaged historical inputs:

```bash
PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 .venv-e3b/bin/python -B outputs/e4a_20261026_phase7a/code/extend_e4a_phase7a.py --replay-from outputs/e4a_20261026_phase7a --out outputs/e4a_phase7a_replay
```

Replay validates the source manifest, loads only packaged2025 raw/annotation inputs, rebuilds all extended alignment/statistics and compares every new CSV. No source ZIP, internet, paid API, GPU or2026 access is needed. The protocol remains identical to the pre-extension lock.
''')


def save_manifests(out):
    dump(out/'input_manifest.json',{'algorithm':'sha256','files':{str(p.relative_to(out)):sha(p) for p in sorted((out/'inputs').rglob('*')) if p.is_file()}})
    dump(out/'extension_code_manifest.json',{'code/extend_e4a_phase7a.py':sha(out/'code/extend_e4a_phase7a.py')})


def run(out):
    initialize(out);raw,anno=extract_historical(out);news,e,audit=align(out,raw,anno);stats,sensitivity=describe(out,news,e)
    plots(out,news,e,stats);report(out,news,e,audit,stats,sensitivity);save_manifests(out)
    verify_previous(json.loads((out/'protected_previous_files.json').read_text()));check(out/'protocol')
    assert sha(out/'protocol/E3C_2026_PROTOCOL.json')==sha(BASE/'protocol/E3C_2026_PROTOCOL.json')
    dump(out/'COMPLETION.json',{'status':'COMPLETE_FEASIBILITY_WITH_PARTIAL_GEMINI','scientific_news_increment_status':'NOT_ESTIMABLE','created_utc':now(),
        'news_models_trained':0,'2026_rows_used_for_analysis':False,'incidental2026sentiment_aggregate_exposure_recorded':True})
    zp=archive(out);shutil.copyfile(out/'E4A_SUMMARY.md',ROOT/'E4A_SUMMARY.md')
    dump(ROOT/'E4A_CURRENT_RUN.json',{'status':'COMPLETE_FEASIBILITY_WITH_PARTIAL_GEMINI','output':str(out),'summary':str(out/'E4A_SUMMARY.md'),'zip':str(zp),'zip_sha256':sha(zp),
        '2026_rows_used_for_analysis':False,'holdout_handling_audit':str(out/'holdout_handling_audit.json')})
    print(sensitivity.to_string(index=False));print('COMPLETE',out)


def replay(source,out):
    if out.exists(): raise FileExistsError('Refuse to overwrite replay')
    for name,h in json.loads((source/'archive_manifest.json').read_text())['files'].items():
        if sha(source/name)!=h: raise RuntimeError('Source changed '+name)
    shutil.copytree(source,out,ignore=shutil.ignore_patterns('e4a_complete_results.zip','e4a_complete_results.zip.sha256','archive_manifest.json','.matplotlib'))
    # Restore the original base alignment before reapplying the extension.
    # Source includes a frozen copy under inputs/pre_extension_alignment.
    for p in (source/'inputs/pre_extension_alignment').glob('*'): shutil.copyfile(p,out/'aligned'/p.name)
    raw=pd.read_csv(out/'inputs/phase7a/AAPL_news_historical_smoke.csv');anno=pd.read_csv(out/'inputs/phase7a/AAPL_llm_historical_resume.csv')
    news,e,a=align(out,raw,anno);s,t=describe(out,news,e);plots(out,news,e,s);report(out,news,e,a,s,t)
    verified=[]
    for folder in ('aligned','tables'):
        for p in (source/folder).glob('*.csv*'):
            pd.testing.assert_frame_equal(pd.read_csv(p),pd.read_csv(out/folder/p.name),check_exact=True);verified.append(str(p.relative_to(source)))
    check(out/'protocol');dump(out/'phase7a_replay_validation.json',{'status':'PASSED','CSV_count':len(verified),'files':sorted(verified),'2026_used_for_analysis':False})
    print('REPLAY PASSED',len(verified),'CSV files')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);p.add_argument('--replay-from',type=Path)
    a=p.parse_args()
    if a.replay_from: replay(a.replay_from.resolve(),a.out.resolve())
    else:
        # Preserve base join files in the extension input archive for exact replay.
        original_initialize=initialize
        def initialize(out):
            original_initialize(out);d=out/'inputs/pre_extension_alignment';d.mkdir()
            for name in ('market_news_alignment.csv.gz','event_news_features.csv','news_metadata_normalized.csv'):
                shutil.copyfile(BASE/'aligned'/name,d/name)
        run(a.out.resolve())
