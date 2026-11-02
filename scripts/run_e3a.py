"""Reproducible CPU event study. Refuse overwrite; never evaluate 2026."""
import argparse
import datetime as dt
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import zipfile
import numpy as np
import pandas as pd

from e3a_core import (SPLITS,PAST,FUTURE,read_pre2026,features,fit_thresholds,eligible,
                     thin,event_mask,outcomes,describe,calendar_counts,contrast,holm)
from e3a_core import validate_adjustment

ROOT=Path(__file__).resolve().parents[1]
MARKET=ROOT/'data/market_20261019'
PREVIOUS=ROOT/'outputs/mamba_multiseed_20261020'
OLD=ROOT/'outputs/mamba_low_resource_20261019_seed42'
LOG=logging.getLogger('E3a')
PREDICTION_SNAPSHOT=None


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path,data):
    path=Path(path);path.write_text(json.dumps(data,indent=2,ensure_ascii=False,default=str)+'\n')


def save(rows,path):
    frame=pd.DataFrame(rows);frame.to_csv(path,index=False);return frame


def protect_manifest():
    from multiseed_common import check_protected
    check_protected()
    files={}
    for folder in (MARKET,OLD,PREVIOUS):
        for path in folder.rglob('*'):
            if path.is_file():files[str(path.relative_to(ROOT))]=sha(path)
    return files


def verify_manifest(files):
    for name,digest in files.items():
        if sha(ROOT/name)!=digest:raise RuntimeError('Protected previous input/result changed: '+name)


def setup(out):
    if out.exists():raise FileExistsError('Refuse overwrite: '+str(out))
    out.mkdir(parents=True)
    for name in ('inputs','tables','figures','code','logs'): (out/name).mkdir()
    handler=logging.FileHandler(out/'logs/e3a.log');handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    LOG.addHandler(handler);LOG.addHandler(logging.StreamHandler());LOG.setLevel(logging.INFO)
    LOG.info('CPU E3a starting; all post2025 observations excluded')
    protected=protect_manifest();write_json(out/'inputs/protected_previous_files.json',protected)
    protocol=json.loads((ROOT/'E3A_PROTOCOL.json').read_text())
    write_json(out/'analysis_plan.json',{**protocol,'frozen_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'source_protocol_sha256':sha(ROOT/'E3A_PROTOCOL.json')})
    provenance=json.loads((MARKET/'provenance.json').read_text())
    write_json(out/'inputs/original_snapshot_provenance.json',provenance)
    sources={};raw={};audit=[]
    for name in ('AAPL','TSLA','QQQ','VIX','VXN'):
        p=MARKET/f'{name}.csv';rp=MARKET/'raw'/f'{name}.csv';info=provenance['symbols'][name]
        if sha(p)!=info['adjusted_sha256'] or sha(rp)!=info['raw_sha256']:raise RuntimeError('Market hash mismatch')
        sources[name]=read_pre2026(p);raw[name]=read_pre2026(rp)
        sources[name].to_csv(out/'inputs'/f'{name}_adjusted_through2025.csv')
        raw[name].to_csv(out/'inputs'/f'{name}_raw_through2025.csv')
        a=sources[name];r=raw[name]
        validate_adjustment(a,r,require_ohlc=name in ('AAPL','TSLA','QQQ'))
        calendar=sources.get('QQQ',read_pre2026(MARKET/'QQQ.csv')).index
        expected=calendar[(calendar>=a.index.min())&(calendar<=a.index.max())]
        missing=expected.difference(a.index)
        if len(missing):raise RuntimeError('Missing sessions: '+name)
        audit.append({'symbol':name,'n_used':len(a),'first':a.index.min().date(),'last':a.index.max().date(),
            'missing_vs_qqq':len(missing),'dividend_days':int((r.get('Dividends',pd.Series(0,index=r.index))!=0).sum()),
            'split_days':int((r.get('Stock Splits',pd.Series(0,index=r.index))!=0).sum()),'source_sha256':sha(p),
            'used_adjusted_sha256':sha(out/'inputs'/f'{name}_adjusted_through2025.csv')})
    save(audit,out/'tables/data_audit.csv')
    frames={};thresholds={};rawframes={};rawthresholds={}
    for ticker in ('AAPL','TSLA'):
        frames[ticker]=features(sources[ticker],sources['QQQ'],sources['VIX'],sources['VXN'])
        thresholds[ticker]=fit_thresholds(frames[ticker])
        rawframes[ticker]=features(raw[ticker],raw['QQQ'],sources['VIX'],sources['VXN'])
        rawthresholds[ticker]=fit_thresholds(rawframes[ticker])
        frames[ticker].to_csv(out/'tables'/f'{ticker}_daily_features_labels.csv')
    write_json(out/'training_thresholds.json',thresholds)
    write_json(out/'training_thresholds_rawclose_sensitivity.json',rawthresholds)
    env={'analysis_python':sys.version,'packages':{p:importlib.metadata.version(p) for p in ('numpy','pandas','scipy')},
         'CUDA_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES'),'GPU_used':False,
         'plot_python':'/usr/bin/python3','command':sys.argv}
    write_json(out/'environment.json',env)
    for name in ('e3a_core.py','run_e3a.py','plot_e3a.py','replay_e3a.py','e3a_interpretation.py'):
        p=ROOT/'scripts'/name
        (out/'code'/name).write_bytes(p.read_bytes())
    (out/'code/E3A_PROTOCOL.json').write_bytes((ROOT/'E3A_PROTOCOL.json').read_bytes())
    (out/'code/test_e3a.py').write_bytes((ROOT/'tests/test_e3a.py').read_bytes())
    return protected,frames,thresholds,rawframes,rawthresholds


def groups(frame,thresholds):
    long=frame.long120_ex5.to_numpy()
    vh=frame.VXN.to_numpy()>=thresholds['VXN_median'];ih=frame.VIX.to_numpy()>=thresholds['VIX_median']
    return {'all':np.ones(len(frame),bool),'long_up':long>0,'long_down':long<0,
        'VXN_high':vh,'VXN_low':~vh,'VIX_high':ih,'VIX_low':~ih,
        'both_high':vh&ih,'both_low':~vh&~ih,'mixed_vol':vh!=ih}


def event_descriptions(frames,thresholds,out):
    rows=[];catalog=[];combinations=[];paths=[];counts=[]
    for ticker,frame in frames.items():
        th=thresholds[ticker]
        for split in SPLITS:
            f=eligible(frame,split);g=groups(f,th)
            counts.append({'ticker':ticker,'split':split,'n_eligible':len(f),'first':f.index.min().date(),
                           'last':f.index.max().date(),'last_label20':f.end20.max().date()})
            for past in PAST:
                for kind in ('raw','z'):
                    for side in (-1,1):
                        mask=event_mask(f,th,past,side,kind)
                        chosen={h:thin(mask,h) for h in FUTURE}
                        for i in np.flatnonzero(mask):
                            r={'ticker':ticker,'split':split,'date':f.index[i].strftime('%Y-%m-%d'),
                               'past_horizon':past,'kind':kind,'side':side,'past_log_pp':f[f'past{past}'].iloc[i],
                               'z':f[f'z{past}'].iloc[i],'VIX':f.VIX.iloc[i],'VXN':f.VXN.iloc[i],
                               'long120_ex5':f.long120_ex5.iloc[i]}
                            for h in FUTURE:
                                y=outcomes(f,side,h,past)
                                r.update({f'selected_h{h}':bool(chosen[h][i]),f'label_date{h}':f[f'label_date{h}'].iloc[i].strftime('%Y-%m-%d'),
                                    f'fwd_pct{h}':y['forward_pct'][i],f'reversal{h}':y['reversal'][i],
                                    f'full_retracement{h}':y['full_retracement'][i]})
                            catalog.append(r)
                        for h in FUTURE:
                            y=outcomes(f,side,h,past)
                            usegroups=g if past==5 else {k:v for k,v in g.items() if not k.startswith('long_')}
                            for sample,selected in (('nonoverlap',chosen[h]),('all_candidates',mask)):
                                for name,m in usegroups.items():
                                    rows.append({'ticker':ticker,'split':split,'past_horizon':past,'kind':kind,'side':side,
                                                 'horizon':h,'sample':sample,'group':name,**describe(selected&m,y)})
                        if past==5 and kind=='raw':
                            anchor=chosen[20]
                            for h in range(1,21):
                                log=f[f'fwd_log{h}'].to_numpy()
                                paths.append({'ticker':ticker,'split':split,'side':side,'day':h,'n_events':int(anchor.sum()),
                                    'cumulative_pct_mean':float((100*np.expm1(log[anchor]/100)).mean()) if anchor.any() else np.nan,
                                    'countertrend_log_mean':float((-side*log[anchor]).mean()) if anchor.any() else np.nan})
            # A single calendar grid per horizon, partitioned into trend states.
            for short in (5,20):
                for long in (60,120):
                    sz=f[f'z{short}'].to_numpy();lz=f[f'context{long}_ex{short}_z'].to_numpy()
                    ss=np.where(sz>.5,1,np.where(sz<-.5,-1,0));ls=np.where(lz>.5,1,np.where(lz<-.5,-1,0))
                    for h in FUTURE:
                        grid=thin(np.ones(len(f),bool),h)
                        for a in (-1,0,1):
                            for b in (-1,0,1):
                                m=grid&(ss==a)&(ls==b);y=outcomes(f,1 if a>=0 else -1,h,short)
                                combinations.append({'ticker':ticker,'split':split,'short_horizon':short,'long_horizon':long,
                                    'short_state':a,'long_state':b,'horizon':h,**describe(m,y)})
            LOG.info('Event descriptions %s %s: %d eligible dates',ticker,split,len(f))
    save(rows,out/'tables/event_statistics.csv');save(catalog,out/'tables/events.csv')
    save(combinations,out/'tables/trend_combinations.csv');save(paths,out/'tables/event_paths.csv')
    save(counts,out/'tables/split_eligibility.csv')


def direction_rules(frames,thresholds,out):
    rows=[];daily={}
    for ticker,frame in frames.items():
        th=thresholds[ticker]
        for split in SPLITS:
            f=eligible(frame,split)
            tails=event_mask(f,th,5,1)|event_mask(f,th,5,-1)
            conflict=tails&(f.past5.to_numpy()*f.long120_ex5.to_numpy()<0)
            for h in FUTURE:
                majority=1 if th[f'up_probability{h}']>=.5 else -1
                momentum=np.sign(f.past20.to_numpy());momentum[momentum==0]=majority
                mr=-np.sign(f.past5.to_numpy());mr[mr==0]=majority
                gate=np.full(len(f),majority,dtype=float);gate[conflict]=np.sign(f.long120_ex5.to_numpy()[conflict])
                truth=np.sign(f[f'fwd_log{h}'].to_numpy());nonflat=truth!=0
                rules={'train_majority':np.full(len(f),majority),'momentum20':momentum,'mean_reversion5':mr,'conflict_gate':gate}
                hits={}
                for name,guess in rules.items():
                    hit=(guess==truth).astype(float);hits[name]=hit
                    recalls=[float((guess[truth==s]==s).mean()) for s in (-1,1) if (truth==s).any()]
                    rows.append({'ticker':ticker,'split':split,'horizon':h,'rule':name,'n_dates':len(f),
                        'accuracy':float(hit.mean()),'balanced_accuracy':float(np.mean(recalls)),
                        'n_flats':int((~nonflat).sum()),'predicted_up_fraction':float((guess>0).mean()),
                        'conflict_gate_coverage':float(conflict.mean()),'training_up_probability':th[f'up_probability{h}']})
                if split=='test':daily[ticker,h]=hits
    save(rows,out/'tables/direction_baselines.csv');return daily


def planned_tests(frames,thresholds,rules,out):
    rows=[];cache={}
    def cc(n,length):
        if (n,length) not in cache:cache[n,length]=calendar_counts(n,length)
        return cache[n,length]
    def add(meta,a,ya,b,yb,length=60):
        rows.append({**meta,'bandwidth':length,**contrast(a,ya,b,yb,cc(len(a),length),length)})
    for ticker,frame in frames.items():
        f=eligible(frame,'test');th=thresholds[ticker];n=len(f);all_=np.ones(n,bool)
        for side in (-1,1):
            mask=event_mask(f,th,5,side)
            for h in FUTURE:
                selected=thin(mask,h);conflict=selected&(side*f.long120_ex5.to_numpy()<0)
                aligned=selected&(side*f.long120_ex5.to_numpy()>0)
                y=outcomes(f,side,h)
                for metric in ('reversal','countertrend_log_pp'):
                    for label,a,b in (('event_vs_unconditional',selected,all_),('conflict_vs_aligned',conflict,aligned)):
                        meta={'family':'primary','ticker':ticker,'side':side,'horizon':h,'metric':metric,'comparison':label}
                        for length in (60,20,120):add(meta,a,y[metric],b,y[metric],length)
                for index in ('VIX','VXN'):
                    high=f[index].to_numpy()>=th[index+'_median']
                    add({'family':'volatility','ticker':ticker,'side':side,'horizon':h,'metric':'reversal','comparison':index+'_high_minus_low'},
                        selected&high,y['reversal'],selected&~high,y['reversal'])
        for h in FUTURE:
            for baseline in ('train_majority','momentum20','mean_reversion5'):
                add({'family':'rules','ticker':ticker,'side':0,'horizon':h,'metric':'accuracy','comparison':'conflict_gate_minus_'+baseline},
                    all_,rules[ticker,h]['conflict_gate'],all_,rules[ticker,h][baseline])
        LOG.info('Planned statistical comparisons prepared: %s',ticker)
    return rows,cache


def sensitivity(frames,thresholds,rawframes,rawthresholds,out):
    rows=[]
    specs=['primary','all_candidates','cooldown20','q05q95','sigma2','normalized_quantiles','naive_context','nextopen','market_excess','raw_close']
    for ticker,frame in frames.items():
        for name in specs:
            f=eligible(rawframes[ticker] if name=='raw_close' else frame,'test')
            th=rawthresholds[ticker] if name=='raw_close' else thresholds[ticker]
            for side in (-1,1):
                m=event_mask(f,th,5,side,kind='sigma2' if name=='sigma2' else 'z' if name=='normalized_quantiles' else 'raw',q=.05 if name=='q05q95' else .1)
                for h in FUTURE:
                    selected=m if name=='all_candidates' else thin(m,20 if name=='cooldown20' else h)
                    variant=name if name in ('nextopen','market_excess') else 'close'
                    y=outcomes(f,side,h,variant=variant,thresholds=th)
                    long=f.past120.to_numpy() if name=='naive_context' else f.long120_ex5.to_numpy()
                    for group,g in [('all',np.ones(len(f),bool)),('conflict',side*long<0),('aligned',side*long>0)]:
                        s=selected&g;desc=describe(s,y)
                        desc['unconditional_reversal']=float(y['reversal'].mean())
                        desc['reversal_probability_gain']=desc['reversal_mean']-desc['unconditional_reversal']
                        rows.append({'ticker':ticker,'variant':name,'side':side,'horizon':h,'group':group,**desc})
        f=eligible(frame,'test');th=thresholds[ticker]
        for year in (2024,2025):
            for side in (-1,1):
                m=event_mask(f,th,5,side)
                for h in FUTURE:
                    selected=thin(m,h)&(f.index.year==year);y=outcomes(f,side,h)
                    rows.append({'ticker':ticker,'variant':f'year{year}','side':side,'horizon':h,'group':'all',**describe(selected,y),
                                 'unconditional_reversal':float(y['reversal'][f.index.year==year].mean())})
    save(rows,out/'tables/robustness.csv')


def mamba_diagnostics(frames,thresholds,out,tests,cache):
    rows=[];dailyrows=[];summary=[];alignment=[]
    for ticker,frame in frames.items():
        f=eligible(frame,'test');th=thresholds[ticker];n=len(f)
        up=event_mask(f,th,5,1);down=event_mask(f,th,5,-1);shock=up|down
        sign=np.sign(f.past5.to_numpy());future=f.fwd_log1.to_numpy()
        anchors=thin(shock,20);age=np.full(n,10000);last=-10000
        for i in range(n):
            if anchors[i]:last=i
            age[i]=i-last
        masks={'all':np.ones(n,bool),'shock_up':up,'shock_down':down,
               'conflict_up':up&(f.long120_ex5.to_numpy()<0),'conflict_down':down&(f.long120_ex5.to_numpy()>0),
               'expost_reversal':shock&(sign*future<0),'expost_continuation':shock&(sign*future>0),
               'phase_event0':age==0,'phase_days1_5':(age>=1)&(age<=5),
               'phase_days6_19':(age>=6)&(age<=19),'phase_away':age>=20,'no_shock':~shock}
        train=frame[(frame.split=='train')&(frame.label_date1<='2022-12-31')]
        trainmean=float(train.fwd_log1.abs().mean())
        rolling=frame.daily_log_pp.abs().rolling(20,min_periods=20).mean().reindex(f.index).to_numpy()
        expected_dates=None;arm_losses={};arm_metrics={};common=None
        for arm in ('E1','E2b'):
            per=[];losses=[];valids=[]
            for seed in (42,43,44,45,46):
                root=OLD if seed==42 else PREVIOUS/f'seed_{seed}'
                path=root/f'{ticker}_{arm}'/f'{ticker}_{arm}'/'predictions.csv'
                if PREDICTION_SNAPSHOT is not None:path=PREDICTION_SNAPSHOT/f'{ticker}_{arm}_seed{seed}.csv'
                saved=out/'inputs/mamba_predictions'/f'{ticker}_{arm}_seed{seed}.csv'
                saved.parent.mkdir(exist_ok=True)
                saved.write_bytes(path.read_bytes())
                pred=pd.read_csv(path,parse_dates=['date','label_date']).set_index('date')
                if expected_dates is None:expected_dates=pred.index
                if not pred.index.equals(expected_dates):raise RuntimeError('Mamba seed/arm calendar mismatch')
                if set(pred['split'])!={'test'} or set(pred.seed)!={seed} or set(pred.arm)!={arm}:raise RuntimeError('Wrong prediction metadata')
                actual=frame.fwd_log1.abs().reindex(pred.index)
                np.testing.assert_allclose(pred.actual_mag_pct,actual,rtol=1e-10,atol=1e-10)
                if not np.array_equal(pred.label_date.to_numpy(),frame.label_date1.reindex(pred.index).to_numpy()):
                    raise RuntimeError('Mamba label date mismatch')
                p=pred.reindex(f.index);valid=p.forecast_mag_pct.notna().to_numpy()
                if common is None:common=valid
                if not np.array_equal(common,valid):raise RuntimeError('Different Mamba availability')
                truth=p.actual_mag_pct.to_numpy();forecast=p.forecast_mag_pct.to_numpy();error=forecast-truth
                losses.append(np.nan_to_num(np.abs(error),nan=0));valids.append(valid)
                for group,mask in masks.items():
                    use=mask&valid;count=int(use.sum())
                    row={'ticker':ticker,'arm':arm,'seed':seed,'group':group,'n_dates':count,
                        'mae_pp':float(np.abs(error[use]).mean()) if count else np.nan,
                        'rmse_pp':float(np.sqrt(np.square(error[use]).mean())) if count else np.nan,
                        'bias_pp':float(error[use].mean()) if count else np.nan,
                        'actual_magnitude_mean':float(truth[use].mean()) if count else np.nan,
                        'forecast_magnitude_mean':float(forecast[use].mean()) if count else np.nan,
                        'rolling20_mae':float(np.abs(rolling[use]-truth[use]).mean()) if count else np.nan,
                        'trainmean_mae':float(np.abs(trainmean-truth[use]).mean()) if count else np.nan}
                    rows.append(row);per.append(row)
                for i in np.flatnonzero(valid):
                    dailyrows.append({'ticker':ticker,'arm':arm,'seed':seed,'date':f.index[i].strftime('%Y-%m-%d'),
                        'label_date':f.label_date1.iloc[i].strftime('%Y-%m-%d'),'actual_magnitude':truth[i],
                        'forecast_magnitude':forecast[i],'absolute_error':abs(error[i]),'error':error[i],
                        'shock_up':bool(up[i]),'shock_down':bool(down[i]),
                        'conflict':bool(shock[i] and sign[i]*f.long120_ex5.iloc[i]<0),
                        'expost_reversal':bool(shock[i] and sign[i]*future[i]<0),'postevent_age':int(age[i])})
                alignment.append({'ticker':ticker,'arm':arm,'seed':seed,'original_prediction_n':len(pred),
                    'e3a_common_calendar_n':n,'matched_n':int(valid.sum()),'excluded_original_dates':len(pred)-int(valid.sum()),
                    'all_original_targets_verified':True,'source_sha256':sha(path)})
            arm_losses[arm]=np.mean(losses,axis=0)
            arm_metrics[arm]=pd.DataFrame(per)
        for arm,m in arm_metrics.items():
            for group,g in m.groupby('group',sort=False):
                r={'ticker':ticker,'arm':arm,'group':group,'n_dates':int(g.n_dates.iloc[0]),'seed_count':5}
                for col in ('mae_pp','rmse_pp','bias_pp','actual_magnitude_mean','forecast_magnitude_mean','rolling20_mae','trainmean_mae'):
                    r[col+'_mean']=float(g[col].mean());r[col+'_seed_sd']=float(g[col].std(ddof=1))
                summary.append(r)
        d=arm_losses['E1']-arm_losses['E2b']
        if (n,60) not in cache:cache[n,60]=calendar_counts(n,60)
        for group in ('shock_up','shock_down','conflict_up','conflict_down'):
            m=masks[group]&common
            tests.append({'family':'mamba','ticker':ticker,'side':0,'horizon':1,'metric':'mae_E1_minus_E2b',
                'comparison':group,'bandwidth':60,**contrast(m,d,common,np.zeros(n),cache[n,60],60)})
        LOG.info('Mamba diagnostics %s: %d common calendar dates, %d observed predictions',ticker,n,int(common.sum()))
    save(rows,out/'tables/mamba_event_metrics_per_seed.csv')
    save(summary,out/'tables/mamba_event_metrics.csv')
    save(dailyrows,out/'tables/mamba_daily_errors.csv')
    save(alignment,out/'tables/mamba_alignment_audit.csv')


def adjust_tests(rows,out):
    df=pd.DataFrame(rows);main=df.bandwidth==60
    if len(df[main])!=98 or len(df[main&(df.family=='primary')])!=48:raise RuntimeError('Planned test family size changed')
    for length in (60,20,120):
        for family in ('primary','volatility','rules','mamba'):
            select=(df.bandwidth==length)&(df.family==family)
            if select.any():
                for method in ('hac','bootstrap'):
                    df.loc[select,method+'_p_holm_family']=holm(df.loc[select,method+'_p'])
    for method in ('hac','bootstrap'):df.loc[main,method+'_p_holm_global98']=holm(df.loc[main,method+'_p'])
    df['primary_decision']=(df.bandwidth==60)&(df.hac_p_holm_global98<.05)&(df.inference_status=='OK')
    df.to_csv(out/'tables/statistical_tests.csv',index=False)
    return df


def table(frame,columns,formats=None):
    formats=formats or {};lines=['|'+'|'.join(columns.values())+'|','|'+'|'.join(['---']*len(columns))+'|']
    for _,r in frame.iterrows():
        cells=[]
        for key in columns:
            value=r[key]
            if pd.isna(value):cells.append('—')
            elif key in formats:cells.append(formats[key](value))
            elif isinstance(value,(float,np.floating)):cells.append(f'{value:.4f}')
            else:cells.append(str(value))
        lines.append('|'+'|'.join(cells)+'|')
    return '\n'.join(lines)


def write_report(out,thresholds,tests):
    stats=pd.read_csv(out/'tables/event_statistics.csv');elig=pd.read_csv(out/'tables/split_eligibility.csv')
    mamba=pd.read_csv(out/'tables/mamba_event_metrics.csv');rules=pd.read_csv(out/'tables/direction_baselines.csv')
    primary=tests[(tests.bandwidth==60)&(tests.family=='primary')]
    vol=pd.read_csv(out/'tables/AAPL_daily_features_labels.csv',usecols=['split','VIX','VXN'])
    train_vol_corr=vol.loc[vol['split']=='train',['VIX','VXN']].corr().iloc[0,1]
    shock=primary[(primary.comparison=='event_vs_unconditional')&(primary.metric=='reversal')].copy()
    conflicts=primary[(primary.comparison=='conflict_vs_aligned')&(primary.metric=='reversal')].copy()
    significant=tests[(tests.bandwidth==60)&tests.primary_decision]
    th=[]
    for ticker,t in thresholds.items():
        for h in PAST:th.append({'ticker':ticker,'h':h,'lower_log_pp':t[f'past{h}']['0.1'],
            'upper_log_pp':t[f'past{h}']['0.9'],'lower_z':t[f'z{h}']['0.1'],'upper_z':t[f'z{h}']['0.9']})
    save(th,out/'tables/thresholds_readable.csv')
    pformat=lambda x:f'{100*x:.1f}%'
    lines=['# E3a — Multi-Horizon Trend & Reversal Event Study','',
        'AAPL／TSLA；2012–2022定義門檻、2023驗證描述、2024–2025探索性測試。2026保留未評估。CPU研究，未訓練新模型、未改動Mamba或既有結果。', '',
        '## 主要發現','',
        f'- 完整列出98項事先固定比較（主要48、波動狀態24、方向規則18、Mamba8）；主要lag60 HAC經全98項Holm校正，通過0.05者 **{len(significant)}項**。小事件格保留於檢定家族，推論不足則不宣稱顯著。',
        '- 反向報酬機率是短期反彈／回檔，不是持續趨勢切換；完全收復先前漲跌幅另列。上漲市場中，急跌後反彈本來就可能高於50%，因此必須與同期間的方向別無條件基準比較。',
        '- 衝突事件的方向規則本身等同在該格採簡單均值回歸；額外價值只能來自可事前辨識的篩選條件與同日期整體預測表現，不能把這兩個相同方向決策當作獨立模型。', '',
        '### 極端5日漲跌後的反向機率：2024–2025','',
        'side=-1為急跌、+1為急漲。事件數採h日冷卻；差異是事件反向機率減去同期間全部可用日的方向別基準。p為98項全域Holm調整後HAC值。', '',
        table(shock,{'ticker':'股票','side':'先前方向','horizon':'未來日數','n_a':'事件數','mean_a':'反向機率','mean_b':'無條件基準','difference':'差異','hac_p_holm_global98':'全域調整p'},
              {'mean_a':pformat,'mean_b':pformat,'difference':lambda x:f'{100*x:+.1f}pp'}),'',
        '### 長短期衝突相對一致：2024–2025','',
        '在同一批被選取的急漲／急跌事件內，比較長期方向相反（衝突）與相同（一致）；長期為t−120至t−5，沒有把短期5日的變動重複算入長期。少於10個事件的任一格僅描述。', '',
        table(conflicts,{'ticker':'股票','side':'短期方向','horizon':'未來日數','n_a':'衝突n','n_b':'一致n','mean_a':'衝突反向率','mean_b':'一致反向率','difference':'差異','inference_status':'推論狀態','hac_p_holm_global98':'全域調整p'},
              {'mean_a':pformat,'mean_b':pformat,'difference':lambda x:f'{100*x:+.1f}pp'}),'',
        '## 研究設計與定義','',
        '調整後Close的5／20／60／120日累積log報酬×100衡量趨勢；一般事件是該股票訓練期間的下10%／上10%尾端，且要求真正負／正報酬。另分析相對事件窗口之前60日波動率的標準化異常變動：z_h=R_h／(sigma[t−h]√h)，所以急漲跌本身不會抬高自己的分母。', '',
        table(pd.DataFrame(th),{'ticker':'股票','h':'過去日數','lower_log_pp':'急跌門檻log pp','upper_log_pp':'急漲門檻log pp','lower_z':'異常跌門檻z','upper_z':'異常漲門檻z'}),'',
        '事件後1／5／20日同時報告累積simple報酬100(C[t+h]/C[t]−1)、反向率、延續率、平盤率、反向log幅度、只在反向樣本的幅度、完全收復機率與收復比例。反向log幅度=−sign(事件前走勢)×未來log報酬；正值有利均值回歸，負值有利動能。完全收復要求該幅度至少等於之前事件漲跌幅。另以0.5 sigma√h排除極小反向變動作描述性穩健性。','',
        f'高／低VIX與VXN各用股票訓練日期的中位數切分，不使用測試分位數。VIX以S&P500選擇權為基礎，VXN對應Nasdaq100；本快照兩者訓練期相關係數為{train_vol_corr:.3f}，分別報告不能視為兩次獨立重現。指數定義見[Cboe VIX](https://www.cboe.com/tradable-products/vix)及[Cboe波動指數方法](https://cdn.cboe.com/api/global/us_indices/governance/Volatility_Index_Methodology_Selected_Broad_Based_Index_Equity_and_ETF_Volatility_Indices.pdf)。', '',
        table(pd.DataFrame([{'ticker':t,'VIX':v['VIX_median'],'VXN':v['VXN_median']} for t,v in thresholds.items()]),{'ticker':'股票','VIX':'VIX中位門檻','VXN':'VXN中位門檻'}),'',
        '### 時間、窗口與資料洩漏','',
        '每個split只使用t與t+20都落在該split的共同事件日期，因此三個未來horizon有相同候選日，且任何標籤都不跨入2026。2010–2011只供落後特徵暖身，所有事件門檻、majority方向與QQQ市場模型只由2012–2022建立。驗證／測試沒有回頭調門檻。', '',
        table(elig,{'ticker':'股票','split':'期間','n_eligible':'共同日期數','first':'第一事件日','last':'最後事件日','last_label20':'最後20日標籤日'}),'',
        '每個父事件家族依時間取第一件，之後至少隔h個交易日，確保其未來h日報酬增量窗口不重疊。長期／波動分組再切分同一批事件，不各自重選。不同事件家族或股票仍可能共用時間，沒有把它們合併成獨立樣本；Holm容許比較間相依。長短期狀態熱圖另用同一固定h日規則網格，再分九格，格數與主事件表不同。', '',
        '### 統計推論','',
        '條件平均與基準的差使用完整交易日時間軸的ratio-of-means influence function、Bartlett/Newey–West HAC lag60。循環區塊bootstrap抽同一時間軸上的事件指標與結果，長度60、4999次、seed20261021，聯合重估事件與無條件基準，保留兩者共變異。沒有對壓縮事件列直接做HAC，也沒有把五個seeds當成五倍獨立日期。',
        '雙尾bootstrap p以虛無中心化及plus-one修正，95% basic區間為名目區間，不是同時信賴區間。條件組至少10件，且至少99% bootstrap樣本分母非零，否則只描述，p以1納入Holm。主要判讀採lag60 HAC全98項Holm；區塊bootstrap作佐證，lag／block20與120完整列為敏感度，不挑最顯著者。', '',
        '## 視覺化','',
        '![急漲跌後的反向機率差與區塊CI](figures/01_reversal_probability_contrasts.png)','',
        '圖1：正值代表反向機率高於同期間方向別基準。灰色標記或無區間表示推論事件不足；區間不作全域同時覆蓋保證。','',
        '![多尺度事件](figures/02_multihorizon_reversal.png)','',
        '圖2：每格為對應h日非重疊抽樣的反向率與n；不同horizon的事件數不同，不能把橫向曲線解讀為相同事件樣本的變化。','',
        '![長短期狀態](figures/03_trend_conflict_heatmap.png)','',
        '圖3：短期5日與扣除該段的長期120日趨勢狀態，±0.5歷史sigma為中性帶；每格為後5日平均simple報酬與n，使用固定5日網格。這是描述性平均，不是因果效應或獲利保證。','',
        '![事件路徑](figures/04_event_paths.png)','',
        '圖4：同一批20日冷卻的急漲／急跌事件，其後1–20日平均simple累積報酬。樣本少，路徑起伏不代表穩定可交易規律。','',
        '![市場波動狀態](figures/05_volatility_regimes.png)','',
        '圖5：高低VIX／VXN在急漲／跌後5日反向率；狀態比較在同父事件集內切分，事件數隨柱列出。','',
        '![穩健性](figures/06_robustness.png)','',
        '圖6：事先固定的門檻、抽樣、開盤起算與市場超額報酬等變體；色彩是相對各自無條件基準的反向率差。未根據此表改動主定義。','',
        '![Mamba幅度誤差](figures/07_mamba_event_errors.png)','',
        '圖7：E1/E2b五seed平均幅度MAE；誤差棒只是五seed樣本SD，不是日期推論CI。ex-post reversal/continuation分層用到了未來真實方向，只供事後診斷。','',
        '![方向規則比較](figures/08_direction_baselines.png)','',
        '## 與既有Mamba的連結','',
        'Mamba只預測下一日絕對log報酬幅度，從未預測正負方向。此處讀取既有20組逐日預測，不重新訓練；逐檔核對所有原始日期、label date與實際100|log(C[t+1]/C[t])|。原Mamba每組501筆預測完整保存，本階段因共同20日標籤窗而只比較482個共同日期，所以MAE與舊501日總表不同，不代表重訓或覆寫結果；對齊數完整保存在mamba_alignment_audit.csv。',
        '先對每seed計算條件MAE/RMSE，再彙整5seed平均／SD。E2b−E1比較使用相同日期先平均五seed loss，再做calendar推論，沒有把預測均值當作原模型，也沒有把seeds當作獨立市場日。', '',
        table(mamba[mamba.group.isin(['all','shock_up','shock_down','conflict_up','conflict_down','expost_reversal','expost_continuation'])],
              {'ticker':'股票','arm':'模型','group':'狀態','n_dates':'日期n','mae_pp_mean':'MAE','rmse_pp_mean':'RMSE','bias_pp_mean':'預測−真實偏差','actual_magnitude_mean_mean':'真實幅度均值','rolling20_mae_mean':'rolling20基準MAE'}),'',
        '幅度模型在反向日誤差大，不足以推論「模型不能辨識反轉方向」。必須先看真實幅度本來是否更大、是否普遍低估，及相對rolling20／訓練均值幅度基準的誤差；方向能力需要E3b重新定義方向標籤並公平訓練。', '',
        '## 簡單方向規則與無條件基準','',
        '全部規則使用同一批共同日期：訓練majority方向、20日動能、反5日走勢的均值回歸，以及「只在急漲跌且長短衝突時回到長期方向，其他日期用訓練majority」的固定gate。此為方向診斷，並非交易策略績效；平盤不算正確方向，balanced accuracy只針對非平盤計算。標籤仍重疊，因此配對差異用完整日曆bootstrap/HAC。', '',
        table(rules[rules.split=='test'],{'ticker':'股票','horizon':'未來日數','rule':'規則','accuracy':'Accuracy','balanced_accuracy':'Balanced accuracy','conflict_gate_coverage':'gate觸發比例'},
              {'accuracy':pformat,'balanced_accuracy':pformat,'conflict_gate_coverage':pformat}),'',
        '## 穩健性與可重現性','',
        'robustness.csv完整保存：重疊全部候選、固定20日冷卻、5%尾端、相對歷史sigma≥2、標準化分位事件、未扣除短期的長期符號、下一交易日Open起算、train-only QQQ市場模型超額報酬、不含股息調整的Yahoo Close及2024／2025分年。未使用2026、未挑選最佳參數，未把敏感度試驗當額外確認。',
        '程式與CLI見README_E3A.md；資料來源與企業行動數見data_audit.csv；inputs保存實際使用的原始／調整CSV至2025、原快照provenance及保護檔案hash。所有新研究產物另存於本資料夾，不修改既有結果。', '',
        '## 限制與E3b建議','',
        '事件由價格本身內生選取，本研究是條件關聯研究，並非外生消息的因果事件研究。AAPL／TSLA也是事先選定的兩檔股票，不能外推為全市場規律。價格來自事後保存、回溯調整的Yahoo快照，而非point-in-time資料庫；完整性只對QQQ日曆驗證，非獨立交易所日曆。',
        '若使用t日收盤與VIX/VXN最終值，信號cutoff必須在這些值皆已公布後。當日收盤至未來收盤屬統計關聯，不保證能以該收盤價成交；next-open穩健性部分處理此問題，但還不包含成本／滑價。',
        'HAC／區塊bootstrap假設近似弱平穩及弱依賴；長期狀態可持續超過120日、結構轉換、測試僅兩年與稀疏極端格都限制推論。固定門檻的bootstrap沒有重估門檻／模型，不代表完整模型開發不確定性。',
        '2024–2025已在先前研究中檢視；即使本次計畫在E3a計算前固定，也仍是探索性延伸，不是新的獨立確認性測試。完整E3b方案見E3B_PROPOSAL.md：共享因果特徵與序列、purged時間切分、同一標籤／日期／預算／seeds、概率校準和相同基準，2026留待研究方案真正鎖定後的獨立驗證。','',
        '## 方法來源','',
        '- [MacKinlay事件研究方法與重疊窗口問題](https://www.bu.edu/econ/files/2011/01/MacKinlay-1996-Event-Studies-in-Economics-and-Finance.pdf)',
        '- [HAC/Bartlett covariance](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html)',
        '- [Circular block bootstrap](https://bashtage.github.io/arch/bootstrap/generated/arch.bootstrap.CircularBlockBootstrap.html)',
        '- [Holm多重比較](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html)','']
    if len(significant):
        lines.insert(8,'通過全域校正的比較（仍屬探索性）：\n\n'+table(significant,{'family':'家族','ticker':'股票','side':'方向','horizon':'h','comparison':'比較','metric':'指標','difference':'差異','hac_p_holm_global98':'全域p'}))
    from e3a_interpretation import interpretation
    section=lines.index('### 極端5日漲跌後的反向機率：2024–2025')
    lines.insert(section,interpretation(out,tests))
    magnitude=stats[(stats.split=='test')&(stats.kind=='raw')&(stats.past_horizon==5)&(stats['sample']=='nonoverlap')&(stats.group=='all')]
    section=lines.index('### 長短期衝突相對一致：2024–2025')
    lines.insert(section,'### 累積報酬與收復幅度\n\n'+table(magnitude,{'ticker':'股票','side':'事件方向','horizon':'未來日數','n_events':'n',
        'forward_pct_mean':'平均累積報酬%','continuation_mean':'延續率','full_retracement_mean':'完全收復率','reversal_only_magnitude_pct':'反向樣本平均幅度%'},
        {'continuation_mean':pformat,'full_retracement_mean':pformat})+'\n')
    (out/'E3A_SUMMARY.md').write_text('\n'.join(lines))


def package(out):
    archive=out/'e3a_complete_results.zip'
    files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name not in ('e3a_complete_results.zip','archive_sha256.txt','archive_manifest.json','status.json')}
    write_json(out/'archive_manifest.json',{'files':files})
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in files:z.write(out/name,'E3a/'+name)
        z.write(out/'archive_manifest.json','E3a/archive_manifest.json')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise RuntimeError('ZIP CRC error')
        for name,digest in files.items():
            if hashlib.sha256(z.read('E3a/'+name)).hexdigest()!=digest:raise RuntimeError('ZIP hash failure')
    (out/'archive_sha256.txt').write_text(sha(archive)+'  '+archive.name+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'outputs/e3a_20261021')
    args=parser.parse_args();out=args.out.resolve()
    if not out.is_relative_to(ROOT/'outputs'):raise ValueError('Outputs must stay in project/outputs')
    protected,frames,thresholds,rawframes,rawthresholds=setup(out)
    event_descriptions(frames,thresholds,out)
    rules=direction_rules(frames,thresholds,out)
    tests,cache=planned_tests(frames,thresholds,rules,out)
    sensitivity(frames,thresholds,rawframes,rawthresholds,out)
    mamba_diagnostics(frames,thresholds,out,tests,cache)
    results=adjust_tests(tests,out);write_report(out,thresholds,results)
    for name in ('README_E3A.md','E3B_PROPOSAL.md'):(out/name).write_bytes((ROOT/name).read_bytes())
    env={**os.environ,'MPLCONFIGDIR':str(ROOT/'.cache/e3a_matplotlib'),'CUDA_VISIBLE_DEVICES':''}
    with (out/'logs/plot.log').open('w') as log:
        subprocess.run(['/usr/bin/python3',str(ROOT/'scripts/plot_e3a.py'),str(out)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    verify_manifest(protected)
    (out/'code/requirements-analysis.txt').write_text('\n'.join(f'{p}=={importlib.metadata.version(p)}' for p in ('numpy','pandas','scipy'))+'\n')
    testpath=ROOT/'logs/e3a-tests.log'
    if testpath.exists():(out/'logs/cpu_tests.log').write_bytes(testpath.read_bytes())
    if (ROOT/'logs/e3a-tests.xml').exists():(out/'logs/cpu_tests.xml').write_bytes((ROOT/'logs/e3a-tests.xml').read_bytes())
    write_json(out/'verification.json',{'status':'PASSED','prior_artifacts_unchanged':True,'no2026_analysis':True,
        'model_training':False,'GPU_used':False,'planned_main_comparisons':98,'primary_comparisons':48,
        'Mamba_original_targets_dates_verified':True,'frozen_training_thresholds':True})
    LOG.info('All inference/plots verified; packing result archive')
    write_json(out/'status.json',{'status':'PACKAGING'})
    # Close the log before hashing and archiving it.
    for handler in list(LOG.handlers):handler.flush();handler.close();LOG.removeHandler(handler)
    package(out)
    write_json(out/'status.json',{'status':'COMPLETE','finished_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'archive':'e3a_complete_results.zip'})
    print('COMPLETE:',out/'e3a_complete_results.zip',flush=True)


if __name__=='__main__':main()
