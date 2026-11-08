"""E7a design regression tests; no new financial model fitting."""
import copy,sys,unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
from e7a_pit_contract import audit,latest_asof,label_within_block
from e7a_development_audit import ar_mean_factor,panel_mean_variance,OUT

class DesignTests(unittest.TestCase):
    def record(self):
        return {'kind':'fundamental_actual','issuer_id':'SYNTHETIC_A','source_document_id':'SYNTHETIC_ORIGINAL','version_sha256':'1'*64,'public_available_utc':'2020-07-31T21:00:00Z','public_time_evidence':'synthetic_feed','version_chain_verified':True,'units':'USD','concept':'NetIncome','period_end':'2020-06-30','accepted_at_utc':'2020-07-31T20:58:00Z','acceptance_timezone_verified':True,'retrieved_at_utc':'2020-07-31T21:01:00Z','value':10}
    def test_future_release_and_same_day_late_release(self):
        r=self.record();self.assertFalse(audit(r,'2020-07-31T20:30:00Z')['eligible']);self.assertTrue(audit(r,'2020-08-03T21:00:00Z')['eligible'])
    def test_revision_does_not_backfill(self):
        a=self.record();b=copy.deepcopy(a);b.update(value=99,version_sha256='2'*64,public_available_utc='2020-09-01T21:00:00Z',accepted_at_utc='2020-09-01T20:58:00Z')
        self.assertEqual(latest_asof([b,a],'2020-08-10T21:00:00Z')['value'],10);self.assertEqual(latest_asof([a,b],'2020-09-02T21:00:00Z')['value'],99)
    def test_unknown_clock_and_period_end_are_not_availability(self):
        r=self.record();r['public_available_utc']=None;self.assertFalse(audit(r,'2020-08-03T21:00:00Z')['eligible'])
        r=self.record();r['accepted_at_utc']='2020-07-31T20:58:00';self.assertFalse(audit(r,'2020-08-03T21:00:00Z')['eligible'])
    def test_news_and_estimates_need_arrival_snapshot(self):
        r=self.record();r['kind']='analyst_estimate';self.assertFalse(audit(r,'2020-08-03T21:00:00Z')['eligible'])
        r.update(provider_received_utc='2020-07-31T21:01:00Z',historical_snapshot_verified=True);self.assertTrue(audit(r,'2020-08-03T21:00:00Z')['eligible'])
    def test_overlapping_label_purge(self):
        self.assertFalse(label_within_block('2020-12-30T21:00:00Z','2021-01-07T21:00:00Z','2012-01-01T00:00:00Z','2020-12-31T23:59:59Z'))
    def test_independent_power_limit_and_common_shock_floor(self):
        self.assertAlmostEqual(ar_mean_factor(12,0),1/12)
        self.assertAlmostEqual(panel_mean_variance(.01,200,12,0,0,0),.01**2/2400)
        floor=.01**2*.1/12
        self.assertGreater(panel_mean_variance(.01,100000,12,.1,0,0),floor)
    def test_synthetic_controls_do_not_confuse_information(self):
        z=pd.read_csv(OUT/'tables/synthetic_method_controls.csv').set_index(['case','forecast'])
        case='shrink_only_no_new_information';self.assertLess(z.loc[(case,'Late'),'Brier'],z.loc[(case,'P'),'Brier']);self.assertAlmostEqual(z.loc[(case,'Late'),'Brier'],z.loc[(case,'matched_constant_shrink'),'Brier'])
        case='duplicated_price_information';self.assertAlmostEqual(z.loc[(case,'Late'),'Brier'],z.loc[(case,'P'),'Brier']);self.assertLess(z.loc[(case,'Late'),'Brier'],z.loc[(case,'matched_constant_shrink'),'Brier'])
    def test_development_period_guard(self):
        z=pd.read_csv(OUT/'tables/development_quarter_statistics.csv');self.assertTrue(z.quarter.between('2017Q1','2022Q4').all());self.assertEqual(z.quarter.nunique(),24)

if __name__=='__main__':unittest.main()
