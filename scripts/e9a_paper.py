"""Render manuscript text/tables and figures from existing E9a aggregate selections."""
import csv,io,json,re
from pathlib import Path
from e9a_build import mdtable

def read(p):return list(csv.DictReader(io.StringIO(p.read_text())))
def main(out):
 if (out/'MANUSCRIPT_VERSION.json').exists() and __import__('json').loads((out/'MANUSCRIPT_VERSION.json').read_text()).get('stage')=='E9b':
  from e9b_paper import main as current; return current(out,Path(__file__).resolve().parents[1])
 t5=read(out/'tables/E5_technical_increments.csv');t6=read(out/'tables/E6_fusion_controls.csv');t4=read(out/'tables/E4c_event_models.csv');d4=read(out/'tables/E4c_event_contrasts.csv')
 fmt=lambda x:format(float(x),'.6f') if x else '—'
 stages=[['E0–E2','AAPL/TSLA; old magnitude cohorts','2012–22 / 2023 / 2024–25','Price/magnitude; not direction classification'],['E3','AAPL/TSLA; 482 common classifier dates each','2012–22 / 2023 / 2024–25','Events; next-open reversal in E3b/c'],['E4c','AAPL; 230 test dates, 65 extreme dates','2023 / 2024 / 2025','Price/news, date-proxy timing; 22 nonoverlap events'],['E5','AAPL/TSLA; 482 test dates each','2012–22 / 2023 / 2024–25','B38 versus T51; five seeds'],['E6','Same 482 dates each; 9 test vintages each','Same as E5','P=E5 T; F16; neural P reused'],['E7–E8a.1','Data/protocol audits; no new prediction task','Development/audit scope only','Qualification, access and future inference design']]
 replacement={'STAGE_TABLE':mdtable(['Stage','Population and unit','Fit / validate / evaluate years','Interpretation'],stages),
 'E5_TABLE':mdtable(['Stock / model','B','T','Benefit B−T','95% interval','HAC / bootstrap Holm8'],[[r['ticker']+' / '+r['model'],fmt(r['B_Brier']),fmt(r['T_Brier']),fmt(r['gain']),'['+fmt(r['ci_low'])+', '+fmt(r['ci_high'])+']',f"{float(r['HAC_Holm']):.4f} / {float(r['bootstrap_Holm']):.4f}"] for r in t5]),
 'E6_TABLE':mdtable(['Stock / expert','P','F logistic','Early','Late','Constant mix','F weight'],[[r['ticker']+' / '+r['model'],fmt(r['P']),fmt(r['F']),fmt(r['Early']),fmt(r['Late']),fmt(r['constant_blend']),r['F_weight']] for r in t6]),
 'E4_TABLE':mdtable(['Method','Brier','Log loss','AUC'],[[r['method'],fmt(r['Brier']),fmt(r['Log_loss']),fmt(r['AUC'])] for r in t4]),
 'E4_TEST_TABLE':mdtable(['Contrast / family','Benefit','95% interval','HAC / bootstrap Holm2'],[[r['contrast']+' / '+r['family'],fmt(r['gain']),'['+fmt(r['ci_low'])+', '+fmt(r['ci_high'])+']',f"{float(r['HAC_Holm']):.6f} / {float(r['bootstrap_Holm']):.4f}"] for r in d4]),
 'REFERENCES':(out/'literature/REFERENCES.md').read_text()}
 text=(out/'PAPER_TEMPLATE.md').read_text()
 for key,value in replacement.items():text=text.replace('{{'+key+'}}',value)
 assert '{{' not in text
 text=text.rstrip()+'\n'
 (out/'PAPER_DRAFT.md').write_text(text)
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 import numpy as np
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':130,'savefig.dpi':180})
 fig,axes=plt.subplots(1,2,figsize=(10,3.8),sharex=True)
 for ax,stock in zip(axes,['AAPL','TSLA']):
  a=[r for r in t5 if r['ticker']==stock];y=np.arange(len(a));v=np.array([float(r['gain']) for r in a]);lo=np.array([float(r['ci_low']) for r in a]);hi=np.array([float(r['ci_high']) for r in a]);ax.errorbar(v,y,xerr=[v-lo,hi-v],fmt='o',capsize=3,color='#235789');ax.set_yticks(y,[r['model'] for r in a]);ax.axvline(0,color='#999999',lw=1);ax.set_title(stock);ax.set_xlabel('Brier(B) − Brier(T)');ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
 fig.suptitle('E5 technical-feature contrasts: original pointwise intervals');fig.tight_layout();fig.savefig(out/'figures/e5_feature_gains.png');plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,3.8));x=np.arange(2);w=.23
 for j,(key,label,color) in enumerate([('P','Price P','#59656f'),('constant_blend','Matched constant mixture','#57a0ad'),('Late','Late(P,F)','#235789')]):
  a=[next(r for r in t6 if r['ticker']=='AAPL' and r['model']==m) for m in ['lstm','mamba']];v=[float(r[key]) for r in a];bars=ax.bar(x+(j-1)*w,v,w,label=label,color=color)
  for b,val in zip(bars,v):ax.text(b.get_x()+b.get_width()/2,val+.00018,f'{val:.6f}',ha='center',fontsize=8)
 ax.set_ylim(.244,.2545);ax.set_xticks(x,['LSTM price expert','Mamba price expert']);ax.set_ylabel('Existing calibrated reversal Brier');ax.set_title('E6 AAPL: fusion versus equal-weight shrinkage control');ax.legend(loc='lower left',fontsize=8);fig.tight_layout();fig.savefig(out/'figures/e6_fusion_controls.png');plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,3.9));a=d4;y=np.arange(len(a));v=np.array([float(r['gain']) for r in a]);lo=np.array([float(r['ci_low']) for r in a]);hi=np.array([float(r['ci_high']) for r in a]);ax.errorbar(v,y,xerr=[v-lo,hi-v],fmt='o',capsize=3,color='#235789');ax.set_yticks(y,[r['contrast']+(' (secondary)' if r['contrast'] not in ['S_P','T_S'] else ' (primary)') for r in a]);ax.axvline(0,color='#999999',lw=1);ax.invert_yaxis();ax.set_xlabel('Reference − candidate event Brier');ax.set_title('E4c AAPL 2025: timing-proxy event cohort only');ax.grid(axis='x',alpha=.2);fig.tight_layout();fig.savefig(out/'figures/e4c_news_gains.png');plt.close(fig)
 print('Manuscript',len(text.split()),'whitespace words; figures 3; new financial estimates 0')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
