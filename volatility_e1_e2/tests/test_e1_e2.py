from argparse import Namespace
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

FILE = Path(__file__).resolve().parents[1] / 'experiments' / 'volatility_e1_e2.py'
spec = importlib.util.spec_from_file_location('e12', FILE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def make_mock_data():
    """Entirely synthetic series; never use its evaluation numbers as market evidence."""
    ix = pd.bdate_range('2010-01-01', '2026-01-09')
    rng = np.random.default_rng(183)
    def stock(level):
        r = rng.normal(0.0002, 0.016, len(ix))
        close = level * np.exp(np.cumsum(r))
        return pd.DataFrame({'Open': close*.999, 'High':close*1.01,
                             'Low':close*.99, 'Close':close,
                             'Volume':rng.integers(100000, 200000, len(ix))}, index=ix)
    qqq = stock(120)
    aapl = stock(80)
    vxn = pd.DataFrame({'Close':20 + np.abs(rng.normal(0, 4, len(ix)))}, index=ix)
    vix = pd.DataFrame({'Close':18 + np.abs(rng.normal(0, 3, len(ix)))}, index=ix)
    return aapl, qqq, vxn, vix


def masks_args():
    return Namespace(train_start='2012-01-01', train_end='2022-12-31',
                     val_start='2023-01-01', val_end='2023-12-31',
                     test_start='2024-01-01', test_end='2025-12-31')


def test_target_is_next_adjacent_session_magnitude():
    a, q, vn, vi = make_mock_data()
    d = m.build_dataset(a, q, vn, vi)
    day = pd.Timestamp('2024-05-13')
    next_day = a.index[a.index.get_loc(day) + 1]
    assert d.at[day,'LabelDate'] == next_day
    expected = 100 * abs(np.log(a.at[next_day,'Close'] / a.at[day,'Close']))
    assert d.at[day,'TargetMagnitudePct'] == pytest.approx(expected)


def test_feature_not_affected_by_tomorrows_stock_close():
    a, q, vn, vi = make_mock_data()
    d1 = m.build_dataset(a, q, vn, vi)
    day = pd.Timestamp('2024-05-13')
    next_day = a.index[a.index.get_loc(day) + 1]
    changed = a.copy()
    changed.loc[next_day, 'Close'] *= 1.4
    d2 = m.build_dataset(changed, q, vn, vi)
    np.testing.assert_allclose(d1.loc[day,m.ALL_FEATURES].to_numpy(float),
                               d2.loc[day,m.ALL_FEATURES].to_numpy(float))
    assert d1.loc[day,'TargetMagnitudePct'] != d2.loc[day,'TargetMagnitudePct']


def test_vrp_on_matching_index_is_known_by_t():
    a, q, vn, vi = make_mock_data()
    d = m.build_dataset(a, q, vn, vi)
    day = pd.Timestamp('2024-05-13')
    assert d.at[day, 'VRP_QQQ'] == pytest.approx(
        vn.at[day, 'Close'] - m.annualized_rv(q['Close'], 20).at[day])
    assert d.at[day, 'VRP_Ratio'] == pytest.approx(
        vn.at[day, 'Close'] / m.annualized_rv(q['Close'], 20).at[day])


def test_split_label_never_crosses_boundary():
    a, q, vn, vi = make_mock_data()
    d = m.build_dataset(a, q, vn, vi)
    masks = m.make_masks(d,masks_args())
    assert all(mask.sum() > 200 for mask in masks.values())
    for group, mask in masks.items():
        assert (d.loc[mask,'LabelDate'] <= pd.Timestamp(getattr(masks_args(),group+'_end'))).all()
    assert not np.any(masks['train'] & masks['val'])
    assert not np.any(masks['val'] & masks['test'])


def test_windows_end_at_cutoff_and_no_future_features():
    X=np.arange(100).reshape(20,5)
    y=np.arange(20)
    mask=np.zeros(20,dtype=bool)
    mask[10:14]=True
    seq,t,ix=m.make_sequences(X,y,4,mask)
    assert (ix == [10,11,12,13]).all()
    assert seq[0,-1,0] == X[10,0]
    assert seq[0,0,0] == X[7,0]
    assert t[0] == y[10]


def test_complete_case_is_shared_across_arms():
    a,q,vn,vi=make_mock_data()
    vn.loc[pd.Timestamp('2024-05-13'),'Close']=np.nan
    d=m.build_dataset(a,q,vn,vi)
    assert pd.Timestamp('2024-05-13') not in d.index
    assert d[m.ALL_FEATURES].notna().all().all()


def test_dm_identical_forecast_not_false_significant():
    y=np.ones(30)
    ref=np.zeros(30)
    diff,p=m.hac_dm_pvalue(y,ref,ref)
    assert diff==0 and np.isnan(p)
