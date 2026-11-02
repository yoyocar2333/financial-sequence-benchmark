"""Standalone Matplotlib publication plots; stdlib CSV, no analysis-env edits."""
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

OUT=Path(sys.argv[1]).resolve();FIG=OUT/'figures'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
    'axes.spines.right':False,'figure.dpi':110,'savefig.dpi':180,'svg.fonttype':'none'})
COLORS={'AAPL':'#267ca8','TSLA':'#c76b32','up':'#bd4f4f','down':'#367aaa'}
manifest=[]


def rows(name):
    with (OUT/'tables'/name).open() as f:return list(csv.DictReader(f))


def num(x):
    try:return float(x)
    except (TypeError,ValueError):return np.nan


def pick(data,**kw):return [r for r in data if all(r[k]==str(v) for k,v in kw.items())]


def finish(fig,name,title):
    fig.suptitle(title,fontsize=15,fontweight='bold')
    fig.tight_layout(rect=[0,0,1,.94])
    for ext in ('png','svg','pdf'):fig.savefig(FIG/f'{name}.{ext}',bbox_inches='tight')
    plt.close(fig);manifest.append({'stem':name,'title':title})


def probability_contrasts():
    data=rows('statistical_tests.csv');fig,axes=plt.subplots(1,2,figsize=(12,5),sharex=True)
    for ax,ticker in zip(axes,('AAPL','TSLA')):
        r=pick(data,ticker=ticker,family='primary',comparison='event_vs_unconditional',metric='reversal',bandwidth=60)
        r=sorted(r,key=lambda x:(int(x['side']),int(x['horizon'])))
        for i,x in enumerate(r):
            y=len(r)-1-i;d=100*num(x['difference']);low=100*num(x['bootstrap_ci_low']);high=100*num(x['bootstrap_ci_high'])
            color=COLORS['down' if x['side']=='-1' else 'up']
            ax.scatter(d,y,color=color if x['inference_status']=='OK' else '#888888',s=55,zorder=3)
            if np.isfinite(low+high):ax.plot([low,high],[y,y],color=color,lw=2)
        ax.axvline(0,color='#555',lw=1);ax.set_title(ticker)
        ax.set_yticks(range(len(r)),[f"{'Drop' if x['side']=='-1' else 'Rise'} -> {x['horizon']}d (n={x['n_a']})" for x in r][::-1])
        ax.set_xlabel('Reversal probability minus unconditional baseline (pp)')
        ax.grid(axis='x',alpha=.2)
    finish(fig,'01_reversal_probability_contrasts','Extreme 5-day moves: reversal lift and nominal block-bootstrap 95% CI')


def multihorizon():
    data=rows('event_statistics.csv');fig,axes=plt.subplots(1,2,figsize=(10,6))
    for ax,ticker in zip(axes,('AAPL','TSLA')):
        a=np.full((8,3),np.nan);ns=np.zeros((8,3),int);labels=[]
        for i,(past,side) in enumerate((p,s) for p in (5,20,60,120) for s in (-1,1)):
            labels.append(f"Past {past}d {'drop' if side<0 else 'rise'}")
            for j,h in enumerate((1,5,20)):
                r=pick(data,ticker=ticker,split='test',past_horizon=past,side=side,horizon=h,kind='raw',sample='nonoverlap',group='all')[0]
                a[i,j]=100*num(r['reversal_mean']);ns[i,j]=int(r['n_events'])
        im=ax.imshow(a,vmin=20,vmax=80,cmap='RdBu',aspect='auto')
        for i in range(8):
            for j in range(3):
                if 0<ns[i,j]<10:ax.add_patch(Rectangle((j-.5,i-.5),1,1,facecolor='white',alpha=.2,hatch='///',edgecolor='#777777',lw=0))
                label=f'{a[i,j]:.0f}%\nn={ns[i,j]}' if ns[i,j] else 'No events\nn=0'
                ax.text(j,i,label,ha='center',va='center',fontsize=9)
        ax.set_yticks(range(8),labels);ax.set_xticks(range(3),['Next 1d','Next 5d','Next 20d']);ax.set_title(ticker)
    fig.colorbar(im,ax=axes.ravel().tolist(),label='Countertrend probability (%)',fraction=.025,pad=.02)
    # Reserve explicit colorbar region instead of tight_layout overlap.
    fig.suptitle('Multi-horizon events: descriptive reversal frequencies',fontsize=15,fontweight='bold')
    fig.subplots_adjust(left=.15,right=.86,wspace=.65,top=.88,bottom=.09)
    fig.text(.5,.005,'Hatched cells: n < 10; descriptive only.',ha='center',fontsize=9)
    for ext in ('png','svg','pdf'):fig.savefig(FIG/f'02_multihorizon_reversal.{ext}',bbox_inches='tight')
    plt.close(fig);manifest.append({'stem':'02_multihorizon_reversal','title':'Multi-horizon reversal probabilities'})


def heatmap():
    data=rows('trend_combinations.csv');fig,axes=plt.subplots(1,2,figsize=(11,4.7))
    values=[]
    for ticker in ('AAPL','TSLA'):
        r=pick(data,ticker=ticker,split='test',short_horizon=5,long_horizon=120,horizon=5)
        values.extend([abs(num(x['forward_pct_mean'])) for x in r])
    lim=max(2,max(v for v in values if np.isfinite(v)))
    for ax,ticker in zip(axes,('AAPL','TSLA')):
        a=np.full((3,3),np.nan);ns=np.zeros((3,3),int)
        for x in pick(data,ticker=ticker,split='test',short_horizon=5,long_horizon=120,horizon=5):
            i=int(x['long_state'])+1;j=int(x['short_state'])+1;a[i,j]=num(x['forward_pct_mean']);ns[i,j]=int(x['n_events'])
        im=ax.imshow(a,vmin=-lim,vmax=lim,cmap='RdBu',aspect='auto')
        for i in range(3):
            for j in range(3):
                if 0<ns[i,j]<10:ax.add_patch(Rectangle((j-.5,i-.5),1,1,facecolor='white',alpha=.2,hatch='///',edgecolor='#777777',lw=0))
                label=f'{a[i,j]:+.2f}%\nn={ns[i,j]}' if ns[i,j] else 'No events\nn=0'
                ax.text(j,i,label,ha='center',va='center')
        ax.set_xticks(range(3),['Down','Neutral','Up']);ax.set_yticks(range(3),['Down','Neutral','Up'])
        ax.set_xlabel('Short 5-day state');ax.set_ylabel('Long 120-minus-5-day state');ax.set_title(ticker)
    fig.colorbar(im,ax=axes.ravel().tolist(),fraction=.025,pad=.03,label='Mean next-5d simple return (%)')
    fig.suptitle('Trend conflict map | fixed 5-session grid, descriptive',fontsize=15,fontweight='bold')
    fig.subplots_adjust(left=.08,right=.87,wspace=.4,top=.84,bottom=.15)
    fig.text(.5,.01,'Hatched cells: n < 10; descriptive only.',ha='center',fontsize=9)
    for ext in ('png','svg','pdf'):fig.savefig(FIG/f'03_trend_conflict_heatmap.{ext}',bbox_inches='tight')
    plt.close(fig);manifest.append({'stem':'03_trend_conflict_heatmap','title':'Long-short trend state map'})


def paths():
    data=rows('event_paths.csv');fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,ticker in zip(axes,('AAPL','TSLA')):
        for side,color,label in [(-1,COLORS['down'],'After extreme drop'),(1,COLORS['up'],'After extreme rise')]:
            r=sorted(pick(data,ticker=ticker,split='test',side=side),key=lambda x:int(x['day']))
            ax.plot([0]+[int(x['day']) for x in r],[0]+[num(x['cumulative_pct_mean']) for x in r],lw=2,color=color,label=label+f" (n={r[0]['n_events']})")
        ax.axhline(0,color='#777',lw=1);ax.set_title(ticker);ax.set_xlabel('Sessions after event')
        ax.set_ylabel('Mean cumulative simple return (%)');ax.legend(fontsize=9);ax.grid(alpha=.2)
    finish(fig,'04_event_paths','Same events over time | 20-session cooldown, no within-family outcome overlap')


def regimes():
    data=rows('event_statistics.csv');fig,axes=plt.subplots(1,2,figsize=(12,4.6))
    for ax,ticker in zip(axes,('AAPL','TSLA')):
        labels=[];pos=0
        for side in (-1,1):
            for index in ('VIX','VXN'):
                for state,color in [('low','#77a9be'),('high','#cc8b56')]:
                    r=pick(data,ticker=ticker,split='test',past_horizon=5,side=side,horizon=5,kind='raw',sample='nonoverlap',group=index+'_'+state)[0]
                    val=100*num(r['reversal_mean']);bars=ax.bar(pos,val,color=color,width=.75)
                    if int(r['n_events'])<10:bars[0].set_hatch('//');bars[0].set_alpha(.5)
                    ax.text(pos,val+1.4,'n='+r['n_events'],ha='center',fontsize=8)
                    labels.append(f"{'Drop' if side<0 else 'Rise'}\n{index} {state}");pos+=1
        ax.set_xticks(range(pos),labels,rotation=55,ha='right');ax.set_ylim(0,110)
        ax.set_ylabel('Next-5d countertrend probability (%)');ax.set_title(ticker);ax.grid(axis='y',alpha=.2)
    finish(fig,'05_volatility_regimes','Volatility strata | common parent events, sparse groups are descriptive')


def robustness():
    data=rows('robustness.csv');variants=['primary','all_candidates','cooldown20','q05q95','sigma2','normalized_quantiles','naive_context','nextopen','market_excess','raw_close']
    columns=[(t,s,h) for t in ('AAPL','TSLA') for s in (-1,1) for h in (5,20)]
    a=np.full((len(variants),len(columns)),np.nan);ns=np.zeros(a.shape,int)
    for i,v in enumerate(variants):
        for j,(t,s,h) in enumerate(columns):
            r=pick(data,ticker=t,side=s,horizon=h,variant=v,group='all')[0]
            a[i,j]=100*num(r['reversal_probability_gain']);ns[i,j]=int(r['n_events'])
    fig,ax=plt.subplots(figsize=(12,7));im=ax.imshow(a,vmin=-40,vmax=40,cmap='RdBu',aspect='auto')
    for i in range(a.shape[0]):
        for j in range(a.shape[1]):ax.text(j,i,f'{a[i,j]:+.0f}pp\nn={ns[i,j]}',ha='center',va='center',fontsize=8)
    ax.set_yticks(range(len(variants)),variants);ax.set_xticks(range(len(columns)),[f"{t}\n{'Drop' if s<0 else 'Rise'} / {h}d" for t,s,h in columns])
    fig.colorbar(im,ax=ax,label='Reversal probability minus own unconditional baseline (pp)',fraction=.025)
    finish(fig,'06_robustness','Prespecified sensitivity | effect sizes, no significance selection')


def mamba():
    data=rows('mamba_event_metrics.csv');fig,axes=plt.subplots(1,2,figsize=(12,5))
    names=['all','shock_up','shock_down','expost_reversal','expost_continuation']
    for ax,ticker in zip(axes,('AAPL','TSLA')):
        for arm,offset,color in [('E1',-.18,'#397da1'),('E2b',.18,'#d58b49')]:
            r=[pick(data,ticker=ticker,arm=arm,group=g)[0] for g in names]
            vals=[num(x['mae_pp_mean']) for x in r];sd=[num(x['mae_pp_seed_sd']) for x in r]
            ax.bar(np.arange(len(names))+offset,vals,width=.34,color=color,label=arm,yerr=sd,capsize=3)
        r=[pick(data,ticker=ticker,arm='E1',group=g)[0] for g in names]
        ax.set_xticks(range(len(names)),[f'{g}\nn={x["n_dates"]}' for g,x in zip(names,r)],rotation=30,ha='right')
        ax.set_title(ticker);ax.set_ylabel('Magnitude MAE (percentage points)');ax.legend();ax.grid(axis='y',alpha=.2)
    finish(fig,'07_mamba_event_errors','Mamba magnitude errors | five-seed mean +/- seed SD; no direction forecasts')


def baselines():
    data=rows('direction_baselines.csv');fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    styles=[('train_majority','#777777'),('momentum20','#3f83a4'),('mean_reversion5','#cf8b4f'),('conflict_gate','#698b53')]
    for ax,ticker in zip(axes,('AAPL','TSLA')):
        for j,(rule,color) in enumerate(styles):
            r=[pick(data,ticker=ticker,split='test',rule=rule,horizon=h)[0] for h in (1,5,20)]
            ax.bar(np.arange(3)+(j-1.5)*.18,[100*num(x['accuracy']) for x in r],width=.17,color=color,label=rule)
        ax.set_xticks(range(3),['1 day','5 days','20 days']);ax.set_ylim(0,85);ax.set_title(ticker)
        ax.set_ylabel('Direction accuracy (%)');ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    finish(fig,'08_direction_baselines','Same-date direction rules | test-sample diagnostics, not trading returns')


for function in (probability_contrasts,multihorizon,heatmap,paths,regimes,robustness,mamba,baselines):function()
write={'matplotlib':matplotlib.__version__,'numpy':np.__version__,'python':sys.version,'figures':manifest}
(OUT/'plot_environment.json').write_text(json.dumps(write,indent=2)+'\n')
html='<!doctype html><meta charset="utf-8"><title>E3a figures</title><style>body{max-width:1200px;margin:30px auto;font-family:system-ui}img{width:100%}select{font-size:18px}</style><h1>E3a figures</h1><p>Exploratory 2024–2025 sample. Select a figure; numerical tables and definitions are in E3A_SUMMARY.md.</p><select id="choice">'
for f in manifest:html+=f'<option value="figures/{f["stem"]}.png">{f["title"]}</option>'
html+='</select><p><img id="chart" src="figures/'+manifest[0]['stem']+'.png"></p><script>document.getElementById("choice").onchange=function(){document.getElementById("chart").src=this.value}</script>'
(OUT/'FIGURES.html').write_text(html)
print('Rendered',len(manifest),'figures in PNG/SVG/PDF')
