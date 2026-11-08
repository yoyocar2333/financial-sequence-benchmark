"""CPU-only evidence, causal-feature and reproduction-adapter regression tests."""
import argparse
from pathlib import Path
import sys,tempfile,unittest
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from reproduce_public import verify_evidence
from e5_core import indicators,wilder,TECH,RELATIVE,block_arrays,FINAL
import e5_core as ec
from run_public_model import arrays_for,execute,load_authorized_market
from analyze_e3b import paired_inference
from e3a_core import calendar_counts


class PublicResearchTests(unittest.TestCase):
    def test_released_evidence_reaggregates(self):
        r=verify_evidence()
        self.assertEqual(r['E1_seed_rows_reaggregated'],20)
        self.assertEqual(r['E5_primary_significant_gains'],0)

    def test_wilder_seed_and_future_invariance(self):
        z=wilder(pd.Series([1.,2.,3.,7.,4.]),3)
        self.assertTrue(np.isnan(z.iloc[1]));self.assertAlmostEqual(z.iloc[2],2)
        self.assertAlmostEqual(z.iloc[3],11/3)
        ix=pd.bdate_range('2010-01-01',periods=600)
        c=pd.Series(100+np.arange(600)*.08+np.sin(np.arange(600)/4),index=ix)
        a=pd.DataFrame({'Close':c,'High':c+1,'Low':c-1,'Volume':1e6+np.arange(600)*100})
        before=indicators(a,a)
        b=a.copy();b.loc[ix[450]:,['Close','High','Low']]*=2;b.loc[ix[450]:,'Volume']*=3
        after=indicators(b,a)
        pd.testing.assert_frame_equal(before.iloc[:450],after.iloc[:450])
        self.assertAlmostEqual(before.previous_high20.iloc[450],a.High.iloc[430:450].max())

    def test_public_adapter_matches_frozen_array_paths(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);(folder/'inputs').mkdir()
            ix=pd.bdate_range('2010-01-04','2025-12-31');t=np.arange(len(ix))
            for j,n in enumerate(['AAPL','QQQ','VIX','VXN']):
                c=50+j*10+.005*t+np.sin(t/(3+j))
                z=pd.DataFrame({'Date':ix,'Open':c+.1,'High':c+1,'Low':c-1,'Close':c,'Volume':1e6+t*10})
                z.to_csv(folder/'inputs'/(n+'_adjusted_through2025.csv'),index=False)
            old=ec.SOURCE
            try:
                ec.SOURCE=folder;f=ec.load('AAPL')
                a,ids,meta=arrays_for(f,'E3b','B')
                b,ids2,meta2=arrays_for(f,'E5','B')
                for k in ids:
                    np.testing.assert_array_equal(ids[k],ids2[k])
                    np.testing.assert_array_equal(a[k][0],b[k][0])
                c,ii,_=arrays_for(f,'E5','T')
                self.assertEqual(c['fit'][0].shape[-2:],(60,51))
                self.assertEqual(a['fit'][0].shape[-2:],(60,38))
                self.assertTrue(np.isfinite(c['test'][0]).all())
                self.assertTrue((f.end20.iloc[ii['fit']]<=pd.Timestamp(FINAL['fit_end'])).all())
                self.assertTrue((f.end20.iloc[ii['stop']]<=pd.Timestamp(FINAL['stop_end'])).all())
                self.assertTrue((f.end20.iloc[ii['cal']]<=pd.Timestamp(FINAL['cal_end'])).all())
            finally:ec.SOURCE=old

    def test_adapter_refuses_gpu_without_flag_and_revised_data(self):
        with tempfile.TemporaryDirectory() as td:
            a=argparse.Namespace(output=Path(td)/'new',model='mamba',allow_gpu=False)
            with self.assertRaisesRegex(ValueError,'allow-gpu'):execute(a)
            p=Path(td)/'AAPL_adjusted_through2025.csv';p.write_text('Date,Close\n2025-01-02,1\n')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):load_authorized_market(Path(td),'AAPL')

    def test_paired_calendar_estimator_and_identical_losses(self):
        counts=calendar_counts(64,10,reps=199,seed=5)
        np.testing.assert_array_equal(counts.sum(axis=1),np.full(199,64))
        same=paired_inference(np.zeros(64),counts,10)[0]
        self.assertEqual(same['difference'],0);self.assertEqual(same['bootstrap_p'],1)
        d=np.sin(np.arange(64))*.01+.001;mask=np.arange(64)%2==0
        r=paired_inference(d,counts,10,mask)[0]
        self.assertEqual(r['n'],32);self.assertAlmostEqual(r['difference'],d[mask].mean())

if __name__=='__main__':unittest.main(verbosity=2)
