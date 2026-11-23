"""Research figures from locked supplementary tables; all settings retained."""
import argparse
import numpy as np,pandas as pd
from pathlib import Path
from e9b_core import O,save

def main(out):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from scipy.cluster.hierarchy import dendrogram
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10.5,'figure.dpi':130,'savefig.dpi':220,'axes.spines.top':False,'axes.spines.right':False})
 read=lambda n:pd.read_csv(out/'tables'/n)
 red=read('technical_redundancy.csv');rec=read('technical_reconstruction_summary.csv');data=red.merge(rec,left_on=['ticker','technical_feature'],right_on=['ticker','feature'],validate='one_to_one')
 save(data,out/'tables/technical_representation_joint.csv')
 features=data.feature.drop_duplicates().tolist();ids={name:i+1 for i,name in enumerate(features)}
 labels={'ma_gap_atr':'MA gap','ma_cross':'MA cross','rsi_center':'RSI','macd_hist_atr':'MACD','bb_z':'BB position','bb_width':'BB width','range_position20':'range position','breakout20':'breakout','volume_logratio20':'volume ratio','breakout_confirmed':'volume-confirmed','adx_scaled':'ADX','di_balance':'DI balance','relative_qqq20':'QQQ relative'}
 fig,axes=plt.subplots(1,2,figsize=(7.8,4.3),sharey=True)
 for ax,t in zip(axes,['AAPL','TSLA']):
  z=data[data.ticker.eq(t)];ax.scatter(z.absolute_spearman,z.mean_R2,c='#235789',s=24)
  for r in z.itertuples():
   offset={5:(-8,9),7:(5,-12),3:(4,9),12:(5,-10),13:(-12,-11)}.get(ids[r.feature],(4,4))
   ax.annotate(str(ids[r.feature]),(r.absolute_spearman,r.mean_R2),xytext=offset,textcoords='offset points',fontsize=8)
  ax.set_title(t);ax.axhline(0,lw=.7,color='gray');ax.set_yscale('symlog',linthresh=.5);ax.set_xlim(0,1.05);ax.set_xlabel('Strongest training |Spearman|');ax.grid(alpha=.15)
 axes[0].set_ylabel('Mean forward reconstruction R²\nsymlog scale')
 proxies=[plt.Line2D([],[],ls='none') for name in features];fig.legend(proxies,[str(ids[n])+' '+labels[n] for n in features],loc='lower center',ncol=4,fontsize=7.5,handlelength=0,handletextpad=0,columnspacing=1.2,bbox_to_anchor=(.5,.0))
 fig.tight_layout(rect=[0,.21,1,1]);fig.savefig(out/'figures/F1_representation.png');fig.savefig(out/'figures/F1_representation.pdf');plt.close(fig)
 # Full correlation matrices and fixed average-linkage dendrograms in supplementary material.
 mat=read('technical_spearman_matrix.csv');order=read('technical_cluster_order.csv')
 for t in ['AAPL','TSLA']:
  cols=order[order.ticker.eq(t)].sort_values('rank').feature.tolist();wide=mat[mat.ticker.eq(t)].pivot(index='feature_a',columns='feature_b',values='spearman').reindex(index=cols,columns=cols)
  fig,ax=plt.subplots(figsize=(12,10));im=ax.imshow(wide,vmin=-1,vmax=1,cmap='RdBu_r');ax.set_xticks(range(len(cols)),cols,rotation=90,fontsize=6);ax.set_yticks(range(len(cols)),cols,fontsize=6);ax.set_title(t+' | training Spearman, clustered 1-|rho|');fig.colorbar(im,ax=ax,shrink=.7);fig.tight_layout();fig.savefig(out/'figures'/f'S1_correlation_{t}.png');plt.close(fig)
  fig,ax=plt.subplots(figsize=(12,4));link=read(f'technical_linkage_{t}.csv');original=mat[mat.ticker.eq(t)].feature_a.drop_duplicates().tolist();dendrogram(link.to_numpy(),labels=original,leaf_rotation=90,leaf_font_size=6,ax=ax);ax.set_title(t+' | fixed average-linkage feature clustering');ax.set_ylabel('1 - |Spearman|');fig.tight_layout();fig.savefig(out/'figures'/f'S2_clusters_{t}.png');plt.close(fig)
 prob=read('fusion_probability_summary.csv');dec=read('fusion_decomposition.csv');identity=read('fusion_raw_identities.csv')
 fig,axes=plt.subplots(2,2,figsize=(7.8,5.9))
 colors={'P':'#59656f','PriorBlend':'#57a0ad','Late':'#235789'};labels={'P':'Price','PriorBlend':'Constant shrink','Late':'Fundamental fusion'}
 for ax,model in zip(axes[0],['lstm','mamba']):
  for arm in ['P','PriorBlend','Late']:
   z=prob[prob.ticker.eq('AAPL')&prob.method.eq(model+'_'+arm)].set_index('version');ax.plot([0,1],[z.loc['raw','brier_mean'],z.loc['calibrated','brier_mean']],'o-',label=labels[arm],c=colors[arm],lw=1.3)
  ax.set_xticks([0,1],['Raw','Calibrated']);ax.set_title('AAPL '+model.upper());ax.set_ylabel('Mean seed Brier');ax.legend(fontsize=8);ax.grid(alpha=.15)
 for ax,model in zip(axes[1],['lstm','mamba']):
  z=dec[dec.ticker.eq('AAPL')&dec.version.eq('calibrated')&dec.bins.eq(10)].set_index('method');x=np.arange(3)
  ax.bar(x-.17,[z.loc[model+'_'+a,'reliability'] for a in ['P','PriorBlend','Late']],.34,color='#c58b6f',label='Reliability penalty')
  ax.bar(x+.17,[z.loc[model+'_'+a,'resolution'] for a in ['P','PriorBlend','Late']],.34,color='#57a0ad',label='Resolution term')
  ax.set_xticks(x,['Price','Const.','Fusion']);ax.set_ylabel('Binned component (10 bins)');ax.set_title('Calibrated score diagnostics');ax.legend(fontsize=8)
 fig.tight_layout();fig.savefig(out/'figures/F2_fusion_calibration.png');fig.savefig(out/'figures/F2_fusion_calibration.pdf');plt.close(fig)
 reliability=read('fusion_reliability_bins.csv');fig,axes=plt.subplots(1,2,figsize=(10,4))
 for ax,t in zip(axes,['AAPL','TSLA']):
  ax.plot([0,1],[0,1],'--',c='gray')
  for m in ['lstm_P','lstm_Late','lstm_PriorBlend','mamba_P','mamba_Late','mamba_PriorBlend']:
   z=reliability[reliability.ticker.eq(t)&reliability.method.eq(m)&reliability.estimator.eq('probability_ensemble')];ax.plot(z.mean_probability,z.observed_rate,'o-',label=m,ms=3,lw=.7)
  ax.set_title(t+' | probability-ensemble visualization');ax.set_xlim(.2,.8);ax.set_ylim(0,1);ax.set_xlabel('Mean forecast within bin');ax.set_ylabel('Observed event fraction');ax.legend(fontsize=6)
 fig.tight_layout();fig.savefig(out/'figures/S3_reliability.png');plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(10,3.5))
 for ax,t in zip(axes,['AAPL','TSLA']):
  z=identity[identity.ticker.eq(t)];ax.scatter(z.P_raw_SD,z.F_weight,c='#235789')
  for r in z.itertuples():ax.annotate(r.model,(r.P_raw_SD,r.F_weight),xytext=(3,3),textcoords='offset points',fontsize=7)
  ax.set_title(t);ax.set_ylim(-.05,1.1);ax.set_xlabel('Price forecast raw SD');ax.set_ylabel('Original fixed fundamental weight')
 fig.tight_layout();fig.savefig(out/'figures/S4_weights_dispersion.png');plt.close(fig)
 c=read('development_six_contrasts.csv');c=c[c.primary_block.eq(True)];fig,ax=plt.subplots(figsize=(8,3.8));v=c.difference.to_numpy();ax.errorbar(v,np.arange(6),xerr=[v-c.bootstrap_ci_low,c.bootstrap_ci_high-v],fmt='o',capsize=3,c='#235789');ax.set_yticks(range(6),c.contrast+' '+c.candidate+' vs '+c.reference,fontsize=8);ax.axvline(0,c='gray',lw=.8);ax.set_xlabel('Pooled conditional-on-two-stocks Brier gain; block60 pointwise CI');ax.invert_yaxis();fig.tight_layout();fig.savefig(out/'figures/S5_development_controls.png');plt.close(fig)
 support=read('news_density_support.csv');gains=read('news_attention_sentiment_contrasts.csv');old=read('news_original_timing_tests.csv');corr=read('news_density_sentiment_correlations.csv')
 fig,axes=plt.subplots(2,2,figsize=(7.8,5.7));names=['retained_0','retained_1_2','retained_3plus'];x=np.arange(3)
 a=support[support.timing.eq('next_session')&support.partition.eq('test')&support.group.eq('events')].set_index('stratum')
 axes[0,0].bar(x,[a.loc[n,'n'] for n in names],color='#57a0ad');axes[0,0].set_xticks(x,['0 retained','1-2','3+']);axes[0,0].set_ylabel('2025 event dates');axes[0,0].set_title('Retained-source density support')
 for can,ref,label,color in [('lr_D','lr_P','Density beyond price','#235789'),('lr_S','lr_D','Sentiment beyond density','#c58b6f')]:
  z=gains[gains.timing.eq('next_session')&gains.partition.eq('test')&gains.version.eq('calibrated')&gains.group.eq('events')&gains.candidate.eq(can)&gains.reference.eq(ref)].set_index('stratum');axes[0,1].plot(x,[z.loc[n,'Brier_gain'] for n in names],'o-',label=label,c=color)
 axes[0,1].axhline(0,c='gray',lw=.7);axes[0,1].set_xticks(x,['0 retained\n(n=6)','1-2\n(n=30)','3+\n(n=29)'],fontsize=8);axes[0,1].set_ylabel('Descriptive paired Brier gain');axes[0,1].legend(fontsize=8)
 z=old[old.candidate.eq('hier_S')&old.reference.eq('hier_P')].set_index('timing');timings=['next_session','delay1','delay2'];v=z.loc[timings,'difference'].to_numpy();lo=z.loc[timings,'bootstrap_ci_low'].to_numpy();hi=z.loc[timings,'bootstrap_ci_high'].to_numpy();axes[1,0].errorbar(x,v,yerr=[v-lo,hi-v],fmt='o',capsize=3,c='#235789');axes[1,0].set_xticks(x,['Next session','+1 session','+2 sessions']);axes[1,0].axhline(0,c='gray',lw=.7);axes[1,0].set_ylabel('Hierarchical S-P gain');axes[1,0].set_title('Original pointwise timing intervals')
 z=corr[corr.timing.eq('next_session')&corr.feature_y.eq('signed_mean')].set_index('partition');axes[1,1].bar(x,[z.loc[n,'spearman'] for n in ['train','validation','test']],color=['#235789','#57a0ad','#b9c7d6']);axes[1,1].set_xticks(x,['2023\ntraining','2024\nvalidation','2025\nexplored']);axes[1,1].set_ylim(0,.5);axes[1,1].set_ylabel('Density / mean tone Spearman');axes[1,1].set_title('Retained-news days only')
 fig.tight_layout(pad=1.5,h_pad=2.0,w_pad=1.3);fig.savefig(out/'figures/F3_attention_sentiment.png',bbox_inches='tight');fig.savefig(out/'figures/F3_attention_sentiment.pdf',bbox_inches='tight');plt.close(fig)
 print('Main figures3, supplementary figures7; every technical target and both stocks retained')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=O);main(p.parse_args().out)
