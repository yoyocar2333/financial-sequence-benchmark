"""Existing fit metadata only: representation width, configurations and seed variability."""
import json
import pandas as pd
from e9b_core import R,O,start,save,sha,dump

def main():
 files=['outputs/e5_20261102/selected_configs.json','outputs/e5_20261102/inputs/selected_configs.json','outputs/e5_20261102/tables/metrics_comparison.csv']
 start('complexity',files);new=json.loads((R/files[0]).read_text());old=json.loads((R/files[1]).read_text());metric=pd.read_csv(R/files[2]);rows=[];sources={}
 for t in ['AAPL','TSLA']:
  for m in ['logistic','xgboost','lightgbm','lstm','mamba']:
   for arm,width in [('B',38),('T',51)]:
    cfg=(old[f'{t}_h5_B_{m}'] if arm=='B' else new[f'{t}_{m}_T']);base=(R/'outputs/e3b_20261026/final/h5'/t/'B'/m if arm=='B' else R/'outputs/e5_20261102/final'/t/'T'/m)
    parameters=[];best=[]
    for seed in [42,43,44,45,46]:
     path=base/f'seed{seed}'/'fit_info.json'
     if path.exists():
      complete=json.loads((path.parent/'COMPLETE.json').read_text());assert complete['files']['fit_info.json']==sha(path)
      info=json.loads(path.read_text());parameters.append(info.get('parameter_count'));best.append(info['best_iteration']);sources[str(path.relative_to(R))]=sha(path)
    z=metric[metric.ticker.eq(t)&metric.method.eq(m+'_'+arm)&metric.version.eq('calibrated')&metric.task.eq('reversal')];assert len(z)==1
    rows.append(dict(ticker=t,model=m,arm=arm,features_per_session=width,flattened_columns=60*width,selected_config_index=cfg['config_index'],configuration=json.dumps(cfg['config'],sort_keys=True),parameter_count=next((x for x in parameters if x is not None),None),Brier_seed_mean=z.brier_mean.iloc[0],Brier_seed_SD=z.brier_std.iloc[0],minimum_stopping_iteration=min(best) if best else None,maximum_stopping_iteration=max(best) if best else None,metadata_cases=len(best)))
 save(pd.DataFrame(rows),O/'tables/complexity_and_seed_stability.csv');dump(O/'audits/complexity_source_hashes.json',sources)
 print('Complexity metadata',len(rows),'settings,',len(sources),'original fit-info hashes')
if __name__=='__main__':main()
