"""Date-generalized frozen E3c feature formulas. Pure functions, no holdout I/O."""
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


def frame_from_prices(stock, vix, vxn, end='2025-12-31'):
    if pd.Timestamp(end)>pd.Timestamp('2026-12-31'): raise ValueError('Protocol ends in2026')
    s=stock.loc[:end].copy();lp=np.log(s.Close);r=lp.diff()*100
    f=pd.DataFrame(index=s.index)
    for c in ('Open','High','Low','Close','Volume'): f[c]=s[c]
    f['daily_log_pp']=r;f['sigma60']=r.rolling(60,min_periods=60).std(ddof=1)
    for h in (5,20,60,120):
        f[f'past{h}']=100*(lp-lp.shift(h));f[f'z{h}']=f[f'past{h}']/(f.sigma60.shift(h)*np.sqrt(h))
    for long in (60,120):
        for short in (5,20):
            f[f'context{long}_ex{short}']=100*(lp.shift(short)-lp.shift(long))
            f[f'context{long}_ex{short}_z']=f[f'context{long}_ex{short}']/(f.sigma60.shift(long)*np.sqrt(long-short))
    for name,z in (('VIX',vix),('VXN',vxn)):
        f[name]=z.Close.reindex(f.index);f[name+'_Change']=z.Close.pct_change(fill_method=None).reindex(f.index)*100
    for h in (5,20): f[f'MA{h}']=s.Close.rolling(h,min_periods=h).mean()
    f['Volatility_10']=s.Close.rolling(10,min_periods=10).std()
    daily=np.log(s.Close/s.Close.shift(1))
    for h in (5,20): f[f'RV{h}']=100*np.sqrt(252)*daily.rolling(h,min_periods=h).std(ddof=1)
    f['reference_sign']=np.sign(f.past5)
    for h in (1,5,20):
        f[f'nextopen_log{h}']=100*(lp.shift(-h)-np.log(s.Open.shift(-1)))
        f[f'label_date{h}']=pd.Series(f.index,index=f.index).shift(-h)
        f[f'y{h}']=(f.reference_sign*f[f'nextopen_log{h}']<0).astype(np.int8)
    f['end20']=pd.Series(f.index,index=f.index).shift(-20)
    return f


def compact_features(f, cutoffs, scaler_fit_end):
    d=np.where(f.past5>=cutoffs['past5_q90'],1,np.where(f.past5<=cutoffs['past5_q10'],-1,0))
    long=(f.context120_ex5>=0).to_numpy(int);vol=(f.VIX>=cutoffs['VIX_median']).to_numpy(int)
    st={'event':d!=0,'direction':d,'long':long,'vol':vol,'cell':(d+1)*4+long*2+vol,
        'vxn_high':(f.VXN>=cutoffs['VXN_median']).to_numpy()}
    x=pd.DataFrame(index=f.index)
    for h in (5,20,60,120): x[f'past{h}']=f[f'past{h}'];x[f'z{h}']=f[f'z{h}']
    for c in ('context60_ex5_z','context120_ex5_z','sigma60','RV5','RV20','VIX','VXN','VIX_Change','VXN_Change','daily_log_pp'): x[c]=f[c]
    x['reference_sign']=f.reference_sign;x['event_direction']=d;x['long_sign']=2*long-1
    x['conflict']=(d*x.long_sign.to_numpy()<0).astype(float);x['VIX_high']=vol;x['VXN_high']=st['vxn_high'].astype(float)
    x['intraday_pp']=100*np.log(f.Close/f.Open);x['overnight_pp']=100*np.log(f.Open/f.Close.shift(1))
    x['range_pct']=100*(f.High-f.Low)/f.Close;x['close_MA5_pp']=100*np.log(f.Close/f.MA5)
    x['close_MA20_pp']=100*np.log(f.Close/f.MA20);x['volume_relative20']=np.log(f.Volume/f.Volume.rolling(20,min_periods=20).mean())
    for c in (0,1,2,3,8,9,10,11): x[f'event_cell_{c}']=(st['cell']==c).astype(float)
    a=x.to_numpy(float);fit=(f.index>='2012-01-01')&(f.index<=scaler_fit_end)&np.isfinite(a).all(axis=1)
    scaler=StandardScaler().fit(a[fit]);values=scaler.transform(a).astype(np.float32)
    return values,st,{'columns':list(x.columns),'scaler_mean':scaler.mean_.tolist(),'scaler_scale':scaler.scale_.tolist(),'fit_n':int(fit.sum()),'fit_end':scaler_fit_end}
