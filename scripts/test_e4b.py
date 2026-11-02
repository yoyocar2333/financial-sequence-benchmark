"""Dataset-level token/version/PIT/coverage invariants on real reconstructed data."""
import argparse
import json
from pathlib import Path
import pandas as pd
import numpy as np
from e4b_core import OUT,fetch
from analyze_e4b import validate


def test(out):
    data,ft=validate(out)
    assert len(data)==2816 and len(ft)==3316
    assert data[data.source_family.eq('fnspid_bounded_headlines')].content.eq('').all()
    assert ft[ft.record_id.isin(data[data.representation.eq('title_only_no_body')].record_id)].source.eq('title').all()
    # A2026URL must fail BEFORE a request or any text parsing.
    try:fetch('https://www.apple.com/newsroom/2026/01/never-read/')
    except ValueError:pass
    else:raise AssertionError('2026URL was not rejected')
    print('Real token accounting / probability / exact-version / missing-body /2026URL / prior-result invariants PASSED')
    print(json.dumps({'records':len(data),'feature_views':len(ft),'headline_only_records':int(data.representation.eq('title_only_no_body').sum()),'2026_rows':int(data.publication_date.gt('2025-12-31').sum())}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);test(p.parse_args().out)
