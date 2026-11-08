"""Reproducible metadata-only coverage analysis. No fitting, scores or 2026 data."""
import argparse
import bisect
import collections
import datetime as dt
import json
from pathlib import Path
from e8a_core import read_csv, write_csv, dump, clock_level, instant, UTC, NY

def news_rows(bundle):
    yield from read_csv(bundle / 'inputs/news_metadata.csv.gz')
    for r in read_csv(bundle / 'inputs/social_metadata.csv'):
        yield {'origin': 'author_repository_metadata', 'record_key': r['record_id_hash'],
               'ticker': r['ticker'],
               'source': 'StockEmotions_processed' if r['view'] == 'processed_stockemo.csv' else 'StockEmotions_annotated',
               'publication_date': r['date_raw'][:10], 'published_at': '', 'precision': 'date_only',
               'retrieved_at': r['retrieved_utc'], 'url_hash': '', 'text_hash': r['text_hash'],
               'representation': 'social_metadata_only', 'content_characters': 0,
               'version_evidence_verified': False}

def analyze(bundle, output):
    output.mkdir(parents=True, exist_ok=True)
    rows = list(news_rows(bundle))
    groups = collections.defaultdict(list)
    for r in rows:
        assert '2012-01-01' <= r['publication_date'] <= '2025-12-31'
        groups[(r['source'], r['ticker'])].append(r)
    sources = sorted({r['source'] for r in rows})
    table = []
    for source in sources:
        for ticker in ('AAPL', 'TSLA'):
            for year in range(2012, 2026):
                g = [r for r in groups[(source, ticker)] if r['publication_date'].startswith(str(year))]
                times = [instant(r.get('published_at')) for r in g]
                urls = [r['url_hash'] for r in g if r.get('url_hash')]
                texts = [r['text_hash'] for r in g if r.get('text_hash')]
                levels = collections.Counter(clock_level(r) for r in g)
                table.append({'source': source, 'ticker': ticker, 'year': year,
                    'retained_rows': len(g), 'distinct_publication_dates': len({r['publication_date'] for r in g}),
                    'body_field_nonempty': sum(int(r.get('content_characters', 0)) > 0 for r in g),
                    'body_ge1000_characters': sum(int(r.get('content_characters', 0)) >= 1000 for r in g),
                    'L1_date_proxy': levels['L1_DATE_PROXY'], 'L2_claimed_time': levels['L2_PUBLISHER_TIME_CLAIM'],
                    'L3_L4_qualified': levels['L3_SOURCE_VERSION_VERIFIED'] + levels['L4_ARRIVAL_VERIFIED'],
                    'midnight_UTC_claims': sum(v is not None and v.hour == v.minute == v.second == 0 for v in times),
                    'URL_duplicate_excess': len(urls) - len(set(urls)),
                    'text_duplicate_excess': len(texts) - len(set(texts)),
                    'snapshot_status': 'RETAINED_ROWS_ONLY' if g else 'NO_RETAINED_ROWS_NOT_NO_NEWS',
                    'documented_monitored_sessions': '', 'monitoring_coverage_fraction': '',
                    'true_zero_news_days': '', 'historical_market_completeness': 'UNKNOWN'})
    write_csv(output / 'source_stock_year_coverage.csv', table)
    levels, chronology = [], []
    for (source, ticker), g in sorted(groups.items()):
        if not g: continue
        c = collections.Counter(clock_level(r) for r in g)
        pub = [instant(r.get('published_at')) for r in g]
        retrieval = [instant(r.get('retrieved_at')) for r in g]
        lag = [(a - b).total_seconds() / 86400 for a, b in zip(retrieval, pub) if a and b]
        date_lag = [(a.date() - dt.date.fromisoformat(r['publication_date'])).days for a, r in zip(retrieval, g) if a]
        levels.append({'source': source, 'ticker': ticker, 'rows': len(g),
                       **{k: c[k] for k in ('L0_UNUSABLE_TIME', 'L1_DATE_PROXY', 'L2_PUBLISHER_TIME_CLAIM', 'L3_SOURCE_VERSION_VERIFIED', 'L4_ARRIVAL_VERIFIED')},
                       'first_publication_date': min(r['publication_date'] for r in g),
                       'last_publication_date': max(r['publication_date'] for r in g),
                       'historical_first_seen_verified': 0, 'historical_version_verified': 0})
        chronology.append({'source': source, 'ticker': ticker, 'rows': len(g),
                           'aware_publisher_timestamp': sum(x is not None for x in pub),
                           'aware_current_retrieval': sum(x is not None for x in retrieval),
                           'negative_retrieval_minus_publication': sum(x < 0 for x in lag),
                           'date_based_retrieval_lag_days_min': min(date_lag) if date_lag else '',
                           'date_based_retrieval_lag_days_max': max(date_lag) if date_lag else '',
                           'asof_certified': False,
                           'note': 'Later retrieval consistency is not historical availability proof'})
    write_csv(output / 'PIT_quality_by_source.csv', levels)
    write_csv(output / 'timestamp_chronology.csv', chronology)
    # Overlap indicates dependence/version review, never automatically merges bodies.
    overlap = []
    keys = sorted(k for k, g in groups.items() if g)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            au = {r['url_hash'] for r in groups[a] if r.get('url_hash')}
            bu = {r['url_hash'] for r in groups[b] if r.get('url_hash')}
            at = {r['text_hash'] for r in groups[a] if r.get('text_hash')}
            bt = {r['text_hash'] for r in groups[b] if r.get('text_hash')}
            if au & bu or at & bt:
                overlap.append({'source_a': a[0], 'ticker_a': a[1], 'source_b': b[0], 'ticker_b': b[1],
                    'shared_URL_keys': len(au & bu), 'shared_text_keys': len(at & bt),
                    'same_version_inferred_from_URL_only': False,
                    'text_hash_conventions': 'E4b_title_plus_body; FNSPID_body; social_original_text; not cross-convention equality proof'})
    write_csv(output / 'cross_source_overlap.csv', overlap)
    social = list(read_csv(bundle / 'inputs/social_metadata.csv'))
    sg = collections.defaultdict(list)
    for r in social: sg[(r['view'], r['ticker'], r['date_raw'][:4])].append(r)
    write_csv(output / 'social_author_dataset_coverage.csv', [
        {'view': k[0], 'ticker': k[1], 'year': k[2], 'retained_rows': len(g),
         'distinct_id_hashes': len({r['record_id_hash'] for r in g}),
         'distinct_text_hashes': len({r['text_hash'] for r in g}),
         'date_min': min(r['date_raw'] for r in g), 'date_max': max(r['date_raw'] for r in g),
         'timestamp_precision': 'date_only_no_timezone', 'strict_PIT_qualified': 0,
         'selected_sample_not_full_stream': True}
        for k, g in sorted(sg.items())])
    proc = collections.defaultdict(set); ann = collections.defaultdict(set)
    proc_text = collections.defaultdict(set); ann_text = collections.defaultdict(set)
    for r in social:
        (proc if r['view'] == 'processed_stockemo.csv' else ann)[r['ticker']].add(r['record_id_hash'])
        (proc_text if r['view'] == 'processed_stockemo.csv' else ann_text)[r['ticker']].add(r['text_hash'])
    write_csv(output / 'social_view_overlap.csv', [
        {'ticker': t, 'processed_distinct_ids': len(proc[t]), 'annotated_distinct_ids': len(ann[t]),
         'shared_ids': len(proc[t] & ann[t]), 'annotated_ids_absent_from_processed': len(ann[t] - proc[t]),
         'ID_namespace_equivalence_verified': False,
         'annotated_distinct_texts': len(ann_text[t]),
         'shared_exact_original_texts': len(proc_text[t] & ann_text[t]),
         'annotated_texts_absent_from_processed': len(ann_text[t] - proc_text[t]),
         'counts_additive': False} for t in ('AAPL', 'TSLA')])
    files = list(read_csv(bundle / 'inputs/stocknet_file_metadata.csv'))
    fc = collections.Counter(r['filename_date'][:4] for r in files)
    write_csv(output / 'stocknet_directory_coverage.csv', [
        {'ticker': t, 'year': year, 'dated_files': fc[str(year)] if t == 'AAPL' else 0,
         'articles_or_posts_count': '', 'files_content_downloaded': False,
         'status': 'FILE_METADATA_ONLY' if t == 'AAPL' else 'ABSENT_FROM_LISTED_TICKER_DIRECTORIES',
         'full_historical_stream_certified': False}
        for t in ('AAPL', 'TSLA') for year in range(2012, 2026)])
    # Proxy window overlap uses frozen actual trading sessions. No label fitting.
    market = list(read_csv(bundle / 'inputs/market_event_metadata.csv'))
    by_stock = {t: sorted([r for r in market if r['ticker'] == t], key=lambda r: r['date']) for t in ('AAPL', 'TSLA')}
    calendar = list(read_csv(bundle / 'inputs/trading_sessions.csv'))
    full_sessions = {t: sorted({r['date'] for r in calendar if r['ticker'] == t}) for t in ('AAPL', 'TSLA')}
    event_table, timing_table, support_table = [], [], []
    for (source, ticker), g in sorted(groups.items()):
        if not g: continue
        days = by_stock[ticker]; sessions = full_sessions[ticker]
        session_positions = {d: i for i, d in enumerate(sessions)}
        cutoffs = [dt.datetime.combine(dt.date.fromisoformat(d), dt.time(17), NY).astimezone(UTC) for d in sessions]
        firsts, shift_counts = {}, collections.Counter()
        for delay in (0, 1, 2):
            count = collections.Counter(); article_dates = []
            for r in g:
                pub = instant(r.get('published_at'))
                pos = bisect.bisect_left(cutoffs, pub) if pub and r['precision'] == 'publisher_time_claim' else bisect.bisect_right(sessions, r['publication_date'])
                pos += delay
                if pos < len(sessions):
                    # Exact text duplication within the same source/window excluded.
                    article_dates.append((pos, r.get('text_hash') or r['record_key']))
                    if delay == 0: firsts[r['record_key']] = sessions[pos]
                    elif firsts.get(r['record_key']) != sessions[pos]: shift_counts[delay] += 1
            if not article_dates: continue
            ix = collections.defaultdict(set)
            for pos, text in article_dates: ix[pos].add(text)
            lo, hi = min(ix), max(ix)
            for day in days:
                i = session_positions[day['date']]
                found = set().union(*(ix.get(j, set()) for j in range(max(0, i - 4), i + 1)))
                count[(day['date'][:4], 'dates')] += 1
                if found: count[(day['date'][:4], 'overlap_dates')] += 1
                if day['event'] in ('True', '1', '1.0'):
                    key = (day['date'][:4], 'events'); count[key] += 1
                    if found: count[(day['date'][:4], 'overlap_events')] += 1
            for year in range(2012, 2026):
                n, m = count[(str(year), 'events')], count[(str(year), 'overlap_events')]
                event_table.append({'source': source, 'ticker': ticker, 'year': year, 'delay_sessions': delay,
                    'price_events': n, 'events_with_retained_source_in_last5': m,
                    'snapshot_event_overlap_fraction': m / n if n else '',
                    'strict_PIT_event_coverage': '', 'source_monitoring_coverage': '',
                    'not_market_news_or_social_completeness': True})
            if delay == 0:
                for period, start, end in [('train_2012_2022', '2012', '2022'), ('validation_2023', '2023', '2023'), ('exploratory_2024_2025', '2024', '2025')]:
                    selected, last = [], -100
                    for day in days:
                        i = session_positions[day['date']]
                        if not (start <= day['date'][:4] <= end): continue
                        if day['event'] not in ('True', '1', '1.0') or i - last < 5: continue
                        # Eligibility only requires known rows for descriptive proxy;
                        # true observation coverage is NA in all cases.
                        found = set().union(*(ix.get(j, set()) for j in range(max(0, i - 4), i + 1)))
                        last = i  # Thin all price events first, independently of source presence.
                        if found:
                            selected.append(day)
                    positives = sum(d['future_y5'] in ('True', '1', '1.0') for d in selected)
                    negatives = sum(d['future_y5'] in ('False', '0', '0.0') for d in selected)
                    support_table.append({'source': source, 'ticker': ticker, 'legacy_partition': period,
                        'nonoverlap5_price_events_with_retained_proxy': len(selected),
                        'reversal_labels': positives,
                        'nonreversal_labels': negatives,
                        'missing_labels': len(selected) - positives - negatives,
                        'formal_E8b_eligible_events': 0,
                        'note': 'First event every5sessions chosen on full price-event calendar before source filter; old partitions diagnostic, not new E8b split'})
        for delay in (1, 2):
            timing_table.append({'source': source, 'ticker': ticker, 'delay_sessions': delay,
                'rows_with_available_base_proxy': len(firsts), 'rows_shifted_inside_calendar': shift_counts[delay],
                'historical_version_evidence_created_by_delay': False})
    write_csv(output / 'event_source_overlap.csv', event_table)
    write_csv(output / 'proxy_timing_sensitivity.csv', timing_table)
    write_csv(output / 'legacy_partition_support.csv', support_table)
    # Gate status is about evidence, not whether a fitted model would improve.
    gates = [
        ('permitted_research_and_reproduction', 'NOT_VERIFIED_FOR_COMBINED_DATASET', 'Author access and existing local files do not certify platform/publisher redistribution rights'),
        ('strict_historical_content_and_availability', 'FAIL', 'Zero L3/L4 source-version records'),
        ('same_source_2train_1validation_1test_years', 'FAIL', 'Apple3years, StockEmotions~1year, FNSPID gaps; StockNet file metadata only'),
        ('documented_session_monitoring_at_least90percent', 'NOT_EVALUABLE', 'No historical query/collector uptime and pagination completeness ledger'),
        ('nonoverlap_event_and_class_support', 'NOT_EVALUABLE', 'No eligible source panel; raw/proxy counts cannot replace eligible independent support'),
        ('100_independent_manual_version_and_relevance_QA', 'NOT_DONE', 'Zero independent manual historical-version reviews in E8a'),
        ('development_only_paired_loss_power_and_size', 'NOT_ESTIMABLE', 'No model fits/loss contrasts; no independent financial-event count invented'),
        ('unseen_preregistered_E8_validation', 'NOT_ESTABLISHED', '2024-2025 explored; original E3c2026 contract excluded from E8')]
    write_csv(output / 'E8b_readiness_gates.csv', [{'gate': g, 'status': s, 'reason': r} for g, s, r in gates])
    result = {'metadata_records_including_overlapping_views': len(rows), 'news_record_rows': sum(not r['source'].startswith('StockEmotions') for r in rows),
              'strict_source_PIT_records': sum(clock_level(r) in ('L3_SOURCE_VERSION_VERIFIED', 'L4_ARRIVAL_VERIFIED') for r in rows),
              'strict_arrival_PIT_records': sum(clock_level(r) == 'L4_ARRIVAL_VERIFIED' for r in rows),
              'historical_monitoring_fraction': None, 'independent_manual_version_reviews': 0,
              'StockNet_AAPL_dated_files': len(files), 'StockNet_TSLA_in_listed_directories': False,
              'E8b_formal': 'NOT_READY', 'new_models': 0, 'GPU_used': False,
              'E3c2026': 'UNCHANGED_NOT_EXECUTED', 'statistical_news_or_social_gain': 'NOT_TESTED'}
    dump(output / 'analysis_results.json', result)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parents[1] / 'outputs/e8a_20261108')
    p.add_argument('--output-dir', type=Path)
    a = p.parse_args(); analyze(a.bundle, a.output_dir or a.bundle / 'tables')
