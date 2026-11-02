"""Export E3c research plots from frozen result tables, CPU-only."""
import argparse
import html
import json
import os
from pathlib import Path
import sys
import numpy as np
import pandas as pd
os.environ.setdefault('MPLCONFIGDIR',str(Path.home()/'stock_prediction/.cache/matplotlib_e3c'))
sys.path.extend([str(Path.home()/'.local/lib/python3.10/site-packages'),'/usr/local/lib/python3.10/dist-packages','/usr/lib/python3/dist-packages'])
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(out):
    dst=out/'figures';dst.mkdir(exist_ok=True);plots=[]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':170})
    (dst/'plot_environment.json').write_text(json.dumps({'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__,'matplotlib':matplotlib.__version__,'matplotlib_path':matplotlib.__file__},indent=2)+'\n')
    m=pd.read_csv(out/'tables/metrics_comparison.csv');t=pd.read_csv(out/'tables/paired_tests.csv')
    r=pd.read_csv(out/'tables/within_state_ranking_tests.csv');h=pd.read_csv(out/'tables/historical_conditional_states.csv')
    def save(fig,name,title):
        fig.savefig(dst/(name+'.png'),bbox_inches='tight');fig.savefig(dst/(name+'.pdf'),bbox_inches='tight');plt.close(fig);plots.append((name,title))
    names=['global_prior','event_prior','direction_prior','state_prior','recent_event_prior','lr_all','lr_event','xgb_all','xgb_event','e3b_logistic_B','e3b_xgboost_B','e3b_lightgbm_B','e3b_lstm_B','recal_lstm_B','e3b_mamba_B','recal_mamba_B','e3b_cal_prior']
    fig,axs=plt.subplots(1,2,figsize=(14,8),sharey=True)
    for ax,ticker in zip(axs,['AAPL','TSLA']):
        z=m[(m.ticker==ticker)&(m.group=='events')].set_index('method').reindex(names);ys=np.arange(len(names))
        for i,name in enumerate(names):
            color='#D87A32' if name.endswith('_event') else ('#3A70A4' if name.startswith('e3b_') else '#637A58')
            ax.errorbar(z.brier_mean.iloc[i],ys[i],xerr=z.brier_std.fillna(0).iloc[i],fmt='o',color=color,capsize=3)
        ax.axvline(z.loc['state_prior','brier_mean'],color='black',linestyle='--',linewidth=1,label='state prior')
        ax.set_yticks(ys,names);ax.invert_yaxis();ax.set_title(ticker);ax.set_xlabel('Event Brier; mean +/- seed SD (not inferential CI)');ax.legend()
    save(fig,'01_event_brier','Event-only evaluation; full-date and specialist models')
    methods=['lr_all','lr_event','xgb_all','xgb_event','e3b_logistic_B','e3b_xgboost_B','e3b_lightgbm_B','e3b_lstm_B','e3b_mamba_B']
    fig,axs=plt.subplots(1,2,figsize=(13,6),sharey=True)
    for ax,ticker in zip(axs,['AAPL','TSLA']):
        q=r[(r.ticker==ticker)&(r.block_length==20)].set_index('method').reindex(methods)
        base=r[(r.ticker==ticker)&(r.block_length==0)].set_index('method').reindex(methods)
        yy=np.arange(len(methods));ax.hlines(yy,q.ci_low,q.ci_high,color='#3A70A4',linewidth=2)
        ax.scatter(q.within_state_auc,yy,label='Within-state AUC',color='#3A70A4')
        ax.scatter(base.event_ROC_AUC,yy+.18,label='Across-event AUC',marker='x',color='#D87A32')
        ax.axvline(.5,color='black',linestyle='--',linewidth=1);ax.set_xlim(0,1);ax.set_yticks(yy,methods);ax.invert_yaxis();ax.set_title(ticker)
        ax.set_xlabel('AUC; pointwise calendar-block20 95% CI');ax.legend(fontsize=8)
    save(fig,'02_within_state_ranking','Distinguish state-average differences from within-state ranking')
    rel=pd.read_csv(out/'tables/event_reliability.csv')
    fig,axs=plt.subplots(1,2,figsize=(12,5),sharey=True)
    selected=['state_prior','lr_all','lr_event','xgb_event','e3b_mamba_B','recal_mamba_B']
    for ax,ticker in zip(axs,['AAPL','TSLA']):
        for name in selected:
            z=rel[(rel.ticker==ticker)&(rel.method==name)];points=[]
            for bid,zz in z.groupby('bin'):
                n=zz.n.sum()
                if n/len(z.seed.unique())>=3:
                    points.append((np.nansum(zz.mean_probability*zz.n)/n,np.nansum(zz.reversal_rate*zz.n)/n))
            if points:
                points=np.asarray(points);ax.plot(points[:,0],points[:,1],'o-',label=name,linewidth=1,markersize=4)
        ax.plot([0,1],[0,1],'k--',linewidth=.8);ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_title(ticker+' / extreme events')
        ax.set_xlabel('Predicted reversal probability');ax.set_ylabel('Observed reversal rate');ax.legend(fontsize=7)
    save(fig,'03_event_calibration','Fixed ten bins; sparse-bin points are descriptive')
    cells=[0,1,2,3,8,9,10,11];labels=[('Crash' if c<4 else 'Surge')+' / '+('Lup' if c//2%2 else 'Ldown')+' / '+('Vhigh' if c%2 else 'Vlow') for c in cells]
    fig,axs=plt.subplots(1,2,figsize=(12,6),sharey=True)
    for ax,ticker in zip(axs,['AAPL','TSLA']):
        rates=np.full((8,3),np.nan);ns=np.zeros((8,3),int)
        for i,c in enumerate(cells):
            for j,part in enumerate(['fit','cal','test']):
                row=h[(h.ticker==ticker)&(h.cell==c)&(h.partition==part)].iloc[0];rates[i,j]=row.reversal_rate;ns[i,j]=int(row.n)
        im=ax.imshow(rates,cmap='viridis',vmin=0,vmax=1,aspect='auto')
        for i in range(8):
            for j in range(3):ax.text(j,i,f'{rates[i,j]:.2f}\nn={ns[i,j]}' if ns[i,j] else 'n=0',ha='center',va='center',fontsize=9,color='white' if np.isnan(rates[i,j]) or rates[i,j]<.6 else 'black')
        ax.set_xticks(range(3),['Train2012-22','Cal2023H2','Test2024-25'],rotation=20);ax.set_yticks(range(8),labels);ax.set_title(ticker)
        fig.colorbar(im,ax=ax,label='Observed reversal rate (descriptive)')
    save(fig,'04_state_drift','Same fixed event states across time; counts matter')
    fig,axs=plt.subplots(1,2,figsize=(12,4.5),sharey=True)
    pairs=[('lr_event','lr_all'),('xgb_event','xgb_all'),('recal_lstm_B','e3b_lstm_B'),('recal_mamba_B','e3b_mamba_B')]
    for ax,ticker in zip(axs,['AAPL','TSLA']):
        z=t[(t.ticker==ticker)&(t.group=='events')&(t.block_length==20)]
        for i,(candidate,reference) in enumerate(pairs):
            row=z[(z.candidate==candidate)&(z.reference==reference)].iloc[0]
            ax.hlines(i,row.bootstrap_ci_low,row.bootstrap_ci_high,color='#3A70A4');ax.scatter(row.difference,i,color='#D87A32')
        ax.axvline(0,color='black',linestyle='--',linewidth=1);ax.set_yticks(range(4),['LR specialist','XGB specialist','LSTM event intercept','Mamba event intercept']);ax.invert_yaxis();ax.set_title(ticker)
        ax.set_xlabel('Brier gain vs all-date/original model; pointwise95% CI')
    save(fig,'05_specialization_gain','Training specialization versus probability-intercept adjustment')
    bins=pd.read_csv(out/'tables/calibration_fixed_score_bins.csv')
    fig,axs=plt.subplots(2,2,figsize=(12,8),sharex=True)
    for col,ticker in enumerate(['AAPL','TSLA']):
        for name in ['lr_event','xgb_event','e3b_mamba_B']:
            z=bins[(bins.ticker==ticker)&(bins.method==name)];data=[]
            for q,zz in z.groupby('score_bin'):
                n=zz.n.sum()
                if n/len(z.seed.unique())>=3:data.append((q,np.nansum(zz.reversal_rate*zz.n)/n,np.nansum(zz.signed_amplitude_mean_pp*zz.n)/n))
            if data:
                data=np.asarray(data);axs[0,col].plot(data[:,0],data[:,1],'o-',label=name);axs[1,col].plot(data[:,0],data[:,2],'o-',label=name)
        axs[0,col].set_title(ticker);axs[0,col].set_ylim(0,1);axs[0,col].set_ylabel('Observed reversal rate');axs[0,col].legend(fontsize=8)
        axs[1,col].axhline(0,color='black',linestyle='--',linewidth=.8);axs[1,col].set_ylabel('Observed signed reversal log return (pp)');axs[1,col].set_xticks(range(1,6));axs[1,col].set_xlabel('Score bins fixed from2023 calibration events')
    save(fig,'06_probability_amplitude','Reversal direction and realized magnitude are separate outcomes')
    groups=['all','events','surge','crash','conflict','event_VIX_high','event_VIX_low'];modelnames=['event_prior','state_prior','lr_all','lr_event','xgb_event','e3b_lstm_B','e3b_mamba_B','recal_mamba_B']
    fig,axs=plt.subplots(1,2,figsize=(13,5),sharey=True)
    for ax,ticker in zip(axs,['AAPL','TSLA']):
        matrix=m[(m.ticker==ticker)&m.method.isin(modelnames)&m.group.isin(groups)].pivot(index='group',columns='method',values='calibration_bias_mean').reindex(index=groups,columns=modelnames)
        im=ax.imshow(matrix,cmap='RdBu_r',vmin=-.25,vmax=.25,aspect='auto');ax.set_yticks(range(len(groups)),groups);ax.set_xticks(range(len(modelnames)),modelnames,rotation=60,ha='right');ax.set_title(ticker);fig.colorbar(im,ax=ax,label='Mean probability - observed reversal rate')
    save(fig,'07_conditional_calibration_bias','Overall calibration can hide conditional probability bias')
    page='<!doctype html><meta charset="utf-8"><title>E3c figures</title><style>body{max-width:1300px;margin:auto;font-family:sans-serif}img{width:100%}</style><h1>E3c figures</h1>'
    for name,title in plots:page+=f'<h2>{html.escape(title)}</h2><a href="{name}.pdf">PDF</a><img src="{name}.png" alt="{html.escape(title)}">'
    (dst/'index.html').write_text(page)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args();plot(args.out)
