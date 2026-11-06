"""Fail-closed research data contract. Synthetic tests only; no data fetching.

It validates declared evidence/chronology; it cannot independently authenticate
a vendor's assertion or turn today's download into a historical capture.
"""
import datetime as dt,re

def utc(value):
    x=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    if x.tzinfo is None:raise ValueError('Timezone evidence required, not a naive guessed clock')
    return x.astimezone(dt.timezone.utc)

def audit(record,cutoff):
    reasons=[];kind=record.get('kind','fundamental_actual')
    required=['issuer_id','source_document_id','version_sha256','public_available_utc','public_time_evidence','version_chain_verified','units','retrieved_at_utc']
    for name in required:
        if not record.get(name):reasons.append('missing_or_unverified:'+name)
    if reasons:return {'eligible':False,'reasons':reasons}
    if not re.fullmatch('[0-9a-f]{64}',record['version_sha256']):reasons.append('invalid_version_sha256')
    try:
        available=utc(record['public_available_utc']);decision=utc(cutoff);retrieved=utc(record['retrieved_at_utc'])
        if available>decision:reasons.append('not_public_at_decision')
        if kind=='fundamental_actual':
            if not record.get('accepted_at_utc') or not record.get('acceptance_timezone_verified'):reasons.append('SEC_acceptance_clock_not_verified')
            else:
                accepted=utc(record['accepted_at_utc'])
                if available<accepted:reasons.append('availability_before_acceptance')
            if record.get('period_end') and dt.date.fromisoformat(record['period_end'])>available.date():reasons.append('actual_for_future_period')
        if record.get('provider_received_utc') and utc(record['provider_received_utc'])>decision:reasons.append('not_received_at_decision')
        if kind in ['news','analyst_estimate']:
            if not record.get('provider_received_utc'):reasons.append('arrival_history_required_for_news_or_estimates')
            if not record.get('historical_snapshot_verified'):reasons.append('historical_snapshot_unverified')
        # A later retrieval can verify an immutable official source document,
        # but never proves a contemporaneous collector first-seen timestamp.
        evidence_grade='ARRIVAL_CERTIFIED' if record.get('provider_received_utc') else 'SOURCE_EVENT_CERTIFIED_NOT_COLLECTOR_ARRIVAL'
    except (ValueError,TypeError) as e:return {'eligible':False,'reasons':['timestamp_error:'+str(e)]}
    return {'eligible':not reasons,'reasons':reasons,'evidence_grade':evidence_grade,'retrieval_is_not_historical_first_seen':retrieved>decision}

def latest_asof(records,cutoff):
    valid=[r for r in records if audit(r,cutoff)['eligible']]
    # Unit/period/concept grouping must happen before selection; caller cannot
    # silently combine incomparable EPS definitions or annual/YTD cash flows.
    keys={(r['issuer_id'],r.get('concept'),r.get('period_end'),r['units']) for r in records}
    if len(keys)>1:raise ValueError('Group identical issuer, concept, period and units before version selection')
    return max(valid,key=lambda r:utc(r['public_available_utc'])) if valid else None

def label_within_block(origin,label_end,block_start,block_end):
    return utc(block_start)<=utc(origin)<=utc(block_end) and utc(label_end)<=utc(block_end)
