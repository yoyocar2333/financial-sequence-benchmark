"""Self-authored synthetic engineering tests. Zero real samples or manual QA."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from e8a1_collector import OfflineCollector, canonical, digest, assess_provenance, timestamp, safe_path

def plan():
    return {'mode': 'offline_synthetic', 'live_enabled': False,
            'synthetic_fixture_permission': 'SELF_AUTHORED_TEST_DATA_ONLY',
            'windows': [{'source': 'SYNTHETIC_SOURCE', 'ticker': t, 'session': d,
                         'query': 'exact_cashtag_' + t, 'window_start': '2030-01-01T22:00:00Z',
                         'window_end': '2030-01-02T22:00:00Z'} for t in ('AAPL', 'TSLA') for d in ['2030-01-02']]}

def item(version='v1', action='create', text='OWNED SYNTHETIC FIXTURE'):
    return {'synthetic': True, 'record_id': 'fixture1', 'version_id': version, 'parent_id': None,
            'ticker': 'AAPL', 'action': action, 'event_at': '2030-01-02T20:00:00Z',
            'published_at': '2030-01-02T19:00:00Z', 'text': text}

def response(items=None, cursor=None, terminal=True, **extra):
    return canonical({'synthetic': True, 'items': items or [], 'next_cursor': cursor,
                      'terminal': terminal, **extra})

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.plan = plan(); self.c = OfflineCollector(self.root, self.plan); self.w = self.plan['windows'][0]
    def tearDown(self): self.temp.cleanup()
    def ingest(self, body=None, **kw):
        return self.c.ingest(self.w, body or response(), '2030-01-02T21:59:55Z', kw.pop('received', '2030-01-02T22:00:00Z'), **kw)
    def test_live_transport_unavailable(self):
        with self.assertRaises(PermissionError): self.c.live()
    def test_live_config_rejected(self):
        p = plan(); p['live_enabled'] = True
        with self.assertRaises(PermissionError): OfflineCollector(self.root / 'x', p)
    def test_unknown_license_fixture_rejected(self):
        p = plan(); p['synthetic_fixture_permission'] = 'UNKNOWN'
        with self.assertRaises(PermissionError): OfflineCollector(self.root / 'x', p)
    def test_real_envelope_rejected(self):
        with self.assertRaises(PermissionError): self.ingest(canonical({'items': []}))
        self.assertEqual(len(list((self.root / 'raw').glob('*'))), 0)
    def test_non_synthetic_item_rejected(self):
        a = item(); a['synthetic'] = False
        with self.assertRaises(PermissionError): self.ingest(response([a]))
        self.assertEqual(self.c.chain[-1]['event']['kind'], 'request_rejected')
    def test_zero_requires_terminal_and_known_window(self):
        self.ingest(); rows = self.c.coverage()
        self.assertTrue(rows[0]['observed_query_zero']); self.assertIsNone(rows[1]['retained_record_ids'])
        self.assertFalse(rows[1]['observed_query_zero'])
    def test_http200_is_not_eof(self):
        self.ingest(response(terminal=False))
        self.assertFalse(self.c.coverage()[0]['monitored_complete'])
    def test_partial_success_is_unknown(self):
        self.ingest(response(errors=['incomplete']))
        self.assertIsNone(self.c.coverage()[0]['retained_record_ids'])
    def test_429_logged_without_automatic_retry(self):
        r = self.ingest(response(errors=['rate limit']), status=429)
        self.assertTrue((self.root / r['raw_path']).exists()); self.assertEqual(len(self.c.chain), 1)
    def test_retry_after_failure_does_not_erase_gap(self):
        self.ingest(status=429); self.ingest()
        self.assertFalse(self.c.coverage()[0]['monitored_complete'])
    def test_late_response_not_historical_monitored_at_cutoff(self):
        self.ingest(received='2030-01-03T00:00:00Z')
        self.assertFalse(self.c.coverage()[0]['monitored_complete'])
    def test_backfill_not_original_monitoring(self):
        self.ingest(backfill=True)
        self.assertFalse(self.c.coverage()[0]['monitored_complete'])
    def test_unproven_continuity_not_complete(self):
        self.ingest(continuity_proven=False)
        self.assertFalse(self.c.coverage()[0]['monitored_complete'])
    def test_fixed_query_cannot_expand(self):
        w = dict(self.w, ticker='OTHER')
        with self.assertRaises(ValueError): self.c.ingest(w, response(), '2030-01-02T21:00:00Z', '2030-01-02T22:00:00Z')
    def test_wrong_ticker_rejected(self):
        a = item(); a['ticker'] = 'TSLA'
        with self.assertRaises(ValueError): self.ingest(response([a]))
    def test_pagination_and_restart(self):
        self.ingest(response([item()], cursor='opaque-page2', terminal=False))
        self.c = OfflineCollector(self.root, self.plan)
        self.ingest(response([item()]), cursor='opaque-page2')
        self.assertEqual(self.c.coverage()[0]['retained_record_ids'], 1)
    def test_repeated_cursor_rejected(self):
        self.ingest(response(cursor='p2', terminal=False))
        with self.assertRaises(ValueError): self.ingest(response(cursor='p2', terminal=False), cursor='p2')
    def test_same_version_conflicting_text_rejected(self):
        self.ingest(response([item()], cursor='p2', terminal=False))
        with self.assertRaises(ValueError): self.ingest(response([item(text='OTHER OWNED FIXTURE')]), cursor='p2')
    def test_edit_versions_retained_separately(self):
        self.ingest(response([item(), item('v2', 'edit', 'OWNED EDIT FIXTURE')]))
        self.assertEqual(len(self.c.state[self.c._slot(self.w)]['records']), 2)
    def test_delete_and_withdraw_remove_content_and_keep_tombstone(self):
        self.ingest(response([item(), item('tombstone', 'delete', '')]))
        removed = self.c.withdraw('SYNTHETIC_SOURCE', 'fixture1', 'fixture deletion', '2030-01-03T00:00:00Z')
        self.assertTrue(removed); self.assertEqual(list((self.root / 'raw').glob('*.json')), [])
        self.assertNotIn('OWNED SYNTHETIC FIXTURE', self.c.journal.read_text())
        self.assertEqual(self.c.chain[-1]['event']['kind'], 'withdrawal')
    def test_withdrawal_survives_restart(self):
        self.ingest(response([item()])); self.c.withdraw('SYNTHETIC_SOURCE', 'fixture1', 'fixture', '2030-01-03T00:00:00Z')
        c = OfflineCollector(self.root, self.plan)
        self.assertIn(('SYNTHETIC_SOURCE', 'fixture1'), c.withdrawn)
        self.assertFalse(c.coverage()[0]['observed_query_zero'])
    def test_deleted_content_not_no_post_observation(self):
        self.ingest(response([item(), item('tombstone', 'delete', '')]))
        r = self.c.coverage()[0]
        self.assertEqual(r['retained_record_ids'], 0); self.assertFalse(r['observed_query_zero'])
    def test_tamper_detected(self):
        self.ingest(); s = self.c.journal.read_text().replace('request_result', 'modified_result')
        self.c.journal.write_text(s)
        with self.assertRaises(ValueError): self.c.verify()
    def test_retained_head_detects_truncation(self):
        self.ingest(); head = self.c.head; self.c.journal.write_text('')
        with self.assertRaises(ValueError): self.c.verify(head)
    def test_manifest_cannot_overwrite(self):
        self.ingest(); self.c.seal_day('2030-01-02', '2030-01-03T00:00:00Z')
        with self.assertRaises(FileExistsError): self.c.seal_day('2030-01-02', '2030-01-03T00:00:00Z')
    def test_changed_plan_on_restart_rejected(self):
        p = plan(); p['windows'] = p['windows'][:1]
        with self.assertRaises(ValueError): OfflineCollector(self.root, p)
    def test_original_config_mutation_does_not_change_contract(self):
        self.plan['windows'][0]['query'] = 'changed'
        self.assertNotEqual(self.c.plan['windows'][0]['query'], 'changed')
    def test_payload_tampering_detected_at_seal(self):
        r = self.ingest(); (self.root / r['raw_path']).write_text('changed')
        with self.assertRaises(ValueError): self.c.seal_day('2030-01-02', '2030-01-03T00:00:00Z')
    def test_rejected_response_is_still_in_manifest(self):
        a = item(); a['ticker'] = 'OTHER'
        with self.assertRaises(ValueError): self.ingest(response([a]))
        r = self.c.seal_day('2030-01-02', '2030-01-03T00:00:00Z')
        self.assertEqual(len(r['raw_sha256']), 1)
    def test_no_2026_demo_seal(self):
        with self.assertRaises(ValueError): self.c.seal_day('2026-01-02', '2030-01-03T00:00:00Z')
    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError): timestamp('2030-01-02T12:00:00')
    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError): safe_path(self.root, '../not-in-store')

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        raw = canonical({'text': 'OWNED EVIDENCE FIXTURE'}); text = b'OWNED EVIDENCE FIXTURE'
        (self.root / 'raw.json').write_bytes(raw); (self.root / 'text.txt').write_bytes(text)
        self.r = {'source': 'SYNTHETIC_SOURCE', 'record_id': 'fixture1', 'version_id': 'v1',
                  'text_sha256': digest(text), 'raw_sha256': digest(raw), 'synthetic': True,
                  'published_at': '2030-01-01T19:00:00Z', 'timestamp_precision': 'timezone_claim',
                  'deletion_compliance_status': 'ACTIVE_USE_PERMITTED', 'research_use_checked_at': '2031-01-01T00:00:00Z'}
        self.ev = {k: self.r[k] for k in ('source', 'record_id', 'version_id', 'text_sha256', 'raw_sha256')}
        self.ev.update(kind='independent_archive_capture', observed_at='2030-01-02T19:00:00Z')
        (self.root / 'review.txt').write_text('SELF_AUTHORED SYNTHETIC REVIEW ARTIFACT; NOT HUMAN QA')
        self.lic = {'source': 'SYNTHETIC_SOURCE', 'project': 'E8', 'research_use': 'APPROVED', 'status': 'ACTIVE',
                    'valid_from': '2031-01-01T00:00:00Z', 'valid_to': '2031-12-31T23:59:59Z'}
    def tearDown(self): self.temp.cleanup()
    def registry(self, arrival=None):
        (self.root / 'witness.json').write_bytes(canonical(self.ev))
        (self.root / 'permission.json').write_bytes(canonical(self.lic))
        ev = [{'path': 'witness.json', 'sha256': digest((self.root / 'witness.json').read_bytes())}]
        if arrival:
            a = dict(self.ev, kind='certified_provider_arrival', observed_at=arrival)
            (self.root / 'arrival.json').write_bytes(canonical(a)); ev.append({'path': 'arrival.json', 'sha256': digest(canonical(a))})
        e = {'reviewer_id': 'SYNTHETIC_REVIEWER_NOT_HUMAN', 'reviewed_at': '2031-01-01T00:00:00Z',
             'review_evidence_path': 'review.txt', 'review_evidence_sha256': digest((self.root / 'review.txt').read_bytes()),
             'raw_path': 'raw.json', 'text_path': 'text.txt', 'permission_path': 'permission.json',
             'permission_sha256': digest(canonical(self.lic)), 'evidence': ev}
        reg = {'SYNTHETIC_SOURCE|fixture1|v1': e}; path = self.root / 'registry.json'; path.write_bytes(canonical(reg))
        return {'registry_root': self.root, 'registry_manifest': 'registry.json', 'expected_registry_sha': digest(path.read_bytes())}
    def assess(self, **kw): return assess_provenance(self.r, '2030-01-02T22:00:00Z', **kw)
    def test_bare_true_fields_never_promote(self):
        self.r.update(verified_public_version_at='2030-01-01T19:00:00Z', version_evidence_verified=True)
        self.assertEqual(self.assess()['PIT_level'], 'L2')
    def test_today_retrieval_not_historical_witness(self):
        self.r['retrieved_at'] = '2031-01-01T00:00:00Z'; self.assertEqual(self.assess()['PIT_level'], 'L2')
    def test_L3_is_not_L4(self):
        r = self.assess(**self.registry()); self.assertEqual(r['PIT_level'], 'L3')
        self.assertFalse(r['asof_eligible']); self.assertIn('SYNTHETIC_OR_UNCLASSIFIED_NOT_REAL_RESEARCH_DATA', r['rejection_reasons'])
    def test_arrival_mode_requires_arrival(self):
        self.assertIn('NO_VERIFIED_PROVIDER_ARRIVAL', self.assess(**self.registry(), mode='arrival')['rejection_reasons'])
    def test_L4_fixture_does_not_count_as_real(self):
        r = self.assess(**self.registry('2030-01-02T20:00:00Z'), mode='arrival')
        self.assertEqual(r['PIT_level'], 'L4'); self.assertFalse(r['asof_eligible'])
    def test_late_capture_not_backdated_to_creation(self):
        self.ev['observed_at'] = '2030-01-03T00:00:00Z'
        self.assertIn('VERSION_OR_ARRIVAL_AFTER_CUTOFF', self.assess(**self.registry())['rejection_reasons'])
    def test_content_binding_changed_rejected(self):
        kw = self.registry(); self.r['text_sha256'] = '0' * 64
        with self.assertRaises(ValueError): self.assess(**kw)
    def test_raw_artifact_changed_rejected(self):
        kw = self.registry(); (self.root / 'raw.json').write_text('tampered')
        with self.assertRaises(ValueError): self.assess(**kw)
    def test_registry_pin_tamper_rejected(self):
        kw = self.registry(); (self.root / 'registry.json').write_text('{}')
        with self.assertRaises(ValueError): self.assess(**kw)
    def test_approval_clock_is_research_use_not_historical_cutoff(self):
        r = self.assess(**self.registry())
        self.assertNotIn('RESEARCH_PERMISSION_NOT_VERIFIED', r['rejection_reasons'])
    def test_expired_permission_rejected(self):
        self.lic['valid_to'] = '2030-12-31T00:00:00Z'
        self.assertIn('RESEARCH_PERMISSION_NOT_VERIFIED', self.assess(**self.registry())['rejection_reasons'])
    def test_source_mode_not_provider_mode(self):
        kw = self.registry('2030-01-03T00:00:00Z')
        self.assertNotIn('VERSION_OR_ARRIVAL_AFTER_CUTOFF', self.assess(**kw)['rejection_reasons'])
        self.assertIn('VERSION_OR_ARRIVAL_AFTER_CUTOFF', self.assess(**kw, mode='arrival')['rejection_reasons'])

if __name__ == '__main__': unittest.main(verbosity=2)
