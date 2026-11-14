"""Freeze an E8a.1 pilot without altering E8a gates or earlier research."""
import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path
from e8a_core import sha, dump, write_csv

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent / 'financial-sequence-benchmark'
OUT = ROOT / 'outputs/e8a1_20261114'
CONTRACTS = ['E8A_SUMMARY.md', 'DATA_CONTRACT_AND_PIT.md', 'E8B_FEASIBILITY_DECISION.md', 'NEXT_STEPS.md', 'AUDIT_PLAN_LOCKED.json', 'tables/E8b_readiness_gates.csv']
SAMPLE_FIELDS = ['source', 'dataset_revision', 'record_id', 'parent_id', 'version_id', 'ticker', 'cashtag', 'company_id', 'entity_binding_status', 'published_at', 'edited_at', 'deleted_at', 'retrieved_at', 'verified_public_version_at', 'verified_capture_at', 'verified_arrival_at', 'raw_sha256', 'source_evidence_uri', 'evidence_index', 'text_sha256', 'representation', 'timestamp_precision', 'timezone', 'access_agreement_id', 'retention_status', 'deletion_compliance_status', 'PIT_level', 'asof_eligible', 'rejection_reasons']

def main():
    if OUT.exists(): raise FileExistsError('Use a new audit directory; preserve prior run')
    for d in ('inputs/e8a_contract', 'sources', 'tables', 'audits', 'code', 'logs', 'schemas', 'engineering_demo'):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    manifest = []
    for name in CONTRACTS:
        p = REPO / 'research/E8a' / name; q = OUT / 'inputs/e8a_contract' / name
        q.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, q)
        manifest.append({'path': 'research/E8a/' + name, 'sha256': sha(p)})
    dump(OUT / 'inputs/e8a_main_contract_hashes.json', manifest)
    # Preserve public relative-link targets too; six governing-file hashes above
    # remain the primary contract, supplementary tables/figures retain their bytes.
    shutil.copytree(REPO / 'research/E8a', OUT / 'inputs/e8a_contract', dirs_exist_ok=True)
    protected = json.loads((ROOT / 'outputs/e8a_20261108/audits/protected_prior_artifacts.json').read_text())
    for p in (ROOT / 'outputs/e8a_20261108').rglob('*'):
        if p.is_file(): protected[str(p.relative_to(ROOT))] = sha(p)
    for name in ('E8A_CURRENT_RUN.json', 'E8A_ARCHIVE_CHECK.json', 'outputs/e8a_20261108_complete_audit.zip'):
        protected[name] = sha(ROOT / name)
    dump(OUT / 'audits/protected_prior_artifacts.json', protected)
    paths = subprocess.check_output(['git', 'ls-files'], cwd=REPO, text=True).splitlines()
    old = {name: sha(REPO / name) for name in paths if name.startswith(('research/', 'scripts/')) and name != 'scripts/RESEARCH_CODE_INDEX.md'}
    for name in ('RESULTS.md', 'requirements.txt', 'notebooks/stock_market_models.ipynb'): old[name] = sha(REPO / name)
    dump(OUT / 'audits/protected_public_science.json', old)
    plan = {'research_date': '2026-11-14', 'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'main_commit': subprocess.check_output(['git', 'rev-parse', 'origin/main'], cwd=REPO, text=True).strip(),
            'branch': 'research/e8a1-provenance-pilot-20261114',
            'scope': 'Public documentation/license audit; conditional real pilot; offline collector and evidence verification only',
            'real_sample_target': [30, 50], 'target_companies': ['AAPL', 'TSLA'],
            'sample_gate': 'No content acquisition without documented permitted research access; no current platform scrape or paid API',
            'sampling_if_permitted': 'Aim40, both tickers,>=4historical years, clock/cutoff and edit/delete strata only if truly available; fixed hash sampling independent of price outcomes',
            'real_source_before2026': True, 'no_new_financial_prediction': True, 'no_Brier_AUC_comparison': True,
            'no_live_collector_or_scheduler': True, 'no_payments_or_applications_or_outbound_messages': True,
            'E8a_gate_contract_unchanged': True, 'E3c2026': 'UNCHANGED_NOT_EXECUTED',
            'independent_manual_QA': 'Only named external researcher reviews with time and evidence count; generated forms count0',
            'synthetic_policy': 'Engineering fixtures marked synthetic; never count toward real samples, L3/L4 totals or100manual reviews',
            'external_registration': 'NOT_REGISTERED'}
    dump(OUT / 'PILOT_PLAN_LOCKED.json', plan)
    dump(OUT / 'audits/plan_lock.json', {'sha256': sha(OUT / 'PILOT_PLAN_LOCKED.json')})
    write_csv(OUT / 'PILOT_SAMPLE_MANIFEST.csv', [], SAMPLE_FIELDS)
    qa_fields = ['candidate_id', 'source', 'record_id', 'version_id', 'ticker', 'evidence_uri', 'entity_relevance', 'clock_timezone_consistent', 'exact_historical_version', 'available_before_cutoff', 'duplicates_reposts_checked', 'edits_deletes_checked', 'semantic_flags', 'decision', 'reviewer_id', 'reviewed_at', 'evidence_sha256', 'notes']
    write_csv(OUT / 'MANUAL_QA_PENDING.csv', [], qa_fields)
    dump(OUT / 'SAMPLE_ACQUISITION_STATUS.json', {'status': 'BLOCKED_PERMISSION_OR_VERSION_EVIDENCE_NOT_AVAILABLE',
        'real_content_rows_acquired': 0, 'L3': 0, 'L4': 0, 'pilot_QA_candidates': 0,
        'independent_manual_QA_completed': 0, 'formal_manual_QA_target': 100,
        'empty_manifest_is_not_no_historical_posts': True})
    print('Locked E8a.1; protected prior artifacts', len(protected), 'and public science', len(old))

if __name__ == '__main__': main()
