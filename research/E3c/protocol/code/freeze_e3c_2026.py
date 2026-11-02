"""Create/check a hash-locked protocol. This command CANNOT execute validation."""
import argparse
import importlib.metadata
import json
from pathlib import Path
from e4a_core import ROOT,SOURCE,sha,dump,now

CODE=['e3c_2026_features.py','freeze_e3c_2026.py','e3c_core.py','e3b_protocol.py','e3a_core.py','e3c_calibration_v1_1.py','analyze_e3b.py','analyze_e3c.py','test_e3c_2026_protocol.py']


def specification():
    old=json.loads((SOURCE/'INDEPENDENT_VALIDATION_PROPOSAL.json').read_text())
    columns=json.loads((SOURCE/'inputs/AAPL_preprocessing.json').read_text())['columns']
    params={'objective':'binary:logistic','tree_method':'hist','max_bin':64,'eval_metric':'logloss',
        'n_jobs':2,'subsample':.8,'colsample_bytree':.8,'verbosity':0,'device':'cpu',
        'booster':'gbtree','gamma':0.,'reg_alpha':0.,'max_delta_step':0.,'colsample_bylevel':1.,
        'colsample_bynode':1.,'grow_policy':'depthwise','max_leaves':0,'base_score':None}
    return {'protocol_id':'E3C-2026-ONE-SHOT-v1.0','status':'FROZEN_NOT_EXECUTED','frozen_utc':now(),
        'origin_proposal_sha256':sha(SOURCE/'INDEPENDENT_VALIDATION_PROPOSAL.json'),
        'origin_proposal':old,'scope':'PRICE/VOLATILITY ONLY E3c; E4a news findings cannot alter this protocol',
        'authority':'User2026-10-26 requested fixed protocol, explicitly NOT execution',
        'data_access':{'holdout_loaded':False,'training_started':False,'inspection_not_before':'2027-01-15T00:00:00Z',
            'embargo':'One scheduled full-year2026 evaluation only after all2026 stock/VIX/VXN sessions and corporate actions available; later if feed incomplete. No partial-year access.',
            'independence':'Before any access, every researcher attests no2026 prices/news/labels/model outputs influenced choices. If breached, retain this as exploratory and pre-register a later unseen period; do not silently substitute dates.'},
        'tickers':['AAPL','TSLA'],'seeds':old['seeds'],'horizon_sessions':5,
        'label':'y=1[sign(100log(Ct/Ct-5))*100log(Ct+5/Ot+1)<0]; flat future non-reversal; exclude flat reference; signed amplitude=-reference_sign*future_log_return_pp',
        'price_policy':'Yahoo raw OHLC/Adj Close/actions snapshot, source and retrieval audit; adjusted OHLC=raw OHLC*AdjClose/Close, volume unchanged; preserve old <=2025 snapshot and separately audit differences from new vendor history. Not a fully PIT market archive.',
        'snapshot_contract':'After embargo freeze one complete2010-2026 snapshot for AAPL/TSLA/QQQ/VIX/VXN with timezone/session audit, raw+adjusted CSV, actions, SHA256. No manual backfills/interpolation. Use one coherent adjustment vintage, retain and quantify all historical revisions against E3c, never choose vintage by scores.',
        'session_contract':'Validate complete common actual exchange sessions; equity regular-session adjusted Open entry t+1 and Close exit t+5. VIX/VXN same-date closing values. No2027 outcomes. Decision17:00 America/New_York assumed; audit actual vendor availability; no transaction-cost/profitability assertion.',
        'fit':{'start':'2012-01-01','end':'2024-12-31','label_purge_sessions':20},
        'calibration':{'start':'2025-07-01','end':'2025-12-31','label_purge_sessions':20,
            'population':'ALL eligible dates, including non-events; separate map for gated pipeline and EACH prior',
            'objective':'sum(logaddexp(0,a*logit(p)+b)-y*(a*logit(p)+b)) + .5*20*((a-1)^2+b^2)',
            'lambda':20.,'a_bounds':[0.,3.],'b_bounds':'unbounded','initial':[1.,0.],
            'solver':'e3c_calibration_v1_1.solve projected Newton','projected_gradient_inf_tolerance':1e-8,'max_iterations':150,
            'logit_probability_clip':[1e-6,1-1e-6],'sigmoid_logit_clip':[-35.,35.],
            'failure':'Stop own validation without changing lambda, model, threshold or trying alternate calibration on holdout. Preserve error; any numerical repair must retain exact objective and be frozen before unsealing outputs.'},
        'unused_supervised':'2025H1, boundary-purged labels,2026; past prices from unused blocks may form causal histories',
        'evaluation':{'start':'2026-01-01','end':'2026-12-31','eligibility':'e3b_protocol.indices: all60-session causal feature history complete; reference_sign!=0; end20<=block_end; same dates for all models; no2027 labels'},
        'scaler':'StandardScaler on finite38-feature calendar observations2012-2024, including unsupervised label-boundary rows; no2025/2026 fit. Fixed cutoffs below, no quantile/median refit.',
        'feature_columns':columns,'feature_formulas':'e3c_2026_features.py frozen alongside protocol; equality to original E3c<=2025 verified without any2026 data',
        'event_cutoffs':old['event_cutoffs'],'event_direction':'+1 past5>=q90; -1 past5<=q10; otherwise0',
        'state':'long_up=context120_ex5>=0; high_VIX=VIX>=frozen median; cell=(event_direction+1)*4+2*long_up+high_VIX;8 event cells',
        'candidate':'Two XGB branches per ticker/seed: fit all eligible2012-2024 and fit event rows only; gate event branch on events, all branch elsewhere; calibrate WHOLE gated pipeline on all2025H2 dates. No early stopping or search.',
        'xgb_ticker_configs':old['configs'],'xgb_common_params':params,'xgb_random_state':'seed; unspecified minor parameters fixed by pinned xgboost-cpu3.0.5 defaults; dump full get_params/config in eventual run',
        'comparators':{'event_prior':'global=(sum y+1)/(n+2), event=(sum event y+1)/(n_event+2); gate by event; independent same global Platt calibration',
            'state_prior':'alpha100 both stocks; start global Beta1, then shrink direction, long sign, VIX sign successively on nested FIT rows; independent same global Platt calibration'},
        'primary':{'estimand':'event Brier gain reference minus candidate; first average5 seed LOSSES at each date',
            'family_size':4,'comparisons':['AAPL XGB vs event_prior','AAPL XGB vs state_prior','TSLA XGB vs event_prior','TSLA XGB vs state_prior'],
            'tests':'two-sided HAC Bartlett lag20 and null-centered basic circular-block20 bootstrap B19999 seed20261026; event-mask ratio influence on full common calendar; Holm4 applied separately to HAC/bootstrap; report unadjusted95% intervals and corrected p-values',
            'sensitivity':'lag/block60, separate sensitivity Holm4 family; thin5 chronological event sampling from first event without consulting y; no replacing primary with a favorable sensitivity',
            'bootstrap_empty_rule':'at least99% draws have nonempty event mask or mark inference insufficient'},
        'secondary':{'family_size':2,'estimand':'XGB average seed within-same-cell pair-weighted AUC versus.5 for each stock',
            'bootstrap':'two-sided null-centered calendar circular-block20 B9999 seed20261026; average concordance kernels across seeds before resampling; basic95% interval; Holm2; block60 sensitivity',
            'metrics':['Brier','LogLoss','ROC_AUC','PR_AUC','BalancedAccuracy','MCC','ECE10','mean probability','probability SD','calibration bias'],
            'classification_threshold':.5,'subgroups':'surge/crash,conflict/aligned,VIX/VXN high-low; descriptive only, no confirmatory subgroup claims'},
        'minimum_support':{'event_dates':20,'reversals':10,'continuations':10,'same_state_positive_negative_pairs':20,
            'failure':'insufficient support; retain all data and outputs, do not change cutoffs/window/period'},
        'timing_claim':'Per stock: positive Brier gain vs BOTH priors with BOTH primary Holm4 HAC/bootstrap p<.05 AND within-state AUC>.5 with Holm2 p<.05; additionally direction of gains retained in block60 sensitivity. Otherwise distinguish mean/calibration gain from timing skill.',
        'execution_rules':['Freeze code/env/data manifests before unsealing predictions; no dashboard/interim outputs','One run per full2026 cohort; fail stops without selecting a better seed or rerunning completed results','Store every seed/checkpoint/config/raw and calibrated probability, fit/cal indices, stats, stdout, audit, ZIP','No news addition; no architecture changes; no tuning from2026; a null result is not proof of no information'],
        'environment':{'python':'3.10.12','packages':{x:importlib.metadata.version(x) for x in ('numpy','pandas','scipy','scikit-learn','xgboost-cpu')},'CPU_threads':2},
        'execution_status':'PROTOCOL_AND_FEATURE_ENGINE_ONLY; no holdout execution is provided by this preparation command'}


def freeze(directory):
    import shutil
    d=Path(directory)
    if d.exists(): raise FileExistsError('Frozen protocol exists; never overwrite')
    (d/'code').mkdir(parents=True)
    dump(d/'E3C_2026_PROTOCOL.json',specification())
    for name in CODE: shutil.copyfile(ROOT/'scripts'/name,d/'code'/name)
    shutil.copyfile(SOURCE/'INDEPENDENT_VALIDATION_PROPOSAL.json',d/'ORIGINAL_PROPOSAL.json')
    shutil.copyfile(ROOT/'E3C_2026_PROTOCOL.md',d/'E3C_2026_PROTOCOL.md')
    paths=[p for p in d.rglob('*') if p.is_file()]
    dump(d/'protocol_lock.json',{'frozen_utc':now(),'files':{str(p.relative_to(d)):sha(p) for p in paths},'2026_data_loaded':False,'training_started':False})
    check(d)


def check(directory):
    d=Path(directory);lock=json.loads((d/'protocol_lock.json').read_text())
    for p,h in lock['files'].items():
        if sha(d/p)!=h: raise RuntimeError('Protocol changed: '+p)
    spec=json.loads((d/'E3C_2026_PROTOCOL.json').read_text())
    assert spec['status']=='FROZEN_NOT_EXECUTED' and len(spec['feature_columns'])==38
    assert not spec['data_access']['holdout_loaded'] and not spec['data_access']['training_started']
    print(json.dumps({'status':'FROZEN_NOT_EXECUTED','files_verified':len(lock['files']),'protocol_sha256':sha(d/'E3C_2026_PROTOCOL.json'),'2026_data_loaded':False}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--freeze',action='store_true');g.add_argument('--check',action='store_true')
    a=p.parse_args();freeze(a.directory) if a.freeze else check(a.directory)
