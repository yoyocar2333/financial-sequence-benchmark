"""E8a metadata-only PIT contracts. No model training or remote collection."""
import csv
import datetime as dt
import gzip
import hashlib
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

UTC = dt.timezone.utc
NY = ZoneInfo('America/New_York')

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def digest(text):
    return hashlib.sha256(str(text or '').encode()).hexdigest()

def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def read_csv(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path, 'rt', encoding='utf-8-sig', newline='') as f:
        yield from csv.DictReader(f)

def write_csv(path, rows, fields=None):
    rows = list(rows); path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(rows[0])
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader(); w.writerows(rows)

def instant(value):
    """No naive timestamp, date-only or malformed value is silently UTC."""
    if not value or not re.search(r'\d[T ]\d', str(value)):
        return None
    try:
        v = dt.datetime.fromisoformat(str(value).replace(' UTC', '+00:00').replace('Z', '+00:00'))
        return v.astimezone(UTC) if v.tzinfo and v.utcoffset() is not None else None
    except (ValueError, TypeError):
        return None

def clock_level(row):
    """Evidence-led, not flag-led. Input evidence is a separately verified registry."""
    public = instant(row.get('verified_public_version_at'))
    capture = instant(row.get('verified_capture_at'))
    claimed = instant(row.get('published_at'))
    version_ok = row.get('version_evidence_verified') is True
    # Exact historical version plus a certified public timestamp or dated capture.
    qualified = version_ok and bool(public or capture)
    if qualified and instant(row.get('verified_arrival_at')):
        return 'L4_ARRIVAL_VERIFIED'
    if qualified:
        return 'L3_SOURCE_VERSION_VERIFIED'
    if claimed and row.get('precision') != 'midnight_unverified':
        return 'L2_PUBLISHER_TIME_CLAIM'
    try:
        dt.date.fromisoformat(row.get('publication_date', ''))
        return 'L1_DATE_PROXY'
    except (ValueError, TypeError):
        pass
    return 'L0_UNUSABLE_TIME'

def strict_eligibility(row, cutoff, mode='source'):
    if mode not in ('source', 'arrival'):
        raise ValueError('mode must be source or arrival')
    c = instant(cutoff)
    if not c:
        raise ValueError('aware decision cutoff required')
    reasons = []
    if row.get('version_evidence_verified') is not True:
        reasons.append('UNVERIFIED_HISTORICAL_CONTENT_VERSION')
    dates = [instant(row.get('verified_public_version_at')), instant(row.get('verified_capture_at'))]
    dates = [v for v in dates if v]
    if not dates:
        reasons.append('NO_CERTIFIED_HISTORICAL_AVAILABILITY')
    # A capture proves availability no earlier than capture; when certified public
    # version time exists it is an independent bound. Neither is current retrieval.
    available = min(dates) if dates else None
    if mode == 'arrival':
        a = instant(row.get('verified_arrival_at'))
        if not a:
            reasons.append('NO_CERTIFIED_PROVIDER_ARRIVAL')
        elif available:
            available = max(available, a)
    if available and available > c:
        reasons.append('AFTER_DECISION_CUTOFF')
    if row.get('use_permission_verified') is not True:
        reasons.append('RESEARCH_USE_PERMISSION_NOT_VERIFIED')
    if row.get('deleted_or_withdrawn') is not False:
        reasons.append('DELETION_OR_USE_STATUS_UNRESOLVED')
    return not reasons, reasons, available.isoformat() if available else None

def proxy_session(row, sessions, delay=0):
    """Exploratory only: date-like records strictly after date; timed records17NY."""
    if delay not in (0, 1, 2):
        raise ValueError('predeclared delays only')
    claimed = instant(row.get('published_at'))
    date = row.get('publication_date', '')[:10]
    if not date:
        return None
    valid = None
    for i, session in enumerate(sessions):
        cutoff = dt.datetime.combine(dt.date.fromisoformat(session), dt.time(17), NY).astimezone(UTC)
        if claimed and row.get('precision') not in ('date_only', 'midnight_unverified'):
            yes = claimed <= cutoff
        else:
            yes = session > date
        if yes:
            valid = i + delay
            break
    return sessions[valid] if valid is not None and valid < len(sessions) else None

def feature_ready(article_available_at, model_released_at, inference_finished_at, cutoff):
    times = [instant(x) for x in (article_available_at, model_released_at, inference_finished_at, cutoff)]
    return all(times) and max(times[:3]) <= times[3]
