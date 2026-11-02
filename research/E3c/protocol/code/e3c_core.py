"""E3c causal compact features, shrinking probability models and fixed inference design."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler
from e3b_protocol import ROOT,SEEDS,FOLDS,FINAL,load_frame,indices,logit,sigmoid,sha,write_json
from e3a_core import thin

OUT=ROOT/'outputs/e3c_20261026'
SOURCE=ROOT/'outputs/e3b_20261026'
METHODS=('global_prior','event_prior','direction_prior','state_prior','recent_event_prior','lr_all','lr_event','xgb_all','xgb_event','recal_lstm_B','recal_mamba_B')
GRIDS={'lr':[{'C':v} for v in (.01,.1,1.)],
       'xgb':[{'max_depth':d,'min_child_weight':c,'n_estimators':n,'reg_lambda':20.,'learning_rate':.03} for d,c,n in [(1,10,50),(2,20,100),(3,30,150)]],
       'prior':[10.,30.,100.]}
PLAN={'version':'E3c-1.0','task':'5-session reversal after E3a raw five-session tail event; exploratory viewed2024-2025; no2026',
 'event':'past5 <= train2012-2022 q10 or >=q90, same E3a exact cutoffs; fold-specific same quantile rule fit on earlier fit-calendar only',
 'target':'E3b sign(past5)*100*log(C[t+5]/Open[t+1])<0; future flats nonreversal, known flat reference excluded',
 'samples':'Same E3b 60-history-complete dates, max20-label purge in every block, test482 dates per stock',
 'split':FINAL,'folds':FOLDS,'seeds':list(SEEDS),'new_representation':'Same compact causal current-state features for new LR/XGB full/event variants; historical horizons5/20/60/120 included. Existing E3b60-window models are archived reference packages, not pure architecture comparisons',
 'complexity_gate':{'new_neural_event_expert_min_train_events':1000,'min_5session_thinned_train_events':300,'min_calibration_events_each_fold':50,'reason':'pragmatic predeclared sample-support gate, not a theorem; no new neural weights if unmet. Existing genuine Mamba/LSTM weights stay frozen'},
 'search':{'candidates':GRIDS,'seed':42,'criterion':'mean three outer-fold event Brier; LR/XGB config chosen jointly by equal mean of all-date and gated-event variant scores to hold capacity fixed between variants','all_search_before_test':True,
 'stopping':'No early stopping on4-10-event blocks; fixed tree rounds are candidate hyperparameters. Inner stop block reused as independent calibration block, not outer labels'},
 'hybrid':'event model trained on tail dates; all-date model trained on all dates with same features/config. Gate expert on events, shared all-date branch off events; global calibration fitted separately for each complete pipeline',
 'calibration':'Fixed identity-prior Platt on ALL inner-calibration dates; eta=a*logit(p)+b, penalty .5*20*((a-1)^2+b^2), slope bound0..3. Same procedure for new models and train-count priors. Sparse event-only sigmoid/isotonic not fitted',
 'priors':'global Beta1,1; event Beta1,1; direction->long120_ex5 sign->VIX median hierarchical pseudo-count alpha10/30/100 selected in expanding CV. recent_event_prior uses cal event counts plus20 pseudo-events at historical event rate, no extra calibration',
 'conditional_heads':'Existing E3b B LSTM/Mamba global Platt kept, add event-only logit intercept fitted on2023H2 event labels with lambda50 identity shrink; no neural retraining, event ordering mathematically unchanged',
 'metrics':['Brier primary, LogLoss,ROC_AUC,PR_AUC,BA,MCC,ECE10,bias','within-coarse-state pair-weighted AUC and within-state probability SD','calibration-period fixed probability quintile bins','signed reversal amplitude separate from probability; historical state/class severity two-part projection, not a directly learned magnitude network'],
 'inference':'mean per-date five-seed losses before calendar ratio HAC20/circular-block20 bootstrap19999; block60 sensitivity. Masks retained on full482-date calendar. minimum20 events and99% nonempty bootstrap. No independent-seed replication',
 'families':'48 primary event-Brier comparisons across both stocks; separate18 within-state AUC tests (new4 + all E3b5 B per stock) Holm. subgroup CIs descriptive; nonoverlap5 sensitivity repeats48 family; nonoverlap20 descriptive when<20 events',
 'ranking_bootstrap':'9999 resamples, block20/60, average seed-specific concordance kernels before bootstrap, compare within-state AUC to0.5; two-sided Holm18',
 'signal_criterion':'Evidence beyond coarse historical averages requires positive event Brier gain versus state_prior with BOTH primary corrected HAC/bootstrap<.05 AND within-state AUC>.5 with corrected bootstrap<.05; isolated calibration/mean gain is not timing skill',
 'resources':'CPU only, two threads, no GPU execution/new packages; genuine E3b neural results reused. Preserve old studies and qua_tum',
 'limits':'Two stocks; fixed existing retrospective adjusted Yahoo snapshot, not point-in-time; thresholds/cells fixed before E3c fitting; previously viewed test remains exploratory',
 'references':['https://scikit-learn.org/stable/modules/calibration.html','https://scikit-learn.org/stable/modules/model_evaluation.html','https://xgboost.readthedocs.io/en/release_3.0.0/python/python_api.html','https://stat.ethz.ch/R-manual/R-devel/library/boot/html/tsboot.html']}


def state(f,cutoff):
    train=f.loc['2012-01-01':cutoff]
    lo,hi=train.past5.quantile([.1,.9]);zlo,zhi=train.z5.quantile([.1,.9])
    vx=float(train.VIX.median());vn=float(train.VXN.median())
    direction=np.where(f.past5>=hi,1,np.where(f.past5<=lo,-1,0))
    long=(f.context120_ex5>=0).astype(int).to_numpy();vol=(f.VIX>=vx).astype(int).to_numpy()
    codes=(direction+1)*4+long*2+vol
    return {'event':direction!=0,'direction':direction,'long':long,'vol':vol,'cell':codes,
        'vxn_high':(f.VXN>=vn).to_numpy(),'z_event':((f.z5<=zlo)|(f.z5>=zhi)).to_numpy(),
        'thresholds':{'past5':[float(lo),float(hi)],'z5':[float(zlo),float(zhi)],'VIX_median':vx,'VXN_median':vn}}


def features(f,cutoff):
    st=state(f,cutoff);x=pd.DataFrame(index=f.index)
    for h in (5,20,60,120):
        x[f'past{h}']=f[f'past{h}'];x[f'z{h}']=f[f'z{h}']
    for n in ('context60_ex5_z','context120_ex5_z','sigma60','RV5','RV20','VIX','VXN','VIX_Change','VXN_Change','daily_log_pp'):
        x[n]=f[n]
    x['reference_sign']=f.reference_sign;x['event_direction']=st['direction'];x['long_sign']=2*st['long']-1
    x['conflict']=(st['direction']*x.long_sign.to_numpy()<0).astype(float)
    x['VIX_high']=st['vol'];x['VXN_high']=st['vxn_high'].astype(float)
    x['intraday_pp']=100*np.log(f.Close/f.Open);x['overnight_pp']=100*np.log(f.Open/f.Close.shift(1))
    x['range_pct']=100*(f.High-f.Low)/f.Close
    x['close_MA5_pp']=100*np.log(f.Close/f.MA5);x['close_MA20_pp']=100*np.log(f.Close/f.MA20)
    x['volume_relative20']=np.log(f.Volume/f.Volume.rolling(20,min_periods=20).mean())
    for code in (0,1,2,3,8,9,10,11):x[f'event_cell_{code}']=(st['cell']==code).astype(float)
    values=x.to_numpy(float);fit=(f.index>='2012-01-01')&(f.index<=cutoff)&np.isfinite(values).all(axis=1)
    scaler=StandardScaler().fit(values[fit]);scaled=scaler.transform(values).astype(np.float32)
    return scaled,st,{'columns':list(x.columns),'scaler_mean':scaler.mean_.tolist(),'scaler_scale':scaler.scale_.tolist(),
        'fit_end':cutoff,'thresholds':st['thresholds'],'fit_n':int(fit.sum())}


def blocks(f,block):
    ranges={'fit':('2012-01-01',block['fit_end']),'cal':(block['stop_start'],block['stop_end'])}
    if 'eval_start' in block:ranges['eval']=(block['eval_start'],block['eval_end'])
    else:ranges={'fit':('2012-01-01',block['fit_end']),'cal':(block['cal_start'],block['cal_end']),
                 'test':(block['test_start'],block['test_end'])}
    return {n:indices(f,a,b) for n,(a,b) in ranges.items()}


def shrink_calibrate(raw,ev,calraw,caly,calev,event_head=False):
    if event_head:
        # One-parameter event correction; probabilities outside the event are untouched.
        xx=logit(calraw)[calev];yy=np.asarray(caly)[calev];c=0.
        for _ in range(50):
            p=sigmoid(xx+c);g=(p-yy).sum()+50*c;h=(p*(1-p)).sum()+50
            step=g/h;c-=step
            if abs(step)<1e-10:break
        return sigmoid(logit(raw)+c*np.asarray(ev)),{'type':'event_intercept','lambda':50.,'offset':float(c),'event_cal_n':len(yy)}
    xx=logit(calraw);yy=np.asarray(caly)
    def objective(theta):
        eta=theta[0]*xx+theta[1];prior=theta-np.array([1.,0.])
        value=np.logaddexp(0,eta).sum()-yy@eta+10*(prior@prior)
        err=sigmoid(eta)-yy;grad=np.array([err@xx,err.sum()])+20*prior
        return float(value),grad
    result=minimize(objective,[1.,0.],jac=True,method='L-BFGS-B',bounds=[(0.,3.),(None,None)],options={'maxiter':300,'ftol':1e-12,'gtol':1e-8})
    if not result.success:raise RuntimeError('Calibration failed '+str(result.message))
    a,b=result.x
    return sigmoid(a*logit(raw)+b),{'type':'identity_prior_Platt','lambda':20.,'slope':float(a),'intercept':float(b),'cal_n':len(yy),'event_cal_n':int(np.asarray(calev).sum())}


class Prior:
    def __init__(self,method,alpha=30.):self.method=method;self.alpha=alpha
    def fit(self,y,st,ids,calids=None):
        self.y=np.asarray(y);self.st=st;self.ids=np.asarray(ids);self.calids=calids
        self.global_p=(self.y[ids].sum()+1)/(len(ids)+2)
        ev=ids[st['event'][ids]];self.event_p=(self.y[ev].sum()+1)/(len(ev)+2)
        return self
    def predict(self,ids):
        ans=[];s=self.st;y=self.y;train=self.ids
        for i in ids:
            if self.method=='global_prior':q=self.global_p
            elif self.method in ('event_prior','recent_event_prior'):
                q=self.event_p if s['event'][i] else self.global_p
                if self.method=='recent_event_prior':
                    cal=self.calids[s['event'][self.calids]==s['event'][i]]
                    q=(y[cal].sum()+20*q)/(len(cal)+20)
            else:
                q=self.global_p;use=train.copy()
                for key in ('direction','long','vol'):
                    use=use[s[key][use]==s[key][i]];q=(y[use].sum()+self.alpha*q)/(len(use)+self.alpha)
                    if self.method=='direction_prior':break
            ans.append(q)
        return np.asarray(ans)


def masks(f,st,ids):
    e=st['event'][ids];d=st['direction'][ids];long=2*st['long'][ids]-1;v=st['vol'][ids].astype(bool)
    return {'all':np.ones(len(ids),bool),'events':e,'non_events':~e,'surge':d==1,'crash':d==-1,
        'conflict':e&(d*long<0),'aligned':e&(d*long>0),'long_up_crash':(d==-1)&(long>0),
        'long_down_surge':(d==1)&(long<0),'event_VIX_high':e&v,'event_VIX_low':e&~v,
        'event_VXN_high':e&st['vxn_high'][ids],'event_VXN_low':e&~st['vxn_high'][ids],
        'z_events':st['z_event'][ids],'nonoverlap5':thin(e,5),'nonoverlap20':thin(e,20),
        'events2024':e&(f.index[ids].year==2024),'events2025':e&(f.index[ids].year==2025)}


def comparisons():
    pairs=[('direction_prior','event_prior'),('state_prior','event_prior'),('recent_event_prior','event_prior'),
        ('lr_event','lr_all'),('xgb_event','xgb_all')]
    for name in ('lr_all','lr_event','xgb_all','xgb_event'):
        pairs.extend([(name,'state_prior'),(name,'event_prior')])
    pairs.extend([('lr_event','e3b_logistic_B'),('xgb_event','e3b_xgboost_B'),('xgb_event','lr_event')])
    for new in ('lr_event','xgb_event'):
        for old in ('e3b_lstm_B','e3b_mamba_B'):pairs.append((new,old))
    for model in ('lstm','mamba'):
        pairs.extend([(f'recal_{model}_B',f'e3b_{model}_B'),(f'recal_{model}_B','state_prior')])
    assert len(pairs)==24 and len(set(pairs))==24
    return pairs
