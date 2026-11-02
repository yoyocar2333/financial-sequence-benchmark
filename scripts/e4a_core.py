"""E4a news provenance and conservative alignment; never infer missing news as zero."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'outputs/e3c_20261026_v1_1'
MAIN_REV = 'fdf6103ff22035a6cd9e6a7e946430f0c2b2e33d'
REVIEW_REV = 'e5a0767415a9123f0a338a73068aa564fac90585'
VENDOR = ROOT / 'vendor/stockllm-pit-news'
OUT = ROOT / 'outputs/e4a_20261026_v1_1'
REPO_URL = 'https://github.com/yoyocar2333/stockllm-pit-news'
TYPES = ['litigation', 'earnings', 'product_launch', 'merger_acquisition', 'regulation', 'other']


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def dump(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False, default=str) + '\n')


def now(): return dt.datetime.now(dt.timezone.utc).isoformat()


def cutoff_utc(dates):
    # A fixed decision deadline AFTER the close, with DST handled by zoneinfo.
    return (pd.DatetimeIndex(dates).normalize() + pd.Timedelta(hours=17)).tz_localize('America/New_York').tz_convert('UTC')


def aware(value):
    if value is None or str(value).strip() in ('', 'nan', 'NaT', 'None'): return None
    try:
        x = pd.Timestamp(value)
    except (ValueError, TypeError): return None
    return x.tz_convert('UTC') if x.tzinfo is not None else None


def true(value):
    return value is True or str(value).strip().lower() == 'true'


def strict_availability(row):
    """Verified availability for the exact text version, not a publisher date guess.

    retrieved_utc is NOT silently substituted for historical first_seen. A later
    backfill does not prove it was unavailable then; historical availability is
    simply unverified. An attested provider archive may supply version_seen_utc.
    """
    reasons = []
    published = aware(row.get('published_utc'))
    seen = aware(row.get('version_seen_utc'))
    if published is None: reasons.append('NO_TIMEZONE_AWARE_PUBLISHED_TIME')
    if seen is None: reasons.append('NO_VERSION_FIRST_SEEN_EVIDENCE')
    if not true(row.get('historical_text_revision_verified', False)): reasons.append('HISTORICAL_TEXT_VERSION_UNVERIFIED')
    if not str(row.get('text_sha256', '')).strip(): reasons.append('MISSING_TEXT_HASH')
    if not str(row.get('availability_evidence', '')).strip(): reasons.append('MISSING_AVAILABILITY_EVIDENCE')
    if reasons: return None, '|'.join(reasons)
    values = [published, seen]
    for key in ('embargo_until_utc', 'version_published_utc'):
        if row.get(key) not in (None, ''):
            value = aware(row[key])
            if value is None: return None, 'INVALID_' + key.upper()
            values.append(value)
    return max(values), 'VERIFIED_VERSION_AVAILABILITY'


def map_available(available, sessions):
    if available is None: return None
    cutoffs = cutoff_utc(sessions)
    i = cutoffs.searchsorted(available, side='left')
    return pd.Timestamp(sessions[i]) if i < len(sessions) else None


def date_only_projection(day, sessions):
    """Publication-only sensitivity: next observed session strictly AFTER date.

    This is not verified historical availability and cannot enter strict models.
    """
    day = pd.Timestamp(day)
    if day.tzinfo is not None: raise ValueError('Expected a date, not a timezone timestamp')
    if day != day.normalize(): raise ValueError('Expected a date-only field')
    i = pd.DatetimeIndex(sessions).searchsorted(day, side='right')
    return pd.Timestamp(sessions[i]) if i < len(sessions) else None


def eligible_record_at(row, cutoff):
    available, reason = strict_availability(row)
    return available is not None and available <= pd.Timestamp(cutoff), reason


def observed_count(articles, ticker, day, covered):
    # Count zero is valid ONLY with an independently audited collection interval.
    if not covered: return np.nan
    return int(((articles.ticker == ticker) & (articles.information_date == day)).sum())


def design():
    return {
        'study': 'E4a-1.0', 'created_utc': now(), 'status': 'LOCKED_BEFORE_ALIGNMENT',
        'primary_task': '5-session reversal after E3c raw-past5 training q10/q90 events',
        'market_source': str(SOURCE.relative_to(ROOT)), 'development_end': '2025-12-31',
        'holdout_2026_used': False, 'no_new_threshold_selection': True,
        'target': 'y=1[sign(past5)*100*log(adjusted_Close[t+5]/adjusted_Open[t+1])<0]; signed amplitude = -sign(past5)*same log return, in log percentage points',
        'decision_time': '17:00 America/New_York on each observed stock session; assumed operational deadline, not proof historical vendor bars arrived by then',
        'strict_news': 'exact text-version historical evidence, timezone-aware publication and version first-seen; available=max(publication,version first-seen,embargo,version publication); <=decision cutoff',
        'timestamp_unknown': 'no implicit UTC for naive timestamps; no midnight fabricated for date-only fields; quarantine from strict inference',
        'date_only_sensitivity': 'earliest ASSUMED cutoff is first observed session strictly after publication date; metadata alignment only; not historical PIT certification',
        'windows': {'prediction': ['new session', 'last5 information sessions, inclusive t'], 'descriptive_neighborhood': 'information session t-5..t+5; positive offsets are never input features'},
        'deduplication': 'one article_id/text_version/ticker; retain updates separately, version-specific first-seen; syndication cluster identity required; same text hash dedup within ticker/window; article count is not grammatical event-record count',
        'missing_news': 'collection unavailable/partial != observed no-news; sentiment never filled using future returns; missing annotation != neutral',
        'models_if_supported': {
            'P': 'E3c event LogisticRegression, same38 price/volatility features; C=.01 fixed',
            'S': 'P + observed-news flag/log1p(count) + mean FinBERT positive/negative/neutral; same article universe as T',
            'T': 'S + six fixed upstream type fractions + actor/object/both role fractions; no triple hashing or threshold search in this sparse study',
            'G': 'P + same article-universe Gemini text-only sentiment/confidence; separate optional arm, never conflate direction_probability with reversal_probability',
            'priors': ['E3c event_prior', 'E3c state_prior alpha100'],
            'seeds': [42,43,44,45,46], 'calibration': 'E3c identity-prior Platt lambda20, projected Newton v1.1; fit on2023H2 only'
        },
        'split': {'fit': ['2012-01-01','2022-12-31'], 'validation': ['2023-01-01','2023-12-31'], 'calibration': ['2023-07-01','2023-12-31'], 'evaluation': ['2024-01-01','2025-12-31'], 'purge': 't+20 within each eligible block, same E3c complete60-session-history cohort'},
        'complexity_gate': {'LR_min_fit_news_events':100,'LR_min_each_fit_class':30,'min_cal_news_events':30,'min_test_events_for_inference':20,'XGB_min_fit_news_events':250,'deep_min_fit_events':1000,
            'rule':'no training at all if2012-2022 PIT news-feature support=0; gate is feasibility, not evidence of statistical power; no relaxing cutoffs after results'},
        'comparisons': ['S vs P','T vs S','T vs state_prior','S vs state_prior'],
        'primary_family': '2stocks x4=8 paired event Brier tests, Holm8 separately for HAC and bootstrap; G adds a declared exploratory family only if real Gemini features are available',
        'secondary_family': 'S and T vs P within-state AUC gains x2stocks=4, two-sided block bootstrap Holm4; coarse state=direction,long120_ex5 sign,VIX median',
        'inference': 'same dates and source observation coverage; mean seed-specific daily LOSSES, not ensemble loss or independent seed samples; calendar ratio HAC lag20 and circular-block20 B19999, seed20261026; block60 sensitivity. Within-state concordance kernels first average over seeds, B9999. Thin by5 sessions sensitivity. Minimum20 event dates,10/class and20 within-state pairs for ranking, >=99% nonempty bootstrap',
        'conditional_analysis': 'news polarity aligned vs opposed to event direction; fixed six event types; report conditional reversal rates and signed/positive-only amplitudes; state-adjusted differences within training-defined cells; full-calendar block intervals; exploratory subgroup CIs, no causal mechanism claim',
        'news_text_models': 'FinBERT/Gemini must read only version-hashed text, no prices/labels/retrieval tools. Exact model revision/prompt/hash saved. Retrospective scoring alone does not establish historical model availability or rule out pretrained-model contamination',
        'fairness': 'P/S/T refit on the SAME supported news-cohort training and calibration dates, evaluated on same dates; full-calendar price-only legacy results are context, not an unequal-population news comparison',
        'stop_rule': 'insufficient historical data => completed coverage/PIT feasibility report, no fabricated effect estimates, no forced neural training',
        'interpretation': '2024-2025 already inspected, exploratory only; no2026 data; association may reflect corporate-source selection rather than causal explanation',
        'upstream_revisions': {'main':MAIN_REV,'research':REVIEW_REV}
    }
