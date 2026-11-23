"""Conference manuscript synthesis from frozen E9b aggregate evidence; no model fitting."""
import argparse,csv,hashlib,io,json,re,shutil
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return list(csv.DictReader(io.StringIO(p.read_text())))
def table(headers,data):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in data])
def main(repo,out):
 out.mkdir(parents=True,exist_ok=True)
 for d in ['tables','figures','audits']:(out/d).mkdir(exist_ok=True)
 assert json.loads((repo/'research/E9a/MANUSCRIPT_VERSION.json').read_text())['stage']=='E9b'
 claims=[]
 def claim(path,selector,fields,description):
  rows=read(repo/path);found=[(i+1,r) for i,r in enumerate(rows) if all(r.get(k)==str(v) for k,v in selector.items())];assert len(found)==1,(path,selector)
  i,row=found[0];claims.append(dict(claim_id='ICEIB_'+str(len(claims)+1).zfill(3),claim=description,source_file=path,source_record=i,selector=json.dumps(selector,sort_keys=True),fields=json.dumps({k:row[k] for k in fields},sort_keys=True),source_sha256=sha(repo/path),status='Frozen-source exploratory evidence; original test family preserved'));return row
 # Table1 preserves all eight primary technical contrasts.
 path='research/E9a/tables/E5_technical_increments.csv';source=read(repo/path);t1=[]
 for row in source:
  c=claim(path,dict(ticker=row['ticker'],model=row['model']),list(row), 'Original primary technical comparison, every stock and architecture retained')
  t1.append([c['ticker'],c['model'],f"{float(c['B_Brier']):.6f}",f"{float(c['T_Brier']):.6f}",f"{float(c['gain']):+.6f}",f"{float(c['bootstrap_Holm']):.4f}"])
 # Compact display retains both stocks/four models; all original cells remain in the ledger.
 compact=[]
 for model in ['xgboost','lightgbm','lstm','mamba']:
  a=next(r for r in source if r['ticker']=='AAPL' and r['model']==model);b=next(r for r in source if r['ticker']=='TSLA' and r['model']==model)
  compact.append([model,f"{float(a['gain']):+.6f}",f"{float(a['bootstrap_Holm']):.4f}",f"{float(b['gain']):+.6f}",f"{float(b['bootstrap_Holm']):.4f}"])
 # Table2 includes the complete LR6 + tree6 primary-block contrast set.
 path='research/E9b/tables/development_all12_contrasts.csv';t2=[]
 for row in read(repo/path):
  if row['block']!='60':continue
  c=claim(path,dict(model=row['model'],contrast=row['contrast'],block=60),['difference','bootstrap_ci_low','bootstrap_ci_high','hac_holm6','bootstrap_holm6','hac_holm12_supplementary','bootstrap_holm12_supplementary'],'Complete development-only matched-input and allocation contrast')
  t2.append([row['model'].replace('logistic','LR').replace('xgboost','XGB').replace('lightgbm','LGBM')+' '+row['contrast'],f"{float(c['difference']):+.6f}",'['+f"{float(c['bootstrap_ci_low']):.6f}, {float(c['bootstrap_ci_high']):.6f}"+']',f"{float(c['bootstrap_holm6']):.4f}",f"{float(c['bootstrap_holm12_supplementary']):.4f}"])
 # Table3 retains all originally displayed news arms and the unconditional probability.
 path='research/E9a/tables/E4c_event_models.csv';t3=[]
 for row in read(repo/path):
  c=claim(path,dict(method=row['method']),list(row),'Original2025 Apple extreme-event cohort; all original displayed arms')
  t3.append([c['method'],f"{float(c['Brier']):.6f}",f"{float(c['Log_loss']):.6f}",f"{float(c['AUC']):.6f}"])
 tables={'TECH_TABLE':table(['Model','AAPL benefit','Holm8 p','TSLA benefit','Holm8 p'],compact),'DEV_TABLE':table(['Contrast','Benefit','95% pointwise CI','Holm6 p','Holm12 p'],t2[:6]),'NEWS_TABLE':table(['Model','Brier','Log loss','AUC'],t3)}
 # Selected narrative/figure claims, exact source rows; no new significance test.
 path='research/E9b/tables/technical_representation_joint.csv'
 for row in read(repo/path):claim(path,dict(ticker=row['ticker'],feature=row['feature']),['spearman','mean_R2','min_R2','max_R2'],'All13 indicator overlap and fixed forward reconstruction targets retained')
 path='research/E9b/tables/fusion_raw_identities.csv'
 for r in read(repo/path):claim(path,dict(ticker=r['ticker'],model=r['model']),list(r),'All ten raw matched-constant fusion diagnostics')
 path='research/E9b/tables/fusion_probability_summary.csv'
 for t in ['AAPL','TSLA']:
  for model in ['logistic','xgboost','lightgbm','lstm','mamba']:
   for arm in ['P','PriorBlend','Late']:
    for version in ['raw','calibrated']:claim(path,dict(ticker=t,method=model+'_'+arm,version=version),['brier_mean','n_dates','n_seeds','sd_probability_mean','AUC_mean'],'Raw and calibrated five-seed losses for Figure1; seeds conditional on same market path')
 for r in read(repo/'research/E9b/tables/fusion_pointwise_intervals.csv'):
  if r.get('ticker')=='AAPL' and r.get('model') in ['lstm','mamba'] and r.get('version')=='calibrated' and r.get('reference')==r.get('model','')+'_PriorBlend':claim('research/E9b/tables/fusion_pointwise_intervals.csv',{k:r[k] for k in ['ticker','model','version','candidate','reference']},list(r),'Pointwise dependence sensitivity; not replacement for original family tests')
 path='research/E9a/CLAIM_EVIDENCE_MATRIX.csv'
 existing=read(repo/path)
 for id in [c['claim_id'] for c in existing if c['claim_id'].startswith(('E4C_','E6_'))]:
  claim(path,dict(claim_id=id),['fields','significance','sample_limitations'],'Original significant secondary exception and qualification retained')
 for name,filters in [('news_density_support.csv',dict(timing='next_session')),('news_attention_sentiment_contrasts.csv',dict(timing='next_session',partition='test',version='calibrated',group='events')),('news_original_timing_tests.csv',{}),('complexity_and_seed_stability.csv',{})]:
  source='research/E9b/tables/'+name
  for row in read(repo/source):
   if not all(row.get(k)==v for k,v in filters.items()):continue
   if name=='news_density_support.csv':keys=['timing','partition','group','stratum']
   elif name=='news_attention_sentiment_contrasts.csv':keys=['timing','partition','version','group','stratum','candidate','reference']
   elif name=='news_original_timing_tests.csv':keys=['timing','version','block_length','group','family','metric','candidate','reference']
   else:keys=['ticker','model','arm']
   claim(source,{k:row[k] for k in keys},list(row),'Narrative cohort, timing, within-source contrast or archived complexity evidence')
 for block in [20,120]:claim('research/E9b/tables/development_all12_contrasts.csv',dict(model='logistic',contrast='C6',block=block),['difference','hac_holm6','bootstrap_holm6','bootstrap_holm12_supplementary'],'Allocation dependence sensitivity, preserved with principal block')
 for name in ['technical_representation_joint.csv','fusion_raw_identities.csv','fusion_probability_summary.csv','fusion_decomposition.csv','fusion_pointwise_intervals.csv','news_density_support.csv','news_attention_sentiment_contrasts.csv','news_original_timing_tests.csv','development_all12_contrasts.csv']:
  shutil.copy2(repo/'research/E9b/tables'/name,out/'tables'/name)
 refs=json.loads((repo/'research/E9a/literature/citation_catalog.json').read_text());refmap={r['id']:r for r in refs}
 text=(out/'FULL_PAPER_TEMPLATE.md').read_text()
 for key,val in tables.items():text=text.replace('{{'+key+'}}',val)
 abstract=(out/'ICEIB2027_ABSTRACT_DRAFT.md').read_text().split('## Abstract\n\n',1)[1].split('\n\n## Keywords',1)[0].strip();text=text.replace('{{ABSTRACT}}',abstract)
 order=[]
 for id in re.findall(r'\[(R\d+)\]',text):
  if id not in order:order.append(id)
 for i,id in enumerate(order,1):text=text.replace('['+id+']','['+str(i)+']')
 bib=[];mapping=[]
 abbreviations={'The Review of Financial Studies':'Rev. Financ. Stud.','The Journal of Finance':'J. Finance','Journal of the Operational Research Society':'J. Oper. Res. Soc.','International Journal of Forecasting':'Int. J. Forecast.','Monthly Weather Review':'Mon. Weather Rev.','Journal of the American Statistical Association':'J. Am. Stat. Assoc.','Journal of the Royal Statistical Society Series B: Statistical Methodology':'J. R. Stat. Soc. B'}
 for i,id in enumerate(order,1):
  if id=='R99':
   bib.append(f'{i}. Financial Sequence Benchmark. Software and Extended Results (v.3a1ab2e). https://github.com/yoyocar2333/financial-sequence-benchmark (accessed on 23 November 2026).');mapping.append(dict(number=i,original_id=id,citation_title='Versioned supplementary research materials',doi='',primary_url='https://github.com/yoyocar2333/financial-sequence-benchmark/tree/3a1ab2e1695aa28168123223d1d3fc181ae1d913/research/E9b',evidence='Own repository, immutable source commit'));continue
  r=refmap[id]
  author='; '.join(a.get('literal',a.get('family','')+', '+''.join(x[0]+'.' for x in re.split(r'[\s-]+',a.get('given','')) if x)) for a in r['authors'])
  venue=abbreviations.get(r.get('venue',''),r.get('venue',''));extra=(r.get('volume','')+', ' if r.get('volume') else '')+r.get('pages','')
  url=('doi:'+r['doi']) if r.get('doi') else r['url']
  bib.append(f"{i}. {author} {r['title'].rstrip('.')}. {venue} {r['year_cited']}{', '+extra.rstrip(', ') if extra else ''}. {url}")
  mapping.append(dict(number=i,original_id=id,citation_title=r['title'],doi=r.get('doi',''),primary_url=r.get('primary_verification_url',r['url']),evidence=r['status']))
 text=text.replace('{{REFERENCES}}','\n\n'.join(bib));assert '{{' not in text
 (out/'ICEIB2027_FULL_PAPER.md').write_text(text.rstrip()+'\n')
 for name,rows in [('SOURCE_CLAIM_LEDGER.csv',claims),('REFERENCE_MAPPING.csv',mapping)]:
  with (out/'audits'/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 metadata=dict(title='Explaining Apparent Predictive Gains in Financial Machine Learning',abstract_words=len(abstract.split()),references=len(order),source_claim_rows=len(claims),source_commit='3a1ab2e1695aa28168123223d1d3fc181ae1d913',new_financial_models=0,internal_stage_ids_in_abstract=False)
 (out/'audits/MANUSCRIPT_METADATA.json').write_text(json.dumps(metadata,indent=2)+'\n');print(json.dumps(metadata,indent=2));print('Whitespace words including tables/references',len(text.split()))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 from iceib2027_active import resolve,build
 if resolve(a.repo/'research/ICEIB2027') is not None:build(a.repo,a.out)
 else:main(a.repo,a.out)
