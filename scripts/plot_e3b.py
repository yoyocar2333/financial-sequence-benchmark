"""Publication artifacts from saved E3b tables; system matplotlib, no GPU imports."""
import argparse
import html
import sys
from pathlib import Path
import numpy as np
import pandas as pd
# Read existing plotting libraries only in this isolated CPU plotting process.
# Core ML NumPy/Pandas are imported before appending these fallback locations.
sys.path.extend([str(Path.home()/'.local/lib/python3.10/site-packages'),'/usr/local/lib/python3.10/dist-packages','/usr/lib/python3/dist-packages'])
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(out):
    figdir=out/'figures';figdir.mkdir(exist_ok=True)
    m=pd.read_csv(out/'tables/metrics_comparison.csv');m=m[m.probability=='calibrated']
    t=pd.read_csv(out/'tables/paired_tests.csv');t=t[(t.block_length==20)&(t.horizon==5)]
    r=pd.read_csv(out/'tables/reliability.csv');s=pd.read_csv(out/'tables/state_metrics.csv')
    seeds=pd.read_csv(out/'tables/metrics_per_seed.csv');seeds=seeds[(seeds.probability=='calibrated')&(seeds.horizon==5)]
    models=['logistic','xgboost','lightgbm','lstm','mamba'];colors={'A':'#3B6FB6','B':'#DF7B38'}
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':170})
    import json
    (out/'figures/plot_environment.json').write_text(json.dumps({'python':sys.version,'matplotlib':matplotlib.__version__,
        'matplotlib_path':matplotlib.__file__,'numpy':np.__version__,'pandas':pd.__version__},indent=2)+'\n')
    figures=[]
    def save(fig,name,title):
        fig.savefig(figdir/(name+'.png'),bbox_inches='tight');fig.savefig(figdir/(name+'.pdf'),bbox_inches='tight')
        plt.close(fig);figures.append((name,title))
    fig,axs=plt.subplots(1,2,figsize=(13,4.8),sharey=True)
    for ax,ticker in zip(axs,['AAPL','TSLA']):
        z=m[(m.ticker==ticker)&(m.horizon==5)];x=np.arange(len(models))
        for offset,arm in [(-.18,'A'),(.18,'B')]:
            zz=z[z.arm==arm].set_index('model').reindex(models)
            ax.bar(x+offset,zz.brier_mean,.34,yerr=zz.brier_std.fillna(0),capsize=3,label=arm,color=colors[arm])
        for base,style in [('cal_prior','--'),('momentum20',':'),('mean_reversion5','-.')]:
            ax.axhline(z[z.model==base].brier_mean.iloc[0],label=base,linestyle=style,linewidth=1.2)
        ax.set_xticks(x,models,rotation=25);ax.set_title(ticker);ax.set_ylabel('5-day Brier (lower is better)');ax.legend(fontsize=8)
        lo=min(z.brier_mean.min()-.007,.21);ax.set_ylim(max(0,lo),max(.26,z[~z.model.str.startswith('hard')].brier_mean.max()+.01))
    fig.suptitle('Mean of five seed scores; error bars = seed SD (not inferential CI)')
    save(fig,'01_brier_h5','Primary Brier comparison')
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
    for ax,ticker in zip(axs,['AAPL','TSLA']):
        z=t[(t.ticker==ticker)&(t.comparison=='feature_gain')].set_index('model').reindex(models[1:])
        yy=np.arange(4);mid=z.difference.to_numpy()
        ax.hlines(yy,z.bootstrap_ci_low,z.bootstrap_ci_high,color='#486D94');ax.scatter(mid,yy,color='#DF7B38')
        ax.axvline(0,color='black',linestyle='--',linewidth=1);ax.set_yticks(yy,models[1:]);ax.set_title(ticker)
        ax.set_xlabel('Brier gain A - B; pointwise block-bootstrap 95% CI')
    save(fig,'02_feature_gains','Multi-scale feature gain (see corrected p values in CSV)')
    fig,axs=plt.subplots(1,2,figsize=(11,4.8),sharey=True)
    for ax,ticker in zip(axs,['AAPL','TSLA']):
        for model in models:
            z=r[(r.ticker==ticker)&(r.horizon==5)&(r.arm=='B')&(r.model==model)&(r.mean_seed_count>=5)]
            ax.plot(z.mean_probability,z.observed_frequency,'o-',label=model,linewidth=1,markersize=4)
        ax.plot([0,1],[0,1],'k--',linewidth=.8);ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_title(ticker+' / B')
        ax.set_xlabel('Predicted reversal probability');ax.set_ylabel('Observed reversal fraction');ax.legend(fontsize=8)
    save(fig,'03_reliability','Fixed ten-bin calibration (bins with >=5 mean seed observations)')
    groupnames=['all','extreme5_up','extreme5_down','conflict_up','conflict_down','VIX_high','VIX_low','VXN_high','VXN_low']
    fig,axs=plt.subplots(1,2,figsize=(14,5),sharey=True)
    for ax,ticker in zip(axs,['AAPL','TSLA']):
        z=s[(s.ticker==ticker)&(s.horizon==5)];prior=z[z.model=='cal_prior'].set_index('group').brier_mean
        matrix=[]
        for model in models:
            zz=z[(z.model==model)&(z.arm=='B')].set_index('group').brier_mean
            matrix.append((1-zz.reindex(groupnames)/prior.reindex(groupnames)).to_numpy())
        matrix=np.asarray(matrix).T;v=max(.05,min(.5,np.nanmax(np.abs(matrix))))
        im=ax.imshow(matrix,aspect='auto',cmap='RdBu',vmin=-v,vmax=v)
        ax.set_xticks(np.arange(5),models,rotation=30);ax.set_yticks(np.arange(len(groupnames)),groupnames);ax.set_title(ticker+' / B')
        fig.colorbar(im,ax=ax,label='Brier skill vs same-state calibrated prior')
    save(fig,'04_state_skill','Conditional-event diagnostics of all-day models; descriptive')
    fig,axs=plt.subplots(1,2,figsize=(12,4.5),sharey=True)
    for ax,ticker in zip(axs,['AAPL','TSLA']):
        for j,arm in enumerate(['A','B']):
            for i,model in enumerate(models):
                vals=seeds[(seeds.ticker==ticker)&(seeds.model==model)&(seeds.arm==arm)].brier.to_numpy()
                pos=i+(j-.5)*.28;ax.scatter(pos+np.linspace(-.04,.04,len(vals)),vals,color=colors[arm],alpha=.8,s=22)
                ax.plot([pos-.07,pos+.07],[vals.mean()]*2,color='black',linewidth=1.5)
        ax.set_xticks(range(5),models,rotation=25);ax.set_title(ticker);ax.set_ylabel('5-day Brier; A blue / B orange')
    save(fig,'05_seed_stability','Five seeds; horizontal ticks are arithmetic seed means')
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
    for ax,ticker in zip(axs,['AAPL','TSLA']):
        for model in models:
            vals=[]
            for h in [1,5,20]:
                zz=m[(m.ticker==ticker)&(m.horizon==h)];p=zz[zz.model=='cal_prior'].brier_mean.iloc[0]
                b=zz[(zz.model==model)&(zz.arm=='B')].brier_mean.iloc[0];vals.append(1-b/p)
            ax.plot([1,5,20],vals,'o-',label=model)
        ax.axhline(0,color='black',linestyle='--',linewidth=1);ax.set_xticks([1,5,20]);ax.set_title(ticker+' / B');ax.set_xlabel('Horizon (trading days)');ax.set_ylabel('Brier skill vs calibrated prior');ax.legend(fontsize=8)
    save(fig,'06_horizon_skill','Primary 5-day and secondary 1-/20-day horizons')
    raw=pd.read_csv(out/'tables/metrics_comparison.csv')
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
    for ax,ticker in zip(axs,['AAPL','TSLA']):
        zz=raw[(raw.ticker==ticker)&(raw.horizon==5)&(raw.arm=='B')].pivot(index='model',columns='probability',values='brier_mean').reindex(models)
        for name,offset,color in [('raw',-.15,'#999999'),('calibrated',.15,'#3B6FB6')]:ax.bar(np.arange(5)+offset,zz[name],.28,label=name,color=color)
        ax.set_xticks(range(5),models,rotation=25);ax.set_title(ticker+' / B');ax.set_ylabel('Brier');ax.legend()
    save(fig,'07_calibration_effect','Fixed calibration, not selected from test results')
    content='<!doctype html><meta charset="utf-8"><title>E3b figures</title><style>body{max-width:1200px;margin:auto;font-family:sans-serif}img{width:100%}</style><h1>E3b research figures</h1>'
    for name,title in figures:content+=f'<h2>{html.escape(title)}</h2><a href="{name}.pdf">PDF</a><img src="{name}.png" alt="{html.escape(title)}">'
    (figdir/'index.html').write_text(content)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args();plot(args.out)
