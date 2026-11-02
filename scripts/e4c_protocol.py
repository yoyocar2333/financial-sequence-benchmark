"""E4c fixed, retrospective Apple-only design. No E4c outcome-driven options."""
from pathlib import Path
import numpy as np
from e3b_protocol import ROOT,sha,write_json,load_frame,indices,logit,sigmoid

OUT=ROOT/'outputs/e4c_20261026'
SOURCE=ROOT/'outputs/e4b_20261026'
SEEDS=(42,43,44,45,46)
TIMINGS=('next_session','delay1','delay2')
TYPES=('litigation','earnings','product_launch','merger_acquisition','regulation','other')
PRICE=['past5','z5','context120_ex5_z','sigma60','VIX','VXN','reference_sign','conflict']
DENSITY=['news_present','news_log_count']
SENTIMENT=['news_signed_mean','news_signed_reference_interaction']
EVENTS=['news_type_earnings','news_type_product_launch','news_type_legal_regulatory','news_type_merger_acquisition']
FEATURES={'P':PRICE,'D':PRICE+DENSITY,'S':PRICE+DENSITY+SENTIMENT,'T':PRICE+DENSITY+SENTIMENT+EVENTS}
PLAN={
 'version':'E4c-1.0','scope':'AAPL Apple Newsroom reconstructed2023-2025 only; retrospective publication-proxy exploratory analysis on already viewed years; no strict PIT or independent confirmation claim',
 'split':{'train':2023,'validation_selection_and_calibration':2024,'exploratory_test':2025},
 'eligibility':'Frozen E3b price-complete60-history dates, nonflat past5 sign, maximum20-session label purge WITHIN EVERY YEAR; common source boundary for all3timings: five-session lookback must start at least2sessions after2023-01-03. Same dates/labels for all models/timings',
 'target':'1 if sign(past5)*100*log(adjusted_Close[t+5]/adjusted_Open[t+1])<0; future flats are continuation. Signed reversal amplitude=-sign(past5)*nextopen_log5 in log percentage points',
 'event_and_state':'Exact existing2012-2022 E3a/E3c past5 q10/q90, long context120_ex5 sign and VIX historical median; never re-estimated using2023-2025',
 'news':'Frozen448Apple full prose, exact text-hash dedup inside each5-information-session window, equal article weights; full-view fixed ProsusAI/finbert revision and unchanged upstreamV1event extraction. No FNSPID, summary, Gemini or TSLA rows in model inputs',
 'timing':'Date-only publication maps to FIRST stock session STRICTLY after date, then optionally+1/+2 sessions. Decision after t close/market index final values. No arrival/version archive; delay sensitivity does not certify PIT',
 'feature_columns':FEATURES,'feature_explanation':'P8price summary; D secondary density-only ablation; S12=P+present/logcount+mean signed FinBERT+signed*reference_sign; T16=S+mean fractions of four broad V1event categories. No-news-in-retained-source signed values0 with explicit present flag; uncollected windows excluded, not zero-imputed. Mean article event fractions; legal+regulation combined. Positive sentiment is not reversal probability',
 'prior':'Train2023 ONLY: global Beta(1,1), event Beta(1,1); hier_P global->event direction(-1,0,+1)->long sign->VIXhigh; pseudo-count30at each level. hier_S adds fixed none/negative<=-.1/neutral/positive>=.1 sentiment bin; hier_T adds fixed broad presence category priority M&A>legal>earnings>product>other. No threshold search',
 'logistic':'All-date StandardScaler fit2023 ONLY + L2 LogisticRegression(lbfgs,tol1e-10,max_iter3000), C in [.01,.1,1]; choose minimum RAW2024ALL-DATE Brier separately per P/D/S/T with smallerC tie-break within1e-12; same search budget and dates. Do not refit raw weights on2024. Check five seeds42-46 determinism; never treat seeds as independent observations',
 'calibration':'Same fixed identity-prior Platt on ALL2024eligible dates after C selection: slope0..3, lambda20 around slope1/intercept0; stable projected Newton. 2024 reused for selection+calibration explicitly, no event-only fitting or calibrated-C search. Preserve raw and calibrated2025predictions. No2025fit/threshold selection',
 'primary':'Calibrated2025TAIL-EVENT paired Brier gains LR P->S and S->T, Holm2 across these two prespecified tests, separate HAC20 and full-calendar circular20-session bootstrap9999. Positive difference means reference loss minus candidate loss',
 'sensitivity':'Identicaldate models under+1/+2news delays; 60sessionHAC/bootstrap; event5session thinning (firstchronological), predeclared not winner selection. Primary claim rests on next_session/block20/event; all sensitivities reported',
 'secondary':'All-date and non-event performance; raw-calibration differences; logloss paired inference; LR D->S density-adjusted sentiment and P->D density diagnostics; hier_P->S->T; LR S/T versus hier_P. Each stated2comparison family separatelyHolm2, diagnostic not primary proof',
 'ranking':'Event pair-weighted AUC within exact frozen direction/long/VIX cells; raw/calibrated. At least20events,10positive,10negative,20samecell positive-negative pairs, and99% valid bootstrap. Test LR P/S/T versus.5 and paired S-P,T-S gains as one Holm5 family per timing/version/block. Preserve full calendar in resampling; tiny subgroups descriptive',
 'signal_criterion':'Beyond price/conditional averages requires positive event Brier improvement versus BOTH LR_P and hier_P with corrected HAC/bootstrap<.05 AND positive within-state AUC gain versus LR_P corrected<.05, plus withinstate AUC>.5 corrected<.05. T additionally requires S->T primary support for event-structure attribution. Calibration-only gains cannot establish event timing',
 'amplitude':'Class probabilities are not a magnitude model. Diagnostic two-part projection uses only2023state/class severity with pseudo-count30, and fixed2024event-probability quartile cutoffs; report signed/absolute realized amplitude, Spearman association, MAE/RMSE; no profit claim',
 'resources':'CPU only two BLAS threads, no package install/GPU training; FNSPID independent complete23.23GBscan with fullfile hash/EOF, never in feature/model dataset',
 'holdout':'No2026data/model execution; exact existing E3c2026protocol bytes preserved. Existing price snapshot retrospective adjusted Yahoo, news recollected2026with unknown historical version. Corporate-source bias and n=one year limit generalization',
 'bootstrap_seed':20261026,'bootstrap_reps':9999,'source_proposal':'outputs/e4b_20261026/E4C_EXPLORATORY_PROPOSAL.md'
}

def clean(value):
    if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    if isinstance(value,np.ndarray):return clean(value.tolist())
    if isinstance(value,(float,np.floating)):return float(value) if np.isfinite(value) else None
    if isinstance(value,(int,np.integer)):return int(value)
    if isinstance(value,np.bool_):return bool(value)
    return value

def dump(path,value):write_json(path,clean(value))
