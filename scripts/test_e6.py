"""Causality and source-value tests, no model training or holdout access."""
import sys,unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
import e3b_protocol as bp
import e6_core as ec
from e6_data import align,CORE,table_row

class E6Tests(unittest.TestCase):
    def test_source_golden_values(self):
        z=pd.read_csv(ec.OUT/'inputs/fundamental_vintages.csv').set_index('vintage')
        # Independently checked against original official financial tables.
        self.assertAlmostEqual(z.loc['AAPL_FY2025_Q1','net_margin'],36330/124300)
        self.assertAlmostEqual(z.loc['TSLA_FY2025_Q3','net_margin'],1373/28095)
        self.assertAlmostEqual(z.loc['TSLA_FY2022_Q3','gross_margin'],.251)
        self.assertAlmostEqual(z.loc['TSLA_FY2013_Q4','revenue_current'],615.219)
        self.assertAlmostEqual(z.loc['AAPL_FY2025_Q2','cfo_margin'],53887/219659)
    def test_footnotes_not_numeric_facts(self):
        vals,_=table_row('Total net sales (1)\n      124,300 119,575',[r'Total net sales'])
        self.assertEqual(vals,[124300.,119575.])
        vals,_=table_row('Total revenues for Q4 were $3 billion',[r'Total revenues'])
        self.assertEqual(vals,[])
    def test_asof_weekend_revision_not_backfilled(self):
        cal=pd.bdate_range('2024-01-01','2024-02-29')
        z=pd.DataFrame([{'release_date':'2024-01-05','vintage':'initial',**dict.fromkeys(CORE,1.)},{'release_date':'2024-01-19','vintage':'revision',**dict.fromkeys(CORE,2.)}])
        a=align(z,cal,2)
        self.assertTrue(pd.isna(a.loc['2024-01-08','revenue_yoy']))
        self.assertEqual(a.loc['2024-01-09','revenue_yoy'],1)
        self.assertEqual(a.loc['2024-01-22','revenue_yoy'],1)
        self.assertEqual(a.loc['2024-01-23','revenue_yoy'],2)
    def test_future_fundamentals_do_not_change_past_transform(self):
        f,a=ec.load('AAPL');base,meta=ec.fundamental_matrix(f,a,'2022-12-31')
        altered=a.copy();altered.loc[altered.index>'2023-12-31',CORE]=12345
        new,nmeta=ec.fundamental_matrix(f,altered,'2022-12-31')
        np.testing.assert_array_equal(base[f.index<='2023-12-31'],new[f.index<='2023-12-31']);self.assertEqual(meta,nmeta)
    def test_fixed_calendar_price_and_no_window_backfill(self):
        f,a=ec.load('TSLA');p,ip,_=ec.arrays(f,a,'P',bp.FINAL);pf,ii,_=ec.arrays(f,a,'PF',bp.FINAL)
        np.testing.assert_array_equal(ip['test'],ii['test']);np.testing.assert_array_equal(p['test'][0],pf['test'][0][:,:,:51])
        self.assertEqual(len(ii['test']),482)
        x,_=ec.fundamental_matrix(f,a,bp.FINAL['fit_end'])
        np.testing.assert_array_equal(pf['test'][0][0,:,51:],x[ii['test'][0]-59:ii['test'][0]+1,:-1])
        self.assertTrue((pd.to_datetime(f.end20.iloc[ii['fit']])<=pd.Timestamp(bp.FINAL['fit_end'])).all())
    def test_no_future_financial_dates_and_all_past_documents(self):
        v=pd.read_csv(ec.OUT/'inputs/fundamental_vintages.csv')
        self.assertTrue(v.release_date.le('2025-12-31').all());self.assertFalse(v.vintage.duplicated().any())
        self.assertTrue(v.SEC_acceptance_datetime.isna().all());self.assertTrue(v.SEC_amendment_datetime.isna().all())
        self.assertFalse(v.historical_first_seen_verified.any())

if __name__=='__main__':unittest.main()
