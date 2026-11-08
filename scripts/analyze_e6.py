"""Offline paired inference, diagnostics, report and archive for locked E6."""
import argparse,json,shutil,sys,zipfile,datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
from e6_core import OUT,ROOT,CPU,ALL,SEEDS,load
from e6_data import CORE,sha,dump
import e3b_protocol as bp
import e5_core as e5
from e3a_core import calendar_counts,holm,thin
from analyze_e3b import metrics,paired_inference
from analyze_e3c import within_state_auc

def md(z,columns=None,decimals=6):
    z=z[columns] if columns else z
    fmt=lambda x:f'{x:.{decimals}f}' if isinstance(x,(float,np.floating)) else str(x)
    return '| '+' | '.join(z.columns)+' |\n|'+'|'.join(['---']*len(z.columns))+'|\n'+'\n'.join('| '+' | '.join(fmt(x) for x in row)+' |' for row in z.itertuples(index=False,name=None))+'\n'

def analyze():
    z=pd.read_csv(OUT/'predictions/all_probabilities.csv.gz')
    if z.duplicated(['ticker','target','method','seed','date']).any():raise RuntimeError('Duplicate prediction keys')
    if not np.isfinite(z[['p','p_raw']]).all().all() or not z[['p','p_raw']].ge(0).all().all() or not z[['p','p_raw']].le(1).all().all():raise RuntimeError('Invalid probabilities')
    if not z.date.le('2025-12-31').all() or not z.label_date.le('2025-12-31').all():raise RuntimeError('Holdout date')
    records=[];pairrows=[];rankrows=[];staterows=[];reliability=[];quality=[]
    for (t,target,method,seed),g in z.groupby(['ticker','target','method','seed']):
        for kind,col in [('calibrated','p'),('raw','p_raw')]:records.append({'ticker':t,'target':target,'method':method,'seed':seed,'probability':kind,**metrics(g.y,g[col])})
    metric=pd.DataFrame(records);metric.to_csv(OUT/'tables/metrics_per_seed.csv',index=False)
    agg=metric.groupby(['ticker','target','method','probability']).agg(n_seeds=('seed','nunique'),n=('n','first'),brier_mean=('brier','mean'),brier_sd=('brier','std'),brier_min=('brier','min'),brier_max=('brier','max'),log_loss=('log_loss','mean'),AUC=('roc_auc','mean'),balanced_accuracy=('balanced_accuracy','mean'),MCC=('mcc','mean'),ECE10=('ece10','mean'),calibration_bias=('calibration_bias','mean')).reset_index()
    agg.to_csv(OUT/'tables/metrics_comparison.csv',index=False)
    thresholds=json.loads((OUT/'inputs/e3a_training_thresholds.json').read_text())
    counts={lag:calendar_counts(482,lag,9999,20261106+lag) for lag in [20,60,100]}
    for t in ['AAPL','TSLA']:
        f,a=load(t);ii=bp.indices(f,bp.FINAL['test_start'],bp.FINAL['test_end']);ff=f.iloc[ii];aa=a.iloc[ii]
        up,down,cell=e5.states(ff,thresholds[t]);events=up|down
        masks={'all':np.ones(482,bool),'extreme_up':up,'extreme_down':down,'extreme_any':events,'conflict':events&(np.sign(ff.past5.to_numpy())!=np.sign(ff.context120_ex5.to_numpy())),'post_release10':aa.release_age_days.to_numpy()<=14,'stale_release60plus':aa.release_age_days.to_numpy()>60,'nonoverlap5':thin(np.ones(482,bool),5),'year2024':ff.index.year==2024,'year2025':ff.index.year==2025}
        quality.append({'ticker':t,'test_dates':482,'first':str(ff.index.min().date()),'last':str(ff.index.max().date()),'test_distinct_vintages':int(aa.vintage.nunique()),'training_distinct_vintages':int(a.loc['2012-01-01':'2022-12-31'].vintage.nunique()),'extreme_event_dates':int(events.sum()),'future_flat_returns':int((ff.nextopen_log5==0).sum()),'missing_any_accounting_on_test':int(aa[CORE].isna().any(axis=1).sum()),'max_release_date_used':str(aa.release_date.max())})
        for target in ['reversal','up_direct']:
            sub=z[(z.ticker==t)&(z.target==target)];pred={};raw={};y=None
            for method,g in sub.groupby('method'):
                ps=[];rs=[]
                for seed,sg in g.groupby('seed'):
                    sg=sg.sort_values('date');np.testing.assert_array_equal(sg.date,ff.index.strftime('%Y-%m-%d'))
                    yy=ff.y5.to_numpy() if target=='reversal' else (ff.nextopen_log5.to_numpy()>0).astype(int)
                    np.testing.assert_array_equal(sg.y,yy);y=yy;ps.append(sg.p.to_numpy());rs.append(sg.p_raw.to_numpy())
                pred[method]=np.stack(ps);raw[method]=np.stack(rs)
            loss={k:np.mean((p-y)**2,axis=0) for k,p in pred.items()}
            comparisons=[]
            def add(family,can,ref,primary=True):comparisons.append({'family':family,'candidate':can,'reference':ref,'primary':primary})
            for m in ['logistic','xgboost']:
                add('H1',f'{m}_F','conditioned_prior');add('H1',f'{m}_PF',f'{m}_P')
            for m in (ALL if target=='reversal' else CPU):
                add('H3',f'{m}_Late',f'{m}_P');add('H3',f'{m}_Late',f'{m}_PriorBlend')
            for m in CPU:
                add('secondary',f'{m}_F','cal_prior',False);add('secondary',f'{m}_PF',f'{m}_F',False)
                if m=='lightgbm':add('secondary',f'{m}_PF',f'{m}_P',False)
            add('secondary','logistic_F','logistic_metadata',False)
            add('secondary','logistic_F_delay5','logistic_F',False);add('secondary','logistic_PF_delay5','logistic_PF',False)
            d=np.column_stack([loss[r['reference']]-loss[r['candidate']] for r in comparisons])
            for lag in [20,60,100]:
                inference=paired_inference(d,counts[lag],lag)
                for r,result in zip(comparisons,inference):pairrows.append({'ticker':t,'target':target,'lag_block':lag,**r,**result})
            for method,ps in pred.items():
                for group,mask in masks.items():
                    if mask.sum()==0:continue
                    values=[metrics(y[mask],p[mask]) for p in ps]
                    staterows.append({'ticker':t,'target':target,'method':method,'group':group,'n':int(mask.sum()),'seeds':len(ps),'brier':float(np.mean([v['brier'] for v in values])),'AUC':float(np.nanmean([v['roc_auc'] for v in values])),'log_loss':float(np.mean([v['log_loss'] for v in values])),'prevalence':float(y[mask].mean()),'mean_probability':float(ps[:,mask].mean())})
                if method in [m+'_'+s for m in (ALL if target=='reversal' else CPU) for s in ['P','Late']]+[m+'_'+s for m in CPU for s in ['F','PF']]:
                    for group,mask in [('all',masks['all']),('extreme_any',events)]:
                        rr=within_state_auc(y,cell,ps,mask,counts[20][:1999])
                        rankrows.append({'ticker':t,'target':target,'method':method,'group':group,'block':20,'bootstrap_reps':1999,**rr})
                pp=ps.mean(axis=0)
                for b in range(10):
                    mask=np.minimum((pp*10).astype(int),9)==b
                    if mask.any():reliability.append({'ticker':t,'target':target,'method':method,'bin':b,'n':int(mask.sum()),'mean_probability':float(pp[mask].mean()),'observed_rate':float(y[mask].mean())})
    pair=pd.DataFrame(pairrows)
    for (target,lag),ix in pair.groupby(['target','lag_block']).groups.items():
        ix=list(ix)
        for fam in ['H1','H3','secondary']:
            ids=pair.index[(pair.target==target)&(pair.lag_block==lag)&(pair.family==fam)]
            for name in ['hac_p','bootstrap_p']:pair.loc[ids,name+'_holm_family']=holm(pair.loc[ids,name])
            pair.loc[ids,'family_n']=len(ids)
        ids=pair.index[(pair.target==target)&(pair.lag_block==lag)&pair.primary]
        for name in ['hac_p','bootstrap_p']:pair.loc[ids,name+'_holm_global_primary']=holm(pair.loc[ids,name])
    pair['joint_positive_family']=(pair.difference>0)&(pair.hac_p_holm_family<.05)&(pair.bootstrap_p_holm_family<.05)
    pair.to_csv(OUT/'tables/paired_tests.csv',index=False)
    rank=pd.DataFrame(rankrows);rank['bootstrap_holm_all']=holm(rank.bootstrap_p);rank['ranking_family_n']=len(rank);rank.to_csv(OUT/'tables/within_state_ranking.csv',index=False)
    pd.DataFrame(staterows).to_csv(OUT/'tables/event_and_release_age_metrics.csv',index=False)
    pd.DataFrame(reliability).to_csv(OUT/'tables/calibration_bins.csv',index=False)
    pd.DataFrame(quality).to_csv(OUT/'tables/data_and_prediction_audit.csv',index=False)
    # Explicit mapped-up audit is a mathematical equivalence check, not a new fit.
    mapped=z[z.target=='reversal'].copy();mapped['p_up']=np.where(mapped.reference_sign<0,mapped.p,1-mapped.p);mapped['up_label']=(mapped.return5_pp>0).astype(int)
    if (mapped.return5_pp==0).any():raise RuntimeError('Flat future return invalidates exact direction mapping audit')
    np.testing.assert_allclose((mapped.p-mapped.y)**2,(mapped.p_up-mapped.up_label)**2,atol=2e-15)
    mapped.to_csv(OUT/'predictions/reversal_mapped_up_probabilities.csv.gz',index=False)
    dump(OUT/'audits/analysis_validation.json',{'status':'PASSED','prediction_rows':len(z),'same_test_dates_per_stock':482,'no2026_model_dates':True,'mapped_up_brier_identical':True,'new_model_fits':json.loads((OUT/'status.json').read_text())['fits'],'primary_tests_h5_reversal':28,'rank_tests_all_secondary':len(rank),'P_reversal_reused_bytechecked':True,'seed_losses_averaged_before_inference':True})
    print('ANALYSIS COMPLETE',len(z),'rows',len(pair),'tests/sensitivities',flush=True)

def plot():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'figure.dpi':140,'axes.spines.top':False,'axes.spines.right':False})
    metric=pd.read_csv(OUT/'tables/metrics_comparison.csv');metric=metric[(metric.target=='reversal')&(metric.probability=='calibrated')]
    names={'logistic':'Logistic','xgboost':'XGBoost','lightgbm':'LightGBM','lstm':'LSTM','mamba':'Mamba'}
    for what in ['models','gains','coverage','fundamentals','ranking','calibration']:
        fig,axes=plt.subplots(1,2,figsize=(12,4.5))
        for ax,t in zip(axes,['AAPL','TSLA']):
            if what=='models':
                z=metric[metric.ticker==t].set_index('method');xs=np.arange(5)
                for off,s,col in [(-.25,'P','#787d8d'),(0,'PF','#3c82a6'),(.25,'Late','#d38e48')]:
                    vals=[z.loc[m+'_'+s,'brier_mean'] if m+'_'+s in z.index else np.nan for m in ALL]
                    ax.bar(xs+off,vals,.24,label=s,color=col)
                ax.axhline(z.loc['cal_prior','brier_mean'],ls='--',c='black',label='Cal. prior');ax.set_xticks(xs,[names[m] for m in ALL],rotation=20);ax.set_ylim(.235,.28);ax.set_ylabel('Mean seed Brier (lower is better)');ax.legend(fontsize=8)
            elif what=='gains':
                z=pd.read_csv(OUT/'tables/paired_tests.csv');z=z[(z.ticker==t)&(z.target=='reversal')&(z.lag_block==20)&z.primary]
                ax.errorbar(z.difference,np.arange(len(z)),xerr=[z.difference-z.bootstrap_ci_low,z.bootstrap_ci_high-z.difference],fmt='o',color='#287e83');ax.axvline(0,ls='--',c='black');ax.set_yticks(np.arange(len(z)),[f'{r.candidate} vs {r.reference}' for r in z.itertuples()],fontsize=7);ax.set_xlabel('Paired Brier gain; block20 basic 95% CI')
            elif what=='coverage':
                v=pd.read_csv(OUT/'inputs/fundamental_vintages.csv');v=v[v.ticker==t];yrs=sorted(v.fiscal_year.unique())
                a=np.array([[v[v.fiscal_year==y][c].notna().sum() for y in yrs] for c in CORE]);im=ax.imshow(a,vmin=0,vmax=4,cmap='YlGnBu',aspect='auto');ax.set_yticks(range(7),CORE,fontsize=8);ax.set_xticks(range(len(yrs)),yrs,rotation=60);ax.set_xlabel('Fiscal year; source observations (not trading days)');fig.colorbar(im,ax=ax,label='Nonmissing quarterly vintages')
            elif what=='fundamentals':
                a=pd.read_csv(OUT/'inputs'/f'{t}_daily_fundamentals.csv');dates=pd.to_datetime(a.date);ax.plot(dates,a.net_margin,label='Net margin');ax.plot(dates,a.gross_margin,label='Gross margin');ax.set_ylim(-.5,.65);ax.set_ylabel('Issuer-vintage ratio; net margin clipped for display');ax.legend();ax.tick_params(axis='x',rotation=30)
            elif what=='ranking':
                z=pd.read_csv(OUT/'tables/within_state_ranking.csv');z=z[(z.ticker==t)&(z.target=='reversal')&(z.group=='all')];ax.scatter(z.within_state_auc,range(len(z)),c='#3e7d91');ax.set_yticks(range(len(z)),z.method,fontsize=7);ax.axvline(.5,ls='--',c='black');ax.set_xlim(.35,.7);ax.set_xlabel('Within existing market-state AUC; descriptive')
            elif what=='calibration':
                z=pd.read_csv(OUT/'tables/calibration_bins.csv');z=z[(z.ticker==t)&(z.target=='reversal')];ax.plot([0,1],[0,1],ls='--',c='gray')
                for m in ['logistic_P','logistic_F','logistic_PF','logistic_Late']:
                    a=z[z.method==m];ax.plot(a.mean_probability,a.observed_rate,'o-',label=m,ms=4)
                ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_xlabel('Predicted probability');ax.set_ylabel('Observed reversal rate');ax.legend(fontsize=7)
            ax.set_title(t)
        fig.tight_layout();fig.savefig(OUT/'figures'/f'{what}.png');fig.savefig(OUT/'figures'/f'{what}.pdf');plt.close(fig)
    print('PLOTS COMPLETE',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--plots',action='store_true');a=ap.parse_args()
    if a.plots:plot()
    else:analyze()
