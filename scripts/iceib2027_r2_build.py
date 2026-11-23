"""Round2 conference revision: deterministic score interpretation, never model training."""
import argparse,csv,hashlib,io,json,re
from decimal import Decimal,localcontext
from pathlib import Path

D=Decimal
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return list(csv.DictReader(io.StringIO(p.read_text())))
def write(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data)
def table(head,data):return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(map(str,r))+' |' for r in data])
def main(repo,out):
 out.mkdir(parents=True,exist_ok=True)
 for name in ['tables','figures','audits']:(out/name).mkdir(exist_ok=True)
 evidence=[];derived=[]
 def one(file,selector):
  candidates=[(i+1,r) for i,r in enumerate(rows(repo/file)) if all(r.get(k)==str(v) for k,v in selector.items())];assert len(candidates)==1,(file,selector,len(candidates));n,r=candidates[0]
  evidence.append(dict(source_file=file,source_record=n,selector=json.dumps(selector,sort_keys=True),fields=json.dumps(r,sort_keys=True),sha256=sha(repo/file)));return r
 def comparison(id,cohort,stock,model,ref,candidate,ref_score,cand_score,delta,ci_low='',ci_high='',p='',family='',interval='',sources=None):
  a,b,e=D(ref_score),D(cand_score),D(delta);assert a>0
  assert abs((a-b)-e)<D('2e-12'),(id,a,b,e)
  with localcontext() as ctx:ctx.prec=40;percent=100*e/a
  r=dict(comparison_id=id,cohort=cohort,stock=stock,model=model,reference=ref,candidate=candidate,reference_Brier=str(a),candidate_Brier=str(b),delta_Brier=str(e),relative_percent=str(percent),CI_low=ci_low,CI_high=ci_high,interval=interval,adjusted_p=p,correction_family=family,delta_formula='reference_Brier-candidate_Brier; source paired difference retained where supplied',percent_formula='100*delta_Brier/reference_Brier; unrounded same-cohort reference; descriptive, no new inference',source_files=json.dumps(sources or []))
  derived.append(r);return r
 techfile='research/E9a/tables/E5_technical_increments.csv'
 for t in rows(repo/techfile):
  one(techfile,dict(ticker=t['ticker'],model=t['model']))
  comparison('technical_'+t['ticker']+'_'+t['model'],'market2024-2025_482dates',t['ticker'],t['model'],'Multiscale price/volatility','Added technical indicators and relative-market series',t['B_Brier'],t['T_Brier'],t['gain'],t['ci_low'],t['ci_high'],t['bootstrap_Holm'],'technical8','Original pointwise block20', [techfile])
 probfile='research/E9b/tables/fusion_probability_summary.csv';cifile='research/E9b/tables/fusion_pointwise_intervals.csv';testfile='research/E6/results/information_and_fusion_gains.csv'
 for stock in ['AAPL','TSLA']:
  for model in ['logistic','xgboost','lightgbm','lstm','mamba']:
   for version in ['raw','calibrated']:
    ref=one(probfile,dict(ticker=stock,method=model+'_PriorBlend',version=version));cand=one(probfile,dict(ticker=stock,method=model+'_Late',version=version))
    ci=one(cifile,dict(ticker=stock,model=model,version=version,candidate=model+'_Late',reference=model+'_PriorBlend'))
    test=one(testfile,dict(ticker=stock,target='reversal',lag_block=20,candidate=model+'_Late',reference=model+'_PriorBlend')) if version=='calibrated' else None
    comparison('fusion_'+stock+'_'+model+'_'+version,'market2024-2025_482dates',stock,model,'Same-weight constant shrinkage','Accounting expert fusion',ref['brier_mean'],cand['brier_mean'],ci['difference'],ci['bootstrap_ci_low'],ci['bootstrap_ci_high'],test['bootstrap_p_holm_family'] if test else '', 'original_fusion20' if test else 'no_new_test','Existing exploratory pointwise block60',[probfile,cifile]+([testfile] if test else []))
 # All development comparisons retained, with the exact equal-stock mean reference.
 metricfile='research/E9b/tables/development_metrics.csv';treefile='research/E9b/tables/tree_control_metrics.csv';devfile='research/E9b/tables/development_all12_contrasts.csv'
 for item in rows(repo/devfile):
  one(devfile,dict(model=item['model'],contrast=item['contrast'],block=item['block']))
  ref=[];cand=[]
  for stock in ['AAPL','TSLA']:
   if item['model']=='logistic':
    rf=one(metricfile,dict(ticker=stock,method=item['reference']));cf=one(metricfile,dict(ticker=stock,method=item['candidate']))
   else:
    rf=one(treefile,dict(ticker=stock,model=item['model'],arm=item['reference']));cf=one(treefile,dict(ticker=stock,model=item['model'],arm=item['candidate']))
   ref.append(D(rf['brier']));cand.append(D(cf['brier']))
  comparison('development_'+item['model']+'_'+item['contrast']+'_block'+item['block'],'development2017-2022_1450dates_each','equal-stock AAPL/TSLA',item['model'],item['reference'],item['candidate'],str(sum(ref)/2),str(sum(cand)/2),item['difference'],item['bootstrap_ci_low'],item['bootstrap_ci_high'],item['bootstrap_holm6'],'LR6_or_tree6; Holm12 separately retained in full source','Pointwise synchronized block'+item['block'],[devfile,metricfile if item['model']=='logistic' else treefile])
 newsmetrics='research/E9a/tables/E4c_event_models.csv';newstests='research/E4c/results/paired_tests.csv'
 pairs=[('lr_D','lr_P','secondary_density_sentiment2'),('lr_S','lr_D','secondary_density_sentiment2'),('lr_S','lr_P','primary_LR_news2'),('lr_T','lr_S','primary_LR_news2'),('hier_S','hier_P','secondary_hier_news2'),('hier_T','hier_S','secondary_hier_news2')]
 for candidate,reference,family in pairs:
  r=one(newsmetrics,dict(method=reference));c=one(newsmetrics,dict(method=candidate));test=one(newstests,dict(timing='next_session',version='calibrated',block_length=20,group='events',family=family,metric='Brier',candidate=candidate,reference=reference))
  comparison('news_'+candidate+'_vs_'+reference,'Apple_news2025_65events','AAPL','logistic' if candidate.startswith('lr') else 'hierarchical',reference,candidate,r['Brier'],c['Brier'],test['difference'],test['bootstrap_ci_low'],test['bootstrap_ci_high'],test['bootstrap_holm2'],family,'Original pointwise block20',[newsmetrics,newstests])
 for candidate in ['lr_S','hier_S','hier_T']:
  r=one(newsmetrics,dict(method='global'));c=one(newsmetrics,dict(method=candidate))
  comparison('news_'+candidate+'_vs_global','Apple_news2025_65events','AAPL','descriptive historical-prior control','global',candidate,r['Brier'],c['Brier'],str(D(r['Brier'])-D(c['Brier'])),family='DESCRIPTIVE_ONLY_NO_NEW_TEST',sources=[newsmetrics])
 # Every original news arm, indicator target, decomposition and sensitivity is indexable.
 extras=[('research/E9b/tables/technical_representation_joint.csv',['ticker','feature']),('research/E9b/tables/fusion_decomposition.csv',['ticker','method','version','bins']),('research/E9b/tables/news_original_timing_tests.csv',['timing','version','block_length','group','family','metric','candidate','reference']),('research/E9b/tables/development_prequential_weights.csv',['ticker','fold','model'])]
 for file,keys in extras:
  for r in rows(repo/file):one(file,{k:r[k] for k in keys})
 for r in rows(repo/newsmetrics):one(newsmetrics,dict(method=r['method']))
 for file,keys in [('research/E9b/tables/news_density_support.csv',['density_stratum']),('research/E9b/tables/news_density_conditioned_metrics.csv',['density_stratum','method']),('research/E9b/tables/news_attention_sentiment_contrasts.csv',['density_stratum'])]:
  for r in rows(repo/file):
   if r.get('timing')!='next_session' or r.get('partition')!='test' or r.get('group')!='events':continue
   if r.get('version','calibrated')!='calibrated':continue
   one(file,r)
 write(out/'tables/R2_SCORE_INTERPRETATION.csv',derived);write(out/'audits/R2_SOURCE_EVIDENCE.csv',evidence)
 byid={r['comparison_id']:r for r in derived}
 def f(x,n=3):return f'{D(x):.{n}f}'
 def scaled(x,n=3):return f'{D(x)*1000:+.{n}f}'
 neural=[]
 for stock in ['AAPL','TSLA']:
  for model in ['lstm','mamba']:
   r=byid['fusion_'+stock+'_'+model+'_calibrated']
   neural.append([stock+' '+('Mamba' if model=='mamba' else 'LSTM'),f(r['reference_Brier'],6),scaled(r['delta_Brier']),f(r['relative_percent']), '['+scaled(r['CI_low'])+', '+scaled(r['CI_high'])+']'])
 news=[]
 display=[('news_lr_D_vs_lr_P','Price → +density'),('news_lr_S_vs_lr_D','Density included → +sentiment'),('news_lr_S_vs_lr_P','Price → +density/sentiment'),('news_hier_S_vs_hier_P','Hierarchical price → +sentiment'),('news_hier_S_vs_global','Historical prior → hierarchical news')]
 for key,label in display:
  r=byid[key];news.append([label,f(r['reference_Brier'],6),scaled(r['delta_Brier']),f(r['relative_percent']),f(r['adjusted_p'],4) if r['adjusted_p'] else 'Descriptive'])
 synthesis=[
 ['Technical indicators','Prices and relative-market-only inputs','Eight contrasts: no corrected positive gain; association ≠ stable transfer.'],
 ['Accounting fusion','Same-weight constant shrinkage','All ten raw gains negative; small calibrated gains have intervals spanning zero.'],
 ['Accounting numbers','Matched metadata, zeros and duplicated prices','Six tree contrasts: adjusted p≥0.4032; no established numerical-content gain.'],
 ['Sequential allocation','Constants and prior-selected single expert','Adjusted p=0.024/0.048; block120 p=0.0744; entirely initialization.'],
 ['News sentiment','Density and historical probability','Primary p=0.1512; secondary p=0.028 is delay-sensitive; prior scores better.']]
 replacements={'FUSION_TABLE':table(['Stock / model','Reference Brier','Gain ×10³','Gain (%)','95% CI ×10³'],neural),'NEWS_TABLE':table(['Comparison','Reference Brier','Gain ×10³','Gain (%)','Adjusted p'],news),'SYNTHESIS_TABLE':table(['Question / information','Critical control','Observed evidence and interpretation'],synthesis)}
 text=(out/'REVISED_PAPER_TEMPLATE.md').read_text()
 for key,value in replacements.items():text=text.replace('{{'+key+'}}',value)
 # Percentages are inserted from full-precision original same-cohort references.
 percentages={'TECH_TSLA_PERCENT':'technical_TSLA_xgboost','LSTM_PERCENT':'fusion_AAPL_lstm_calibrated','MAMBA_PERCENT':'fusion_AAPL_mamba_calibrated','NEWS_DENSITY_PERCENT':'news_lr_D_vs_lr_P','NEWS_SENTIMENT_PERCENT':'news_lr_S_vs_lr_D','NEWS_TOTAL_PERCENT':'news_lr_S_vs_lr_P','NEWS_HIER_PERCENT':'news_hier_S_vs_hier_P','NEWS_PRIOR_PERCENT':'news_hier_S_vs_global','INIT_PERCENT':'development_logistic_C6_block60'}
 for key,id in percentages.items():text=text.replace('{{'+key+'}}',f(byid[id]['relative_percent']))
 abstract=(out/'ICEIB2027_REVISED_ABSTRACT.md').read_text().split('## Abstract\n\n')[1].split('\n\n## Keywords')[0].strip();text=text.replace('{{ABSTRACT}}',abstract)
 # Keep the existing conference reference set/order; additional source-method detail is supplementary.
 baseline=(repo/'research/ICEIB2027/ICEIB2027_FULL_PAPER.md').read_text();references=baseline.split('## References\n\n',1)[1];text=text.replace('{{REFERENCES}}',references.strip())
 assert '{{' not in text
 (out/'ICEIB2027_REVISED_FULL_PAPER.md').write_text(text.rstrip()+'\n')
 full=['# Cross-Experiment Results Synthesis','\n'+table(['Research question','Candidate information','Critical baseline/control','Main observed result','Statistical evidence','Scientific interpretation'],[
  ['Can indicators add to prices?','Twelve price/volume transforms plus relative-market series','Multiscale prices; relative-market-only control','Eight original primary contrasts retained; only TSLA XGBoost positive point change','No positive Holm8 result; full block20 CIs in frozen tables','Representation overlap is not conditional redundancy; forward mapping instability is diagnostic'],
  ['Does accounting fusion add information?','Reported accounting expert','Same-weight constant mixture, before/after calibration','Ten raw losses worse; calibrated neural cases small/opposite across stocks','Existing block60 CIs span0; original20-family p=1 for displayed cases','Separate calibrators can change gains without changing source information'],
  ['Do actual numbers beat input-format controls?','Seven accounting values','Same metadata/width; zero values and duplicate prices','All6LR+6tree contrasts and20/60/120 sensitivities retained','Tree-family adjusted p≥.4032; no common p across experiments','Input dimensions alone do not certify equal effective capacity'],
  ['Does sequential fusion complement experts?','Previous-fold weight allocation','Same-weight/tuned constants; prior-selected component','Gain+.005726 entirely2017–2018; later forecasts identical','LR-family p.0240; combined12 p.0480; block120 p.0744','Initialization benefit, not persistent diversification'],
  ['Does sentiment add beyond coverage?','FinBERT tone and event proportions','Price+density; hierarchical price; historical prior','Density+.021825; extra tone+.000744; prior.256489 vs hier tone.259011','Primary2 p.1512; secondaryhier2 p.028, delay-sensitive; prior difference descriptive','Source density and content differ; a weak price comparator can exaggerate apparent news benefit']]),'\nEach row retains its own cohort and correction family. Different absolute Brier scores are never ranked across rows. Relative gains in R2_SCORE_INTERPRETATION.csv divide by the corresponding unrounded reference, not by a shared0.25 constant. No percentage is a return or classification-accuracy change.']
 (out/'RESULTS_SYNTHESIS_TABLE.md').write_text('\n\n'.join(full)+'\n')
 # Complete source families, not only the neural illustration in the main text.
 labels={'C1':'Accounting values vs. zero-value control','C2':'Accounting values vs. duplicated-price control','C3':'Accounting values vs. price-only','C4':'Sequential fusion vs. same-weight shrinkage','C5':'Sequential fusion vs. independently tuned shrinkage','C6':'Sequential fusion vs. prior-selected single expert'}
 supp=['# Supplementary Results — complete comparisons',
 'All rows retain original cohorts, signs, intervals and correction families. Gain = reference Brier minus candidate Brier; ×10³ changes display units only. Relative gain (%) = 100 × gain / unrounded reference. Interval endpoints remain absolute source differences (displayed ×10³); no new inference is attached to percentages. Raw fusion rows have no newly calculated p-value. These descriptive additions do not replace the frozen E9b tables.',
 '## Table S1. All eight technical additions',table(['Stock/model','Reference','Candidate','Gain ×10³','Gain %','95% CI ×10³','Original bootstrap Holm8 p'],[[r['stock']+' '+r['model'],f(r['reference_Brier'],6),f(r['candidate_Brier'],6),scaled(r['delta_Brier']),f(r['relative_percent']),'['+scaled(r['CI_low'])+', '+scaled(r['CI_high'])+']',f(r['adjusted_p'],4)] for r in derived if r['comparison_id'].startswith('technical_')]),
 'Intervals and tests above use the original block20 analysis. All 13 reconstruction targets and complete rank correlations remain in [technical representation diagnostics](../../E9b/tables/technical_representation_joint.csv) and [the original matrix](../../E9b/tables/technical_spearman_matrix.csv). No high correlation is treated as proof of conditional redundancy.',
 '## Table S2. All ten accounting-fusion settings before/after calibration',table(['Stock/model','Stage','Constant reference','Fusion','Gain ×10³','Gain %','Existing block60 CI ×10³','Original calibrated Holm20 p'],[[r['stock']+' '+r['model'],r['comparison_id'].rsplit('_',1)[-1],f(r['reference_Brier'],6),f(r['candidate_Brier'],6),scaled(r['delta_Brier']),f(r['relative_percent']),'['+scaled(r['CI_low'])+', '+scaled(r['CI_high'])+']',f(r['adjusted_p'],4) if r['adjusted_p'] else 'Not retested'] for r in derived if r['comparison_id'].startswith('fusion_')]),
 'The CI block60 is an existing pointwise E9b diagnostic; the adjusted p column is the original E6 calibrated block20 fusion family of20. They are not a new joint test. Complete [raw/calibrated distribution summaries](../../E9b/tables/fusion_probability_summary.csv), [ten-bin decompositions including grouping remainder](../../E9b/tables/fusion_decomposition.csv), [raw identities](../../E9b/tables/fusion_raw_identities.csv) and [per-seed records](../../E9b/tables/fusion_probability_per_seed.csv) are unchanged.',
 '## Table S3. All six logistic and six tree matched controls',table(['Readable contrast (source code)','Model / block','Reference','Candidate','Gain ×10³','Gain %','95% CI ×10³','Original Holm6 p','Original Holm12 p'],[[labels[item['contrast']]+' ('+item['contrast']+')',item['model']+' / '+item['block'],f(byid['development_'+item['model']+'_'+item['contrast']+'_block'+item['block']]['reference_Brier'],6),f(byid['development_'+item['model']+'_'+item['contrast']+'_block'+item['block']]['candidate_Brier'],6),scaled(item['difference']),f(byid['development_'+item['model']+'_'+item['contrast']+'_block'+item['block']]['relative_percent']),'['+scaled(item['bootstrap_ci_low'])+', '+scaled(item['bootstrap_ci_high'])+']',f(item['bootstrap_holm6'],4),f(item['bootstrap_holm12_supplementary'],4)] for item in rows(repo/devfile)]),
 'References/candidates above are exact equal-stock means of each source score (2017–2022;1,450 dates/stock), not averages of daily independent earnings events. Six LR and six tree families stay separate; the combined12 sensitivity is reported additionally. Block20/60/120 rows remain complete. Initialization is documented in [foldwise choices](../../E9b/tables/development_prequential_weights.csv); actual/zero/duplicated controls share metadata and width, without a claim of equal effective capacity.',
 '## Table S4. All news predictors and nested contrasts',table(list(rows(repo/newsmetrics)[0]),[[r[k] for k in rows(repo/newsmetrics)[0]] for r in rows(repo/newsmetrics)]),
 table(['Candidate vs. reference','Reference Brier','Candidate Brier','Gain ×10³','Gain %','Original CI ×10³','Original adjusted p','Family'],[[r['candidate']+' vs. '+r['reference'],f(r['reference_Brier'],6),f(r['candidate_Brier'],6),scaled(r['delta_Brier']),f(r['relative_percent']),'['+scaled(r['CI_low'])+', '+scaled(r['CI_high'])+']' if r['CI_low'] else 'No new interval',f(r['adjusted_p'],4) if r['adjusted_p'] else 'Descriptive only',r['correction_family']] for r in derived if r['comparison_id'].startswith('news_')]),
 'P = prices; D = prices+density/existence; S = D+tone/interaction; T = S+four event-type proportions; hier = hierarchical shrinkage; global = original historical prior. These original codes are confined to the complete source tables. Same65 extreme events; these scores are never ranked against market-wide or development cohorts. Full [timing/delay/sensitivity tests](../../E9b/tables/news_original_timing_tests.csv), [density support](../../E9b/tables/news_density_support.csv), [stratified metrics](../../E9b/tables/news_density_conditioned_metrics.csv) and [density/sentiment contrasts](../../E9b/tables/news_attention_sentiment_contrasts.csv) retain sparse and negative results.',
 '## Complete settings and inference',
 'The frozen [market/technical study](../../E5/README.md), [accounting study](../../E6/E6_SUMMARY.md), [news study](../../E4c/README.md), [E9b methods and integrity](../../E9b/SUPPLEMENTARY_METHODS_AND_INTEGRITY.md) and original machine-readable tables are the authoritative settings. Brier, log loss, AUC, calibration and ranking refer to different properties. No revised model, threshold, p-value, confidence interval or financial evaluation was generated for this editorial revision.']
 (out/'SUPPLEMENTARY_RESULTS.md').write_text('\n\n'.join(supp)+'\n')
 metadata=dict(stage='ICEIB2027_R2',title='Diagnosing Apparent Predictive Gains in Financial Machine Learning',baseline='User six-page PDF and matching Word; original conference body retained as editorial baseline',abstract_words=len(abstract.split()),relative_arithmetic_rows=len(derived),source_evidence_rows=len(evidence),scientific_fits=0,new_inferential_tests=0,delta_units='Absolute Brier; table columns ×10³ explicitly scaled',references=12,sections_results=['4.1 Overview of Experimental Findings','4.2 Technical Indicators: Representation versus New Information','4.3 Fundamental Fusion: Calibration versus Information Gain','4.4 Matched Controls: Does Additional Accounting Information Help?','4.5 News Density versus Sentiment','4.6 Cross-Experiment Synthesis'])
 (out/'audits/R2_MANUSCRIPT_METADATA.json').write_text(json.dumps(metadata,indent=2)+'\n');print(json.dumps(metadata,indent=2))
 print('WORDS including tables/references',len(text.split()))
 print('PERCENTAGES',{k:f(byid[v]['relative_percent']) for k,v in percentages.items()})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.repo,a.out)
