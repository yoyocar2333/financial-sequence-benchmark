"""Read existing E4 assets into a content-free, version-aware audit packet."""
import collections
import csv
import gzip
import json
import re
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from e8a_core import sha, digest, dump, read_csv, write_csv, instant

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('E8A_OUTPUT', ROOT / 'outputs/e8a_20261108')).resolve()
A = ROOT / 'outputs/e4a_20261026_phase7a'
B = ROOT / 'outputs/e4b_20261026'
C = ROOT / 'outputs/e4c_20261026'

def canonical_url(value):
    u = urlsplit(value or '')
    query = [(k, v) for k, v in parse_qsl(u.query) if not k.lower().startswith('utm_') and k.lower() not in ('ref', 'source', 'fbclid', 'gclid')]
    return urlunsplit((u.scheme.lower(), u.netloc.lower(), u.path.rstrip('/'), urlencode(sorted(query)), ''))

def normalized(origin, rid, ticker, source, date, published, precision, retrieved, url, text_hash, representation, characters):
    if not ('2012-01-01' <= date[:10] <= '2025-12-31'):
        raise ValueError('Historical row scope violation; no content inspection permitted')
    t = instant(published)
    if 'midnight' in precision.lower() or (source.startswith('FNSPID') and t and t.hour == t.minute == t.second == 0):
        precision = 'midnight_unverified'
    elif not t:
        precision = 'date_only'
    else:
        precision = 'publisher_time_claim'
    return {'origin': origin, 'record_key': digest(origin + '|' + rid), 'ticker': ticker,
            'source': source, 'publication_date': date[:10], 'published_at': published,
            'precision': precision, 'retrieved_at': retrieved,
            'url_hash': digest(canonical_url(url)) if url else '', 'text_hash': text_hash,
            'representation': representation, 'content_characters': characters,
            'verified_public_version_at': '', 'verified_capture_at': '', 'verified_arrival_at': '',
            'version_evidence_verified': False, 'use_permission_verified': False,
            'deleted_or_withdrawn': '', 'source_monitoring_complete': '',
            'feature_inference_historical': False}

def artifact_inventory():
    paths = set()
    for p in (ROOT / 'outputs').glob('e4*'):
        if p.is_dir():
            paths.update(x for x in p.rglob('*') if x.is_file())
    paths.update((ROOT / 'scripts').glob('*e4*.py'))
    paths.update(ROOT.glob('E4*'))
    paths.update(ROOT.glob('README_E4*'))
    paths.add(ROOT / 'data/market_20261019/raw/StockLLM_phase7A.zip')
    paths.add(ROOT / 'data/fnspid_bf9189c41527198897d1af3e17b1a0095279fc45/nasdaq_exteral_data.csv')
    rows = []
    for p in sorted(paths):
        if not p.is_file(): continue
        name = str(p.relative_to(ROOT)); size = p.stat().st_size
        mutable = p.name.endswith(('.sqlite', '.sqlite-shm', '.sqlite-wal'))
        active = any(name.startswith(str(x.relative_to(ROOT)) + '/') for x in (A, B, C))
        if size <= 128_000_000 and not mutable:
            h, proof = sha(p), 'E8a_fresh_byte_hash'
        elif p.with_suffix(p.suffix + '.sha256').exists():
            h = p.with_suffix(p.suffix + '.sha256').read_text().split()[0]; proof = 'prior_sidecar_not_rehashed'
        else:
            h, proof = '', 'metadata_only_large_or_mutable'
        if p.suffix in ('.pkl', '.pt', '.pth', '.bin'):
            kind = 'model_artifact_hash_only_never_loaded'
        elif '/predictions/' in name: kind = 'predictions'
        elif '/features/' in name: kind = 'features'
        elif '/raw/' in name or '/http/' in name: kind = 'raw_or_HTTP'
        elif '/figures/' in name: kind = 'figure'
        elif p.suffix == '.zip': kind = 'archive_not_independent_observations'
        else: kind = 'code_metadata_report_or_table'
        rows.append({'path': name, 'bytes': size, 'sha256': h, 'hash_scope': proof,
                     'role': kind, 'active_canonical_stage': active,
                     'observation_count_policy': 'physical_artifact_not_extra_articles'})
    write_csv(OUT / 'audits/artifact_inventory.csv', rows)
    groups = collections.defaultdict(list)
    for r in rows:
        if r['sha256']: groups[r['sha256']].append(r)
    write_csv(OUT / 'tables/artifact_inventory_summary.csv', [
        {'role': role, 'physical_files': len(g), 'bytes': sum(r['bytes'] for r in g),
         'active_files': sum(r['active_canonical_stage'] for r in g)}
        for role in sorted({r['role'] for r in rows})
        for g in [[r for r in rows if r['role'] == role]]])
    dump(OUT / 'audits/inventory_scope.json', {
        'physical_files': len(rows), 'fresh_hash_files': sum(r['hash_scope'] == 'E8a_fresh_byte_hash' for r in rows),
        'repeated_hash_groups': sum(len(g) > 1 for g in groups.values()),
        'active_roots': [str(p.relative_to(ROOT)) for p in (A, B, C)],
        'older_and_replay_versions_included_in_physical_inventory': True,
        'large_FNSPID_master_rehashed_in_E8a': False,
        'FNSPID_full_scan_evidence': 'Prior E4c EOF/full SHA evidence reused, target exports freshly hashed and row-recomputed',
        'no_pickle_or_checkpoint_deserialized': True})

def prepare():
    if (OUT / 'inputs/news_metadata.csv.gz').exists():
        raise FileExistsError('Preserve captured packet; use new run for new sources')
    artifact_inventory()
    records = []
    for r in read_csv(A / 'aligned/news_metadata_normalized.csv'):
        if r['publication_date'][:4] != '2023': continue  # 52 summaries below have exact-version identities.
        records.append(normalized('E4a_metadata100', r['article_id'], 'AAPL', 'Apple_metadata100',
                                  r['publication_date'], r['published_utc'], r['timestamp_precision'], '',
                                  r['url'], r['text_sha256'], 'metadata_only', 0))
    raw = list(read_csv(B / 'datasets/news_unified.csv.gz'))
    bad_hashes = 0
    id_hash = {}
    for r in raw:
        # Scope gate precedes any reading of title/body for hashes.
        if not ('2012-01-01' <= r['publication_date'][:10] <= '2025-12-31'):
            raise ValueError('Unexpected E4b historical scope')
        actual = digest(r['title'] + '\n\n' + r['content'])
        bad_hashes += actual != r['text_sha256']
        id_hash[r['record_id']] = r['text_sha256']
        family = {'apple_newsroom_recollected': 'Apple_recollected',
                  'phase7a_original_summary': 'Phase7A_summary',
                  'fnspid_bounded_headlines': 'FNSPID_All_external_partial'}[r['source_family']]
        records.append(normalized('E4b_unified', r['record_id'], r['ticker'], family,
                                  r['publication_date'], r['published_utc'], r['timestamp_precision'], r['retrieved_utc'],
                                  r['url'], r['text_sha256'], r['representation'], int(r['content_characters'])))
    features = list(read_csv(B / 'features/article_features.csv'))
    orphans = sum(id_hash.get(r['record_id']) != r['text_sha256'] for r in features)
    duplicate_views = len(features) - len({(r['record_id'], r['source']) for r in features})
    primary = sum(r['primary_view'] == 'True' for r in features)
    bad_probability = sum(abs(sum(float(r[k]) for k in ('sent_positive', 'sent_negative', 'sent_neutral')) - 1) > 1e-5 for r in features)
    chunks = [json.loads(line) for line in (B / 'features/finbert_chunks.jsonl').open()]
    chunk_groups = collections.defaultdict(list)
    for r in chunks: chunk_groups[(r['record_id'], r['source'])].append(r)
    # Original chunk fields are inspected, then recomputed without model execution.
    errors, max_difference = 0, 0.
    for r in features:
        g = chunk_groups[(r['record_id'], r['source'])]
        total = sum(int(v['tokens']) for v in g)
        for out, key in [('sent_positive', 'positive'), ('sent_negative', 'negative'), ('sent_neutral', 'neutral')]:
            # Stored FinBERT chunks use probability labels, not future-return labels.
            value = sum(float(v[key]) * int(v['tokens']) for v in g) / total
            d = abs(float(r[out]) - value); max_difference = max(max_difference, d)
            errors += d > 1e-6
    gemini = list(read_csv(B / 'features/gemini_original36_exact_version_join.csv'))
    gemini_bad = sum(id_hash.get(r['record_id']) != r['text_sha256'] for r in gemini)
    feature_stats = [
        {'check': 'E4b_article_text_hash', 'observations': len(raw), 'failures': bad_hashes},
        {'check': 'feature_exact_record_and_version_join', 'observations': len(features), 'failures': orphans},
        {'check': 'unique_record_feature_view', 'observations': len(features), 'failures': duplicate_views},
        {'check': 'one_primary_view_per_article_record', 'observations': len(raw), 'failures': abs(primary - len(raw))},
        {'check': 'FinBERT_probability_sum', 'observations': len(features), 'failures': bad_probability},
        {'check': 'FinBERT_chunk_weight_reconstruction', 'observations': len(chunks), 'failures': errors},
        {'check': 'Gemini_same_summary_version_join', 'observations': len(gemini), 'failures': gemini_bad}]
    write_csv(OUT / 'tables/feature_integrity.csv', feature_stats)
    dump(OUT / 'audits/feature_integrity.json', {'chunk_max_absolute_difference': max_difference,
         'inference_rerun': False, 'historical_feature_available_claim': False,
         'manual_semantic_gold_reviewed_in_E8a': 0, 'no_original_Gemini_service_revision_certification': True})
    for ticker in ('AAPL', 'TSLA'):
        for r in read_csv(C / f'fnspid_audit/{ticker}_all_retained_rows.csv.gz'):
            date = r['Date'][:10]
            if not ('2012-01-01' <= date <= '2025-12-31'):
                raise ValueError('Unexpected FNSPID historical scope')
            body = r['Article']
            records.append(normalized('E4c_FNSPID_Nasdaq', str(r['source_csv_row']), ticker, 'FNSPID_Nasdaq_fullscan',
                                      date, r['Date'], '', '', r['Url'], digest(body) if body else '',
                                      'nonempty_body_not_certified_fulltext' if body.strip() else 'headline_only', len(body)))
    fields = list(records[0])
    with gzip.open(OUT / 'inputs/news_metadata.csv.gz', 'wt', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader(); w.writerows(records)
    # Copy only already-public/timeless source evidence and content-free market metadata.
    market_fields = ['ticker', 'date', 'partition', 'event', 'event_direction', 'conflict', 'future_y5']
    write_csv(OUT / 'inputs/market_event_metadata.csv', [
        {k: r[k] for k in market_fields} for r in read_csv(A / 'aligned/market_news_alignment.csv.gz')
        if '2012-01-01' <= r['date'] <= '2025-12-31'])
    # Information-time calendar MUST NOT be the purged model-evaluation calendar.
    write_csv(OUT / 'inputs/trading_sessions.csv', [
        {'ticker': ticker, 'date': r['Date'][:10]}
        for ticker in ('AAPL', 'TSLA') for r in read_csv(A / f'inputs/{ticker}_adjusted_through2025.csv')
        if '2011-01-01' <= r['Date'][:10] <= '2025-12-31'])
    selected = [B / 'datasets/news_unified.csv.gz', B / 'datasets/news_unified_feature_input.csv.gz',
                B / 'features/article_features.csv', B / 'features/finbert_chunks.jsonl',
                B / 'features/gemini_original36_exact_version_join.csv',
                B / 'features/model_registry.json', C / 'data/daily_features.csv.gz',
                C / 'data/article_timing_manifest.csv', C / 'fnspid_audit/COMPLETE.json',
                C / 'fnspid_audit/QUALITY_COMPLETE.json', A / 'aligned/news_metadata_normalized.csv']
    selected += [A / f'inputs/{t}_adjusted_through2025.csv' for t in ('AAPL', 'TSLA')]
    selected += [C / f'fnspid_audit/{t}_all_retained_rows.csv.gz' for t in ('AAPL', 'TSLA')]
    predictions = []
    for p in sorted((C / 'predictions').glob('*.csv.gz')):
        selected.append(p)
        counts = collections.Counter(); seen = set(); dup = invalid = after2025 = 0
        for r in read_csv(p):
            if r.get('date', '') > '2025-12-31': after2025 += 1; continue
            counts[(r.get('partition', 'test'), r.get('timing', ''), r.get('method', ''), r.get('seed', 'mean'))] += 1
            key = tuple(r.get(k, '') for k in ('ticker', 'date', 'partition', 'timing', 'method', 'seed'))
            dup += key in seen; seen.add(key)
            for k in ('p_raw', 'p_calibrated'):
                if k in r:
                    try: invalid += not (0 <= float(r[k]) <= 1)
                    except ValueError: invalid += 1
        for (partition, timing, method, seed), count in sorted(counts.items()):
            predictions.append({'file': p.name, 'partition': partition, 'timing': timing, 'method': method,
                                'seed': seed, 'rows': count, 'file_duplicate_keys': dup,
                                'file_invalid_probabilities': invalid, 'after2025_rows_excluded': after2025})
    write_csv(OUT / 'tables/prior_prediction_inventory.csv', predictions)
    write_csv(OUT / 'audits/canonical_input_manifest.csv', [
        {'path': str(p.relative_to(ROOT)), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in selected])
    dump(OUT / 'inputs/e4_feature_registry.json', json.loads((B / 'features/model_registry.json').read_text()))
    dump(OUT / 'inputs/FNSPID_full_scan_evidence.json', json.loads((C / 'fnspid_audit/COMPLETE.json').read_text()))
    # Directory listing only: counts of dated files do not assert counts of posts.
    listing = json.loads((OUT / 'sources/e8a_repo_0.json').read_text())['value']['structuredContent']
    entries = json.loads(listing['content'])
    write_csv(OUT / 'inputs/stocknet_file_metadata.csv', [
        {'ticker': 'AAPL', 'filename_date': r['name'], 'bytes': r['size'], 'git_blob_sha1': r['sha']}
        for r in entries if r['type'] == 'file'])
    dump(OUT / 'audits/prepare_complete.json', {'metadata_news_rows': len(records),
        'feature_views': len(features), 'feature_primary_views': primary, 'FinBERT_chunks': len(chunks),
        'Gemini_summary_views': len(gemini), 'features_verified_without_model_execution': True,
        'new_models': 0, 'no_GPU': True, '2026_rows_used': 0,
        'independent_original_version_QA': 0, 'all_checks_passed': all(r['failures'] == 0 for r in feature_stats)})
    print('Metadata packet:', len(records), 'news records; feature checks:', feature_stats)

if __name__ == '__main__':
    prepare()
