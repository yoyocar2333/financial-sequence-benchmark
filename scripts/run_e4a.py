"""CPU-only, offline E4a coverage study on pinned news metadata and <=2025 prices."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import numpy as np
import pandas as pd
from e4a_core import ROOT,SOURCE,VENDOR,MAIN_REV,REVIEW_REV,OUT,REPO_URL,TYPES,sha,dump,now,design,cutoff_utc,date_only_projection,strict_availability
from e3b_protocol import load_frame,indices
from e3c_core import features
from freeze_e3c_2026 import freeze,check

CODE=['e4a_core.py','run_e4a.py','plot_e4a.py','test_e4a.py','freeze_e3c_2026.py','e3c_2026_features.py',
      'test_e3c_2026_protocol.py','e3a_core.py','e3b_protocol.py','e3c_core.py','e3c_calibration_v1_1.py']


def protect():
    protected={}
    for study in ('mamba_multiseed_20261020','e3a_20261021','e3b_20261026','e3c_20261026_v1_1'):
        d=ROOT/'outputs'/study
        for p in d.glob('*complete*.zip*'): protected[str(p.relative_to(ROOT))]=sha(p)
        for name in ('archive_manifest.json','status.json','E3C_SUMMARY.md','INDEPENDENT_VALIDATION_PROPOSAL.json'):
            if (d/name).exists(): protected[str((d/name).relative_to(ROOT))]=sha(d/name)
    for name in ('E3A_SUMMARY.md','E3B_SUMMARY.md','E3C_SUMMARY.md','E3C_CURRENT_RUN.json'):
        if (ROOT/name).exists(): protected[name]=sha(ROOT/name)
    for p in (ROOT/'scripts').glob('*e3*.py'):
        if p.name not in CODE: protected[str(p.relative_to(ROOT))]=sha(p)
    # Verify E3c archived CSV data, configurations and prediction bytes before copying.
    manifest=json.loads((SOURCE/'archive_manifest.json').read_text())['files']
    for name,h in manifest.items():
        if sha(SOURCE/name)!=h: raise RuntimeError('E3c archived result changed: '+name)
    return protected


def verify_previous(protected):
    for p,h in protected.items():
        if sha(ROOT/p)!=h: raise RuntimeError('Prior research changed: '+p)


def prepare(out):
    if out.exists(): raise FileExistsError('Preserve existing study; use a new --out for replay')
    protected=protect()
    for n in ('inputs','code','tables','aligned','figures','logs'): (out/n).mkdir(parents=True,exist_ok=True)
    dump(out/'protected_previous_files.json',protected)
    dump(out/'evaluation_plan.json',design())
    for p in (SOURCE/'inputs').glob('*through2025.csv'): shutil.copyfile(p,out/'inputs'/p.name)
    for n in ('AAPL_preprocessing.json','TSLA_preprocessing.json','e3a_training_thresholds.json','original_snapshot_provenance.json'):
        shutil.copyfile(SOURCE/'inputs'/n,out/'inputs'/n)
    for rev in (MAIN_REV,REVIEW_REV): shutil.copytree(VENDOR/rev,out/'inputs/news_project'/rev)
    for name in ('metrics_comparison.csv','within_state_ranking_tests.csv','signal_vs_average_evidence.csv','event_counts_and_amplitude.csv'):
        shutil.copyfile(SOURCE/'tables'/name,out/'inputs'/('E3C_'+name))
    for ticker in ('AAPL','TSLA'):
        for method in ('event_prior','state_prior','lr_event','xgb_event'):
            seeds=[-1] if method.endswith('prior') else [42,43,44,45,46]
            for seed in seeds:
                p=SOURCE/'predictions'/f'{ticker}_{method}_seed{seed}.csv'
                (out/'inputs/E3C_predictions').mkdir(exist_ok=True)
                shutil.copyfile(p,out/'inputs/E3C_predictions'/p.name)
    for n in CODE: shutil.copyfile(ROOT/'scripts'/n,out/'code'/n)
    for name in ('README_E4A.md','E3C_2026_PROTOCOL.md'): shutil.copyfile(ROOT/name,out/name)
    freeze(out/'protocol')
    input_files=[p for p in (out/'inputs').rglob('*') if p.is_file()]
    dump(out/'input_manifest.json',{'algorithm':'sha256','upstream_main':MAIN_REV,'upstream_research':REVIEW_REV,
        'source_files':'GitHub fetch_file pinned refs; local LF/trailing-newline canonicalization; SHA256 below defines replay bytes',
        'market_inputs_end':'2025-12-31','files':{str(p.relative_to(out)):sha(p) for p in input_files}})
    dump(out/'code_manifest.json',{n:sha(out/'code'/n) for n in CODE})
    dump(out/'environment.json',{'python':sys.version,'executable':sys.executable,'GPU_used':False,'paid_API_calls':0,'new_packages_installed':False,
        'packages':{n:importlib.metadata.version(n) for n in ('numpy','pandas','scipy','scikit-learn','xgboost-cpu','torch','mamba_ssm')}})
    (out/'environment.lock.txt').write_text(subprocess.check_output([sys.executable,'-B','-m','pip','freeze'],text=True))
    for script,log in [('test_e4a.py','pit_tests.log'),('test_e3c_2026_protocol.py','protocol_parity_tests.log')]:
        result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts'/script)],capture_output=True,text=True)
        (out/'logs'/log).write_text(result.stdout+result.stderr)
        if result.returncode: raise RuntimeError('Tests failed: '+script)
    return protected


def schema(out):
    dump(out/'NEWS_INPUT_CONTRACT.json',{
        'required_article_fields':['article_id','ticker','published_utc','version_seen_utc','availability_evidence','text_sha256','historical_text_revision_verified','source','url'],
        'optional_version_fields':['version_published_utc','embargo_until_utc','updated_utc','retrieved_utc','syndication_cluster_id','text_version'],
        'time_format':'ISO8601 timezone-aware; original publisher timezone preserved; UTC normalized; date-only publication_date separate',
        'published_vs_retrieved':'A2026 retrieval does not establish historical first_seen; retrieve time is not substituted for publication or proof of2012-2025 availability',
        'feature_join_key':['article_id','text_sha256','extractor_revision','prompt_sha256'],
        'FinBERT':['positive','negative','neutral','model_revision','inferred_utc','token_count','chunk_count','input_sha256'],
        'Gemini':['sentiment','confidence','event_type','model_id','server_model_version_if_available','prompt_sha256','response_sha256','inferred_utc','text_only_no_tools','input_sha256'],
        'event_type_taxonomy':TYPES,'event_quality':'V1 syntactic heuristic, no independently human-validated financial-event gold; AI pre-review is not gold; V2 still blocked upstream',
        'collection_intervals':['ticker','source','start_utc','end_utc','successful_poll_log_sha256','scope_complete','outage_flags'],
        'observed_zero':'Only source-scoped successful complete collection can yield count0. Missing corpus/features is UNKNOWN and never neutral sentiment.',
        'do_not_import':['synthetic demonstrations','upstream next-day direction probabilities as5day reversal forecasts','future_return-derived sentiment','2026 real holdout prices or articles'],
        'needed_recovery_files':['data/raw/apple_public_v1/apple_newsroom_articles.csv','outputs/apple_public_v1/article_manifest.csv','outputs/apple_public_v1/article_features.csv','outputs/apple_public_v1/finbert_chunks.jsonl','original Gemini per-article cache,model/prompt/version metadata','historical source-version/availability and collection logs'],
        'note':'450-article corporate-only2023-2025 recovery alone still provides no2012-2022 news training and noTSLA; a changed later split would be a new separately frozen exploratory protocol'})
    pd.DataFrame(columns=['article_id','ticker','published_utc','version_seen_utc','availability_evidence','text_sha256','historical_text_revision_verified','source','url']).to_csv(out/'aligned/news_input_template.csv',index=False)


def metadata(out):
    base=out/'inputs/news_project';m=base/MAIN_REV;r=base/REVIEW_REV
    a=pd.read_csv(r/'reports/apple_extraction_audit_v1/blind_review_manifest.csv',dtype=str)
    pop=json.loads((r/'reports/apple_extraction_audit_v1/sample_freeze.json').read_text())
    assert len(a)==100 and a.article_id.is_unique and set(a.article_id)==set(pop['selected_ids'])
    assert a.publication_date.str.startswith('2023-').all()
    a['ticker']='AAPL';a['source']='Apple Newsroom English';a['timestamp_precision']='date_only'
    a['sample_scope']='100/152 uniform-random2023 extraction-review subset; not the full450-article corpus'
    a['historical_text_revision_verified']=False
    for c in ('published_utc','version_seen_utc','availability_evidence','FinBERT_positive','FinBERT_negative','FinBERT_neutral','Gemini_sentiment','news_event_type'): a[c]=None
    a['strict_status']=[strict_availability(x)[1] for x in a.to_dict('records')]
    assert all(strict_availability(x)[0] is None for x in a.to_dict('records'))
    a['eligible_for_model']=False
    a.to_csv(out/'aligned/news_metadata_normalized.csv',index=False)
    summary=json.loads((m/'reports/apple_public_v1/collection_summary.json').read_text())
    registry=json.loads((m/'reports/apple_public_v1/model_registry.json').read_text())
    rows=[{'dataset':'Apple public pilot','ticker':'AAPL','year':int(y),'reported_articles':n,'locally_observed_metadata_rows':int((a.publication_date.str[:4]==y).sum()),
        'article_features_available':0,'published_precision':'date_only','historical_revision_verified':False,'reported_retrieved_utc':summary['retrieved_utc'],
        'status':'UPSTREAM_REPORTED_COUNTS_NOT_REPRODUCED_FROM_FULL_CORPUS'} for y,n in summary['articles_by_year'].items()]
    rows += [{'dataset':'Gemini/FinBERT PoC','ticker':'AAPL','year':2025,'reported_articles':52,'locally_observed_metadata_rows':0,'article_features_available':0,
        'published_precision':'raw corpus/cache unavailable','historical_revision_verified':False,'status':'UPSTREAM_REPORTED_2025JAN02_FEB03_ONLY'},
        {'dataset':'TSLA','ticker':'TSLA','year':None,'reported_articles':None,'locally_observed_metadata_rows':0,'article_features_available':0,'published_precision':'unknown','historical_revision_verified':False,'status':'NO_TSLA_CORPUS_IN_REPOSITORY'}]
    pd.DataFrame(rows).to_csv(out/'tables/news_source_inventory.csv',index=False)
    dump(out/'news_provenance_audit.json',{'main_commit':MAIN_REV,'review_commit':REVIEW_REV,'full_raw_articles_available':False,
        'article_features_available':False,'Gemini_cache_available':False,'local_real_metadata_rows':len(a),'strict_verified_rows':0,
        'upstream_pilot_article_count':summary['articles'],'upstream_pilot_year_counts':summary['articles_by_year'],'upstream_model_registry':registry,
        'schema_only_synthetic_examples_excluded':True,'upstream_archive_scan2026_year_metadata_not_used_as_news':True,
        'market_data_reused':'E3c frozen adjusted snapshot only; upstream pilot market CSV with2026 boundary was not fetched/run',
        'collection_not_rerun':'Current website refetch cannot reconstruct historical exact versions; would not repair missing2012-2022 orTSLA support'})
    return a


def market_alignment(out,articles):
    allrows=[];joins=[];features_rows=[];coverage=[];support=[];known=[]
    for ticker in ('AAPL','TSLA'):
        f=load_frame(ticker,out);assert f.index.max()<=pd.Timestamp('2025-12-31')
        _,st,meta=features(f,'2022-12-31')
        expected=json.loads((out/'inputs'/f'{ticker}_preprocessing.json').read_text())
        assert expected['columns']==meta['columns'];np.testing.assert_allclose(expected['thresholds']['past5'],meta['thresholds']['past5'],atol=1e-12)
        dates=f.index;local=articles[articles.ticker==ticker].copy()
        local['assumed_information_date']=pd.to_datetime([date_only_projection(x,dates) for x in local.publication_date])
        loc_index={d:i for i,d in enumerate(dates)}
        partitions=[('fit','2012-01-01','2022-12-31'),('validation','2023-01-01','2023-12-31'),('test','2024-01-01','2025-12-31')]
        ticker_rows=[]
        for part,a,b in partitions:
            ii=indices(f,a,b)
            for i in ii:
                d=dates[i];ev=bool(st['event'][i]);cell=int(st['cell'][i])
                nearby=local[local.assumed_information_date.between(dates[max(0,i-4)],d)]
                same=local[local.assumed_information_date==d]
                amp=-float(f.reference_sign.iloc[i])*float(f.nextopen_log5.iloc[i])
                row={'ticker':ticker,'date':d.strftime('%Y-%m-%d'),'partition':part,'decision_cutoff_utc':cutoff_utc([d])[0].isoformat(),
                    'entry_session':dates[i+1].strftime('%Y-%m-%d'),'label_session5':pd.Timestamp(f.label_date5.iloc[i]).strftime('%Y-%m-%d'),
                    'label_end20':pd.Timestamp(f.end20.iloc[i]).strftime('%Y-%m-%d'),'event':int(ev),'event_direction':int(st['direction'][i]),
                    'long_up':int(st['long'][i]),'VIX_high':int(st['vol'][i]),'VXN_high':int(st['vxn_high'][i]),'cell':cell,
                    'conflict':int(ev and st['direction'][i]*(2*st['long'][i]-1)<0),'past5_pp':f.past5.iloc[i],'past20_pp':f.past20.iloc[i],
                    'past60_pp':f.past60.iloc[i],'past120_pp':f.past120.iloc[i],'VIX':f.VIX.iloc[i],'VXN':f.VXN.iloc[i],
                    'future_y5':int(f.y5.iloc[i]),'future_signed_reversal_amplitude_pp':amp,'future_executable_return_pp':f.nextopen_log5.iloc[i],
                    'strict_news_observation_status':'UNKNOWN_COLLECTION_AND_VERSION_AVAILABILITY','strict_news_count':np.nan,
                    'strict_news_features_available':False,'observed_metadata_subset_articles_new':len(same),'observed_metadata_subset_articles_last5':len(nearby),
                    'subset_zero_means_no_news':False,'FinBERT_score':np.nan,'Gemini_score':np.nan,'news_event_type':None}
                allrows.append(row);ticker_rows.append(row)
                if ev:
                    features_rows.append({**row,'news_inference_eligible':False,'exclusion_reason':'no audited historical news features; metadata-only counts not model features'})
                    # Both retrospective and post-event alignment retained; no future news is a feature.
                    for art in local.itertuples():
                        if pd.isna(art.assumed_information_date): continue
                        lag=loc_index[pd.Timestamp(art.assumed_information_date)]-i
                        if -5<=lag<=5:
                            joins.append({'ticker':ticker,'event_date':row['date'],'partition':part,'article_id':art.article_id,'publication_date':art.publication_date,
                                'assumed_information_date':pd.Timestamp(art.assumed_information_date).strftime('%Y-%m-%d'),'relative_information_session':lag,
                                'prediction_window_last5':-4<=lag<=0,'post_event':lag>0,'strict_model_input':False,
                                'alignment_tier':'DATE_ONLY_UNVERIFIED_METADATA_SUBSET','url':art.url,'text_sha256':art.text_sha256})
        frame=pd.DataFrame(ticker_rows)
        # Verify existing E3c model evaluation dates, targets and masks, without refitting.
        old=pd.read_csv(out/'inputs/E3C_predictions'/f'{ticker}_state_prior_seed-1.csv')
        test=frame[frame.partition=='test']
        np.testing.assert_array_equal(test.date,old.date);np.testing.assert_array_equal(test.future_y5,old.target)
        np.testing.assert_array_equal(test.event,old.event)
        for part,z in frame.groupby('partition',sort=False):
            e=z[z.event.eq(1)]
            support.append({'ticker':ticker,'partition':part,'eligible_dates':len(z),'event_dates':len(e),'event_reversals':int(e.future_y5.sum()),
                'event_continuations':int(len(e)-e.future_y5.sum()),'reversal_rate':e.future_y5.mean(),'signed_amplitude_mean_pp':e.future_signed_reversal_amplitude_pp.mean(),
                'strict_news_feature_event_dates':0,'metadata_subset_last5_event_dates':int(e.observed_metadata_subset_articles_last5.gt(0).sum()),
                'complete_news_observation_dates':0,'true_news_coverage_rate':np.nan})
        for year,z in frame.groupby(pd.to_datetime(frame.date).dt.year):
            e=z[z.event.eq(1)]
            coverage.append({'ticker':ticker,'year':year,'eligible_dates':len(z),'event_dates':len(e),
                'observed_metadata_articles':int(local.publication_date.str.startswith(str(year)).sum()),
                'dates_with_known_subset_last5':int(z.observed_metadata_subset_articles_last5.gt(0).sum()),
                'events_with_known_subset_last5':int(e.observed_metadata_subset_articles_last5.gt(0).sum()),
                'complete_collection_days':0,'strict_PIT_feature_days':0,'true_news_coverage_rate':np.nan,'status':'UNKNOWN_FULL_COVERAGE'})
        for art in local.to_dict('records'):
            art['assumed_information_date']=pd.Timestamp(art['assumed_information_date']).strftime('%Y-%m-%d') if pd.notna(art['assumed_information_date']) else None
            known.append(art)
    market=pd.DataFrame(allrows);events=pd.DataFrame(features_rows)
    market.to_csv(out/'aligned/market_news_alignment.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    events.to_csv(out/'aligned/event_news_features.csv',index=False)
    join=pd.DataFrame(joins)
    join.to_csv(out/'aligned/news_event_alignment_metadata_only.csv',index=False)
    pd.DataFrame(known).to_csv(out/'aligned/news_metadata_with_assumed_dates.csv',index=False)
    pd.DataFrame(coverage).to_csv(out/'tables/coverage_by_year.csv',index=False)
    support=pd.DataFrame(support);support.to_csv(out/'tables/market_event_support.csv',index=False)
    events.groupby(['ticker','partition','event_direction','long_up','VIX_high']).agg(n=('future_y5','size'),reversals=('future_y5','sum'),reversal_rate=('future_y5','mean'),signed_amplitude_mean_pp=('future_signed_reversal_amplitude_pp','mean')).reset_index().to_csv(out/'tables/market_state_support.csv',index=False)
    return market,events,join,support


def blocked_statistics(out):
    rows=[]
    for ticker in ('AAPL','TSLA'):
        for family,tests in [('primary_Brier_Holm8',['S-P','T-S','T-state_prior','S-state_prior']),('secondary_conditional_AUC_Holm4',['S-P','T-P'])]:
            for comparison in tests:
                rows.append({'ticker':ticker,'family':family,'comparison':comparison,'status':'NOT_ESTIMABLE','reason':'No2012-2022 historical news-feature training support; no matched PIT news feature evaluation cohort',
                    'paired_dates':0,'estimate':np.nan,'hac_p':np.nan,'bootstrap_p':np.nan,'holm_p':np.nan,'ci_low':np.nan,'ci_high':np.nan})
    pd.DataFrame(rows).to_csv(out/'tables/news_incremental_tests.csv',index=False)
    rows=[]
    for ticker in ('AAPL','TSLA'):
        for group in ['FinBERT_positive','FinBERT_negative','FinBERT_neutral','Gemini_positive','Gemini_negative',*TYPES]:
            rows.append({'ticker':ticker,'news_condition':group,'status':'NOT_ESTIMABLE','news_feature_events':0,'reversal_rate':np.nan,'signed_amplitude_mean_pp':np.nan,'positive_reversal_magnitude_mean_pp':np.nan,'reason':'Per-article historical sentiment/event features unavailable'})
    pd.DataFrame(rows).to_csv(out/'tables/news_conditional_outcomes.csv',index=False)
    dump(out/'model_feasibility_decision.json',{'status':'COVERAGE_FEASIBILITY_ONLY','new_models_trained':0,'GPU_used':False,
        '2012_2022_news_feature_train_events':{'AAPL':0,'TSLA':0},'strict_verified_news_records':0,
        'reason':'Missing full article/feature corpora; supplied metadata only2023 and pilot2023-2025 outside original training. NoTSLA corpus. Date-only/unverified historical text cannot establish strict PIT.',
        'claim':'Cannot estimate incremental news signal; this is neither a positive result nor evidence that news is ineffective',
        '2026_market_or_real_news_used':False})


def baseline_context(out):
    mm=pd.read_csv(out/'inputs/E3C_metrics_comparison.csv')
    z=mm[mm.group.eq('events') & mm.method.isin(['event_prior','state_prior','lr_event','xgb_event'])].copy()
    z['status']='EXISTING_E3C_CONTEXT_ONLY_NO_NEWS_COMPARISON';z.to_csv(out/'tables/existing_price_baselines.csv',index=False)
    data=pd.concat([pd.read_csv(p) for p in sorted((out/'inputs/E3C_predictions').glob('*.csv'))],ignore_index=True)
    data['origin']='Unchanged E3c5day forecasts; no E4a model refit'
    data.to_csv(out/'aligned/existing_price_predictions.csv.gz',index=False,compression={'method':'gzip','mtime':0})


def report(out,events,join,support):
    # Avoid an optional tabulate dependency.
    def table(df,cols):
        def val(x):
            if pd.isna(x): return 'NA'
            if isinstance(x,(float,np.floating)): return f'{x:.4f}'
            return str(x)
        return '| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+'\n'.join('| '+' | '.join(val(v) for v in row)+' |' for row in df[cols].itertuples(index=False,name=None))
    bylag=join.groupby(['partition','relative_information_session']).article_id.nunique().reset_index(name='unique_articles')
    bylag.to_csv(out/'tables/metadata_event_neighborhood_counts.csv',index=False)
    selected=events[(events.partition=='validation')&events.ticker.eq('AAPL')]
    covered=selected[selected.observed_metadata_subset_articles_last5.gt(0)]
    baseline=pd.read_csv(out/'tables/existing_price_baselines.csv')
    b=baseline[['ticker','method','n_mean','brier_mean','roc_auc_mean','ece10_mean']]
    text=f'''# E4a — News-Conditioned Reversal Study

本輪完成**新聞來源／PIT稽核、既有市場事件對齊、資料覆蓋與可行性研究**。目前無法估計新聞的新增預測能力：公開新聞專案缺逐篇情緒／事件輸出，且其2023–2025 AAPL語料不含原定2012–2022訓練期，亦無TSLA語料。沒有訓練新模型、沒有GPU作業或付費API；沒有使用2026行情、真實新聞或標籤。

## 已核實的資料

已固定 [stockllm-pit-news]({REPO_URL}) main `{MAIN_REV}` 與 research/event-extraction-e0-e4 `{REVIEW_REV}`。程式、公開報表及來源清單保存於 inputs/news_project，逐檔SHA256在 input_manifest.json；GitHub文本下載僅做LF／末尾換行正規化，研究以歸檔SHA256定義精確輸入。未改動遠端倉庫。

- 上游 collection_summary **報告**450篇Apple企業新聞：2023年152、2024年158、2025年140；並報告900列FinBERT／事件特徵。原始內文、完整article_manifest、article_features與Gemini cache未公開；本輪無法從完整語料重算450篇或原始成績。
- 實際可逐篇核對的是 **100篇真實2023新聞的ID、日期、URL、text hash**，為上游從152篇中固定隨機抽取的事件抽取審查樣本。抽樣seed20261014，不是100個股票事件，也不是450篇全語料。
- 另一個Gemini／FinBERT PoC報告52篇AAPL、2025-01-02至02-03、21個預測日；同樣缺原始語料與逐篇輸出。它的次日方向任務不能代替本研究5日反轉任務。
- 合成範例（含假2026日期）只屬程式fixture，完全排除於分析；上游archive_scan的2026頁面年份／hash也不是本研究新聞樣本。未執行其會抓2026邊界行情的collector。
- TSLA真實新聞語料：未提供；**不能因此說TSLA沒有新聞**。

## Point-in-time稽核與固定對齊

截止點固定為交易日17:00 America/New_York，UTC隨DST改變，預測仍從次交易日調整Open至t+5調整Close。這是本研究的營運時間假設；現有Yahoo回溯調整快照沒有歷史到達日誌，不能宣稱市場來源本身已完成PIT認證。

嚴格新聞可用時間要求：發布時間有時區、**該內文版本**的首次可見證據、版本hash及歷史版本可核對；available=max(發布、版本首次可見、禁發截止、版本發布)。2026回抓時間不能替代歷史first-seen。缺時間／證據的新聞是可取得性未知，不當作當年不可取得，也不當作已可取得。

現有Apple資料只有發布日期，且historical_text_revision_verified=false。因此100/100逐篇metadata均不能進入嚴格PIT模型，**已驗證可用文章數=0**；此0描述驗證狀態，不是市場新聞數。發布日期和修改時間是不同欄位；時間戳應保留時區與版本資訊。[官方日期欄位說明](https://developers.google.com/search/docs/appearance/structured-data/article)

僅為可行性，另提供「發布日期後第一個實際交易日」的保守**假設日期**對齊；不虛構00:00時間、不聲稱已消除歷史修訂。預測候選窗口為當期及過去4個資訊交易日；事件附近t-5至t+5只作描述，正offset標記post_event，絕不進特徵。資料缺口保留NA；不把缺新聞填成情緒中立，不用未來報酬生成情緒。

## 市場事件與新聞覆蓋

市場資料逐位元沿用E3c through2025快照，調整OHLC=raw OHLC×AdjClose/Close，Volume不變。E3c的8狀態、2012–2022急漲跌q10/q90、長期context120_ex5及VIX中位數不變。標籤為 `1[sign(past5)*100log(C[t+5]/Open[t+1])<0]`；幅度為相反符號的同一log報酬，以log百分點表示。flat future不算反轉。每個區段t+20不跨界，與E3c60日共同歷史規則相同，測試日期及標籤逐列核對。

{table(support,['ticker','partition','eligible_dates','event_dates','event_reversals','reversal_rate','strict_news_feature_event_dates','metadata_subset_last5_event_dates'])}

AAPL完整2023驗證年有{len(selected)}個價格事件；其中{len(covered)}個事件可在**已知100篇子樣本**的過去5資訊日內找到至少一篇metadata。這只給出該子樣本的已知重合，既不是全市場新聞覆蓋率，也不是新聞情緒可用率。全語料、每日來源完整性與歷史版本證據皆缺，真正新聞覆蓋率記NA。

原訓練區段兩檔的嚴格新聞特徵事件都為0。即使找回完整450篇與其輸出，2023才開始的AAPL單一企業來源仍不能支援原2012–2022新聞訓練，也不能代表TSLA或獨立媒體對負面／法律事件的報導。若未來改用較晚訓練區段，須另立固定探索性協定，不得暗中改本輪時間切分。

![市場事件與新聞來源的年份支援](figures/01_support_timeline.png)

![已知子樣本與急漲跌事件的對齊](figures/02_metadata_event_timeline.png)

![PIT與特徵可用性稽核](figures/03_feasibility_gates.png)

![事件附近已知子樣本metadata](figures/04_event_neighborhood.png)

## 情緒、事件類型與模型比較

FinBERT revision上游固定為 `0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031`，但本輪沒有其逐篇機率。FinBERT輸出是positive/negative/neutral的文本情緒，**不是5日反轉機率**。[FinBERT模型卡](https://huggingface.co/ProsusAI/finbert)

Gemini亦缺逐篇輸出、原始prompt與可獨立核對的歷史服務版本／訓練截止；不能用現在Gemini讀歷史文章就聲稱當年可部署。即使日後補做text-only推論，也應標記回溯文字研究，另評估版本修訂及預訓練知識污染。本輪沒有呼叫Gemini或下載模型權重。

上游V1事件是固定詞彙＋語法動詞紀錄；尚無獨立人工事件gold。research分支明確保留V2未放行狀態，AI預審不是獨立人工答案。因此不把抽取筆數當作金融事件密度，也不把未驗證V2接入股價模型。六類taxonomy保留以便後續審核，沒有從URL字串猜事件或情緒。

以下是**既有E3c價格模型**在相同482測試日中事件子集的背景成績，完全沿用原檔，不是E4a新增新聞比較：

{table(b,['ticker','method','n_mean','brier_mean','roc_auc_mean','ece10_mean'])}

E3c既有同狀態排序與多重校正結果仍保存在 inputs/E3C_*，並未因E4a重挑模型。新聞能否改善這些模型的平均機率、狀態內排序或校準，目前**不可識別**；不支持「新聞有效」，也不支持「新聞無效」。同時，波動幅度Mamba與方向反轉分類任務仍須區分。

已固定P=38維價格事件LR、S=P+情緒／新聞數、T=S+低維事件結構；歷史事件／狀態機率為主要基準。只有取得同一文章宇宙、實際可用性與訓練支援後才能跑；所有P/S/T在相同支援日期重新擬合，不能拿全日期舊模型和稀疏新聞模型直接比較。暫不訓練深度模型。

## 統計與穩健性

預先固定主要8個事件Brier比較（2檔×S-P、T-S、T-state_prior、S-state_prior），HAC20與日期circular-block20 bootstrap19999各作Holm8；block60及5日去重事件作敏感性。次要4個同市場狀態內AUC增益檢定另作Holm4。先對同日期五seed損失／concordance kernel平均，seed不當獨立樣本；最低20事件、10反轉／10延續、20同狀態正負配對且99%bootstrap有效。

新聞條件反轉率、signed幅度及正反轉條件幅度，須在相同價格狀態內比較；僅描述關聯，不把企業來源選擇或事件後報導當作因果機制。急漲跌、衝突與高低VIX條件不根據測試表現改門檻。

**本輪12個預定推論（8 Brier＋4 ranking）均為NOT_ESTIMABLE，p值／CI／效果量留NA，不填p=1。** `news_conditional_outcomes.csv`同樣明列未估計原因。日期延後一個交易日只是一種敏感性假設，不能修復缺失歷史版本；沒有把metadata子樣本缺席當作無新聞組來計算虛假的情緒差異。

## 2026一次性協定已固定，未執行

`protocol/E3C_2026_PROTOCOL.json`、`protocol_lock.json`及程式快照固定同一XGBoost gated-event family、38特徵、原始門檻、fit2012–2024／cal2025H2、seeds42–46與4個Brier／2個ranking檢定。2026全年度資料齊備、最早2027-01-15且另行授權後才可一次評估。未改成測試排名挑出的AAPL-XGB／TSLA-LR混合；E4a新聞不加入該驗證。完整定義及獨立性聲明見 [固定協定](protocol/E3C_2026_PROTOCOL.md)。

已新增日期通用特徵引擎，僅用<=2025資料確認38特徵、狀態、標籤、cohort與purging等價，並測試未來已知資料擾動不影響歷史特徵／scaler；沒有讀2026。協定檢查器無驗證執行選項，避免誤啟動。正式執行器與新資料清單仍須在任何2026解封前固定，不能直接重用會截到2025的舊runner。

## 產物與下一步

- `aligned/market_news_alignment.csv.gz`：所有可評估市場日期、截止時間、因果市場特徵、**future_前綴的事後標籤**與新聞未知旗標。
- `aligned/event_news_features.csv`：全部急漲跌事件；不可訓練的新聞欄位維持NA。
- `aligned/news_event_alignment_metadata_only.csv`：真實100篇子樣本與事件前後資訊日對齊；明確禁止作嚴格模型輸入。
- `tables/coverage_by_year.csv`、`market_event_support.csv`、`news_source_inventory.csv`、`news_incremental_tests.csv`、`news_conditional_outcomes.csv`。
- `NEWS_INPUT_CONTRACT.json`、`evaluation_plan.json`、`news_provenance_audit.json`、完整<=2025行情與來源／程式hash。
- `figures/`四組PNG／PDF與HTML索引；`logs/` PIT邊界與特徵等價測試；`e4a_complete_results.zip`。

下一步優先找回上游本機 `article_manifest.csv`、`article_features.csv`、Gemini cache及歷史版本／來源完整性日誌，再確認是否有2012–2022與TSLA的同規格新聞。只有來源可得時間、語料年份與訓練事件支援足夠，才啟動已固定的低複雜度比較。若只有2023–2025企業新聞，適合另立受限的回溯可行性研究，不應冒充原設計的新聞增益驗證。2026保留資料不為補樣本而開啟。
'''
    (out/'E4A_SUMMARY.md').write_text(text)


def archive(out):
    excluded={'e4a_complete_results.zip','e4a_complete_results.zip.sha256','archive_manifest.json','status.json'}
    paths=[p for p in out.rglob('*') if p.is_file() and p.name not in excluded]
    dump(out/'archive_manifest.json',{'algorithm':'sha256','files':{str(p.relative_to(out)):sha(p) for p in sorted(paths)}})
    paths.append(out/'archive_manifest.json')
    zp=out/'e4a_complete_results.zip'
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for p in sorted(paths): z.write(p,str(Path(out.name)/p.relative_to(out)))
    with zipfile.ZipFile(zp) as z:
        if z.testzip(): raise RuntimeError('Archive CRC failure')
    (out/'e4a_complete_results.zip.sha256').write_text(sha(zp)+'  '+zp.name+'\n')
    return zp


def run(out):
    protected=prepare(out)
    dump(out/'status.json',{'status':'RUNNING','started_utc':now(),'CPU_only':True})
    schema(out);articles=metadata(out);market,events,join,support=market_alignment(out,articles)
    blocked_statistics(out);baseline_context(out);report(out,events,join,support)
    result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/plot_e4a.py'),'--out',str(out)],capture_output=True,text=True)
    (out/'logs/plot.log').write_text(result.stdout+result.stderr)
    if result.returncode: raise RuntimeError('Plotting failed; see logs/plot.log')
    verify_previous(protected);check(out/'protocol')
    dump(out/'validation.json',{'old_research_hashes_unchanged':True,'E3c_archive_manifest_verified':True,'old_test_date_label_masks_exact':True,
        'market_rows':len(market),'event_rows':len(events),'metadata_article_rows':len(articles),'metadata_event_links':len(join),
        'strict_PIT_article_rows':0,'new_models_trained':0,'GPU_used':False,'2026_data_loaded':False,'future_protocol_status':'FROZEN_NOT_EXECUTED'})
    dump(out/'COMPLETION.json',{'status':'COMPLETE_FEASIBILITY_ONLY','scientific_news_effect_status':'NOT_ESTIMABLE','created_utc':now(),'2026_used':False})
    zp=archive(out)
    dump(out/'status.json',{'status':'COMPLETE_FEASIBILITY_ONLY','completed_utc':now(),'zip':str(zp),'new_models_trained':0,'2026_used':False})
    shutil.copyfile(out/'E4A_SUMMARY.md',ROOT/'E4A_SUMMARY.md')
    dump(ROOT/'E4A_CURRENT_RUN.json',{'status':'COMPLETE_FEASIBILITY_ONLY','output':str(out),'summary':str(out/'E4A_SUMMARY.md'),'zip':str(zp),'zip_sha256':sha(zp),'2026_used':False})
    print(json.dumps({'status':'COMPLETE_FEASIBILITY_ONLY','output':str(out),'zip':str(zp),'support':support.to_dict('records')},ensure_ascii=False,indent=2))


def replay(source,out):
    if out.exists(): raise FileExistsError('Refuse to overwrite replay')
    original=json.loads((source/'archive_manifest.json').read_text())['files']
    for name,h in original.items():
        if sha(source/name)!=h: raise RuntimeError('Source archive content changed: '+name)
    for n in ('inputs','code','protocol'): shutil.copytree(source/n,out/n)
    for n in ('tables','aligned','figures','logs'): (out/n).mkdir(exist_ok=True)
    for n in ('evaluation_plan.json','README_E4A.md','E3C_2026_PROTOCOL.md'): shutil.copyfile(source/n,out/n)
    schema(out);a=metadata(out);m,e,j,s=market_alignment(out,a);blocked_statistics(out);baseline_context(out);report(out,e,j,s)
    result=subprocess.run([sys.executable,'-B',str(out/'code/plot_e4a.py'),'--out',str(out)],capture_output=True,text=True)
    (out/'logs/plot.log').write_text(result.stdout+result.stderr)
    if result.returncode: raise RuntimeError('Replay plotting failed')
    verified=[]
    for directory in ('tables','aligned'):
        for p in sorted((source/directory).glob('*')):
            if p.is_file():
                pd.testing.assert_frame_equal(pd.read_csv(p),pd.read_csv(out/directory/p.name),check_exact=True)
                verified.append(str(p.relative_to(source)))
    check(out/'protocol')
    dump(out/'replay_validation.json',{'status':'PASSED','CSV_tables_exactly_reproduced':verified,'2026_used':False,'network_or_GPU_used':False})
    print(json.dumps({'status':'REPLAY_PASSED','CSV_count':len(verified),'out':str(out)}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT)
    p.add_argument('--replay-from',type=Path)
    a=p.parse_args();replay(a.replay_from.resolve(),a.out.resolve()) if a.replay_from else run(a.out.resolve())
