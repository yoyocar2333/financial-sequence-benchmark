"""Third-round scientific restoration from frozen aggregates and archived calibration audits."""
import argparse,csv,io,json,hashlib
from pathlib import Path
from decimal import Decimal as D

def rows(p):return list(csv.DictReader(io.StringIO(p.read_text())))
def table(head,data):return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(map(str,r))+' |' for r in data])
def main(repo,bundle):
 old=repo/'research/ICEIB2027/round2';derived=rows(old/'tables/R2_SCORE_INTERPRETATION.csv');byid={r['comparison_id']:r for r in derived}
 f=lambda x,n=3:f'{D(str(x)):.{n}f}'
 scaled=lambda x:f'{D(str(x))*1000:+.3f}'
 models=[('xgboost','XGBoost'),('lightgbm','LightGBM'),('lstm','LSTM'),('mamba','Mamba')]
 tech=[]
 for model,name in models:
  a=byid['technical_AAPL_'+model];t=byid['technical_TSLA_'+model]
  tech.append([name,scaled(a['delta_Brier']),f(a['adjusted_p'],4),scaled(t['delta_Brier']),f(t['adjusted_p'],4)])
 neural=[]
 for stock in ['AAPL','TSLA']:
  for model in ['lstm','mamba']:
   r=byid['fusion_'+stock+'_'+model+'_calibrated'];neural.append([stock+' '+('LSTM' if model=='lstm' else 'Mamba'),f(r['reference_Brier'],6),scaled(r['delta_Brier']),f(r['relative_percent']),'['+scaled(r['CI_low'])+', '+scaled(r['CI_high'])+']'])
 cal=rows(bundle/'tables/CALIBRATION_SUMMARY.csv');bycal={r['method']:r for r in cal};audit=[]
 for model in ['lstm','mamba']:
  for arm,name in [('Late','fusion')]:
   r=bycal[model+'_'+arm];audit.append([('LSTM' if model=='lstm' else 'Mamba')+' '+name,f(r['slope_min'])+'…'+f(r['slope_max'])+' ('+r['negative_slopes']+'/5)',f(r['raw_Brier'],6)+'→'+f(r['calibrated_Brier'],6),f(r['raw_AUC'],6)+'→'+f(r['calibrated_AUC'],6)])
 synthesis=[['Technical','Multiscale prices; market-only','Eight contrasts: no corrected positive gain.'],['Accounting fusion','Same-weight constants; raw/calibration audit','Calibrated AAPL gains uncertain; TSLA gains negative.'],['Values / allocation','Matched formats; preceding-fold expert','No tree advantage; sequential gain only at startup.'],['News sentiment','Density; historical probability','Primary p=.1512; secondary p=.028 is delay-sensitive; prior scores better.']]
 replacements={'TECHNICAL_TABLE':table(['Model','AAPL gain','AAPL p','TSLA gain','TSLA p'],tech),'FUSION_TABLE':table(['Stock/model','Reference BS','Gain ×10³','Gain %','95% CI ×10³'],neural),'CALIBRATION_TABLE':table(['Pipeline','a range (negative)','Brier raw→cal','AUC raw→cal'],audit),'SYNTHESIS_TABLE':table(['Question','Critical control','Cohort-specific finding'],synthesis)}
 text=(bundle/'PAPER_TEMPLATE.md').read_text()
 for key,val in replacements.items():text=text.replace('{{'+key+'}}',val)
 percentages={'TECH_TSLA_PERCENT':'technical_TSLA_xgboost','LSTM_PERCENT':'fusion_AAPL_lstm_calibrated','MAMBA_PERCENT':'fusion_AAPL_mamba_calibrated','NEWS_DENSITY_PERCENT':'news_lr_D_vs_lr_P','NEWS_SENTIMENT_PERCENT':'news_lr_S_vs_lr_D','NEWS_TOTAL_PERCENT':'news_lr_S_vs_lr_P','NEWS_HIER_PERCENT':'news_hier_S_vs_hier_P','NEWS_PRIOR_PERCENT':'news_hier_S_vs_global','INIT_PERCENT':'development_logistic_C6_block60'}
 for key,id in percentages.items():text=text.replace('{{'+key+'}}',f(byid[id]['relative_percent']))
 abstract=(bundle/'ABSTRACT.md').read_text().split('\n\n',1)[1].strip();text=text.replace('{{ABSTRACT}}',abstract)
 text=text.replace('{{REFERENCES}}',(old/'ICEIB2027_REVISED_FULL_PAPER.md').read_text().split('## References\n\n')[1].strip())
 text=text.replace('{{EVIDENCE_COMMIT}}',json.loads((bundle/'EVIDENCE_VERSION.json').read_text())['commit'])
 text=text.replace('(figures/r2_design_overview.png)','(../round2/figures/r2_design_overview.png)')
 assert '{{' not in text
 (bundle/'ICEIB2027_FULL_PAPER.md').write_text(text.rstrip()+'\n')
 metadata=dict(stage='ICEIB2027_R3',abstract_words=len(abstract.split()),main_tables=4,main_figures=1,editable_equations=5,references=12,calibration_rows=30,pipelines=6,financial_fits=0,calibrator_fits=0,new_pvalues=0,evidence_commit=json.loads((bundle/'EVIDENCE_VERSION.json').read_text())['commit'])
 (bundle/'audits/MANUSCRIPT_METADATA.json').write_text(json.dumps(metadata,indent=2)+'\n');print(json.dumps(metadata,indent=2));print('WORDS',len(text.split()))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--bundle',type=Path,required=True);a=p.parse_args();main(a.repo,a.bundle)
