"""Create fake market CSVs ONLY for engineering smoke tests."""
from pathlib import Path
import numpy as np
import pandas as pd


def make(outdir):
    outdir=Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ix=pd.bdate_range('2010-01-01','2026-01-09')
    rng=np.random.default_rng(123)
    for ticker,base in [('AAPL',70),('TSLA',50),('QQQ',100)]:
        close=base*np.exp(np.cumsum(rng.normal(.0002,.018,len(ix))))
        pd.DataFrame({'Date':ix,'Open':close*.999,'High':close*1.01,
                      'Low':close*.99,'Close':close,
                      'Volume':rng.integers(100000,1000000,len(ix))}).to_csv(outdir/f'{ticker}.csv',index=False)
    for ticker,base in [('VXN',22),('VIX',19)]:
        close=base+np.abs(rng.normal(0,4,len(ix)))
        pd.DataFrame({'Date':ix,'Close':close}).to_csv(outdir/f'{ticker}.csv',index=False)
    print('SYNTHETIC ONLY — NOT ACTUAL HISTORICAL DATA:',outdir)

if __name__=='__main__':
    import sys
    make(sys.argv[1] if len(sys.argv)>1 else 'data/synthetic')
