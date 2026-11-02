"""Meaningful CPU checks of causality, split purging, inference and installed tree APIs."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ.setdefault('OPENBLAS_NUM_THREADS','2');os.environ.setdefault('OMP_NUM_THREADS','2')
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from e3b_protocol import (ROOT,SOURCE,BASE,EXTRA,CONFIGS,FINAL,FOLDS,SEEDS,MAIN_MODELS,
                         load_frame,feature_matrix,indices,windows,calibrate)
from e3b_models import fit_cpu
from analyze_e3b import paired_inference,comparison_vectors,metrics
from e3a_core import calendar_counts,validate_adjustment


def test_data():
    assert len(BASE)==15 and len(EXTRA)==23
    for ticker in ('AAPL','TSLA'):
        f=load_frame(ticker);assert f.index.max()<=pd.Timestamp('2025-12-31')
        for arm in ('A','B'):
            scaled,meta=feature_matrix(f,arm,FINAL['fit_end']);ids=indices(f,FINAL['test_start'],FINAL['test_end'])
            x=windows(scaled,ids);assert x.shape==(len(ids),60,15 if arm=='A' else 38)
            assert np.isfinite(x).all()
            assert meta['feature_fit_end']=='2022-12-31'
        raw=pd.read_csv(SOURCE/'inputs'/f'{ticker}_raw_through2025.csv',parse_dates=['Date']).set_index('Date')
        adj=pd.read_csv(SOURCE/'inputs'/f'{ticker}_adjusted_through2025.csv',parse_dates=['Date']).set_index('Date')
        validate_adjustment(adj,raw,True)
        for block in FOLDS+[FINAL]:
            ranges=[('2012-01-01',block['fit_end']),(block['stop_start'],block['stop_end'])]
            if 'eval_start' in block:ranges.append((block['eval_start'],block['eval_end']))
            else:ranges.extend([(block['cal_start'],block['cal_end']),(block['test_start'],block['test_end'])])
            previous=None
            for start,end in ranges:
                ids=indices(f,start,end);assert len(ids)>50
                assert f.end20.iloc[ids].max()<=pd.Timestamp(end)
                if previous is not None:assert previous<f.index[ids].min()
                previous=f.end20.iloc[ids].max()
                for h in (1,5,20):
                    np.testing.assert_array_equal(f[f'y{h}'].iloc[ids],(f.reference_sign.iloc[ids]*f[f'nextopen_log{h}'].iloc[ids]<0).astype(int))
        i=indices(f,'2024-01-01','2025-12-31')[12]
        for h in (1,5,20):
            expected=100*np.log(adj.Close.iloc[i+h]/adj.Open.iloc[i+1])
            np.testing.assert_allclose(f[f'nextopen_log{h}'].iloc[i],expected,atol=1e-10)
    # Perturb every future OHLC and VIX/VXN level: no fit-prefix feature or scaler may change.
    with tempfile.TemporaryDirectory(dir=ROOT/'.cache',prefix='e3b_causality_') as td:
        source=Path(td);(source/'inputs').mkdir()
        for p in (SOURCE/'inputs').glob('*_adjusted_through2025.csv'):
            z=pd.read_csv(p,float_precision='round_trip');future=z.Date>'2016-06-30'
            for col in ('Open','High','Low','Close'):
                if col in z:z.loc[future,col]*=2
            z.to_csv(source/'inputs'/p.name,index=False)
        original=load_frame('AAPL');changed=load_frame('AAPL',source)
        for arm in ('A','B'):
            a,ma=feature_matrix(original,arm,'2016-06-30');b,mb=feature_matrix(changed,arm,'2016-06-30')
            np.testing.assert_allclose(a[original.index<='2016-06-30'],b[original.index<='2016-06-30'],equal_nan=True,rtol=2e-5,atol=2e-5)
            np.testing.assert_allclose(ma['scaler_mean'],mb['scaler_mean'],rtol=1e-10,atol=1e-10)
            np.testing.assert_allclose(ma['scaler_scale'],mb['scaler_scale'],rtol=1e-9,atol=1e-9)
            assert np.max(np.abs(a[original.index>'2016-06-30']-b[original.index>'2016-06-30']))>1


def test_statistics():
    rng=np.random.default_rng(17);n=150
    loss={(model,arm):rng.uniform(.1,.3,n) for model in MAIN_MODELS for arm in ('A','B')}
    for arm in ('A','B'):loss[('logistic',arm)]=np.full(n,.25)
    for model in ('cal_prior','momentum20','mean_reversion5'):loss[(model,'shared')]=np.full(n,.25)
    rows,d=comparison_vectors(loss);assert len(rows)==51 and d.shape==(150,51)
    c=calendar_counts(n,20,reps=199,seed=42);assert np.all(c.sum(axis=1)==n)
    result=paired_inference(np.column_stack([np.zeros(n),np.full(n,.01)]),c,20)
    assert result[0]['hac_p']==1 and result[0]['bootstrap_p']==1
    np.testing.assert_allclose(result[1]['difference'],.01)
    assert result[1]['bootstrap_ci_low']>.009999
    mask=np.arange(n)%3==0;result=paired_inference(d,c,20,mask)
    np.testing.assert_allclose(result[0]['difference'],d[mask,0].mean())
    # Average per-seed losses, not loss of ensemble probability.
    y=np.array([0,1]);p=np.array([[.2,.8],[.8,.2]])
    assert np.mean((p-y)**2)>.25 and np.mean((p.mean(axis=0)-y)**2)==.25
    assert metrics(y,np.array([0.,1.]))['brier']==0
    yc=np.array([0,1]*30);pc=np.linspace(.1,.9,60)
    p,info=calibrate(pc,yc,np.array([.2,.8]));assert np.isfinite(p).all() and info['n_calibration']==60


def test_tree_interfaces():
    rng=np.random.default_rng(42);x=rng.normal(size=(200,60,15)).astype(np.float32)
    y=(x[:,-1,0]+rng.normal(size=200)>.1).astype(int)
    with tempfile.TemporaryDirectory(dir=ROOT/'.cache',prefix='e3b_models_') as td:
        for name in ('logistic','xgboost','lightgbm'):
            folder=Path(td)/name;folder.mkdir()
            pred,info=fit_cpu(name,CONFIGS[name][0],42,x[:120],y[:120],x[120:160],y[120:160],{'eval':x[160:]},folder)
            assert pred['eval'].shape==(40,) and np.isfinite(pred['eval']).all()
            assert (folder/'training_history.csv').exists() and info['best_iteration']>0
            print(name,'real CPU fit/early-stop/save/predict PASSED',flush=True)


def test_report_interfaces():
    # Synthetic tables live ONLY in a deleted temporary cache, never research outputs.
    import analyze_e3b as a
    rng=np.random.default_rng(1);rows=[];state=[];events=[];tests=[];reliability=[]
    groupnames=['all','extreme5_up','extreme5_down','extreme5_any','conflict_up','conflict_down','conflict_any','aligned_extreme','VIX_high','VIX_low','VXN_high','VXN_low','nonoverlap_extreme','year2024','year2025']
    y=np.tile([0,1],30)
    for ticker in ('AAPL','TSLA'):
        for h in (1,5,20):
            keys=[(model,arm) for model in ('logistic',)+MAIN_MODELS for arm in ('A','B')]+[(model,'shared') for model in ('cal_prior','train_prior','momentum20','mean_reversion5','hard_momentum20','hard_MR5')]
            loss={}
            for model,arm in keys:
                for seed in (SEEDS if arm!='shared' else (-1,)):
                    p=rng.uniform(.3,.7,60);meta={'ticker':ticker,'horizon':h,'model':model,'arm':arm,'seed':seed}
                    met=metrics(y,p,True)
                    for version in ('raw','calibrated'):rows.append({**meta,'probability':version,**met})
                    for group in groupnames:state.append({**meta,'group':group,**met})
                loss[(model,arm)]=(p-y)**2
                for binid in range(10):reliability.append({'ticker':ticker,'horizon':h,'model':model,'arm':arm,'bin':binid,'mean_seed_count':6,'mean_probability':.05+.1*binid,'observed_frequency':.05+.1*binid})
            cr,d=comparison_vectors(loss)
            for meta,stat in zip(cr,paired_inference(d,calendar_counts(60,20,reps=99,seed=42),20)):
                tests.append({'ticker':ticker,'horizon':h,'block_length':20,**meta,**stat,'hac_holm_family':1.,'bootstrap_holm_family':1.})
            for group in groupnames:events.append({'ticker':ticker,'horizon':h,'group':group,'n':60,'reversal_rate':.5})
    fields=['brier','log_loss','roc_auc','pr_auc','balanced_accuracy','mcc','accuracy','ece10','calibration_bias','calibration_slope']
    m=pd.DataFrame(rows);sm=pd.DataFrame(state)
    summary=m.groupby(['ticker','horizon','model','arm','probability'])[fields].agg(['mean','std','min','max']).reset_index()
    summary.columns=['_'.join(c).rstrip('_') for c in summary.columns]
    sg=sm.groupby(['ticker','horizon','model','arm','group'])[['n','prevalence']+fields[:9]].agg(['mean','std']).reset_index()
    sg.columns=['_'.join(c).rstrip('_') for c in sg.columns]
    with tempfile.TemporaryDirectory(dir=ROOT/'.cache',prefix='e3b_output_test_') as td:
        out=Path(td);(out/'tables').mkdir();(out/'figures').mkdir()
        summary.to_csv(out/'tables/metrics_comparison.csv',index=False)
        m.to_csv(out/'tables/metrics_per_seed.csv',index=False);sg.to_csv(out/'tables/state_metrics.csv',index=False)
        pd.DataFrame(tests).to_csv(out/'tables/paired_tests.csv',index=False)
        pd.DataFrame(reliability).to_csv(out/'tables/reliability.csv',index=False)
        subprocess.run([sys.executable,'-B',str(ROOT/'scripts/plot_e3b.py'),'--out',str(out)],check=True)
        previous=a.OUT
        try:a.OUT=out;a.report(summary,pd.DataFrame(tests),sg,pd.DataFrame(events))
        finally:a.OUT=previous
        assert (out/'E3B_SUMMARY.md').stat().st_size>1000 and len(list((out/'figures').glob('*.png')))==7
    print('Synthetic schema/report/7 PNG+PDF figures PASSED; temporary artifacts deleted',flush=True)


if __name__=='__main__':
    test_data();print('Causal features, next-open labels, all purged splits and no2026 PASSED',flush=True)
    test_statistics();print('Paired calendar bootstrap, seed aggregation and metrics PASSED',flush=True)
    test_tree_interfaces();test_report_interfaces()
    print('All E3b CPU checks PASSED; CUDA must be checked on host',flush=True)
