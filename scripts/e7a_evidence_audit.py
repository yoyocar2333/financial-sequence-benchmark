"""Read existing aggregate evidence, audit PIT readiness, never refit models."""
import json,re
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import t,norm
from e7a_development_audit import ROOT,OUT,sha,dump,panel_mean_variance

def run():
    claims=[];sourcefiles={}
    def add(stage,claim,estimate,units,status,source,limits):
        p=ROOT/source
        if p.exists():sourcefiles[source]=sha(p)
        claims.append({'stage':stage,'claim':claim,'estimate':estimate,'units':units,'evidence_status':status,'source_path':source,'interpretation_limit':limits})
    # E0 is an archived table, not a new reconstruction of notebook predictions.
    e0=ROOT.parent/'financial-sequence-benchmark/RESULTS.md'
    if not e0.exists():raise FileNotFoundError('Retained E0 repository table unavailable')
    add('E0','Archived Naive MAPE AAPL/TSLA','0.6766 / 2.6378','percent MAPE','ARCHIVED_RECORD_ONLY','../financial-sequence-benchmark/RESULTS.md','2025-11 single recorded month; source notebook not rerun; no direct comparability to Brier or amplitude MAE')
    path='outputs/mamba_multiseed_20261020/metrics_multiseed.csv';z=pd.read_csv(ROOT/path)
    a=z.groupby(['ticker','arm']).mae_pp.mean().unstack()
    for ticker in ['AAPL','TSLA']:add('E1_E2',ticker+' E1/E2b five-seed amplitude MAE',f'{a.loc[ticker,"E1"]:.9f} / {a.loc[ticker,"E2b"]:.9f}','return percentage points MAE','EXPLORATORY_PAIRED_NO_CONFIRMED_GAIN',path,'501 shared dates; batch8; five seeds are not five independent market histories')
    path='outputs/e3a_20261021/tables/statistical_tests.csv';z=pd.read_csv(ROOT/path);q=z[(z.family=='primary')&(z.bandwidth==60)];add('E3a','Declared primary event comparisons supported after correction',f'{int(q.primary_decision.sum())} / {len(q)}','eligible rows; original family98','EXPLORATORY_EVENT_DESCRIPTIVE',path,'Some family98 contrasts ineligible/sparse; do not report eligible rows as98 independent tests or infer universal mean reversion')
    path='outputs/e3b_20261026/tables/paired_tests.csv';z=pd.read_csv(ROOT/path);q=z[(z.horizon==5)&(z.block_length==20)];positive=(q.difference>0)&(q.hac_holm_family<.05)&(q.bootstrap_holm_family<.05);add('E3b','h5 paired benchmark positive corrected comparisons',f'{int(positive.sum())} / {len(q)}','same-date Brier comparisons','EXPLORATORY_NOT_CONFIRMATORY',path,'A/B15/38 features; different from E5 T51 or E6 PF66; CV grid not exhaustive')
    path='outputs/e3c_20261026_v1_1/tables/signal_vs_average_evidence.csv';z=pd.read_csv(ROOT/path);add('E3c','Joint event Brier plus within-state timing evidence',f'{int(z.joint_timing_evidence.sum())} / {len(z)}','prespecified model evidence rules','EXPLORATORY_NO_JOINT_TIMING_EVIDENCE',path,'Use completed v1.1 rather than stopped original numerical attempt; coarse cells do not remove all possible heterogeneity')
    path='outputs/e4c_20261026/tables/paired_tests.csv';z=pd.read_csv(ROOT/path);q=z[(z.timing=='next_session')&(z.version=='calibrated')&(z.block_length==20)&(z.family=='primary_LR_news2')&(z.group=='events')&(z.metric=='Brier')]
    for r in q.itertuples():add('E4c',r.candidate+' versus '+r.reference,f'{r.difference:.9f}; Holm bootstrap p={r.bootstrap_holm2:.4f}','Brier loss reduction','EXPLORATORY_NEWS_UNVERIFIED_HISTORICAL_PIT',path,'AAPL only65 events in2025;2023/2024 train/calibration; does not share E3/E5/E6 two-year482-date estimand')
    path='outputs/e5_20261102/tables/paired_tests.csv';z=pd.read_csv(ROOT/path);q=z[(z.family=='primary_feature8')&(z.block_length==20)];add('E5','Technical feature primary gains passing joint correction',f'{int(q.joint_significant.sum())} / {len(q)}','T versus B Brier comparisons','EXPLORATORY_FEATURE_REPRESENTATION_STUDY',path,'12 deterministic price/volume transforms and additional QQQ source must be distinguished; fixed C does not equal matched effective capacity')
    path='outputs/e6_20261106/tables/paired_tests.csv';z=pd.read_csv(ROOT/path)
    for target in ['reversal','up_direct']:
        for family in ['H1','H3']:
            q=z[(z.target==target)&(z.family==family)&(z.lag_block==20)];add('E6',target+' '+family+' positive joint corrected comparisons',f'{int(q.joint_positive_family.sum())} / {len(q)}','paired Brier family','EXPLORATORY_PIT_RECONSTRUCTION_ONLY',path,'Direct-up significant AAPL Logistic Late has Fweight1; no inference of complementarity or genuine new information from dropping weak P')
    path='outputs/e6_20261106/tables/within_state_ranking.csv';z=pd.read_csv(ROOT/path);add('E6','Positive corrected within-state ranking tests',f'{int(((z.within_state_auc>.5)&(z.bootstrap_holm_all<.05)).sum())} / {len(z)}','secondary ranking comparisons','EXPLORATORY_NO_CONFIRMED_RANKING',path,'112 mixed task/group diagnostics, not112 independent markets; H2 deferred')
    pd.DataFrame(claims).to_csv(OUT/'tables/research_claims_ledger.csv',index=False)
    dump(OUT/'audits/evidence_source_hashes.json',sourcefiles)
    # Assess what is actually held locally, not vendors' advertised maxima.
    v=pd.read_csv(ROOT/'outputs/e6_20261106/inputs/fundamental_vintages.csv');pit=[]
    for ticker,g in v.groupby('ticker'):
        pit.append({'ticker':ticker,'quarterly_versions':len(g),'first_release':g.release_date.min(),'last_release':g.release_date.max(),'SEC_acceptance_nonmissing':int(g.SEC_acceptance_datetime.notna().sum()),'amendment_timestamp_nonmissing':int(g.SEC_amendment_datetime.notna().sum()),'historical_first_seen_verified':int(g.historical_first_seen_verified.sum()),'historical_version_proven':int(g.historical_version_proven.sum()),'strict_E7_primary_eligible_versions':0,'status':'RECONSTRUCTION_ONLY_NOT_STRICT_PIT_READY'})
    pd.DataFrame(pit).to_csv(OUT/'tables/current_pit_readiness.csv',index=False)
    fields=[]
    for (ticker,year),g in v.groupby(['ticker','fiscal_year']):
        fields.append({'ticker':ticker,'fiscal_year':year,'quarterly_versions':len(g),**{name+'_available':int(g[name].notna().sum()) for name in ['revenue_yoy','eps_yoy_symmetric','gross_margin','net_margin','operating_margin','cfo_margin','cash_asset_ratio']}})
    pd.DataFrame(fields).to_csv(OUT/'tables/current_fundamental_field_coverage.csv',index=False)
    # More variance references than the single matched-shrink planning scale.
    dev=pd.read_csv(OUT/'tables/development_variance_summary.csv');refs=[]
    for name,sel in [('matched_shrink',dev.comparison.eq('matched_shrink_increment')),('F_vs_prior',dev.comparison.eq('F_vs_training_prior')),('strong_tree_total',dev.comparison.eq('total_vs_P')&dev.price_model.eq('xgboost')),('weak_highdim_Logistic_total_stress',dev.comparison.eq('total_vs_P')&dev.price_model.eq('logistic'))]:
        refs.append({'variance_reference':name,'maximum_quarter_sd':float(dev.loc[sel,'quarter_sd'].max()),'future_comparison_measured':False,'note':'pre2023 raw fixedconfig0 proxy only; actual calibrated C1-C6 require new cross-industry pilot variance audit'})
    refs.append({'variance_reference':'Early_PMF_vs_PM_primary_C1','maximum_quarter_sd':np.nan,'future_comparison_measured':False,'note':'No matched P+metadata CV experiment exists; cannot infer C1 power from F-only or Late results'})
    pd.DataFrame(refs).to_csv(OUT/'tables/variance_reference_limits.csv',index=False)
    stress=[]
    for row in refs:
        sigma=row['maximum_quarter_sd']
        if not np.isfinite(sigma):continue
        for quarters in [12,16]:
            for name,rm,ri,phi in [('independent',0,0,0),('moderate',.05,.1,.3),('strong',.15,.15,.6)]:
                se=np.sqrt(panel_mean_variance(sigma,200,quarters,rm,ri,phi));critical=t.ppf(1-.05/12,quarters-1)
                stress.append({'variance_reference':row['variance_reference'],'stocks':200,'quarters':quarters,'scenario':name,'quarter_sigma':sigma,'SE':se,'primary_family_n':6,'single_contrast_MDE80':(critical+norm.ppf(.8))*se,'three_leg_MDE_joint80_equal_scale_unionbound':(critical+norm.ppf(1-.2/3))*se,'not_a_guarantee_for_unknown_Early_contrast':True})
    pd.DataFrame(stress).to_csv(OUT/'tables/variance_stress_and_16quarter_candidate.csv',index=False)
    dump(OUT/'audits/review_scope.json',{'stages':['E0','E1_E2','E3a','E3b','E3c_v1.1','E4a','E4b','E4c','E5','E6'],'heldout_existing_results_read_for_review':True,'existing_test_values_used_for_new_model_selection':False,'new_market_fits':0,'new_real_test_predictions':0,'power_predictions_only2017_2022':True,'no2026_validation':True,'data_contract_not_sufficient_to_authenticate_vendor_assertions':True})
    print('EVIDENCE AND PIT AUDIT COMPLETE',len(claims),flush=True)

if __name__=='__main__':run()
