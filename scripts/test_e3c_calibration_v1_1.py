"""Regress actual failed case and KKT/old-solver agreement; no test-set predictions."""
import json
import numpy as np
from e3c_core import ROOT,OUT,SOURCE,FOLDS,load_frame,features,blocks,shrink_calibrate as old_calibrate
from e3c_calibration_v1_1 import shrink_calibrate,solve

def main():
    checked=0;old_success=0;maximum=0.
    for ticker in ('AAPL','TSLA'):
        f=load_frame(ticker,SOURCE)
        for family in ('lr','xgb'):
            for ci in range(3):
                for block in FOLDS:
                    base=OUT/'cv'/ticker/family/f'c{ci}'/block['name']
                    if not (base/'event/COMPLETE.json').exists():continue
                    _,s,_=features(f,block['fit_end']);ids=blocks(f,block);e=s['event'][ids['cal']];y=f.y5.iloc[ids['cal']].to_numpy()
                    pa=np.load(base/'all/raw_predictions.npz')['cal'];pe=np.load(base/'event/raw_predictions.npz')['cal']
                    for raw in (pa,np.where(e,pe,pa)):
                        theta,info=solve(raw,y);assert info['projected_gradient_inf']<1e-8
                        p,new=shrink_calibrate(raw,e,raw,y,e)
                        try:
                            pp,old=old_calibrate(raw,e,raw,y,e);error=np.max(abs(p-pp));maximum=max(maximum,float(error));assert error<1e-6;old_success+=1
                        except RuntimeError:pass
                        assert np.isfinite(p).all();checked+=1
    # Boundary active-set and constant/single-class calibration cases.
    for y in (np.zeros(30),np.ones(30),np.arange(30)%2):
        for raw in (np.full(30,.5),np.linspace(.01,.99,30),np.linspace(.99,.01,30)):
            theta,info=solve(raw,y);assert info['projected_gradient_inf']<1e-8 and 0<=theta[0]<=3
    assert checked==66
    print(json.dumps({'historical_calibration_cases_verified':checked,'successful_old_solver_cases_agree':old_success,
        'max_probability_difference':maximum,'failed_case_fixed':True,'KKT_tolerance':1e-8,'test_predictions_used':False},indent=2),flush=True)

if __name__=='__main__':main()
