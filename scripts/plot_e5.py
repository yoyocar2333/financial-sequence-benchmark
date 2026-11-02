"""Plots from completed E5 CSVs only; English axes, Chinese report captions."""
import argparse,sys
from pathlib import Path
sys.path.append(str(Path.home()/'.local/lib/python3.10/site-packages'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from e5_core import OUT,MODELS

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150,'savefig.dpi':180})
COLORS={'B':'#426987','T':'#b47d3b'}

def save(fig,name):
    fig.tight_layout();fig.savefig(OUT/'figures'/name,bbox_inches='tight');plt.close(fig)


def run():
    m=pd.read_csv(OUT/'tables/metrics_comparison.csv');m=m[(m.version=='calibrated')&(m.task=='reversal')]
    def val(t,method,col='brier_mean'):return m[(m.ticker==t)&(m.method==method)][col].iloc[0]
    for ticker in ['AAPL','TSLA']:
        f=pd.read_csv(OUT/'inputs'/f'{ticker}_technical_and_labels.csv',parse_dates=['Date']).set_index('Date').loc['2024-01-01':'2025-12-31']
        fig,ax=plt.subplots(3,1,figsize=(12,8),sharex=True,gridspec_kw={'height_ratios':[2,1,1]})
        ax[0].plot(f.index,f.Close,label='Adjusted close',color='#253746',lw=1)
        ax[0].plot(f.index,f.ma20,label='SMA20',lw=.8);ax[0].plot(f.index,f.ma60,label='SMA60',lw=.8)
        ax[0].fill_between(f.index,f.bb_lower,f.bb_upper,alpha=.15,label='BB20 +/-2 SD')
        ax[0].set_title(ticker+' | frozen 2024-2025 data; indicators use past observations only');ax[0].legend(ncol=4,fontsize=8)
        ax[1].plot(f.index,f.rsi14,color='#72548b');ax[1].axhline(30,color='gray',ls='--');ax[1].axhline(70,color='gray',ls='--');ax[1].set_ylabel('RSI14');ax[1].set_ylim(0,100)
        ax[2].plot(f.index,f.adx14,color='#38796a');ax[2].axhline(20,color='gray',ls='--');ax[2].axhline(25,color='gray',ls=':');ax[2].set_ylabel('ADX14')
        ax[2].fill_between(f.index,0,f.adx14,where=f.adx14>=25,color='#38796a',alpha=.18,label='Trend: ADX>=25');ax[2].legend(loc='upper right',fontsize=8)
        ax[0].set_xlim(f.index.min(),f.index.max())
        save(fig,'01_'+ticker+'_indicators.png')
    gains=pd.read_csv(OUT/'tables/feature_gains.csv')
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
    names=['xgboost','lightgbm','lstm','mamba']
    for ax,t in zip(axes,['AAPL','TSLA']):
        z=gains[gains.ticker==t].set_index('candidate').reindex([k+'_T' for k in names]);y=np.arange(4)
        ax.hlines(y,z.bootstrap_ci_low,z.bootstrap_ci_high,color='#426987',lw=2)
        ax.scatter(z.difference,y,color=['#38796a' if q else '#b47d3b' for q in z.joint_significant],s=55,zorder=3)
        ax.axvline(0,color='gray',ls='--');ax.set_title(t);ax.set_yticks(y,labels=names);ax.set_xlabel('Brier gain: B - T\npointwise block20 95% CI; family Holm8')
    save(fig,'02_feature_gains.png')
    fig,axes=plt.subplots(1,2,figsize=(12,4.8))
    for ax,t in zip(axes,['AAPL','TSLA']):
        xx=np.arange(5)
        for j,arm in enumerate(['B','T']):
            yy=[val(t,k+'_'+arm) for k in MODELS];ax.bar(xx+(j-.5)*.32,yy,.32,label=arm,color=COLORS[arm])
        ax.axhline(val(t,'cal_prior'),color='black',ls=':',label='Calibration prior')
        ax.set_xticks(xx,labels=MODELS,rotation=20);ax.set_title(t);ax.set_ylabel('Brier (lower better)');ax.set_ylim(min(m[m.ticker==t].brier_mean.min(),min(yy))-.006,max(max([val(t,k+'_'+a) for k in MODELS for a in ['B','T']]),.255)+.004);ax.legend(fontsize=8)
    save(fig,'03_models_B_T.png')
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    hybrid=['momentum20','mean_reversion5','state_prior','rule_hybrid','ungated_H0','hybrid_H']
    for ax,t in zip(axes,['AAPL','TSLA']):
        vals=[val(t,k) for k in hybrid];ax.barh(np.arange(len(hybrid)),vals,color=['#9daab4']*3+['#b47d3b','#426987','#38796a']);ax.set_yticks(np.arange(len(hybrid)),labels=hybrid);ax.axvline(val(t,'cal_prior'),ls=':',color='black');ax.set_xlim(min(vals)-.004,max(vals)+.003);ax.set_title(t);ax.set_xlabel('Calibrated Brier')
    save(fig,'04_hybrid_baselines.png')
    state=pd.read_csv(OUT/'tables/state_metrics.csv')
    groupnames=['all','events','acute_rise','acute_fall','conflict','ADX_trend','ADX_range','ADX_transition','VIX_high','VIX_low']
    fig,axes=plt.subplots(2,1,figsize=(13,7.5))
    for ax,t in zip(axes,['AAPL','TSLA']):
        a=[]
        for model in names:
            a.append([float(state[(state.ticker==t)&(state.method==model+'_B')&(state.group==g)].brier.iloc[0]-state[(state.ticker==t)&(state.method==model+'_T')&(state.group==g)].brier.iloc[0]) for g in groupnames])
        a=np.asarray(a);limit=max(.002,np.abs(a).max());im=ax.imshow(a,cmap='RdBu',vmin=-limit,vmax=limit,aspect='auto')
        ax.set_yticks(np.arange(4),labels=names);ax.set_xticks(np.arange(len(groupnames)),labels=groupnames,rotation=18,ha='right');ax.set_title(t+' | subgroup Brier gain B-T; descriptive, no significance selection')
        for i in range(4):
            for j in range(len(groupnames)):ax.text(j,i,f'{a[i,j]:+.4f}',ha='center',va='center',fontsize=8,color='white' if abs(a[i,j])>.6*limit else 'black')
        fig.colorbar(im,ax=ax,pad=.01)
    save(fig,'05_regime_feature_gains.png')
    rank=pd.read_csv(OUT/'tables/within_state_ranking.csv');rank=rank[rank.block_length==20]
    fig,axes=plt.subplots(1,2,figsize=(12,5),sharex=True)
    for ax,t in zip(axes,['AAPL','TSLA']):
        z=rank[rank.ticker==t].sort_values('method');yy=np.arange(len(z));ax.hlines(yy,z.ci_low,z.ci_high,color='#426987');ax.scatter(z.within_state_auc,yy,color='#426987');ax.axvline(.5,ls='--',color='black');ax.set_yticks(yy,labels=z.method);ax.set_xlim(0,1);ax.set_title(t);ax.set_xlabel('Event within-state AUC; pointwise block20 CI\nfamily Holm12 p in CSV')
    save(fig,'06_within_state_ranking.png')
    redundant=pd.read_csv(OUT/'tables/training_feature_redundancy.csv')
    fig,axes=plt.subplots(1,2,figsize=(12,6),sharex=True)
    for ax,t in zip(axes,['AAPL','TSLA']):
        z=redundant[redundant.ticker==t].sort_values('absolute_spearman');ax.barh(z.technical_feature,z.absolute_spearman,color='#426987');ax.set_xlim(0,1);ax.set_title(t);ax.set_xlabel('Max absolute Spearman with existing B feature\n2012-2022 only; association is not equivalence')
    save(fig,'07_representation_overlap.png')
    st=pd.read_csv(OUT/'tables/regime_stability.csv');fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,t in zip(axes,['AAPL','TSLA']):
        base=np.zeros(3)
        for reg,c in [('range','#b47d3b'),('transition','#b7c0c9'),('trend','#426987')]:
            vals=[float(st[(st.ticker==t)&(st.partition==part)&(st.regime==reg)].share.iloc[0]) for part in ['train','validation','test']]
            ax.bar(np.arange(3),vals,bottom=base,label=reg,color=c);base+=vals
        ax.set_xticks(np.arange(3),labels=['2012-2022','2023','2024-2025']);ax.set_ylim(0,1);ax.set_title(t);ax.set_ylabel('Fraction of eligible dates');ax.legend(fontsize=8)
    save(fig,'08_regime_coverage.png')
    rel=pd.read_csv(OUT/'tables/reliability.csv');fig,axes=plt.subplots(1,2,figsize=(11,4.6))
    for ax,t in zip(axes,['AAPL','TSLA']):
        for method in ['xgboost_B','xgboost_T','mamba_B','mamba_T','hybrid_H','state_prior']:
            z=rel[(rel.ticker==t)&(rel.method==method)&(rel.mean_seed_count>=10)].sort_values('bin');ax.plot(z.predicted,z.observed,'o-',label=method,lw=1,ms=4)
        ax.plot([0,1],[0,1],'k--',lw=.7);ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_xlabel('Mean predicted probability');ax.set_ylabel('Observed reversal frequency');ax.set_title(t);ax.legend(fontsize=7)
    save(fig,'09_calibration.png')
    nav=pd.read_csv(OUT/'tables/trading_daily_NAV_primarycost.csv.gz',parse_dates=['date']);fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,t in zip(axes,['AAPL','TSLA']):
        for method in ['buy_hold','momentum20','literal_rule_hybrid','hybrid_H','xgboost_T','mamba_T']:
            z=nav[(nav.ticker==t)&(nav.method==method)].pivot(index='date',columns='offset',values='nav').ffill().fillna(1)
            ax.plot(z.index,z.mean(axis=1),label=method,lw=1.2)
        ax.set_xlim(z.index.min(),z.index.max())
        ax.set_title(t+' | mean of all 5 fixed schedules');ax.set_ylabel('NAV, initial 1');ax.set_xlabel('10bps fee+slippage EACH SIDE; long/cash');ax.legend(fontsize=7)
    save(fig,'10_secondary_trading_NAV.png')
    print('E5 figures created:11 PNG files',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path);a=p.parse_args()
    if a.directory:OUT=a.directory.resolve()
    run()
