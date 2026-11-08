"""Offline replay from content-free audit inputs, not renewed source PIT proof."""
import argparse
import json
import tempfile
from pathlib import Path
from e8a_core import dump, sha
from e8a_analyze import analyze

def replay(bundle, output):
    if output.exists():
        raise FileExistsError('Fresh output directory required')
    manifest = json.loads((bundle / 'audits/replay_input_hashes.json').read_text())
    for name, expected in manifest.items():
        if sha(bundle / name) != expected:
            raise ValueError('Audit input changed: ' + name)
    analyze(bundle, output)
    compared = []
    for p in sorted(output.glob('*.csv')):
        if sha(p) != sha(bundle / 'tables' / p.name):
            raise AssertionError('Replayed table differs: ' + p.name)
        compared.append(p.name)
    if json.loads((output / 'analysis_results.json').read_text()) != json.loads((bundle / 'tables/analysis_results.json').read_text()):
        raise AssertionError('Summary mismatch')
    result = {'status': 'PASSED', 'replayed_tables': len(compared), 'tables': compared,
              'inputs_verified': len(manifest), 'raw_source_authentication_repeated': False,
              'models_fitted': 0, 'GPU_used': False, '2026_used': False}
    dump(output / 'replay_validation.json', result)
    print(json.dumps(result))

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    a = p.parse_args(); replay(a.bundle.resolve(), a.output_dir.resolve())
