"""Locked E6 information/fusion study. Old scientific modules remain untouched."""
import os,json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import e3b_protocol as bp
import e5_core as e5
from e6_data import CORE,align

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('E6_BUNDLE_ROOT',ROOT/'outputs/e6_20261106')).resolve()
SOURCE=ROOT/'outputs/e5_20261102'
SEEDS=(42,43,44,45,46)
CPU=('logistic','xgboost','lightgbm')
ALL=CPU+('lstm','mamba')
F_COLS=CORE+['release_age_scaled']+[c+'_missing' for c in CORE]+['reference_sign']
PLAN={
 'version':'E6-1.0','locked_before_new_fits':True,'H2_deferred':True,
 'scope':'Exploratory existing 2024-2025; no2026 financial facts,prices,news or labels used. Administrative IR page metadata/search contamination disclosed separately. Existing E3c2026 protocol immutable.',
 'H1':'Incremental accounting information: F vs sign-conditioned historical probability and matched fixed-config Early(P,F) vs frozen P; accounting-values vs metadata-only F control reported separately.',
 'H3':'Prediction fusion: Late(P,F_logistic) vs P and matched same-weight Late(P,training-prior). Best-component comparisons secondary. A lower pooled loss alone is not evidence that a novel architecture extracts more information.',
 'P':'Exactly E5 T: 60x51 price/volatility/multiscale/technical/QQQ. Five seeds and frozen selected configs. Reversal raw/cal predictions copied and hash checked, not refitted. Direct-up P requires new CPU fits with the same frozen configs.',
 'F':F_COLS,'F_definition':'7 scale-free accounting metrics + past release age/180 cap1 +7 explicit missing flags + common past5 sign metadata. Current-date 1x16 compact LR/XGB/LGBM; NOT pure architecture comparison with 60-history price models. F contains no analyst forecasts and no Earnings Surprise.',
 'source':'Original issuer-vintage quarterly releases/statements. SEC JSON/archive/bulk HTTP403 is audited; Apple issuer-hosted as-filed PDFs retained where available. Date-only release +2 strictly subsequent trading sessions; sensitivity +5. Historical first-seen/version/SEC acceptance/amendment times unknown remain null. Thus PIT-aware conservative reconstruction, not certified historical PIT.',
 'vintages':'Never replace old daily features with later comparatives or later split-adjusted EPS. Same-release YoY EPS symmetric denominator abs(now)+abs(prior)+.1; legacy TSLA EPS-growth unknown if comparative column not verified. Quarter/YTD CF denominators matched; unavailable amounts remain missing. No valuation ratios mixing retrospectively adjusted prices with historical unadjusted EPS.',
 'preprocessing':'Median imputation/StandardScaler training calendar only per fold. Fixed value bounds [-5,5] for numeric ratios; missing flags before imputation; age cap180days and stale accounting after370days. No zero-as-no-fundamentals. At each sequence step use only that step as-of F, never broadcast a newly filed report into past sequence steps.',
 'task':'Primary h5 reversal = sign(past5)*log(C[t+5]/O[t+1])<0. Secondary independently trained direct up = log(C[t+5]/O[t+1])>0. Same all-date482 calendars, 60-history and original end20 purge; mapped-up from reversal kept distinct, exact Brier equality checked only if no flat future returns.',
 'split':bp.FINAL,'folds':bp.FOLDS,'seeds':list(SEEDS),
 'search':'F only: same 3 prior candidate configs x3 expanding folds, seed42, mean raw outer Brier. P and Early P+F: use E5 per-ticker per-model selected configuration unchanged, no extra architecture/learning-rate search. F configs chosen on reversal and frozen also for secondary direct-up. No test feedback.',
 'late':'Use common F_logistic expert for every P architecture. Fixed five weights wF=0,.25,.5,.75,1 selected by equal mean raw expanding-fold Brier; tie lowest wF. All choices before test generation. Then independently apply same ridge-C1 unconstrained Platt2023H2 to each complete pipeline. Matched-prior blend uses exactly same wF, hence controls for shrinkage. Fixed 50/50 also retained as sensitivity.',
 'neural_gate':'No new event/quarter-specific neural encoders if <100 distinct training report vintages per ticker. Pragmatic sample-support limit, not power theorem. Existing E5 genuine Mamba/LSTM five-seed predictions are evaluated in Late Fusion; this is frozen-neural late fusion, NOT newly trained fundamental-aware Mamba. No fake fallback.',
 'calibration':'Same E5 ridge-C1 Platt on2023H2, unconstrained slope; calibrated primary and raw retained. Negative slopes explicitly reported. Simple prior has access to same calibration period. No test-based calibration choice.',
 'primary_inference':'H1 Holm8:2tickers x2simplemodels x(F vs conditioned prior;Early vsP). H3 Holm20:2tickers x5Pmodels x(Late vsP;Late vs same-weight prior blend). GlobalHolm28 also. Average five seed losses per day first. Full-calendar Bartlett HAC20 & circular block20 bootstrap9999 centered two-sided p/basic CIs; lag/block60 sensitivity and block100 dependence stress. No seeds as extra days; report only8quarterly releases per test stock as effective-update warning.',
 'secondary':'Direct-up same families separate; LightGBM early,F vsmetadata,Brier &AUC/calibration descriptives; within-existing8market-state pairwise AUC all/event diagnostic not H2 modeling, bootstrap1999 and Holm over released ranking family; post-release and extreme events descriptive only. No trading backtest.',
 'stopping':'Finite grid only; CPU2 threads, no package/environment/system changes; no new GPU work necessary with quarter-count gate. Fits/checkpoints/config/history/probabilities saved. Preserve all prior results.',
 'independent_validation':'E6 cannot be appended to E3c2026. Separately lock lawful PIT snapshots, final model/feature choices and a genuinely unseen future period before E6 once-only independent evaluation.'
}

def load(ticker,delay=2):
    # Bundle-local input path supports offline reconstruction after unzipping.
    e5.SOURCE=OUT
    f=e5.load(ticker)
    v=pd.read_csv(OUT/'inputs/fundamental_vintages.csv')
    a=align(v[v.ticker.eq(ticker)],f.index,delay)
    f.attrs.update(ticker=ticker)
    return f,a

def fundamental_matrix(f,a,cutoff):
    x=pd.DataFrame(index=f.index)
    for c in CORE:
        x[c]=a[c].clip(-5,5)
        x[c+'_missing']=a[c].isna().astype(float)
    x['release_age_scaled']=a.release_age_days.clip(0,180).fillna(180)/180
    x['reference_sign']=f.reference_sign
    x=x[F_COLS]
    fit=(x.index>='2012-01-01')&(x.index<=cutoff)
    med=x.loc[fit].median().fillna(0)
    filled=x.fillna(med);sc=StandardScaler().fit(filled.loc[fit])
    values=sc.transform(filled).astype(np.float32)
    return values,{'columns':F_COLS,'medians':med.to_dict(),'mean':sc.mean_.tolist(),'scale':sc.scale_.tolist(),'fit_end':cutoff}

def arrays(f,a,arm,block,target='reversal'):
    x,meta=fundamental_matrix(f,a,block['fit_end'])
    p,pm=e5.transform(f,'T',block['fit_end']) if arm!='F' and arm!='M' else (None,None)
    ranges={'fit':('2012-01-01',block['fit_end']),'stop':(block['stop_start'],block['stop_end'])}
    if 'eval_start' in block:ranges['eval']=(block['eval_start'],block['eval_end'])
    else:ranges.update(cal=(block['cal_start'],block['cal_end']),test=(block['test_start'],block['test_end']))
    ids={k:bp.indices(f,*ab) for k,ab in ranges.items()}
    if arm=='PF':x=np.concatenate([p,x[:,:-1]],axis=1)
    elif arm=='P':x=p
    elif arm=='M':x=x[:,len(CORE):] # report age, missing flags, common orientation only
    elif arm!='F':raise ValueError(arm)
    y=f.y5.to_numpy() if target=='reversal' else (f.nextopen_log5.to_numpy()>0).astype(np.int8)
    result={k:(x[ii,None,:] if arm in ('F','M') else bp.windows(x,ii),y[ii]) for k,ii in ids.items()}
    if not all(np.isfinite(v[0]).all() for v in result.values()):raise ValueError('Invalid model input')
    return result,ids,{'F':meta,'P':pm,'arm':arm,'target':target}

def existing_config(ticker,model):
    z=json.loads((OUT/'inputs/e5_selected_configs.json').read_text())
    return z[f'{ticker}_{model}_T']
