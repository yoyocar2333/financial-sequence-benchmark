"""Check public E8a aggregate consistency, not raw-source PIT authentication."""
import argparse
import json
from pathlib import Path
from e8a_core import read_csv

def validate(bundle):
    coverage = list(read_csv(bundle / 'tables/source_stock_year_coverage.csv'))
    pit = list(read_csv(bundle / 'tables/PIT_quality_by_source.csv'))
    for r in pit:
        g = [v for v in coverage if v['source'] == r['source'] and v['ticker'] == r['ticker']]
        assert sum(int(v['retained_rows']) for v in g) == int(r['rows'])
        assert sum(int(r[k]) for k in ('L0_UNUSABLE_TIME', 'L1_DATE_PROXY', 'L2_PUBLISHER_TIME_CLAIM', 'L3_SOURCE_VERSION_VERIFIED', 'L4_ARRIVAL_VERIFIED')) == int(r['rows'])
        assert int(r['L3_SOURCE_VERSION_VERIFIED']) == int(r['L4_ARRIVAL_VERIFIED']) == 0
    assert all(r['monitoring_coverage_fraction'] == '' and r['true_zero_news_days'] == '' for r in coverage)
    assert all(int(r['failures']) == 0 for r in read_csv(bundle / 'tables/feature_integrity.csv'))
    assert all(0 <= int(r['events_with_retained_source_in_last5']) <= int(r['price_events']) for r in read_csv(bundle / 'tables/event_source_overlap.csv'))
    assert all(int(r['reversal_labels']) + int(r['nonreversal_labels']) + int(r['missing_labels']) == int(r['nonoverlap5_price_events_with_retained_proxy']) for r in read_csv(bundle / 'tables/legacy_partition_support.csv'))
    gates = list(read_csv(bundle / 'tables/E8b_readiness_gates.csv'))
    assert len(gates) == 8 and not any(r['status'] == 'PASS' for r in gates)
    results = json.loads((bundle / 'tables/analysis_results.json').read_text())
    assert results['E8b_formal'] == 'NOT_READY' and results['new_models'] == 0
    assert results['E3c2026'] == 'UNCHANGED_NOT_EXECUTED'
    print(json.dumps({'public_aggregate_checks': 'PASSED', 'raw_source_PIT_proved': False,
                      'models_fitted': 0, '2026_validation_executed': False}))

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    validate(p.parse_args().bundle)
