"""Original round2 design/uncertainty figures from frozen aggregates, not new inference."""
import argparse,textwrap
from pathlib import Path
import numpy as np,pandas as pd

def main(bundle):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import FancyBboxPatch
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9.5,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':300})
 f,ax=plt.subplots(figsize=(6,2.55));ax.set_xlim(0,3);ax.set_ylim(0,3.2);ax.axis('off')
 def box(x,y,w,h,text,color):
  patch=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.03',facecolor=color,edgecolor='#506575',linewidth=.65);ax.add_patch(patch);ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=8.7)
 titles=['Technical indicators','Accounting fusion','News sentiment']
 candidates=['Prices + indicator\nrepresentations','Price + accounting\nexpert probability','Price + retained\nnews content']
 controls=['Multiscale prices +\nmarket-only control','Same-weight constant;\nmatched numeric inputs','Density-only and\nhistorical probabilities']
 for i,title in enumerate(titles):
  ax.text(i+.5,3.05,title,ha='center',va='center',fontsize=9.5,fontweight='bold');box(i+.04,2.10,.92,.58,candidates[i],'#e8eff5');box(i+.04,.93,.92,.69,controls[i],'#dcebee')
  ax.annotate('',(i+.5,1.67),(i+.5,2.06),arrowprops=dict(arrowstyle='->',color='#506575',lw=.9));ax.text(i+.5,1.86,'Compare',ha='center',va='center',fontsize=8)
 box(.04,.04,2.92,.52,'Reference loss → gain + uncertainty → ranking + provenance','#f5eee8');f.tight_layout(pad=.2);f.savefig(bundle/'figures/r2_design_overview.png',bbox_inches='tight');plt.close(f)
 data=pd.read_csv(bundle/'tables/R2_SCORE_INTERPRETATION.csv')
 choose=['fusion_AAPL_lstm_raw','fusion_AAPL_lstm_calibrated','fusion_AAPL_mamba_raw','fusion_AAPL_mamba_calibrated'];z=data.set_index('comparison_id').loc[choose]
 f,ax=plt.subplots(figsize=(6,2.15));y=np.arange(4)
 for i,r in enumerate(z.itertuples()):
  value=r.delta_Brier*1000;low=r.CI_low*1000;high=r.CI_high*1000;color='#995b43' if choose[i].endswith('_raw') else '#215c7a'
  ax.errorbar(value,y[i],xerr=[[value-low],[high-value]],fmt='s' if choose[i].endswith('_raw') else 'o',color=color,capsize=3,ms=4,lw=1)
 ax.axvline(0,c='#555555',lw=.8);ax.set_yticks(y,['LSTM, raw','LSTM, calibrated','Mamba, raw','Mamba, calibrated']);ax.invert_yaxis();ax.set_xlabel('Brier benefit beyond matched constant (×10⁻³)');ax.grid(axis='x',alpha=.18);f.tight_layout(pad=.4);f.savefig(bundle/'figures/r2_fusion_uncertainty.png',bbox_inches='tight');plt.close(f)
 # Full families retained visually; the main figure is a named mechanism illustration.
 z=data[data.comparison_id.str.startswith('technical_')];f,ax=plt.subplots(figsize=(7,3.6));value=z.delta_Brier.to_numpy()*1000;low=z.CI_low.to_numpy()*1000;high=z.CI_high.to_numpy()*1000
 ax.errorbar(value,np.arange(len(z)),xerr=[value-low,high-value],fmt='o',capsize=3,ms=4,c='#215c7a');ax.axvline(0,c='gray',lw=.8);ax.set_yticks(range(len(z)),z.stock+' '+z.model);ax.invert_yaxis();ax.set_xlabel('Technical gain (×10⁻³); original block20 pointwise CI');f.tight_layout();f.savefig(bundle/'figures/S1_all_technical.png');plt.close(f)
 z=data[data.comparison_id.str.startswith('fusion_')];f,axes=plt.subplots(1,2,figsize=(10,5.0),sharex=True)
 for ax,stock in zip(axes,['AAPL','TSLA']):
  a=z[z.stock.eq(stock)].reset_index(drop=True)
  for i,r in a.iterrows():
   v=r.delta_Brier*1000;l=r.CI_low*1000;h=r.CI_high*1000;raw=r.comparison_id.endswith('_raw');ax.errorbar(v,i,xerr=[[v-l],[h-v]],fmt='s' if raw else 'o',color='#995b43' if raw else '#215c7a',capsize=2,ms=3)
  ax.axvline(0,c='gray',lw=.8);ax.set_yticks(range(len(a)),[r.model+' '+('raw' if r.comparison_id.endswith('_raw') else 'calibrated') for r in a.itertuples()],fontsize=8);ax.invert_yaxis();ax.set_title(stock);ax.set_xlabel('Gain ×10⁻³; block60 pointwise CI')
 f.tight_layout();f.savefig(bundle/'figures/S2_all_fusion.png');plt.close(f)
 print('Two main diagrams/figures + full technical/fusion supplementary figures generated')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);main(p.parse_args().bundle)
