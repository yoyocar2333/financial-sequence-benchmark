"""Export transparent coverage/PIT feasibility figures, not fabricated news effects."""
import argparse
import json
import os
from pathlib import Path
import sys
import numpy as np
import pandas as pd


def plot(out):
    os.environ.setdefault('MPLCONFIGDIR',str(out/'.matplotlib'))
    # Reuse installed plotting packages, without changing either research venv.
    for p in (Path.home()/'.local/lib/python3.10/site-packages',Path('/usr/local/lib/python3.10/dist-packages'),Path('/usr/lib/python3/dist-packages')):
        if p.exists(): sys.path.append(str(p))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140,'savefig.dpi':180})
    fdir=out/'figures';fdir.mkdir(exist_ok=True)
    cov=pd.read_csv(out/'tables/coverage_by_year.csv');market=pd.read_csv(out/'aligned/market_news_alignment.csv.gz')
    news=pd.read_csv(out/'aligned/news_metadata_with_assumed_dates.csv');links=pd.read_csv(out/'aligned/news_event_alignment_metadata_only.csv')
    names=[]
    def save(fig,name):
        fig.savefig(fdir/(name+'.png'),bbox_inches='tight');fig.savefig(fdir/(name+'.pdf'),bbox_inches='tight');plt.close(fig);names.append(name)

    fig,ax=plt.subplots(2,1,figsize=(11,7),sharex=True,gridspec_kw={'height_ratios':[1,1.1]})
    for ticker,color in [('AAPL','#2471a3'),('TSLA','#bf502d')]:
        z=cov[cov.ticker==ticker];ax[0].plot(z.year,z.event_dates,'o-',label=ticker,color=color)
    ax[0].set(ylabel='Eligible price-event dates',title='E4a: price-event support exists; historical news support is missing');ax[0].legend(ncol=2)
    ax[1].bar([2023,2024,2025],[152,158,140],color='#dfe9ed',edgecolor='#497c90',hatch='//',label='Upstream-reported AAPL articles (full corpus unavailable)')
    ax[1].bar([2023],[100],color='#296c70',width=.4,label='Locally available real article metadata subset')
    for a in ax:
        a.axvspan(2011.5,2022.5,color='#ddd',alpha=.25);a.axvline(2022.5,color='#666',ls='--',lw=.7);a.axvline(2023.5,color='#666',ls='--',lw=.7)
        a.set_xticks(range(2012,2026));a.grid(axis='y',alpha=.15);a.set_xlim(2011.5,2025.5)
    ax[1].text(2015,90,'2012-2022 news-feature training support: 0\nTSLA news corpus: not supplied\nTrue news coverage: UNKNOWN',bbox={'facecolor':'white','edgecolor':'#ddd'})
    ax[1].set(ylabel='Articles, NOT price events',xlabel='Year (no2026 observations)');ax[1].legend(loc='upper left',fontsize=8)
    fig.tight_layout();save(fig,'01_support_timeline')

    fig,ax=plt.subplots(2,1,figsize=(11,6.5),sharex=True)
    a=market[(market.ticker=='AAPL')&market.partition.eq('validation')].copy();d=pd.to_datetime(a.date)
    ax[0].plot(d,a.past5_pp,color='#aab4bb',lw=.9)
    for direction,color,label in [(1,'#168365','Surge'),(-1,'#c54c46','Crash')]:
        z=a[a.event_direction==direction];ax[0].scatter(pd.to_datetime(z.date),z.past5_pp,color=color,s=24,label=label,zorder=3)
    ax[0].set(ylabel='Past5 log return (pp)',title='AAPL2023: fixed price events and known news metadata (not sentiment)');ax[0].legend(ncol=2)
    counts=pd.to_datetime(news.assumed_information_date).dt.to_period('W').value_counts().sort_index()
    ax[1].bar(counts.index.to_timestamp(),counts.values,width=5,color='#296c70')
    ax[1].set(ylabel='Known subset articles/week',xlabel='Assumed first session strictly after publication date')
    ax[1].text(.02,.92,'Only100/152 randomly sampled2023 articles; absent bars do not mean no news.',transform=ax[1].transAxes,va='top',fontsize=9)
    for a in ax: a.grid(axis='y',alpha=.15)
    fig.tight_layout();save(fig,'02_metadata_event_timeline')

    fig,ax=plt.subplots(figsize=(10,4.8))
    labels=['Real article metadata available','Exact publication time verified','Version first-seen evidence','Historical body version verified','Per-article sentiment/event features','2012-2022 news-feature event rows']
    values=[100,0,0,0,0,0];ys=np.arange(len(labels))
    ax.barh(ys,values,color=['#296c70']+['#a7b7c2']*5);ax.invert_yaxis();ax.set_yticks(ys,labels)
    for y,v in zip(ys,values): ax.text(v+1,y,str(v),va='center')
    ax.set(xlim=(0,115),xlabel='Verified usable records in this delivery',title='Feasibility gate fails before any news model is trained')
    fig.text(.25,.015,'Zeros describe supplied/verified data, not actual historical news activity.',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1));save(fig,'03_feasibility_gates')

    fig,ax=plt.subplots(figsize=(10,4.8))
    l=links[links.ticker.eq('AAPL')&links.partition.eq('validation')]
    c=l.groupby('relative_information_session').size().reindex(range(-5,6),fill_value=0)
    ax.bar(c.index,c.values,color=['#65898e' if x<=0 else '#d59266' for x in c.index]);ax.axvline(.5,color='#444',ls='--')
    ax.set(xticks=range(-5,6),xlabel='Assumed information-session offset relative to price event',ylabel='Article-event pairs (dependent)',title='Known2023 subset near AAPL events: descriptive alignment only')
    ax.text(.02,.95,'Post-event news is not a prediction input.\nAn article/event may appear in several pairs; no independent-pair tests.',transform=ax.transAxes,va='top',fontsize=9)
    ax.grid(axis='y',alpha=.15);fig.tight_layout();save(fig,'04_event_neighborhood')
    html='<!doctype html><html lang="en"><meta charset="utf-8"><title>E4a feasibility figures</title><style>body{font:16px sans-serif;max-width:1100px;margin:30px auto}img{width:100%;height:auto}p{line-height:1.5}</style><h1>E4a coverage and PIT feasibility</h1><p>No incremental news effects were estimated.2026 holdout remains unopened.</p>'
    for name in names: html+=f'<h2>{name}</h2><a href="{name}.pdf">PDF</a><img src="{name}.png" alt="{name}">'
    (fdir/'index.html').write_text(html)
    (fdir/'plot_environment.json').write_text(json.dumps({'matplotlib':matplotlib.__version__,'figures':names,'GPU_used':False},indent=2)+'\n')
    print('Saved4 PNG/PDF figures and HTML index')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);plot(p.parse_args().out)
