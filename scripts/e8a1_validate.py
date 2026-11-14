"""Validate empty real pilot, unchanged gates and deterministic table replay."""
import argparse
import csv
import json
import tempfile
from pathlib import Path
from e8a1_build import tables, FIELDS
from e8a1_collector import digest

def validate(bundle):
    with (bundle / 'PILOT_SAMPLE_MANIFEST.csv').open() as f:
        r = csv.DictReader(f); rows = list(r)
        assert r.fieldnames == FIELDS and not rows, 'No real samples authorized in this frozen pilot'
    with (bundle / 'MANUAL_QA_PENDING.csv').open() as f:
        assert not list(csv.DictReader(f)), 'Generated QA may not be reported as completed'
    status = json.loads((bundle / 'SAMPLE_ACQUISITION_STATUS.json').read_text())
    assert status['real_content_rows_acquired'] == status['L3'] == status['L4'] == status['independent_manual_QA_completed'] == 0
    for row in json.loads((bundle / 'inputs/e8a_main_contract_hashes.json').read_text()):
        relative = row['path'].removeprefix('research/E8a/')
        assert digest((bundle / 'inputs/e8a_contract' / relative).read_bytes()) == row['sha256']
    with tempfile.TemporaryDirectory(prefix='e8a1_replay_') as d:
        out = Path(d); tables(bundle, out)
        count = 0
        for p in out.iterdir():
            assert p.read_bytes() == (bundle / 'tables' / p.name).read_bytes(), p.name
            count += 1
    gates = list(csv.DictReader((bundle / 'tables/E8b_readiness_decision.csv').open()))
    assert len(gates) == 8
    assert all(r['E8a1_status'] in ('PASS', 'FAIL', 'NOT_EVALUABLE', 'BLOCKED') and r['threshold_changed'] == 'False' for r in gates)
    assert not all(r['E8a1_status'] == 'PASS' for r in gates)
    result = {'status': 'PASSED', 'real_samples': 0, 'L3': 0, 'L4': 0, 'human_QA': 0,
              'replayed_files': count, 'CSV_tables': 5, 'schemas': 2, 'result_JSON': 1,
              'source_cards': 15, 'E8b': 'NOT_READY', 'source_authenticity_proved_by_replay': False}
    print(json.dumps(result)); return result

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--bundle', type=Path, required=True)
    validate(p.parse_args().bundle)
