"""Parity and prefix invariance checks on <=2025 data only, no2026 input files."""
import json
import numpy as np
from e4a_core import SOURCE
from e3b_protocol import load_frame,indices
from e3c_core import features
from e3a_core import read_pre2026
from e3c_2026_features import frame_from_prices,compact_features


def check():
    cuts=json.loads((SOURCE/'INDEPENDENT_VALIDATION_PROPOSAL.json').read_text())['event_cutoffs']
    results=[]
    for ticker in ('AAPL','TSLA'):
        z={n:read_pre2026(SOURCE/'inputs'/f'{n}_adjusted_through2025.csv') for n in (ticker,'VIX','VXN')}
        old=load_frame(ticker,SOURCE);new=frame_from_prices(z[ticker],z['VIX'],z['VXN'])
        oldx,olds,oldmeta=features(old,'2022-12-31');x,s,meta=compact_features(new,cuts[ticker],'2022-12-31')
        np.testing.assert_allclose(oldx,x,rtol=1e-6,atol=1e-6,equal_nan=True)
        assert oldmeta['columns']==meta['columns']
        for name in ('event','direction','long','vol','cell','vxn_high'): np.testing.assert_array_equal(olds[name],s[name])
        for a,b in (('2012-01-01','2022-12-31'),('2023-07-01','2023-12-31'),('2024-01-01','2025-12-31')):
            ii=indices(old,a,b);jj=indices(new,a,b);np.testing.assert_array_equal(ii,jj)
            np.testing.assert_array_equal(old.y5.iloc[ii],new.y5.iloc[jj])
            np.testing.assert_allclose(old.nextopen_log5.iloc[ii],new.nextopen_log5.iloc[jj],atol=1e-12)
        # Mutate only known2025 observations, proving <=2024 features/scaler unaffected.
        altered=z[ticker].copy();altered.loc['2025-01-01':,['Open','High','Low','Close']]*=2
        changed=frame_from_prices(altered,z['VIX'],z['VXN']);xx,_,mm=compact_features(changed,cuts[ticker],'2024-12-31')
        original,_,om=compact_features(new,cuts[ticker],'2024-12-31');prefix=new.index<='2024-12-31'
        np.testing.assert_allclose(xx[prefix],original[prefix],equal_nan=True,atol=1e-6)
        np.testing.assert_array_equal(mm['scaler_mean'],om['scaler_mean'])
        results.append({'ticker':ticker,'feature_parity':True,'label_and_cohort_parity':True,'prefix_invariance':True,'max_date':str(new.index.max().date()),'2026_loaded':False})
    print(json.dumps(results,indent=2))


if __name__=='__main__': check()
