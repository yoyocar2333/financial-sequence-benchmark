"""CPU-only E3a features, predictable event selection and calendar inference."""
import csv
import io
import math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm

SPLITS={'train':('2012-01-01','2022-12-31'),'val':('2023-01-01','2023-12-31'),'test':('2024-01-01','2025-12-31')}
PAST=(5,20,60,120)
FUTURE=(1,5,20)


def read_pre2026(path):
    # Filter date strings before converting any post-2025 prices into numbers.
    with Path(path).open(newline='') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames
        rows=[row for row in reader if row['Date'][:10]<='2025-12-31']
    buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=fields)
    writer.writeheader();writer.writerows(rows);buffer.seek(0)
    df=pd.read_csv(buffer,parse_dates=['Date'],float_precision='round_trip').set_index('Date').sort_index()
    if not df.index.is_unique:raise ValueError('Duplicate source dates')
    return df


def validate_adjustment(adjusted,raw,require_ohlc=False):
    required=('Open','High','Low','Close') if require_ohlc else ('Close',)
    if any(c not in adjusted for c in required):raise ValueError('Required price columns missing')
    np.testing.assert_allclose(adjusted.Close,raw['Adj Close'],rtol=1e-10)
    for col in ('Open','High','Low'):
        if col in adjusted:np.testing.assert_allclose(adjusted[col],raw[col]*raw['Adj Close']/raw.Close,rtol=1e-8,atol=1e-8)
    cols=[c for c in ('Open','High','Low','Close') if c in adjusted]
    if not (adjusted[cols]>0).all().all():raise ValueError('Invalid nonpositive prices')


def features(stock,qqq,vix,vxn):
    stock=stock.loc[:'2025-12-31'].copy()
    lp=np.log(stock.Close);r=lp.diff()*100
    out=pd.DataFrame(index=stock.index)
    out['close']=stock.Close;out['daily_log_pp']=r
    out['sigma60']=r.rolling(60,min_periods=60).std(ddof=1)
    for h in PAST:
        out[f'past{h}']=100*(lp-lp.shift(h))
        out[f'z{h}']=out[f'past{h}']/(out.sigma60.shift(h)*np.sqrt(h))
    out['long120_ex5']=100*(lp.shift(5)-lp.shift(120))
    out['long120_ex5_z']=out.long120_ex5/(out.sigma60.shift(120)*np.sqrt(115))
    for long in (60,120):
        for short in (5,20):
            out[f'context{long}_ex{short}']=100*(lp.shift(short)-lp.shift(long))
            out[f'context{long}_ex{short}_z']=out[f'context{long}_ex{short}']/(out.sigma60.shift(long)*np.sqrt(long-short))
    out['VIX']=vix.Close.reindex(out.index);out['VXN']=vxn.Close.reindex(out.index)
    out['split']='warmup'
    for split,(a,b) in SPLITS.items():out.loc[a:b,'split']=split
    qlog=np.log(qqq.Close.reindex(out.index))
    out['qqq_daily_log_pp']=qlog.diff()*100
    for h in range(1,21):
        out[f'fwd_log{h}']=100*(lp.shift(-h)-lp)
        out[f'fwd_pct{h}']=100*np.expm1(out[f'fwd_log{h}']/100)
    for h in FUTURE:
        out[f'nextopen_log{h}']=100*(lp.shift(-h)-np.log(stock.Open.shift(-1)))
        out[f'qqq_fwd_log{h}']=100*(qlog.shift(-h)-qlog)
        out[f'label_date{h}']=pd.Series(out.index,index=out.index).shift(-h)
    out['end20']=pd.Series(out.index,index=out.index).shift(-20)
    return out


def fit_thresholds(frame,raw_frame=None):
    train=frame[frame.split=='train']
    result={}
    for h in PAST:
        for kind in ('past','z'):
            col=f'{kind}{h}'
            result[col]={str(q):float(train[col].quantile(q)) for q in (.05,.1,.9,.95)}
    for name in ('VIX','VXN'):result[name+'_median']=float(train[name].median())
    for h in FUTURE:
        a,b=SPLITS['train']
        t=train[(train[f'label_date{h}']<=b)&train[f'fwd_log{h}'].notna()]
        result[f'up_probability{h}']=float((t[f'fwd_log{h}']>0).mean())
    t=train[['daily_log_pp','qqq_daily_log_pp']].dropna()
    alpha,beta=np.linalg.lstsq(np.column_stack([np.ones(len(t)),t.qqq_daily_log_pp]),t.daily_log_pp,rcond=None)[0]
    result['market_model']={'alpha_daily_pp':float(alpha),'beta':float(beta),'n_train':len(t)}
    result['training_feature_n']=len(train)
    return result


def eligible(frame,split):
    a,b=SPLITS[split]
    needed=[f'z{h}' for h in PAST]+['long120_ex5_z','VIX','VXN','fwd_log20']
    mask=(frame.index>=a)&(frame.index<=b)&(frame.end20<=b)&frame[needed].notna().all(axis=1)
    return frame.loc[mask].copy()


def thin(mask,cooldown):
    mask=np.asarray(mask,bool);selected=np.zeros(len(mask),bool);last=-cooldown
    for i in np.flatnonzero(mask):
        if i-last>=cooldown:selected[i]=True;last=i
    return selected


def event_mask(frame,thresholds,past=5,side=1,kind='raw',q=.1):
    key=f'z{past}' if kind=='z' else f'past{past}'
    if kind=='sigma2':mask=side*frame[f'z{past}'].to_numpy()>=2
    else:
        cut=thresholds[key][str(1-q) if side==1 else str(q)]
        mask=(frame[key].to_numpy()>=cut) if side==1 else (frame[key].to_numpy()<=cut)
    return mask & (side*frame[f'past{past}'].to_numpy()>0)


def outcomes(frame,side,h,past=5,variant='close',thresholds=None):
    log=frame[f'fwd_log{h}'].to_numpy()
    if variant=='nextopen':log=frame[f'nextopen_log{h}'].to_numpy()
    if variant=='market_excess':
        m=thresholds['market_model']
        log=log-h*m['alpha_daily_pp']-m['beta']*frame[f'qqq_fwd_log{h}'].to_numpy()
    pct=100*np.expm1(log/100);signed=-side*log
    return {'forward_log_pp':log,'forward_pct':pct,'reversal':(signed>1e-12).astype(float),
            'continuation':(signed<-1e-12).astype(float),'flat':(np.abs(signed)<=1e-12).astype(float),
            'countertrend_log_pp':signed,'positive_reversal_log_pp':np.maximum(signed,0),
            'full_retracement':(signed>=np.abs(frame[f'past{past}'].to_numpy())).astype(float),
            'substantial_reversal':(signed>.5*frame.sigma60.to_numpy()*np.sqrt(h)).astype(float),
            'retracement_fraction':signed/np.maximum(np.abs(frame[f'past{past}'].to_numpy()),1e-9)}


def describe(mask,y):
    mask=np.asarray(mask,bool);n=int(mask.sum())
    result={'n_events':n}
    for key,values in y.items():result[key+'_mean']=float(np.mean(values[mask])) if n else np.nan
    if n:
        result['forward_pct_median']=float(np.median(y['forward_pct'][mask]))
        reversal=mask&(y['reversal']>0)
        result['reversal_only_magnitude_pct']=float(np.abs(y['forward_pct'][reversal]).mean()) if reversal.any() else np.nan
    return result


def holm(pvalues):
    p=np.asarray(pvalues,float);p=np.where(np.isfinite(p),p,1.)
    order=np.argsort(p,kind='stable');out=np.empty(len(p))
    out[order]=np.minimum(1,np.maximum.accumulate(p[order]*(len(p)-np.arange(len(p)))))
    return out


def calendar_counts(n,length,reps=4999,seed=20261021):
    rng=np.random.default_rng(seed)
    starts=rng.integers(0,n,(reps,math.ceil(n/length)))
    ix=((starts[:,:,None]+np.arange(length))%n).reshape(reps,-1)[:,:n]
    return np.stack([np.bincount(row,minlength=n) for row in ix]).astype(float)


def contrast(a,ya,b,yb,counts,lag=60,min_n=10):
    """Conditional mean difference + full-calendar ratio influence HAC/bootstrap."""
    a=np.asarray(a,float);b=np.asarray(b,float);ya=np.asarray(ya,float);yb=np.asarray(yb,float)
    if not (len(a)==len(b)==len(ya)==len(yb)) or not np.isfinite(ya).all() or not np.isfinite(yb).all():
        raise ValueError('Inference requires a complete finite shared calendar')
    n=len(a);na=int(a.sum());nb=int(b.sum())
    ma=float(a@ya/na) if na else np.nan;mb=float(b@yb/nb) if nb else np.nan
    result={'n_calendar':n,'n_a':na,'n_b':nb,'mean_a':ma,'mean_b':mb,'difference':ma-mb,
            'inference_status':'insufficient_events' if min(na,nb)<min_n else 'OK',
            'hac_p':np.nan,'hac_se':np.nan,'hac_ci_low':np.nan,'hac_ci_high':np.nan,
            'bootstrap_p':np.nan,'bootstrap_ci_low':np.nan,'bootstrap_ci_high':np.nan,
            'bootstrap_valid_fraction':np.nan}
    if min(na,nb)<min_n:return result
    influence=a/(na/n)*(ya-ma)-b/(nb/n)*(yb-mb)
    influence-=influence.mean()
    lrv=float(influence@influence/n)
    for k in range(1,min(lag,n-1)+1):lrv+=2*(1-k/(lag+1))*float(influence[k:]@influence[:-k]/n)
    se=np.sqrt(max(lrv,0)/n);delta=ma-mb
    p=float(2*norm.sf(abs(delta/se))) if se else (1. if abs(delta)<1e-14 else 0.)
    result.update(hac_p=p,hac_se=float(se),hac_ci_low=float(delta-1.95996398454*se),hac_ci_high=float(delta+1.95996398454*se))
    dena=counts@a;denb=counts@b;valid=(dena>0)&(denb>0)
    result['bootstrap_valid_fraction']=float(valid.mean())
    if valid.mean()<.99:
        result['inference_status']='sparse_bootstrap_groups';result['hac_p']=np.nan
        return result
    boot=(counts@(a*ya))[valid]/dena[valid]-(counts@(b*yb))[valid]/denb[valid]
    centered=boot-delta
    result['bootstrap_p']=float((1+np.count_nonzero(np.abs(centered)>=abs(delta)))/(len(boot)+1))
    low,high=np.quantile(boot,[.025,.975])
    result.update(bootstrap_ci_low=float(2*delta-high),bootstrap_ci_high=float(2*delta-low))
    return result
