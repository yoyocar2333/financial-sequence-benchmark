"""Compact original conference figures from already-frozen aggregate tables; no new statistics."""
import argparse
from pathlib import Path
import pandas as pd,numpy as np

def main(bundle):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9.5,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150,'savefig.dpi':300})
 prob=pd.read_csv(bundle/'tables/fusion_probability_summary.csv')
 fig,axes=plt.subplots(1,2,figsize=(6,2.35),sharey=True)
 models=['logistic','xgboost','lightgbm','lstm','mamba'];x=np.arange(5)
 for ax,t in zip(axes,['AAPL','TSLA']):
  for version,color,marker,label in [('raw','#945340','s','Raw'),('calibrated','#225779','o','Calibrated')]:
   z=prob[prob.ticker.eq(t)&prob.version.eq(version)].set_index('method')
   gain=[z.loc[m+'_PriorBlend','brier_mean']-z.loc[m+'_Late','brier_mean'] for m in models]
   ax.plot(x,gain,marker+'-',label=label,c=color,ms=4,lw=1)
  ax.axhline(0,c='gray',lw=.7);ax.set_title(t);ax.set_xticks(x,['LR','XGB','LGBM','LSTM','Mamba'],rotation=25);ax.grid(alpha=.15);ax.legend(fontsize=8)
 axes[0].set_ylabel('Fusion benefit vs constant')
 fig.tight_layout(pad=.7,w_pad=1);fig.savefig(bundle/'figures/figure1_fusion_controls.png',bbox_inches='tight');plt.close(fig)
 support=pd.read_csv(bundle/'tables/news_density_support.csv');gains=pd.read_csv(bundle/'tables/news_attention_sentiment_contrasts.csv');names=['retained_0','retained_1_2','retained_3plus'];x=np.arange(3)
 a=support[support.timing.eq('next_session')&support.partition.eq('test')&support.group.eq('events')].set_index('stratum');fig,axes=plt.subplots(1,2,figsize=(6,2.35))
 axes[0].bar(x,[a.loc[n,'n'] for n in names],color='#57a0ad');axes[0].set_ylabel('Event dates');axes[0].set_xticks(x,['0 retained','1–2','3+']);axes[0].set_title('2025 retained-source support')
 for can,ref,label,color in [('lr_D','lr_P','Density beyond price','#225779'),('lr_S','lr_D','Sentiment beyond density','#945340')]:
  z=gains[gains.timing.eq('next_session')&gains.partition.eq('test')&gains.version.eq('calibrated')&gains.group.eq('events')&gains.candidate.eq(can)&gains.reference.eq(ref)].set_index('stratum');axes[1].plot(x,[z.loc[n,'Brier_gain'] for n in names],'o-',label=label,c=color,ms=4,lw=1)
 axes[1].axhline(0,c='gray',lw=.7);axes[1].set_xticks(x,['0 (n=6)','1–2 (n=30)','3+ (n=29)']);axes[1].set_ylabel('Paired Brier benefit');axes[1].legend(fontsize=7.5);axes[1].grid(alpha=.15)
 fig.tight_layout(pad=.7,w_pad=1);fig.savefig(bundle/'figures/figure2_news_density.png',bbox_inches='tight');plt.close(fig)
 print('Two original figures; all10 fusion settings and fixed news strata retained')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);main(p.parse_args().bundle)
