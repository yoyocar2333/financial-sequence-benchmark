"""CPU-only E5 prediction integrity, paired inference and regime diagnostics."""
import argparse,itertools,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from analyze_e3b import metrics,paired_inference
from analyze_e3c import within_state_auc
from e3a_core import calendar_counts,holm,thin
import e3b_protocol as bp
from e5_core import OUT,TECH,RELATIVE,MODELS,RULES,SEEDS,FINAL,states,rule_scores


def frame(ticker):
    f=pd.read_csv(OUT/'inputs'/f'{ticker}_technical_and_labels.csv',parse_dates=['Date']).set_index('Date')
    f.attrs['ticker']=ticker
    return f


def subgroup_masks(f,t):
    up,down,cell=states(f,t);event=up|down
    conflict=event&(np.sign(f.context120_ex5.to_numpy())!=np.sign(f.past5.to_numpy()))
    masks={'all':np.ones(len(f),bool),'events':event,'acute_rise':up,'acute_fall':down,'conflict':conflict,
           'aligned_events':event&~conflict,'VIX_high':(f.VIX>=t['VIX_median']).to_numpy(),'VIX_low':(f.VIX<t['VIX_median']).to_numpy(),
           'year2024':f.index.year==2024,'year2025':f.index.year==2025,'nonoverlap_events':thin(event,5)}
    for name in ['trend','range','transition']:masks['ADX_'+name]=(f.regime==name).to_numpy()
    return masks,cell


def tests_for(loss):
    ans=[]
    def add(family,candidate,reference):
        ans.append(({'family':family,'candidate':candidate,'reference':reference},loss[reference]-loss[candidate]))
    for model in ['xgboost','lightgbm','lstm','mamba']:add('primary_feature8',model+'_T',model+'_B')
    for model in ['logistic','xgboost']:add('secondary_control4',model+'_T',model+'_C')
    for reference,candidate in itertools.combinations(['xgboost_T','lightgbm_T','lstm_T','mamba_T'],2):add('secondary_architecture12',candidate,reference)
    for reference in ['ungated_H0','rule_hybrid','momentum20','mean_reversion5','state_prior','logistic_B']:add('secondary_hybrid12','hybrid_H',reference)
    for candidate in RULES:add('secondary_rules14',candidate,'cal_prior')
    assert len(ans)==25
    return ans


def analyze():
    if json.loads((OUT/'status.json').read_text())['status'] not in ['TRAINING_COMPLETE','ANALYZING','COMPLETE']:
        raise RuntimeError('All training must complete before test analysis')
    lock=json.loads((OUT/'selection_locked.json').read_text())
    assert bp.sha(OUT/'selected_configs.json')==lock['sha256']
    # Raw fit archives are immutable; analysis writes only independent tables.
    artifact_audit=[]
    for phase,n in [('cv',162),('final',90)]:
        files=list((OUT/phase).rglob('COMPLETE.json'));assert len(files)==n,(phase,len(files))
        for p in files:
            for name,h in json.loads(p.read_text())['files'].items():assert bp.sha(p.parent/name)==h,str(p.parent/name)
            artifact_audit.append({'phase':phase,'folder':str(p.parent.relative_to(OUT)),'hashes_verified':True})
    pd.DataFrame(artifact_audit).to_csv(OUT/'audits/model_integrity.csv',index=False)
    probability_files=[p for p in (OUT/'predictions').glob('*.csv') if not p.name.endswith('_cal_source.csv')]
    assert len(probability_files)==162,len(probability_files)
    predictions=pd.concat([pd.read_csv(p) for p in probability_files],ignore_index=True)
    assert np.isfinite(predictions[['p_raw','p_calibrated','p_up']]).all().all()
    assert predictions[['p_raw','p_calibrated','p_up']].ge(0).all().all() and predictions[['p_raw','p_calibrated','p_up']].le(1).all().all()
    predictions.to_csv(OUT/'predictions/all_test_probabilities.csv.gz',index=False,compression='gzip')
    thresholds=json.loads((OUT/'inputs/e3a_training_thresholds.json').read_text())
    metricrows=[];groupmetrics=[];ensemble=[];testrows=[];rankrows=[];lossrows=[];state_rows=[];reliability=[];integrity=[];correlation=[];regime=[];amplitudes=[];rawrules=[]
    counts={}
    for ticker in ['AAPL','TSLA']:
        full=frame(ticker);ii=bp.indices(full,FINAL['test_start'],FINAL['test_end']);f=full.iloc[ii]
        assert len(f)==482 and f.index.max().year<=2025
        y=f.y5.to_numpy();yu=(f.nextopen_log5>0).to_numpy();masks,cell=subgroup_masks(f,thresholds[ticker]);loss={};ps={};rawps={}
        for name,mask in masks.items():
            amp=-f.reference_sign.to_numpy()*f.nextopen_log5.to_numpy()
            state_rows.append({'ticker':ticker,'group':name,'n':int(mask.sum()),'reversal_rate':float(y[mask].mean()) if mask.any() else np.nan,'signed_reversal_amplitude_mean_pp':float(amp[mask].mean()) if mask.any() else np.nan})
        z=predictions[predictions.ticker==ticker]
        for method,data in z.groupby('method'):
            seeds=sorted(data.seed.unique());expected=list(SEEDS) if method.endswith(('_B','_T','_C','_H','_H0')) else [-1]
            assert seeds==expected,(ticker,method,seeds)
            probs=[];raw=[]
            for seed,s in data.groupby('seed'):
                s=s.sort_values('date');np.testing.assert_array_equal(s.date,f.index.strftime('%Y-%m-%d'))
                np.testing.assert_array_equal(s.target_reversal,y);np.testing.assert_allclose(s.executable_log_return_pp,f.nextopen_log5,atol=1e-11)
                p=s.p_calibrated.to_numpy();pr=s.p_raw.to_numpy();probs.append(p);raw.append(pr)
                integrity.append({'ticker':ticker,'method':method,'seed':int(seed),'n':len(s),'same_dates_labels_returns':True})
                for version,q in [('calibrated',p),('raw',pr)]:
                    metricrows.append({'ticker':ticker,'method':method,'seed':int(seed),'version':version,'task':'reversal',**metrics(y,q,True)})
                metricrows.append({'ticker':ticker,'method':method,'seed':int(seed),'version':'calibrated','task':'direction_mapped',**metrics(yu,s.p_up,True)})
                for name,mask in masks.items():
                    if mask.any():groupmetrics.append({'ticker':ticker,'method':method,'seed':int(seed),'group':name,**metrics(y[mask],p[mask])})
            pseed=np.stack(probs);rseed=np.stack(raw)
            ps[method]=pseed;rawps[method]=rseed;loss[method]=((pseed-y)**2).mean(axis=0)
            ensemble.append({'ticker':ticker,'method':method,'definition':'separate mean-probability ensemble; NOT mean seed metric',**metrics(y,pseed.mean(axis=0),True)})
            for i,d in enumerate(f.index):lossrows.append({'ticker':ticker,'method':method,'date':str(d.date()),'target':int(y[i]),'mean_seed_probability':float(pseed[:,i].mean()),'mean_seed_brier':float(loss[method][i])})
            for b in range(10):
                use=np.minimum((pseed*10).astype(int),9)==b
                reliability.append({'ticker':ticker,'method':method,'bin':b,'mean_seed_count':float(use.sum()/len(pseed)),'predicted':float(pseed[use].mean()) if use.any() else np.nan,'observed':float(np.broadcast_to(y,pseed.shape)[use].mean()) if use.any() else np.nan})
            if method in RULES:
                literal=rule_scores(f)[method].to_numpy();up=(literal>0);active=literal!=0
                rawrules.append({'ticker':ticker,'method':method,'active_n':int(active.sum()),'coverage':float(active.mean()),'active_direction_accuracy':float((up[active]==yu[active]).mean()) if active.any() else np.nan,'literal_position':'long if raw score>0 else cash; distinct from calibrated forecasts'})
            # Severity bins use only already-fitted 2023 calibration predictions to set boundaries.
            if method in ['xgboost_T','lightgbm_T','lstm_T','mamba_T','hybrid_H']:
                label,arm=method.rsplit('_',1)
                for seed in SEEDS:
                    folder=OUT/'final'/ticker/arm/label/f'seed{seed}'
                    cal=pd.read_csv(folder/'calibration_predictions.csv');meta=json.loads((folder/'calibration.json').read_text())
                    cp=bp.sigmoid(meta['coefficient']*bp.logit(cal.p_raw)+meta['intercept'])
                    _,_,calcell=states(full,thresholds[ticker]);calids=bp.indices(full,FINAL['cal_start'],FINAL['cal_end'])
                    cu,cd,_=states(full,thresholds[ticker]);ce=(cu|cd)[calids]
                    bounds=np.quantile(cp[ce],[.2,.4,.6,.8]);bins=np.searchsorted(bounds,pseed[list(SEEDS).index(seed)],side='right')
                    for b in range(5):
                        use=masks['events']&(bins==b)
                        signed=-f.reference_sign.to_numpy()*f.nextopen_log5.to_numpy()
                        amplitudes.append({'ticker':ticker,'method':method,'seed':seed,'bin':b+1,'n':int(use.sum()),'bounds_source':'2023H2 event probability quantiles','lower_bound':float(bounds[b-1]) if b else 0.,'upper_bound':float(bounds[b]) if b<4 else 1.,'reversal_rate':float(y[use].mean()) if use.any() else np.nan,'signed_reversal_amplitude_pp':float(signed[use].mean()) if use.any() else np.nan})
        comparisons=tests_for(loss)
        for length in [20,60]:
            counts[length]=calendar_counts(len(f),length,reps=9999,seed=20261102)
            stats=paired_inference(np.column_stack([x[1] for x in comparisons]),counts[length],length)
            for (meta,_),stat in zip(comparisons,stats):testrows.append({'ticker':ticker,'block_length':length,**meta,**stat})
        # Confirmatory-style corrections within this exploratory stage only.
        for method in ['xgboost_T','lightgbm_T','lstm_T','mamba_T','hybrid_H','rule_hybrid']:
            for length in [20,60]:rankrows.append({'ticker':ticker,'method':method,'block_length':length,**within_state_auc(y,cell,ps[method],masks['events'],counts[length])})
        # Training-only redundancy; associations do not establish information identity.
        xb,meta=bp.feature_matrix(full,'B',FINAL['fit_end'])
        tr=(full.index>='2012-01-01')&(full.index<=FINAL['fit_end'])&np.isfinite(xb).all(axis=1)&np.isfinite(full[TECH+[RELATIVE]]).all(axis=1)
        for c in TECH+[RELATIVE]:
            correlations=[spearmanr(xb[tr,j],full.loc[tr,c]).statistic for j in range(xb.shape[1])]
            j=int(np.nanargmax(np.abs(correlations)))
            correlation.append({'ticker':ticker,'technical_feature':c,'most_correlated_B_feature':meta['columns'][j],'spearman':float(correlations[j]),'absolute_spearman':float(abs(correlations[j])),'sample':'2012-2022 training only','n':int(tr.sum())})
        for part,(a,b) in {'train':('2012-01-01','2022-12-31'),'validation':('2023-01-01','2023-12-31'),'test':('2024-01-01','2025-12-31')}.items():
            ids=bp.indices(full,a,b);zz=full.iloc[ids];changed=zz.regime.ne(zz.regime.shift());changed.iloc[0]=False
            for r in ['trend','range','transition']:
                use=(zz.regime==r)
                next_same=(zz.regime.shift(-1)==r)&use
                regime.append({'ticker':ticker,'partition':part,'regime':r,'n':int(use.sum()),'share':float(use.mean()),'reversal_rate':float(zz.y5[use].mean()) if use.any() else np.nan,'next_day_same_state_rate':float(next_same.iloc[:-1].sum()/use.iloc[:-1].sum()) if use.iloc[:-1].sum() else np.nan,'all_state_daily_switch_rate':float(changed.iloc[1:].mean())})
    m=pd.DataFrame(metricrows);m.to_csv(OUT/'tables/metrics_per_seed.csv',index=False)
    fields=['brier','log_loss','roc_auc','balanced_accuracy','mcc','ece10','mean_probability','calibration_bias','calibration_slope']
    mean=m.groupby(['ticker','method','version','task'])[fields].agg(['mean','std','min','max']);mean.columns=['_'.join(c) for c in mean.columns];mean.reset_index().to_csv(OUT/'tables/metrics_comparison.csv',index=False)
    g=pd.DataFrame(groupmetrics);g.to_csv(OUT/'tables/state_metrics_per_seed.csv',index=False)
    gg=g.groupby(['ticker','method','group'])[['n','prevalence']+fields[:-1]].mean().reset_index();gg.to_csv(OUT/'tables/state_metrics.csv',index=False)
    pd.DataFrame(ensemble).to_csv(OUT/'tables/ensemble_metrics_separate.csv',index=False)
    pd.DataFrame(integrity).to_csv(OUT/'audits/prediction_integrity.csv',index=False)
    pd.DataFrame(state_rows).to_csv(OUT/'tables/event_and_regime_counts.csv',index=False)
    pd.DataFrame(lossrows).to_csv(OUT/'tables/daily_paired_losses.csv.gz',index=False,compression='gzip')
    pd.DataFrame(reliability).to_csv(OUT/'tables/reliability.csv',index=False)
    pd.DataFrame(amplitudes).to_csv(OUT/'tables/event_probability_and_amplitude.csv',index=False)
    pd.DataFrame(correlation).to_csv(OUT/'tables/training_feature_redundancy.csv',index=False)
    pd.DataFrame(regime).to_csv(OUT/'tables/regime_stability.csv',index=False)
    pd.DataFrame(rawrules).to_csv(OUT/'tables/literal_rule_coverage.csv',index=False)
    tests=pd.DataFrame(testrows)
    for (length,family),idx in tests.groupby(['block_length','family']).groups.items():
        tests.loc[idx,'hac_holm_family']=holm(tests.loc[idx,'hac_p']);tests.loc[idx,'bootstrap_holm_family']=holm(tests.loc[idx,'bootstrap_p'])
    for length,idx in tests.groupby('block_length').groups.items():
        assert len(idx)==50
        tests.loc[idx,'hac_holm_global50']=holm(tests.loc[idx,'hac_p']);tests.loc[idx,'bootstrap_holm_global50']=holm(tests.loc[idx,'bootstrap_p'])
    tests['joint_significant']=(tests.difference>0)&(tests.hac_holm_family<.05)&(tests.bootstrap_holm_family<.05)
    tests.to_csv(OUT/'tables/paired_tests.csv',index=False)
    tests[(tests.family=='primary_feature8')&(tests.block_length==20)].to_csv(OUT/'tables/feature_gains.csv',index=False)
    rank=pd.DataFrame(rankrows)
    for length,idx in rank.groupby('block_length').groups.items():rank.loc[idx,'bootstrap_holm12']=holm(rank.loc[idx,'bootstrap_p'])
    rank.to_csv(OUT/'tables/within_state_ranking.csv',index=False)
    selected=json.loads((OUT/'selected_configs.json').read_text());old=json.loads((OUT/'inputs/selected_configs.json').read_text());selection=[]
    for t in ['AAPL','TSLA']:
        for model in MODELS:
            a=old[f'{t}_h5_B_{model}'];b=selected[f'{t}_{model}_T']
            selection.append({'ticker':t,'model':model,'B_config':json.dumps(a['config'],sort_keys=True),'T_config':json.dumps(b['config'],sort_keys=True),'same_config':a['config']==b['config'],'B_CV_brier':min(a['CV_mean_brier']),'T_CV_brier':min(b['cv_means'])})
    pd.DataFrame(selection).to_csv(OUT/'tables/selection_changes.csv',index=False)
    slopes=[]
    for p in (OUT/'predictions').glob('*_calibration.json'):
        z=json.loads(p.read_text());slopes.append({'file':p.name,**z,'negative_rule_slope':bool(z['coefficient']<0)})
    pd.DataFrame(slopes).to_csv(OUT/'tables/rule_calibration_slopes.csv',index=False)
    bp.write_json(OUT/'audits/analysis_integrity.json',{'status':'PASSED','prediction_files':162,'test_rows_per_method_seed':482,'model_fits_verified':252,'primary_comparisons':8,'secondary_comparisons':42,'within_state_tests':12,'seeds_not_independent_dates':True,'flat_test_returns':0,'new2026_data_read':False})
    print('E5 ANALYSIS PASSED; primary joint significance',int(tests[(tests.family=='primary_feature8')&(tests.block_length==20)].joint_significant.sum()),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path);a=p.parse_args()
    if a.directory:OUT=a.directory.resolve()
    analyze()
