"""Repair a CSV column-name collision; no probability changes or new training.

Frozen runner's calibration metadata expands a dict whose `method` overwrote
the pipeline name. Recover names and diagnostics from unchanged raw outputs.
"""
import json
import numpy as np
import pandas as pd
from e6_core import OUT,ALL,CPU,load
from e6_data import dump,sha
import e3b_protocol as bp

def main():
    path=OUT/'tables/calibration_parameters.csv';before=sha(path)
    dest=OUT/'audits/calibration_parameters_before_name_repair.csv'
    if not dest.exists():dest.write_bytes(path.read_bytes())
    z=pd.read_csv(OUT/'predictions/all_probabilities.csv.gz');result=[]
    weights=json.loads((OUT/'fusion_weights.json').read_text())
    for target in ['reversal','up_direct']:
        for t in ['AAPL','TSLA']:
            f,_=load(t);cal=bp.indices(f,bp.FINAL['cal_start'],bp.FINAL['cal_end']);test=bp.indices(f,bp.FINAL['test_start'],bp.FINAL['test_end']);fit=bp.indices(f,'2012-01-01',bp.FINAL['fit_end'])
            y=f.y5.to_numpy() if target=='reversal' else (f.nextopen_log5.to_numpy()>0).astype(int);prior=(y[fit].sum()+1)/(len(fit)+2)
            for seed in [42,43,44,45,46]:
                cache={}
                for m in CPU:
                    for arm in ['F','PF']+(['P'] if target=='up_direct' else []):
                        with np.load(OUT/'final'/target/t/arm/m/f'seed{seed}'/'raw_predictions.npz') as a:cache[f'{m}_{arm}']={k:a[k].copy() for k in a.files}
                with np.load(OUT/'final'/target/t/'M/logistic'/f'seed{seed}'/'raw_predictions.npz') as a:cache['logistic_metadata']={k:a[k].copy() for k in a.files}
                for m in (ALL if target=='reversal' else CPU):
                    if target=='reversal':
                        with np.load(OUT/'reused_P/final'/t/m/f'seed{seed}'/'raw_predictions.npz') as a:cache[f'{m}_P']={k:a[k].copy() for k in a.files}
                    pp=cache[f'{m}_P'];fp=cache['logistic_F']
                    for label,w in [('Late',weights[f'{t}_{m}']['F_weight']),('Late50',.5),('PriorBlend',weights[f'{t}_{m}']['F_weight'])]:cache[f'{m}_{label}']={k:(1-w)*pp[k]+w*(prior if label=='PriorBlend' else fp[k]) for k in ['cal','test']}
                for name,a in cache.items():
                    p,meta=bp.calibrate(a['cal'],y[cal],a['test']);old=z[(z.ticker==t)&(z.target==target)&(z.method==name)&(z.seed==seed)].sort_values('date')
                    np.testing.assert_allclose(p,old.p,atol=1e-12)
                    result.append({'ticker':t,'target':target,'method':name,'seed':seed,'calibration_method':meta.pop('method'),**meta})
    pd.DataFrame(result).to_csv(path,index=False)
    dump(OUT/'audits/calibration_metadata_repair.json',{'reason':'Frozen trainer dict expansion overwrote pipeline method name with calibration algorithm name in auxiliary CSV. Raw predictions, trained models, plan and hypothesis tests unchanged.','before_sha256':before,'after_sha256':sha(path),'reconstructed_records':len(result),'all_reconstructed_probabilities_match_existing':True,'new_model_fits':0})
    print('CALIBRATION METADATA REPAIRED',len(result),flush=True)

if __name__=='__main__':main()
