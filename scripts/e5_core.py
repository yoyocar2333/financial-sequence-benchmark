"""Frozen, causal E5 technical representations and small regime hybrid."""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import e3b_protocol as bp

ROOT=bp.ROOT
OUT=ROOT/'outputs/e5_20261102'
SOURCE=ROOT/'outputs/e3b_20261026'
SEEDS=bp.SEEDS
FINAL=bp.FINAL
FOLDS=bp.FOLDS
CONFIGS=bp.CONFIGS
MODELS=bp.MODELS
TECH=['ma_gap_atr','ma_cross','rsi_center','macd_hist_atr','bb_z','bb_width',
      'range_position20','breakout20','volume_logratio20','breakout_confirmed','adx_scaled','di_balance']
RELATIVE='relative_qqq20'
RULES=['ma20_60','rsi14','macd','bollinger','breakout_volume','relative_strength','rule_hybrid']
HYBRID=['trend_reversal_score','mr_reversal_score','gate','reference_sign','gated_trend','gated_mr']


def wilder(series,n=14):
    a=np.asarray(series,float);out=np.full(len(a),np.nan);buffer=[];state=None
    for i,v in enumerate(a):
        if not np.isfinite(v):buffer=[];state=None;continue
        if state is None:
            buffer.append(v)
            if len(buffer)==n:state=float(np.mean(buffer));out[i]=state
        else:state=(state*(n-1)+v)/n;out[i]=state
    return pd.Series(out,index=series.index)


def indicators(stock,qqq):
    c,h,l,v=stock.Close,stock.High,stock.Low,stock.Volume
    x=pd.DataFrame(index=stock.index)
    ma20=c.rolling(20).mean();ma60=c.rolling(60).mean();sd=c.rolling(20).std(ddof=0)
    true_range=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=wilder(true_range)
    delta=c.diff();gain=wilder(delta.clip(lower=0));loss=wilder((-delta).clip(lower=0))
    rsi=100*gain/(gain+loss)
    rsi=rsi.mask((gain+loss)==0,50)
    macd=c.ewm(span=12,adjust=False,min_periods=12).mean()-c.ewm(span=26,adjust=False,min_periods=26).mean()
    signal=macd.ewm(span=9,adjust=False,min_periods=9).mean()
    upper=h.rolling(20).max().shift(1);lower=l.rolling(20).min().shift(1)
    volume_base=v.rolling(20).mean().shift(1)
    up=h.diff();down=-l.diff()
    plus=wilder(up.where((up>down)&(up>0),0).mask(up.isna()))/atr*100
    minus=wilder(down.where((down>up)&(down>0),0).mask(down.isna()))/atr*100
    dx=100*(plus-minus).abs()/(plus+minus)
    dx=dx.mask((plus+minus)==0,0)
    adx=wilder(dx)
    x['ma_gap_atr']=(ma20-ma60)/atr
    sign=np.sign(ma20-ma60)
    x['ma_cross']=sign.diff().fillna(0)/2
    x['rsi_center']=(rsi-50)/50
    x['macd_hist_atr']=(macd-signal)/atr
    x['bb_z']=(c-ma20)/sd
    x['bb_width']=4*sd/ma20
    x['range_position20']=(c-lower)/(upper-lower)
    x['breakout20']=(c>upper).astype(float)-(c<lower).astype(float)
    x['volume_logratio20']=np.log((v+1)/(volume_base+1))
    x['breakout_confirmed']=x.breakout20*(v/volume_base>=1.5)
    x['adx_scaled']=adx/100
    x['di_balance']=(plus-minus)/100
    q=qqq.Close.reindex(c.index)
    sigma=100*np.log(c/c.shift()).rolling(60).std()
    x[RELATIVE]=100*(np.log(c/c.shift(20))-np.log(q/q.shift(20)))/(sigma*np.sqrt(20))
    x['rsi14']=rsi;x['adx14']=adx;x['atr14']=atr;x['ma20']=ma20;x['ma60']=ma60
    x['bb_upper']=ma20+2*sd;x['bb_lower']=ma20-2*sd
    x['previous_high20']=upper;x['previous_low20']=lower
    x['volume_ratio20']=v/volume_base
    x['trend_weight']=np.where(adx>=25,1.,np.where(adx<20,0.,.5))
    x['regime']=np.where(adx>=25,'trend',np.where(adx<20,'range','transition'))
    return x


def load(ticker):
    f=bp.load_frame(ticker,source=SOURCE)
    s=bp.read_pre2026(SOURCE/'inputs'/f'{ticker}_adjusted_through2025.csv')
    q=bp.read_pre2026(SOURCE/'inputs/QQQ_adjusted_through2025.csv')
    x=indicators(s,q)
    for c in x:f[c]=x[c]
    f.attrs['ticker']=ticker
    return f


def rule_scores(f):
    # Literal threshold rules are distinct from smooth hybrid experts.
    scores=pd.DataFrame(index=f.index)
    scores['ma20_60']=np.sign(f.ma_gap_atr)
    scores['rsi14']=np.where(f.rsi14<30,1.,np.where(f.rsi14>70,-1.,0.))
    scores['macd']=np.sign(f.macd_hist_atr)
    scores['bollinger']=np.where(f.bb_z<-2,1.,np.where(f.bb_z>2,-1.,0.))
    scores['breakout_volume']=f.breakout_confirmed
    scores['relative_strength']=np.sign(f[RELATIVE])
    trend=(np.tanh(f.ma_gap_atr/3)+np.tanh(3*f.macd_hist_atr)+f.breakout_confirmed+np.tanh(f[RELATIVE]))/4
    mr=-(np.tanh((f.rsi14-50)/20)+np.tanh(f.bb_z/2))/2
    scores['trend_expert']=trend;scores['mr_expert']=mr
    scores['rule_hybrid']=f.trend_weight*trend+(1-f.trend_weight)*mr
    return scores


def hybrid_features(f):
    r=rule_scores(f);x=pd.DataFrame(index=f.index)
    x['trend_reversal_score']=-f.reference_sign*r.trend_expert
    x['mr_reversal_score']=-f.reference_sign*r.mr_expert
    x['gate']=f.trend_weight;x['reference_sign']=f.reference_sign
    x['gated_trend']=x.gate*x.trend_reversal_score
    x['gated_mr']=(1-x.gate)*x.mr_reversal_score
    return x


def transform(f,arm,cutoff):
    if arm in ('H','H0'):
        cols=HYBRID if arm=='H' else HYBRID[:4]
        x=hybrid_features(f)[cols]
        fit=(f.index>='2012-01-01')&(f.index<=cutoff)&np.isfinite(x).all(axis=1)
        sc=StandardScaler().fit(x.loc[fit]);values=sc.transform(x).astype(np.float32)
        return values,{'columns':cols,'mean':sc.mean_.tolist(),'scale':sc.scale_.tolist(),'fit_end':cutoff,'representation':'six/four current summaries from same historical data; no extra information'}
    base,meta=bp.feature_matrix(f,'B',cutoff)
    if arm=='B':return base,meta
    cols=[RELATIVE] if arm=='C' else TECH+[RELATIVE]
    x=f[cols];fit=(f.index>='2012-01-01')&(f.index<=cutoff)&np.isfinite(x).all(axis=1)
    sc=StandardScaler().fit(x.loc[fit]);extra=sc.transform(x).astype(np.float32)
    return np.concatenate([base,extra],axis=1),{'base':meta,'extra_columns':cols,'extra_mean':sc.mean_.tolist(),'extra_scale':sc.scale_.tolist(),'feature_fit_end':cutoff}


def block_arrays(f,arm,block):
    x,meta=transform(f,arm,block['fit_end'])
    ranges={'fit':('2012-01-01',block['fit_end']),'stop':(block['stop_start'],block['stop_end'])}
    if 'eval_start' in block:ranges['eval']=(block['eval_start'],block['eval_end'])
    else:ranges.update(cal=(block['cal_start'],block['cal_end']),test=(block['test_start'],block['test_end']))
    ids={k:bp.indices(f,a,b) for k,(a,b) in ranges.items()}
    xs={k:(x[ii,None,:] if arm in ('H','H0') else bp.windows(x,ii)) for k,ii in ids.items()}
    if not all(np.isfinite(v).all() for v in xs.values()):raise ValueError('E5 extras change the common finite calendar')
    return {k:(v,f.y5.iloc[ids[k]].to_numpy()) for k,v in xs.items()},ids,meta


def states(f,thresholds):
    up=f.past5>=thresholds['past5']['0.9'];down=f.past5<=thresholds['past5']['0.1']
    cell=(f.reference_sign>0).astype(int)*4+(f.context120_ex5>0).astype(int)*2+(f.VIX>=thresholds['VIX_median']).astype(int)
    return up.to_numpy(),down.to_numpy(),cell.to_numpy()


PLAN={
 'version':'E5-1.0','locked_before_new_fits':True,
 'scope':'Exploratory already-viewed 2024-2025 only. No2026 prices/news loaded; E3c sealed protocol unchanged. This is NOT preregistered confirmation.',
 'task':'h5 reversal, same next adjusted Open to day t+5 adjusted Close, known past5 sign; direction probability is algebraically mapped, no flat test returns',
 'secondary_scope':'No new h1/h20 or magnitude fits. Event, conflict, ADX and volatility subgroups descriptive. Direction probability is mapped from reversal, not an independently trained direction task.',
 'feature_B':bp.BASE+bp.EXTRA,'feature_T_extra':TECH+[RELATIVE],'feature_C_extra':[RELATIVE],
 'technical_definitions':{'MA':'SMA20 vs SMA60, cross flag from sign change','RSI':'Wilder14 seeded with first14 mean;70/30 fixed','MACD':'EMA12-EMA26; signal EMA9; pandas adjust=False, 2010 warmup','Bollinger':'SMA20 +/-2 population SD (ddof0)','support_resistance':'prior20 rolling High max/Low min, shifted1; close breakout','volume':'current Volume/prior20 mean>=1.5, prior window excludes today','ADX':'Wilder14 ATR,DM,DX and ADX; >=25 trend, <20 range,20-25 transition','relative':'20day stock log return minus QQQ, scaled stock sigma60*sqrt20'},
 'hypothesis':'Compact investor representations may help finite models; deterministic transformations do not create independent price information; QQQ control isolates genuinely additional source.',
 'rules':RULES,'rule_probabilities':'fixed score s in[-1,1], p_up=sigmoid(2s), mapped to reversal with past5 sign; C1 ridge Platt2023H2 for comparison; save literal raw AND calibrated and calibration slopes. Negative slope can invert rule; report it.',
 'hybrid':'Fixed ADX gate 0/.5/1 mixes smooth momentum and MR; learned six-feature ridge Logistic adds gated expert interactions; four-feature ungated control includes same experts/gate/reference; C=.001,.01,.1. No complex hybrid escalation based on test scores.',
 'fairness':'T all5 models same 60x51 observations, C same60x39 for Logistic/XGB. B existing60x38 E3b completed predictions/CV reused with hashes; no old model overwritten/retrained. Same3 candidates x same3 folds, seed42 selection. Compact hybrid is information compression, not an equal-capacity architectural comparison.',
 'folds':FOLDS,'split':FINAL,'purge':'all blocks t+20 stays in block and full60 history; identical482 test dates per stock',
 'search_configs':CONFIGS,'new_CV_fits':162,'new_final_fits':90,'reused_B_final_fits':50,'seeds':list(SEEDS),
 'training':'Reuse unchanged E3b fitting module: neural batch64,max24,patience4,AdamW,BCE,clip1,dropout.1; trees300,max earlystop25; CPU2 threads. Input width only changes. One GPU process,allocator.10,duty.50,>=2GiB admission,actualCUDA errors stop own queue, no external-growth stop.',
 'calibration':'Same E3b unconstrained C1 ridge Platt2023H2; all primary metrics calibrated, raw retained. No test-based choice between calibration methods.',
 'selection':'Only expanding CV raw Brier selects model configuration; all selection locked before writing new test predictions. Baseline old B configs frozen, not chosen from test ranking.',
 'primary_inference':'8 tests = 2stocks x4 architectures T vs B; positive=Brier_reference-Brier_candidate. seed losses averaged on each date, HAC20 & circular block20 bootstrap9999, each Holm8; block60 sensitivity. Raw p and CIs retained, significance requires both corrected p<.05 and positive gain.',
 'secondary_families':{'control':4,'architecture':12,'hybrid':12,'rules':14},
 'secondary_detail':'control T vs C for Logistic/XGB; architecture all6pairs in T; hybrid_H vs H0,rule_hybrid,momentum20,mean_reversion5,state_prior,logistic_B; 7rules vs cal_prior. Separate Holm families plus globalHolm50 over primary+secondary. No claim total research selection controlled.',
 'ranking':'Events same cells = past5 direction x long120ex5 sign x VIX high. Per-seed concordance averaged before calendar bootstrap9999, Holm12 for 4T+H+rule_hybrid x2stocks; never multiply n by seeds.',
 'regime_stability':'Regime frequencies, one-day switching, persistence and ADX20/25 transition band; descriptive, no threshold winner selected.',
 'backtest':'Secondary long/cash only, same h5 nextOpen-to-t+5Close; signals every5 trading sessions for5 fixed offset schedules, no overlapping positions/leverage. p_up>=.55 fixed. Costs each side fee5bps+slippage5bps primary, total5/20bps sensitivities; daily NAV, turnover,exposure,maxDD; cash0, adjusted-price proxy, no shorting. BuyHold samefirstentry/lastexit and soft momentum20. All schedules and costs reported, no best-offset selection; investment metrics not prediction evidence.',
 'independent_validation':'E5 not added to E3c2026 protocol; later E5 holdout requires separate future preregistration and access audit.'
}
