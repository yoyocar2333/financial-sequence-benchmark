"""Lock audit scope/gates before new row-level coverage computation."""
import json
import os
from pathlib import Path
from e8a_core import sha, dump

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('E8A_OUTPUT', ROOT / 'outputs/e8a_20261108')).resolve()

def main():
    if (OUT / 'AUDIT_PLAN_LOCKED.json').exists():
        raise FileExistsError('Do not replace locked plan')
    for name in ('inputs', 'tables', 'audits', 'figures', 'code', 'sources', 'logs'):
        (OUT / name).mkdir(parents=True, exist_ok=True)
    plan = {
        'version': 'E8a-v1', 'research_date': '2026-11-08',
        'scope': 'E4a-E4c all artifact inventory, canonical news row audit, social source feasibility; no model fitting',
        'historical_rows': ['2012-01-01', '2025-12-31'],
        'active_news_inputs': ['E4a_100metadata_plus52summary', 'E4b_2816_version_records', 'E4c_FNSPID_fullscan_target_exports'],
        'counting': 'Separate source/dataset version, stock link, content representation and feature view. Canonical datasets are not summed into unique articles without cross-source deduplication.',
        'PIT_levels': {
            'L0': 'unusable timestamp', 'L1': 'date proxy or unverified UTC-midnight precision',
            'L2': 'timezone-aware publisher timestamp claim only',
            'L3': 'exact historical content version plus independently verified source-public time or dated historical capture',
            'L4': 'L3 plus certified provider arrival; current retrieval is never historical arrival'
        },
        'future_feature_clocks': 'Text observation and semantic model release/revision/inference clocks are distinct; retrospective feature extraction is not historical deployed prediction.',
        'unknown_not_zero': 'No source observation ledger -> monitoring coverage and true no-news rates remain NA. Zero retained rows only describes fixed local snapshot.',
        'E8b_screening_gates_not_power_guarantees': {
            'research_use': 'documented permission/terms compatible with intended research, deletion compliance and reproduction policy',
            'strict_PIT': '100% records used have exact-version evidence and certified availability <= cutoff; unresolved records excluded, missingness retained',
            'source_continuity': 'same declared source/query at least2train+1validation+1test years; >=90% documented monitored sessions in EACH partition',
            'event_support_per_stock': {'nonoverlap5_train':100, 'validation':40, 'test':60, 'train_min_each_class':20, 'validation_min_each_class':10, 'test_min_each_class':20},
            'manual_QA': '100 stratified document/version checks including both tickers, boundary times and edits; zero critical future/version errors; >=95% entity relevance on reviewed sample',
            'inference': 'paired common dates, source ablations, metadata/constant-shrink controls; development-only dependence and joint-comparison power check required before any formal comparison',
            'independence': '2024-2025 already inspected, cannot be new confirmation; E8 needs separately preregistered unseen future period, E3c2026 unchanged'
        },
        'E8b_exploratory_only': 'If strict gates fail, a date-proxy sensitivity case study may be separately specified, never renamed formal PIT. No such training in E8a.',
        'social': 'Only primary official documentation and author datasets; no unauthorized access, payment, new keys, user contact or current social/2026 content collection.',
        'no_new_model_training': True, 'no_GPU': True, 'E3c2026': 'UNCHANGED_NOT_EXECUTED',
        'registration_status': 'LOCAL_AUDIT_PLAN_NOT_EXTERNAL_PREREGISTRATION',
        'threshold_note': 'Engineering screening targets fixed before new E8a row-level audit; not empirically powered requirements or retrospective E4 pass/fail claims.'
    }
    dump(OUT / 'AUDIT_PLAN_LOCKED.json', plan)
    protected = json.loads((ROOT / 'outputs/e7b_20261107/audits/protected_prior_artifacts.json').read_text())
    for n in ('E4A_CURRENT_RUN.json', 'E4B_CURRENT_RUN.json', 'E4C_CURRENT_RUN.json', 'E7B_CURRENT_RUN.json', 'E3C_2026_PROTOCOL.md'):
        protected[n] = sha(ROOT / n)
    for d in ('outputs/e4a_20261026_phase7a', 'outputs/e4b_20261026', 'outputs/e4c_20261026'):
        for p in (ROOT / d).rglob('*'):
            if p.is_file() and p.suffix not in ('.zip', '.sqlite', '.wal', '.shm') and p.stat().st_size <= 128_000_000:
                protected[str(p.relative_to(ROOT))] = sha(p)
    dump(OUT / 'audits/protected_prior_artifacts.json', protected)
    dump(OUT / 'audits/plan_lock.json', {'plan_sha256': sha(OUT / 'AUDIT_PLAN_LOCKED.json'), 'protected_files': len(protected)})
    print('E8a audit scope/gates locked; protected artifacts:', len(protected))

if __name__ == '__main__':
    main()
