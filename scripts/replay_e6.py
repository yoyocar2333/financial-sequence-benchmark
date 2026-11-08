"""Recompute E6 statistics from frozen predictions in a NEW offline directory."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--destination',required=True,type=Path);p.add_argument('--no-plots',action='store_true');a=p.parse_args()
    source=a.source.resolve();dest=a.destination.resolve()
    if dest.exists():raise FileExistsError('Use a new destination; original results never overwritten')
    dest.mkdir(parents=True)
    for name in ['inputs','code','predictions']:
        shutil.copytree(source/name,dest/name)
    for name in ['status.json','evaluation_plan.json','selected_F_configs.json','fusion_weights.json','environment.json']:
        shutil.copyfile(source/name,dest/name)
    for name in ['tables','figures','audits']: (dest/name).mkdir()
    env=os.environ.copy();env.update(E6_BUNDLE_ROOT=str(dest),OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
    subprocess.run([sys.executable,'-B',str(dest/'code/analyze_e6.py')],env=env,check=True)
    if not a.no_plots:subprocess.run([sys.executable,'-B',str(dest/'code/analyze_e6.py'),'--plots'],env=env,check=True)
    import pandas as pd
    from pandas.testing import assert_frame_equal
    names=['metrics_per_seed.csv','metrics_comparison.csv','paired_tests.csv','within_state_ranking.csv','event_and_release_age_metrics.csv','calibration_bins.csv','data_and_prediction_audit.csv']
    for name in names:assert_frame_equal(pd.read_csv(source/'tables'/name),pd.read_csv(dest/'tables'/name),check_exact=False,atol=1e-12,rtol=1e-12)
    (dest/'REPLAY_VALIDATION.json').write_text(json.dumps({'status':'PASSED','tables_recomputed_and_matched':names,'new_model_fits':0,'GPU_used':False,'2026_validation_executed':False},indent=2)+'\n')
    print('E6 OFFLINE REPLAY PASSED',dest,flush=True)

if __name__=='__main__':main()
