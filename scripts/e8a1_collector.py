"""Offline-only collector kernel. No network adapter, credentials or scheduler.

Hash chains detect changes relative to an externally retained head; they are not
independent timestamping, WORM storage, or evidence that historical content is true.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

def digest(value):
    return hashlib.sha256(value).hexdigest()

def timestamp(value):
    if not isinstance(value, str): raise ValueError('Timestamp string required')
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None: raise ValueError('Timezone required')
    return parsed.astimezone(dt.timezone.utc)

def safe_path(root, relative):
    root = Path(root).resolve(); path = (root / relative).resolve()
    if not path.is_relative_to(root): raise ValueError('Path outside evidence store')
    return path

def atomic_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())

class OfflineCollector:
    def __init__(self, root, plan):
        if plan.get('mode') != 'offline_synthetic' or plan.get('live_enabled') is not False:
            raise PermissionError('This kernel cannot enable a live transport')
        if plan.get('synthetic_fixture_permission') != 'SELF_AUTHORED_TEST_DATA_ONLY':
            raise PermissionError('Only self-authored engineering fixtures accepted')
        self.root = Path(root); self.plan = json.loads(canonical(plan))
        self.root.mkdir(parents=True, exist_ok=True)
        frozen_plan = self.root / 'plan_locked.json'
        if frozen_plan.exists():
            if frozen_plan.read_bytes() != canonical(self.plan): raise ValueError('Collector plan changed on restart')
        else: atomic_new(frozen_plan, canonical(self.plan))
        self.journal = self.root / 'journal.jsonl'
        self.chain = []; self.head = '0' * 64
        if self.journal.exists():
            self.verify()
            self.chain = [json.loads(x) for x in self.journal.read_text().splitlines()]
            if self.chain: self.head = self.chain[-1]['hash']
        self.state = {}; self.raw_paths = {}; self.withdrawn = set()
        # Replay only projections. Never reset pagination state silently on restart.
        for e in self.chain:
            if e['event']['kind'] in ('request_result', 'request_rejected') and 'slot' in e['event']['data']:
                self._project(e['event']['data'])
            if e['event']['kind'] == 'withdrawal': self.withdrawn.add((e['event']['data']['source'], e['event']['data']['record_id']))

    def _append(self, kind, data):
        event = {'kind': kind, 'synthetic': True, 'data': data}
        value = {'index': len(self.chain), 'previous': self.head, 'event': event}
        value['hash'] = digest(canonical(value))
        with self.journal.open('ab') as f:
            f.write(canonical(value) + b'\n'); f.flush(); os.fsync(f.fileno())
        self.chain.append(value); self.head = value['hash']

    def verify(self, expected_head=None):
        previous = '0' * 64
        lines = self.journal.read_text().splitlines() if self.journal.exists() else []
        for i, line in enumerate(lines):
            r = json.loads(line); h = r.pop('hash')
            if r['index'] != i or r['previous'] != previous or digest(canonical(r)) != h:
                raise ValueError('Journal chain mismatch')
            previous = h
        if expected_head is not None and expected_head != previous:
            raise ValueError('Journal differs from retained external head')
        return previous

    def _slot(self, spec):
        return (spec['source'], spec['ticker'], spec['session'])

    def _project(self, d):
        key = tuple(d['slot'])
        current = self.state.setdefault(key, {'cursor': None, 'seen': [], 'failed': False, 'complete': False,
                                            'records': {}, 'continuity': True, 'backfilled': False})
        current.update(d['projection'])

    def ingest(self, spec, body, request_started, response_received, status=200, cursor=None,
               continuity_proven=True, backfill=False):
        try:
            return self._ingest(spec, body, request_started, response_received, status, cursor, continuity_proven, backfill)
        except (ValueError, PermissionError, KeyError, TypeError) as exc:
            data = {'query_sha256': digest(canonical(spec)), 'raw_sha256': digest(body) if isinstance(body, bytes) else None,
                    'error_type': type(exc).__name__, 'response_content_or_credentials_logged': False}
            if isinstance(body, bytes):
                raw_name = 'raw/' + digest(body) + '.json'
                if (self.root / raw_name).exists(): data['raw_path'] = raw_name
            try:
                timestamp(response_received); data['response_received_at'] = response_received
            except (ValueError, TypeError): pass
            if spec in self.plan['windows'] and not self.state.get(self._slot(spec), {}).get('complete'):
                data.update(slot=list(self._slot(spec)), projection={'failed': True, 'continuity': False, 'complete': False})
            self._append('request_rejected', data)
            if 'slot' in data: self._project(data)
            raise

    def _ingest(self, spec, body, request_started, response_received, status=200, cursor=None,
               continuity_proven=True, backfill=False):
        """Inject one owned synthetic response; no implicit HTTP, sleeping or retry."""
        if spec not in self.plan['windows']: raise ValueError('Query/window not in fixed plan')
        start, received = timestamp(request_started), timestamp(response_received)
        if received < start: raise ValueError('Response precedes request')
        if not isinstance(body, bytes) or len(body) > self.plan.get('max_response_bytes', 1_000_000):
            raise ValueError('Invalid response bytes/size')
        key = self._slot(spec)
        state = self.state.get(key, {'cursor': None, 'seen': [], 'failed': False, 'complete': False,
                                    'records': {}, 'continuity': True, 'backfilled': False}).copy()
        if state['complete']: raise ValueError('Window already terminal; use explicit new revision')
        if cursor != state['cursor']: raise ValueError('Unexpected pagination cursor')
        result = {'slot': list(key), 'query_sha256': digest(canonical(spec)), 'cursor_in': cursor,
                  'request_started_at': request_started, 'response_received_at': response_received,
                  'status': status, 'raw_sha256': digest(body), 'response_bytes': len(body),
                  'backfill': backfill, 'auth_headers_recorded': False}
        payload = json.loads(body)
        if payload.get('synthetic') is not True:
            raise PermissionError('Real external content ingestion disabled in this phase')
        raw_relative = 'raw/' + result['raw_sha256'] + '.json'
        raw_path = self.root / raw_relative
        if raw_path.exists():
            if raw_path.read_bytes() != body: raise ValueError('Content-address collision')
        else: atomic_new(raw_path, body)
        result['raw_path'] = raw_relative
        if status != 200:
            result.update(projection={'failed': True, 'continuity': False}, disposition='RETRY_REQUIRES_EXPLICIT_NEW_RESPONSE')
            self._append('request_result', result); self._project(result)
            return result
        if not isinstance(payload.get('items'), list): raise ValueError('Missing item array')
        next_cursor = payload.get('next_cursor')
        if next_cursor is not None and (not isinstance(next_cursor, str) or not next_cursor):
            raise ValueError('Invalid opaque cursor')
        seen = list(state['seen'])
        if next_cursor is not None and (next_cursor == cursor or next_cursor in seen):
            raise ValueError('Pagination loop')
        if cursor is not None: seen.append(cursor)
        records = dict(state['records'])
        window_start, window_end = timestamp(spec['window_start']), timestamp(spec['window_end'])
        for r in payload['items']:
            if r.get('synthetic') is not True: raise PermissionError('Fixture record must be synthetic')
            if r.get('ticker') != spec['ticker']: raise ValueError('Ticker/source query mismatch')
            if r.get('action') not in ('create', 'edit', 'delete'): raise ValueError('Unknown lifecycle action')
            if not window_start < timestamp(r['event_at']) <= window_end:
                raise ValueError('Event outside requested observation window')
            rid = r['record_id']; version = r['version_id']
            if not isinstance(rid, str) or not rid or not isinstance(version, str) or not version:
                raise ValueError('Record/version identity required')
            entity = rid + '|' + version
            text = r.get('text', '')
            if entity in records and records[entity]['text_sha256'] != digest(text.encode()):
                raise ValueError('Conflicting contents under same version ID')
            records[entity] = {'record_id': rid, 'version_id': version, 'parent_id': r.get('parent_id'),
                'ticker': r['ticker'], 'action': r['action'], 'published_at': r.get('published_at'),
                'event_at': r['event_at'], 'text_sha256': digest(text.encode()),
                'retrieved_at': response_received, 'verified_public_version_at': None,
                'verified_arrival_at': None, 'PIT_level': 'NOT_CERTIFIED_SYNTHETIC',
                'raw_sha256': result['raw_sha256'], 'synthetic': True}
        terminal = next_cursor is None and payload.get('terminal') is True and not payload.get('errors')
        complete = (terminal and continuity_proven is True and not state['failed'] and state['continuity']
                    and received <= window_end and not backfill and not state['backfilled'])
        projection = {'cursor': next_cursor, 'seen': seen, 'records': records,
                      'failed': state['failed'] or bool(payload.get('errors')),
                      'continuity': state['continuity'] and continuity_proven is True,
                      'backfilled': state['backfilled'] or backfill,
                      'complete': complete}
        result.update(projection=projection, raw_path=raw_relative,
                      terminal_response=terminal, disposition='OBSERVED_QUERY_COMPLETE' if complete else 'INCOMPLETE_OR_DELAYED')
        self._append('request_result', result); self._project(result)
        return result

    def coverage(self):
        """Denominator is planned source/query/ticker/session windows, never post dates."""
        result = []
        for w in self.plan['windows']:
            s = self.state.get(self._slot(w)); complete = bool(s and s['complete'])
            deleted = {r['record_id'] for r in s['records'].values() if r['action'] == 'delete'} if s else set()
            count = len({r['record_id'] for r in s['records'].values() if r['action'] != 'delete'
                         and r['record_id'] not in deleted and (w['source'], r['record_id']) not in self.withdrawn}) if s else None
            result.append({'source': w['source'], 'ticker': w['ticker'], 'session': w['session'],
                'planned_denominator': 1, 'monitored_complete': complete,
                'observed_query_zero': bool(complete and not s['records']),
                'retained_record_ids': count if complete else None,
                'status': 'COMPLETE_QUERY_ONLY' if complete else 'UNKNOWN_OR_INCOMPLETE',
                'whole_platform_completeness_proved': False, 'synthetic': True})
        return result

    def withdraw(self, source, record_id, reason, occurred_at):
        timestamp(occurred_at)
        if not reason: raise ValueError('Withdrawal reason required')
        # Raw responses may contain several records. Remove the entire affected
        # blob; manifests retain only a tombstone, not the withdrawn content.
        removed = []
        for r in self.chain:
            event = r['event']
            if event['kind'] != 'request_result': continue
            d = event['data']
            if d['slot'][0] == source and any(x['record_id'] == record_id for x in d['projection'].get('records', {}).values()):
                path = self.root / 'raw' / (d['raw_sha256'] + '.json')
                if path.exists(): path.unlink(); removed.append(d['raw_sha256'])
        self.withdrawn.add((source, record_id))
        self._append('withdrawal', {'source': source, 'record_id': record_id, 'reason': reason, 'occurred_at': occurred_at,
                                    'removed_blob_sha256': sorted(set(removed)), 'derivative_invalidation_required': True})
        return removed

    def seal_day(self, date, sealed_at):
        timestamp(sealed_at)
        if dt.date.fromisoformat(date).year < 2027: raise ValueError('Demo seal dates must not use2026 validation')
        for p in (self.root / 'raw').glob('*.json'):
            if digest(p.read_bytes()) != p.stem: raise ValueError('Raw payload changed')
        selected = {e['event']['data']['raw_path'] for e in self.chain if e['event']['kind'] in ('request_result', 'request_rejected')
                    and e['event']['data'].get('raw_path') and e['event']['data'].get('response_received_at')
                    and timestamp(e['event']['data']['response_received_at']).date().isoformat() == date}
        raw = {name: digest((self.root / name).read_bytes()) for name in sorted(selected) if (self.root / name).exists()}
        value = {'date': date, 'sealed_at': sealed_at, 'journal_head': self.verify(),
                 'raw_sha256': raw, 'plan_sha256': digest(canonical(self.plan)), 'synthetic': True,
                 'manifest_day_timezone': 'UTC', 'external_timestamp_or_WORM_certified': False}
        path = self.root / 'manifests' / (date + '.json')
        atomic_new(path, canonical(value) + b'\n')
        return value

    def live(self, *args, **kwargs):
        raise PermissionError('No live network transport is implemented or authorized')

def assess_provenance(record, cutoff, registry_root=None, registry_manifest=None, expected_registry_sha=None, mode='source', research_use_at=None):
    """Only an externally reviewed, hash-pinned registry can add evidence clocks.

    This verifies binding/format, not the truth of an attestation, reviewer identity,
    rights interpretation or external clock. Those require independent human audit.
    """
    c = timestamp(cutoff)
    if mode not in ('source', 'arrival'): raise ValueError('Unknown availability mode')
    level = 'L0'; reasons = []; verified = {}; time_candidates = []
    try:
        p = timestamp(record.get('published_at'))
        level = 'L1' if record.get('timestamp_precision') in ('date_only', 'midnight_unverified') else 'L2'
    except (ValueError, TypeError):
        try: dt.date.fromisoformat(record.get('publication_date', '')); level = 'L1'
        except (ValueError, TypeError): pass
    permission = False
    if registry_root and registry_manifest and expected_registry_sha:
        manifest_path = safe_path(registry_root, registry_manifest)
        if digest(manifest_path.read_bytes()) != expected_registry_sha: raise ValueError('Untrusted registry manifest')
        registry = json.loads(manifest_path.read_bytes())
        key = '|'.join(record.get(k, '') for k in ('source', 'record_id', 'version_id'))
        entry = registry.get(key)
        if entry:
            if not all(entry.get(k) for k in ('reviewer_id', 'reviewed_at', 'review_evidence_sha256')):
                raise ValueError('Unsigned/unfinished evidence review record')
            timestamp(entry['reviewed_at'])
            review_path = safe_path(registry_root, entry['review_evidence_path'])
            if digest(review_path.read_bytes()) != entry['review_evidence_sha256']: raise ValueError('Review artifact hash mismatch')
            for field, expected in [('raw_path', 'raw_sha256'), ('text_path', 'text_sha256')]:
                content = safe_path(registry_root, entry[field]).read_bytes()
                if digest(content) != record.get(expected): raise ValueError('Raw/text source artifact mismatch')
            for ev in entry.get('evidence', []):
                path = safe_path(registry_root, ev['path']); raw = path.read_bytes()
                if digest(raw) != ev['sha256']: raise ValueError('Evidence artifact changed')
                a = json.loads(raw)
                for k in ('source', 'record_id', 'version_id', 'text_sha256', 'raw_sha256'):
                    if a.get(k) != record.get(k) or not record.get(k): raise ValueError('Evidence version/content binding mismatch')
                kind = a.get('kind')
                if kind in ('independent_archive_capture', 'source_version_log'):
                    field = 'verified_capture_at' if kind == 'independent_archive_capture' else 'verified_public_version_at'
                    t = timestamp(a['observed_at']); verified[field] = t.isoformat(); time_candidates.append(t)
                elif kind == 'certified_provider_arrival':
                    verified['verified_arrival_at'] = timestamp(a['observed_at']).isoformat()
            if time_candidates:
                level = 'L4' if 'verified_arrival_at' in verified else 'L3'
            # Permission independently bound to source/project via reviewed artifact.
            license_path = safe_path(registry_root, entry['permission_path'])
            license_raw = license_path.read_bytes()
            if digest(license_raw) != entry['permission_sha256']: raise ValueError('Permission artifact changed')
            lic = json.loads(license_raw)
            use_clock = timestamp(research_use_at or record.get('research_use_checked_at'))
            permission = (lic.get('source') == record.get('source') and lic.get('project') == 'E8'
                          and lic.get('research_use') == 'APPROVED' and lic.get('status') == 'ACTIVE'
                          and timestamp(lic['valid_from']) <= use_clock <= timestamp(lic['valid_to']))
    if level not in ('L3', 'L4'): reasons.append('NO_INDEPENDENT_HISTORICAL_CONTENT_VERSION_EVIDENCE')
    available = min(time_candidates) if time_candidates else None
    arrival = verified.get('verified_arrival_at')
    if mode == 'arrival':
        if arrival and available: available = max(available, timestamp(arrival))
        else: reasons.append('NO_VERIFIED_PROVIDER_ARRIVAL')
    if available and available > c: reasons.append('VERSION_OR_ARRIVAL_AFTER_CUTOFF')
    if not permission: reasons.append('RESEARCH_PERMISSION_NOT_VERIFIED')
    if record.get('deletion_compliance_status') != 'ACTIVE_USE_PERMITTED': reasons.append('DELETION_OR_USE_STATUS_UNRESOLVED')
    if record.get('synthetic') is not False: reasons.append('SYNTHETIC_OR_UNCLASSIFIED_NOT_REAL_RESEARCH_DATA')
    return {'PIT_level': level, 'verified_clocks': verified, 'effective_available_at': available.isoformat() if available else None,
            'asof_eligible': not reasons, 'rejection_reasons': reasons,
            'independent_historical_truth_proved_by_software': False}
