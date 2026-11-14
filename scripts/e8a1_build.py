"""Rebuild pilot audit tables and schemas, never collect or fit financial data."""
import argparse
import csv
import json
from pathlib import Path
from e8a1_collector import digest, canonical, OfflineCollector

FIELDS = ['source', 'dataset_revision', 'record_id', 'parent_id', 'version_id', 'ticker', 'cashtag', 'company_id', 'entity_binding_status', 'published_at', 'edited_at', 'deleted_at', 'retrieved_at', 'verified_public_version_at', 'verified_capture_at', 'verified_arrival_at', 'raw_sha256', 'source_evidence_uri', 'evidence_index', 'text_sha256', 'representation', 'timestamp_precision', 'timezone', 'access_agreement_id', 'retention_status', 'deletion_compliance_status', 'PIT_level', 'asof_eligible', 'rejection_reasons']

def write(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True); rows = list(rows)
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def tables(bundle, output):
    cards = json.loads((bundle / 'sources/evidence_cards.json').read_text())
    write(output / 'source_access_evidence.csv', cards)
    write(output / 'source_manifest.csv', [
        {'source_id': c['id'], 'url': c['url'], 'checked_date': c['checked_date'],
         'page_revision': c['observed_page_revision'], 'evidence_locator': c['evidence_locator'],
         'evidence_card_sha256': digest(canonical(c)), 'original_HTTP_sha256': '',
         'hash_scope': 'curated_documentation_card_not_original_HTTP_or_post',
         'historical_content_sample': False} for c in cards])
    frozen = list(csv.DictReader((bundle / 'inputs/e8a_contract/tables/E8b_readiness_gates.csv').open()))
    decisions = [
        ('BLOCKED', 'ST01-ST07,RD01-RD02,BZ01-BZ02', 'No project-approved raw-content access or research retention/export agreement; no application/payment sent'),
        ('FAIL', 'PILOT_SAMPLE_MANIFEST.csv,SAMPLE_ACQUISITION_STATUS.json', '0real records,0L3,0L4; no independently bound historical content witness'),
        ('NOT_EVALUABLE', 'ST03-ST06,RD01,BZ01-BZ02', 'No same-source ticker panel; service-wide history claims do not establish2train+1validation+1test years'),
        ('NOT_EVALUABLE', 'ST05,RD01', 'No source query/pagination/uptime ledger; backup seq_id absent and RFR monthly recent versions are not original monitor logs'),
        ('NOT_EVALUABLE', 'PILOT_SAMPLE_MANIFEST.csv', 'No qualified panel; no nonoverlap event/class supports inferred from post counts'),
        ('BLOCKED', 'MANUAL_QA_PENDING.csv,MANUAL_QA_PROTOCOL.md', '0real candidates and0completed human reviews; pilot30-50material target differs from formal100QA'),
        ('NOT_EVALUABLE', 'PILOT_PLAN_LOCKED.json', 'No new models/losses; no paired Brier variance, dependency, test-size or power estimates fabricated'),
        ('BLOCKED', 'inputs/e8a_contract/AUDIT_PLAN_LOCKED.json', 'Separate E8 unseen period/preregistration not established; E3c2026 excluded and unchanged')]
    write(output / 'E8b_readiness_decision.csv', [
        {'gate': f['gate'], 'frozen_E8a_status': f['status'], 'E8a1_status': d[0],
         'evidence': d[1], 'reason': d[2], 'threshold_changed': False}
        for f, d in zip(frozen, decisions)])
    write(output / 'real_sample_and_QA_counts.csv', [
        {'measure': k, 'actual': n, 'target_or_scope': note}
        for k, n, note in [('new_real_records', 0, 'conditional30-50pilot'), ('real_L3_qualified', 0, 'source-version'),
                          ('real_L4_qualified', 0, 'source-plus-arrival'), ('pilot_real_QA_candidates', 0, '30-50materials'),
                          ('independent_human_QA_completed', 0, 'formal100distinctdocuments'),
                          ('financial_models_fitted', 0, 'prohibited'), ('new_Brier_AUC_comparisons', 0, 'prohibited')]])
    write(output / 'source_costs_and_actions.csv', [
        {'source': s, 'public_cost_evidence': cost, 'project_spend': 0, 'approval_or_action_required': action, 'evidence': refs}
        for s, cost, action, refs in [
            ('Stocktwits Enterprise', 'Custom quote; amount/academic discount not published', 'Professor/institution requests sample contract,4year coverage,version/arrival/delete logs,retention and derived-output permissions', 'ST01,ST03-ST06'),
            ('Stocktwits Edge', 'Displayed US$229.50/year promotional consumer subscription; NOT historical raw API budget', 'Do not buy to solve4yearrawdata gate; general1yearhistory cannot establish entitlement', 'ST03,ST07'),
            ('Reddit RFR', 'Approved noncommercial academic dataset access free; compute/export costs unconfirmed', 'Institutional email,faculty sponsor,IRB/exemption,research proposal,individual accounts; clarify version snapshots', 'RD01-RD02'),
            ('Benzinga/Massive', 'Contract/plan price and research redistribution rights not established here', 'Obtain permitted sample and explicit immutable history/receipt scope; no automatic trial/signup', 'BZ01-BZ02'),
            ('Common Crawl', 'ArchiveHTTPaccess free; ownstorage/compute separate and unpriced', 'Review underlying publisher rights first; historical capture metadata alone not blanket text use', 'CC01-CC02')]])
    schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'E8a1ProvenanceRecord',
        'type': 'object', 'additionalProperties': False,
        'required': FIELDS + ['synthetic'],
        'properties': {k: {'type': ['string', 'null']} for k in FIELDS}}
    schema['properties'].update(synthetic={'type': 'boolean'}, ticker={'enum': ['AAPL', 'TSLA']},
        PIT_level={'enum': ['L0', 'L1', 'L2', 'L3', 'L4', 'NOT_VERIFIED']},
        asof_eligible={'type': 'boolean'}, rejection_reasons={'type': 'array', 'items': {'type': 'string'}})
    for k in ['raw_sha256', 'text_sha256']:
        schema['properties'][k] = {'type': ['string', 'null'], 'pattern': '^[a-f0-9]{64}$'}
    dump(output / 'provenance_record.schema.json', schema)
    dump(output / 'collector_config.schema.json', {'$schema': 'https://json-schema.org/draft/2020-12/schema',
        'title': 'Offline-onlyCollectorPlan', 'type': 'object', 'required': ['mode', 'live_enabled', 'synthetic_fixture_permission', 'windows'],
        'properties': {'mode': {'const': 'offline_synthetic'}, 'live_enabled': {'const': False},
        'synthetic_fixture_permission': {'const': 'SELF_AUTHORED_TEST_DATA_ONLY'},
        'windows': {'type': 'array', 'items': {'type': 'object', 'required': ['source', 'ticker', 'session', 'query', 'window_start', 'window_end']}}}})
    dump(output / 'audit_results.json', {'status': 'COMPLETE_PILOT_AUDIT_EXTERNAL_DATA_BLOCKED',
        'real_samples': 0, 'L3': 0, 'L4': 0, 'manual_QA_candidates': 0, 'manual_QA_completed': 0,
        'formal_QA_target': 100, 'pilot_material_target': [30, 50], 'source_evidence_cards': len(cards),
        'E8b': 'NOT_READY', 'frozen_thresholds_changed': False, 'financial_models': 0,
        'new_financial_scores': 0, 'live_collector_started': False, 'applications_sent': 0, 'payments': 0,
        'E3c2026': 'UNCHANGED_NOT_EXECUTED'})

def demo(output):
    if output.exists(): raise FileExistsError('New demo output required')
    plan = {'mode': 'offline_synthetic', 'live_enabled': False, 'synthetic_fixture_permission': 'SELF_AUTHORED_TEST_DATA_ONLY',
       'windows': [{'source': 'SYNTHETIC_SOURCE', 'ticker': t, 'session': '2030-01-02', 'query': 'cashtag:' + t,
                    'window_start': '2030-01-01T22:00:00Z', 'window_end': '2030-01-02T22:00:00Z'} for t in ('AAPL', 'TSLA')]}
    c = OfflineCollector(output, plan)
    fixture = {'synthetic': True, 'record_id': 'OWNED_FIXTURE_1', 'version_id': 'v1', 'ticker': 'AAPL',
               'action': 'create', 'event_at': '2030-01-02T20:00:00Z', 'published_at': '2030-01-02T19:00:00Z',
               'text': 'SELF-AUTHORED SYNTHETIC TEST CONTENT; NO MARKET CLAIM'}
    page = canonical({'synthetic': True, 'items': [fixture], 'next_cursor': 'opaque-second-page', 'terminal': False})
    c.ingest(plan['windows'][0], page, '2030-01-02T21:59:50Z', '2030-01-02T21:59:51Z')
    # Explicit restart proves cursor projection survives an offline process restart.
    c = OfflineCollector(output, plan)
    c.ingest(plan['windows'][0], canonical({'synthetic': True, 'items': [], 'next_cursor': None, 'terminal': True}),
             '2030-01-02T21:59:55Z', '2030-01-02T22:00:00Z', cursor='opaque-second-page')
    c.ingest(plan['windows'][1], canonical({'synthetic': True, 'error': 'fixture rate limit'}),
             '2030-01-02T21:59:55Z', '2030-01-02T22:00:00Z', status=429)
    write(output / 'coverage.csv', c.coverage())
    c.seal_day('2030-01-02', '2030-01-03T00:00:00Z')
    dump(output / 'DEMO_ONLY.json', {'synthetic': True, 'real_records': 0, 'research_L3_L4': 0,
          'planned_windows': 2, 'complete_query_windows': 1, 'failed_or_unknown': 1,
          'synthetic_coverage_fraction': .5, 'real_source_coverage_inferred': False,
          'journal_head': c.verify(), 'network_transport': 'ABSENT'})

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--bundle', type=Path); p.add_argument('--output-dir', type=Path, required=True); p.add_argument('--demo', action='store_true')
    a = p.parse_args()
    if a.demo: demo(a.output_dir)
    else:
        if not a.bundle: p.error('--bundle required for table replay')
        tables(a.bundle, a.output_dir)
