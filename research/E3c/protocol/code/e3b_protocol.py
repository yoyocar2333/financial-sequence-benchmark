"""Frozen E3b design, causal feature construction and time purging."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from e3a_core import features as trend_features,read_pre2026

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/e3b_20261026'
SOURCE=ROOT/'outputs/e3a_20261021'
SEEDS=(42,43,44,45,46)
HORIZONS=(5,1,20)
MODELS=('logistic','xgboost','lightgbm','lstm','mamba')
MAIN_MODELS=('xgboost','lightgbm','lstm','mamba')
BASE=['Open','High','Low','Close','Volume','MA5','MA20','Volatility_10','RV5','RV20','VXN','VXN_Change','VIX','VIX_Change','reference_sign']
EXTRA=[f'{k}{h}' for k in ('past','z') for h in (5,20,60,120)]+[
    f'context{long}_ex{short}{suffix}' for long in (60,120) for short in (5,20) for suffix in ('','_z')]+[
    'sigma60','tail_up','tail_down','ztail_up','ztail_down','VIX_high','VXN_high']
CONFIGS={
    'logistic':[{'C':x} for x in (.001,.01,.1)],
    'xgboost':[{'max_depth':d,'min_child_weight':m,'reg_lambda':l,'learning_rate':r} for d,m,l,r in [(2,20,10,.03),(3,30,20,.03),(4,50,40,.02)]],
    'lightgbm':[{'num_leaves':d,'min_child_samples':m,'reg_lambda':l,'learning_rate':r} for d,m,l,r in [(4,40,10,.03),(8,60,20,.03),(16,80,40,.02)]],
    'lstm':[{'width':32,'lr':.001,'weight_decay':.01},{'width':32,'lr':.0003,'weight_decay':.01},{'width':64,'lr':.0003,'weight_decay':.01}],
    'mamba':[{'width':32,'lr':.001,'weight_decay':.01},{'width':32,'lr':.0003,'weight_decay':.01},{'width':64,'lr':.0003,'weight_decay':.01}]}
FOLDS=[{'name':str(year),'fit_end':f'{year}-06-30','stop_start':f'{year}-07-01','stop_end':f'{year}-12-31',
        'eval_start':f'{year+1}-01-01','eval_end':f'{year+2}-12-31'} for year in (2016,2018,2020)]
FINAL={'fit_end':'2022-12-31','stop_start':'2023-01-01','stop_end':'2023-06-30','cal_start':'2023-07-01','cal_end':'2023-12-31','test_start':'2024-01-01','test_end':'2025-12-31'}
PLAN={
    'version':'E3b-1.0','scope':'Exploratory finite-budget benchmark on previously viewed 2024-2025; 2026 never loaded',
    'scope_from_proposal':'Main binary reversal benchmark implemented; optional material-reversal sigma threshold, three-class/neutral task, extra same-day arm and trading profitability deferred before fitting; not selected using test results',
    'primary_horizon':5,'secondary_horizons':[1,20],'seeds':list(SEEDS),'sequence_length':60,
    'target':'1 if sign(past5 close log return) * log(C[t+h]/Open[t+1]) < 0 else 0; future flats non-reversal; known flat reference excluded',
    'cutoff':'After t stock/VIX/VXN final data available; execution reference next session adjusted Open; no cost/slippage profitability claim',
    'feature_A':BASE,'feature_B_extra':EXTRA,
    'common_orientation':'reference_sign is common target-conditioning metadata in BOTH A/B; not a B-only hint about target definition',
    'representation':'All models see identical 60xd causal observations; trees/logistic flatten, neural models use same sequence; no tree-only aggregation shortcut',
    'preprocessing':'Training-calendar-only thresholds and StandardScaler, refit separately per fold; final subgroup definitions use frozen E3a training thresholds. No global2012-2022 thresholds in earlier CV folds',
    'split':FINAL,'folds':FOLDS,'purge':'All blocks require t+20 within the same block, even h1/5, for identical dates across horizons; valid entire 60-day history required',
    'search':{'candidates_per_model':3,'folds':3,'selection_seed':42,'criterion':'unweighted mean of OUTER-fold raw-probability Brier','inner_stopping':'last half-year before each outer fold, not outer evaluation labels','tie_break':'lowest config index','candidate_grid':CONFIGS},
    'training':{'neural_batch':64,'max_epochs':24,'neural_patience':4,'minimum_Brier_improvement':1e-5,'tree_max_rounds':300,'tree_patience':25,'CPU_threads':2,
                'neural_loss':'unweighted BCEWithLogits','optimizer':'AdamW','gradient_clip':1.,'dropout':.1,'Mamba':'genuine mamba_ssm.Mamba(d_state16,d_conv4,expand2)',
                'resource':'single GPU process; allocator fraction .10, duty .50; no external-growth/utilization preemption; CUDA/OOM/device errors halt queue',
                'deviation':'New classification study uses batch64/duty.50 rather than amplitude-study batch8/duty.25; all LSTM/Mamba A/B arms share this choice; memory checked by genuine GPU smoke before training'},
    'calibration':'Fixed ridge Platt sigmoid(C=1) on2023H2 only, per seed/model/arm/horizon; no selection between raw and calibrated test results; calibrated probabilities primary, raw retained',
    'classification_threshold':.5,
    'baselines':['logistic same-window same3-candidate CV','train prior Beta(1,1)','calibration prior Beta(1,1), fair primary constant with same calibration data','momentum20 sigmoid(past20/[current RV20 daily sigma*sqrt20]) direction mapped to reversal, same Platt calibration','mean_reversion5 sigmoid(-past5/[current RV5 daily sigma*sqrt5]) direction mapped to reversal, same Platt calibration','hard momentum20 and always-reversal MR5 descriptive only'],
    'baseline_caveat':'Hard MR5 always predicts target reversal and hard momentum5 always non-reversal by definition. Beating these hard extremes does not establish value; primary comparisons use calibrated soft baselines and logistic',
    'metrics':['Brier primary','LogLoss','ROC_AUC','PR_AUC','BalancedAccuracy','MCC','accuracy','ECE10 fixed bins','calibration bias/slope','reliability diagrams'],
    'subgroups':['all','extreme5_up','extreme5_down','extreme5_any','conflict_up','conflict_down','conflict_any','aligned_extreme','VIX_high','VIX_low','VXN_high','VXN_low','nonoverlap_extreme','year2024','year2025'],
    'distinction':'Models trained on all eligible dates; subgroup metrics do NOT represent separately trained event-only predictors. No conditioning on future reversal for primary feature groups',
    'inference':'Paired same-date Brier losses, first average five seed losses; Bartlett HAC lag20 primary, calendar circular block bootstrap length20 B4999 RNG20261026; lag/block60 sensitivity; never treat seeds as extra independent dates',
    'family':'Per horizon102 comparisons: 24 within-arm model pairs +8 A-B gains +64 main model versus logistic/cal-prior/momentum/MR baselines +6 Mamba-versus-other gain interactions. h5 Holm102 primary; h1+h20 Holm204 secondary; globalHolm306 also reported',
    'subgroup_inference':'Descriptive metrics and pointwise block CIs, minimum20 dates and two labels for AUC; no posthoc subgroup significance claims',
    'complexity_limit':'Small fixed search, not exhaustive optimization; rankings apply to these budgets, calibration and two stocks, not universal architecture superiority',
    'references':['https://xgboost.readthedocs.io/en/stable/python/python_api.html','https://lightgbm.readthedocs.io/en/stable/Parameters.html','https://scikit-learn.org/stable/modules/calibration.html','https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html','https://github.com/state-spaces/mamba']}


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_json(p,data):
    p=Path(p);temp=p.with_name(p.name+'.tmp');temp.write_text(json.dumps(data,indent=2,ensure_ascii=False,default=str,allow_nan=False)+'\n');temp.replace(p)


def load_frame(ticker,source=SOURCE):
    data={n:read_pre2026(source/'inputs'/f'{n}_adjusted_through2025.csv') for n in (ticker,'QQQ','VIX','VXN')}
    s=data[ticker];f=trend_features(s,data['QQQ'],data['VIX'],data['VXN'])
    f['Open']=s.Open;f['High']=s.High;f['Low']=s.Low;f['Close']=s.Close;f['Volume']=s.Volume
    f['MA5']=s.Close.rolling(5,min_periods=5).mean();f['MA20']=s.Close.rolling(20,min_periods=20).mean()
    f['Volatility_10']=s.Close.rolling(10,min_periods=10).std()
    r=np.log(s.Close/s.Close.shift(1))
    f['RV5']=100*np.sqrt(252)*r.rolling(5,min_periods=5).std(ddof=1)
    f['RV20']=100*np.sqrt(252)*r.rolling(20,min_periods=20).std(ddof=1)
    for n in ('VIX','VXN'):f[n+'_Change']=data[n].Close.pct_change(fill_method=None).reindex(f.index)*100
    f['reference_sign']=np.sign(f.past5)
    for h in HORIZONS:f[f'y{h}']=(f.reference_sign*f[f'nextopen_log{h}']<0).astype(np.int8)
    return f


def feature_matrix(f,arm,cutoff):
    train=f.loc['2012-01-01':cutoff]
    if not len(train):raise ValueError('No feature-fitting history')
    x=f.copy();thresholds={}
    for name in ('past5','z5'):
        thresholds[name]=[float(train[name].quantile(.1)),float(train[name].quantile(.9))]
    for name in ('VIX','VXN'):thresholds[name]=float(train[name].median())
    x['tail_up']=(x.past5>=thresholds['past5'][1]).astype(float)
    x['tail_down']=(x.past5<=thresholds['past5'][0]).astype(float)
    x['ztail_up']=(x.z5>=thresholds['z5'][1]).astype(float)
    x['ztail_down']=(x.z5<=thresholds['z5'][0]).astype(float)
    for name in ('VIX','VXN'):x[name+'_high']=(x[name]>=thresholds[name]).astype(float)
    columns=BASE+(EXTRA if arm=='B' else [])
    values=x[columns].to_numpy(dtype=np.float64)
    fit=(x.index>='2012-01-01')&(x.index<=cutoff)&np.isfinite(values).all(axis=1)
    scaler=StandardScaler().fit(values[fit])
    scaled=scaler.transform(values).astype(np.float32)
    meta={'columns':columns,'thresholds':thresholds,'feature_fit_start':'2012-01-01','feature_fit_end':cutoff,
          'scaler_mean':scaler.mean_.tolist(),'scaler_scale':scaler.scale_.tolist(),'scaler_n':int(fit.sum())}
    return scaled,meta


def indices(f,start,end):
    needed=BASE+[c for c in EXTRA if c not in ('tail_up','tail_down','ztail_up','ztail_down','VIX_high','VXN_high')]
    finite=np.isfinite(f[needed].to_numpy(float)).all(axis=1)
    valid_history=pd.Series(finite).rolling(60,min_periods=60).sum().eq(60).to_numpy()
    mask=(f.index>=start)&(f.index<=end)&(f.end20<=end)&(f.reference_sign.to_numpy()!=0)&valid_history
    ids=np.flatnonzero(mask)
    if len(ids) and (pd.to_datetime(f.end20.iloc[ids])>pd.Timestamp(end)).any():raise RuntimeError('Label crosses split')
    return ids


def windows(scaled,ids):
    offsets=np.arange(-59,1)
    return np.ascontiguousarray(scaled[ids[:,None]+offsets[None,:]],dtype=np.float32)


def sigmoid(x):
    x=np.clip(np.asarray(x,float),-35,35);return 1/(1+np.exp(-x))


def logit(p):
    p=np.clip(np.asarray(p,float),1e-6,1-1e-6);return np.log(p/(1-p))


def calibrate(raw_cal,ycal,raw_test):
    from sklearn.linear_model import LogisticRegression
    if len(np.unique(ycal))!=2:raise RuntimeError('Calibration needs both classes')
    c=LogisticRegression(C=1.,solver='lbfgs',max_iter=500).fit(logit(raw_cal).reshape(-1,1),ycal)
    p=c.predict_proba(logit(raw_test).reshape(-1,1))[:,1]
    return p,{'method':'ridge Platt sigmoid','C':1.,'coefficient':float(c.coef_[0,0]),'intercept':float(c.intercept_[0]),'n_calibration':len(ycal)}
