"""CPU preflight: causality, support, calibration, conditional AUC and real model APIs."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ.setdefault('OPENBLAS_NUM_THREADS','2');os.environ.setdefault('OMP_NUM_THREADS','2')
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from e3c_core import ROOT,SOURCE,FINAL,FOLDS,SEEDS,GRIDS,METHODS,Prior,load_frame,features,blocks,comparisons,shrink_calibrate,masks
from analyze_e3c import within_state_auc,RANK_METHODS
from run_e3c import fit


def data_checks():
    for ticker in ('AAPL','TSLA'):
        f=load_frame(ticker,SOURCE);x,s,meta=features(f,FINAL['fit_end']);assert x.shape[1]==38
        assert f.index.max()<=pd.Timestamp('2025-12-31')
        for block in FOLDS+[FINAL]:
            xx,ss,_=features(f,block['fit_end']);bb=blocks(f,block)
            for part,ii in bb.items():
                assert np.isfinite(xx[ii]).all()
                end=block['fit_end'] if part=='fit' else (block['stop_end'] if 'eval_start' in block and part=='cal' else block.get('eval_end') if part=='eval' else block['cal_end'] if part=='cal' else block['test_end'])
                assert f.end20.iloc[ii].max()<=pd.Timestamp(end)
        ids=blocks(f,FINAL);y=f.y5.to_numpy();mutated=y.copy();mutated[ids['test']]=1-y[ids['test']]
        for method in ('global_prior','event_prior','direction_prior','state_prior','recent_event_prior'):
            p=Prior(method).fit(y,s,ids['fit'],ids['cal']).predict(ids['test'])
            q=Prior(method).fit(mutated,s,ids['fit'],ids['cal']).predict(ids['test'])
            np.testing.assert_array_equal(p,q)
        old=pd.read_csv(SOURCE/'final/h5'/ticker/'B/mamba/seed42/predictions.csv')
        np.testing.assert_array_equal(old.date,f.index[ids['test']].strftime('%Y-%m-%d'))
        assert masks(f,s,ids['test'])['events'].sum()==(101 if ticker=='AAPL' else 122)
    with tempfile.TemporaryDirectory(dir=ROOT/'.cache',prefix='e3c_causality_') as td:
        tmp=Path(td);(tmp/'inputs').mkdir()
        for p in (SOURCE/'inputs').glob('*_adjusted_through2025.csv'):
            z=pd.read_csv(p,float_precision='round_trip');future=z.Date>'2016-06-30'
            for col in ('Open','High','Low','Close','Volume'):
                if col in z:z.loc[future,col]*=2
            z.to_csv(tmp/'inputs'/p.name,index=False)
        original=load_frame('AAPL',SOURCE);changed=load_frame('AAPL',tmp)
        a,sa,ma=features(original,'2016-06-30');b,sb,mb=features(changed,'2016-06-30');prefix=original.index<='2016-06-30'
        np.testing.assert_allclose(a[prefix],b[prefix],equal_nan=True,rtol=2e-5,atol=2e-5)
        np.testing.assert_allclose(ma['scaler_mean'],mb['scaler_mean'],rtol=1e-9,atol=1e-9)
        np.testing.assert_array_equal(sa['cell'][prefix],sb['cell'][prefix])
    print('Causal features/cells/scalers, all purged splits, old dates, prior no-label-leak PASSED',flush=True)


def statistical_checks():
    y=np.array([0,0,0,1,0,1,1,1]);cell=np.array([0]*4+[1]*4);p=np.array([.2]*4+[.8]*4);mask=np.ones(8,bool)
    assert roc_auc_score(y,p)>.5 and within_state_auc(y,cell,p,mask)['within_state_auc']==.5
    assert within_state_auc(y,cell,y,mask)['within_state_auc']==1.
    assert within_state_auc(y,cell,1-y,mask)['within_state_auc']==0.
    assert within_state_auc(y,cell,np.stack([y,1-y]),mask)['within_state_auc']==.5
    raw=np.linspace(.1,.9,40);ev=np.arange(40)%2==0;caly=np.array([0,1]*20)
    corrected,info=shrink_calibrate(raw,ev,raw,caly,ev,event_head=True)
    np.testing.assert_allclose(corrected[~ev],raw[~ev],atol=1e-14)
    np.testing.assert_array_equal(np.argsort(corrected[ev]),np.argsort(raw[ev]))
    assert abs(info['offset'])<1
    pp,ci=shrink_calibrate(raw,ev,raw,caly,ev);assert np.isfinite(pp).all() and 0<=ci['slope']<=3
    assert len(comparisons())==24 and len(set(comparisons()))==24
    print('Between-state vs within-state AUC, seed-kernel averaging, head invariance and calibration PASSED',flush=True)


def fit_checks():
    rng=np.random.default_rng(2);x=rng.normal(size=(200,38)).astype(np.float32);y=(x[:,0]+rng.normal(size=200)>0).astype(int)
    with tempfile.TemporaryDirectory(dir=ROOT/'.cache',prefix='e3c_fit_') as td:
        for name in ('lr','xgb'):
            folder=Path(td)/name;p=fit(name,GRIDS[name][0],42,x[:150],y[:150],{'eval':x[150:]},folder)
            q=fit(name,GRIDS[name][0],42,x[:150],y[:150],{'eval':x[150:]},folder)
            np.testing.assert_array_equal(p['eval'],q['eval']);assert (folder/'feature_importance.csv').exists()
            (folder/'training_history.csv').write_text('tampered')
            try:fit(name,GRIDS[name][0],42,x[:150],y[:150],{'eval':x[150:]},folder)
            except RuntimeError:pass
            else:raise AssertionError('Tampered completed fit was accepted')
    print('Real Logistic/XGBoost fit/checkpoint/history/cache-integrity PASSED',flush=True)


def report_checks():
    import analyze_e3c as a
    names=list(METHODS)+[f'e3b_{model}_{arm}' for model in ('logistic','xgboost','lightgbm','lstm','mamba') for arm in ('A','B')]+['e3b_cal_prior','e3b_momentum20','e3b_mean_reversion5']
    groups=['all','events','non_events','surge','crash','conflict','aligned','long_up_crash','long_down_surge','event_VIX_high','event_VIX_low','event_VXN_high','event_VXN_low','z_events','nonoverlap5','nonoverlap20','events2024','events2025']
    mm=[];tt=[];rr=[];ee=[];hh=[];reliability=[];bins=[];tim=[]
    for ticker in ('AAPL','TSLA'):
        for name in names:
            for group in groups:
                mm.append({'ticker':ticker,'method':name,'group':group,'n_mean':100,'prevalence_mean':.5,'brier_mean':.25,'brier_std':.001,'log_loss_mean':.693,'roc_auc_mean':.5,'ece10_mean':.05,'calibration_bias_mean':.01,'mean_probability_mean':.5,'probability_sd_mean':.02})
            rr.append({'ticker':ticker,'method':name,'block_length':0,'event_ROC_AUC':.5,'within_state_auc':.5,'matched_positive_negative_pairs':100})
            for b in range(10):reliability.append({'ticker':ticker,'method':name,'seed':42,'bin':b,'n':10,'mean_probability':.05+.1*b,'reversal_rate':.05+.1*b})
            for b in range(1,6):bins.append({'ticker':ticker,'method':name,'seed':42,'score_bin':b,'n':20,'reversal_rate':.5,'signed_amplitude_mean_pp':.1*b})
        for method in RANK_METHODS:
            for length in (20,60):rr.append({'ticker':ticker,'method':method,'block_length':length,'within_state_auc':.5,'matched_positive_negative_pairs':100,'ci_low':.4,'ci_high':.6,'bootstrap_holm18':1.})
        for group in ('events','nonoverlap5','nonoverlap20'):
            for length in (20,60):
                for can,ref in comparisons():tt.append({'ticker':ticker,'group':group,'block_length':length,'candidate':can,'reference':ref,'difference':0.,'bootstrap_ci_low':-.01,'bootstrap_ci_high':.01,'hac_holm48':1.,'bootstrap_holm48':1.})
        for group in groups:ee.append({'ticker':ticker,'group':group,'n':100,'reversal_rate':.5,'signed_amplitude_mean_pp':0.})
        for part in ('fit','cal','test'):
            for code in range(12):hh.append({'ticker':ticker,'partition':part,'cell':code,'n':10,'reversal_rate':.5})
        for method in ('lr_all','lr_event','xgb_all','xgb_event'):tim.append({'ticker':ticker,'method':method,'Brier_gain_vs_state':0.,'hac_holm48':1.,'bootstrap_holm48':1.,'within_state_AUC':.5,'ranking_holm18':1.,'joint_timing_evidence':False})
    with tempfile.TemporaryDirectory(dir=ROOT/'.cache',prefix='e3c_report_') as td:
        dst=Path(td);(dst/'tables').mkdir();(dst/'figures').mkdir()
        for name,rows in [('metrics_comparison',mm),('paired_tests',tt),('within_state_ranking_tests',rr),('historical_conditional_states',hh),('event_reliability',reliability),('calibration_fixed_score_bins',bins)]:pd.DataFrame(rows).to_csv(dst/'tables'/f'{name}.csv',index=False)
        subprocess.run([sys.executable,'-B',str(ROOT/'scripts/plot_e3c.py'),'--out',str(dst)],check=True)
        previous=a.OUT
        try:a.OUT=dst;a.report(pd.DataFrame(mm),pd.DataFrame(tt),pd.DataFrame(rr),pd.DataFrame(tim),pd.DataFrame(ee),pd.DataFrame(hh))
        finally:a.OUT=previous
        assert len(list((dst/'figures').glob('*.png')))==7 and (dst/'E3C_SUMMARY.md').stat().st_size>1000
    print('Synthetic reporting schema and7 PNG/PDF plots PASSED; temporary fake artifacts deleted',flush=True)


if __name__=='__main__':
    data_checks();statistical_checks();fit_checks();report_checks();print('ALL E3c CPU preflight checks PASSED',flush=True)
