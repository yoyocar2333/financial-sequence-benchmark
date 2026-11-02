"""Rebuild only what the released aggregate evidence can reproduce.

No imports of a GPU model, downloads, training, raw market data or news.
"""
import argparse,csv,json,math,statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(stage,name):
    with (ROOT/'research'/stage/'results'/name).open(newline='') as f:return list(csv.DictReader(f))

def one(rows,**fields):
    matches=[r for r in rows if all(r[k]==str(v) for k,v in fields.items())]
    if len(matches)!=1:raise ValueError(f'Expected one row for {fields}; got {len(matches)}')
    return matches[0]

def verify_evidence():
    seed=read('E1_E2','metrics_multiseed.csv');summary=read('E1_E2','T01_magnitude.csv')
    assert len(seed)==20
    for t in ['AAPL','TSLA']:
        for a in ['E1','E2b']:
            z=[r for r in seed if r['ticker']==t and r['arm']==a]
            assert sorted(int(r['seed']) for r in z)==[42,43,44,45,46]
            assert all(int(r['n_test'])==501 for r in z)
            s=one(summary,ticker=t,arm=a)
            for field,metric,operation in [('mae_pp','mae_mean',statistics.mean),('mae_pp','mae_std',statistics.stdev),('rmse_pp','rmse_mean',statistics.mean)]:
                assert math.isclose(operation(float(r[field]) for r in z),float(s[metric]),rel_tol=1e-12,abs_tol=1e-12),(t,a,metric)
    e3b=read('E3b','metrics_comparison.csv')
    assert math.isclose(float(one(e3b,ticker='AAPL',horizon=5,model='mamba',arm='B',probability='calibrated')['brier_mean']),.2484942602062394,abs_tol=1e-12)
    assert math.isclose(float(one(e3b,ticker='TSLA',horizon=5,model='lstm',arm='A',probability='calibrated')['brier_mean']),.2475966546477379,abs_tol=1e-12)
    evidence=read('E3c','signal_vs_average_evidence.csv')
    assert len(evidence)==8 and all(r['joint_timing_evidence'].lower()=='false' for r in evidence)
    e4=read('E4c','T12_news_models.csv');tests=read('E4c','T13_news_tests.csv')
    p=float(one(e4,method='lr_P')['brier_cal']);s=float(one(e4,method='lr_S')['brier_cal'])
    gain=one(tests,family='primary_LR_news2',candidate='lr_S',reference='lr_P')
    assert math.isclose(p-s,float(gain['difference']),abs_tol=1e-12)
    assert math.isclose(float(gain['bootstrap_holm2']),.1512,abs_tol=1e-12)
    fn=read('E4c','T11_fnspid.csv')
    counts={t:sum(int(r['article_rows']) for r in fn if r['ticker']==t) for t in ['AAPL','TSLA']}
    assert counts=={'AAPL':9338,'TSLA':10587}
    e5=read('E5','metrics_comparison.csv');gains=read('E5','feature_gains.csv')
    assert len(gains)==8
    for r in gains:
        can=one(e5,ticker=r['ticker'],method=r['candidate'],version='calibrated',task='reversal')
        ref=one(e5,ticker=r['ticker'],method=r['reference'],version='calibrated',task='reversal')
        assert math.isclose(float(ref['brier_mean'])-float(can['brier_mean']),float(r['difference']),abs_tol=1e-12)
    assert all(r['joint_significant'].lower()=='false' for r in gains)
    rank=[r for r in read('E5','within_state_ranking.csv') if r['block_length']=='20']
    assert len(rank)==12 and all(float(r['bootstrap_holm12'])>=.05 for r in rank)
    return {'status':'PASSED','E1_seed_rows_reaggregated':20,'E1_E2_groups':4,'E3b_headline_metrics':'verified','E3c_joint_tests_without_evidence':8,'E4c_LR_news_gain_p':.1512,'FNSPID_target_rows':counts,'E5_primary_tests':8,'E5_primary_significant_gains':0,'E5_within_state_tests':12,'new_training':False,'raw_data_used':False,'GPU_used':False,'independent_validation_executed':False,'scope':'aggregate consistency and plot reproduction; not original model fitting or resampling'}

def figures(out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    z=read('E1_E2','T01_magnitude.csv');fig,axes=plt.subplots(1,2,figsize=(9,3.6))
    for ax,t in zip(axes,['AAPL','TSLA']):
        r=[one(z,ticker=t,arm=a) for a in ['E1','E2b']]
        ax.bar(['E1','E2b'],[float(x['mae_mean']) for x in r],yerr=[float(x['mae_std']) for x in r],color=['#426987','#b47d3b'],capsize=3);ax.set_title(t);ax.set_ylabel('MAE (percentage points); seed SD')
    fig.tight_layout();fig.savefig(out/'E1_E2_multiseed.png',dpi=160);plt.close(fig)
    for stage in ['E3b','E5']:
        z=read(stage,'metrics_comparison.csv');arms=['A','B'] if stage=='E3b' else ['B','T'];models=['xgboost','lightgbm','lstm','mamba']
        fig,axes=plt.subplots(1,2,figsize=(11,4))
        for ax,t in zip(axes,['AAPL','TSLA']):
            for j,a in enumerate(arms):
                rows=[one(z,ticker=t,horizon=5,model=m,arm=a,probability='calibrated') if stage=='E3b' else one(z,ticker=t,method=m+'_'+a,version='calibrated',task='reversal') for m in models]
                ax.bar(np.arange(4)+(j-.5)*.33,[float(r['brier_mean']) for r in rows],.33,label=a)
            ax.set_xticks(np.arange(4),models,rotation=15);ax.set_title(t);ax.set_ylabel('Calibrated Brier (lower better)');ax.legend()
        fig.tight_layout();fig.savefig(out/(stage+'_models.png'),dpi=160);plt.close(fig)
    z=read('E4c','T12_news_models.csv');methods=['lr_P','lr_S','lr_T','hier_P','hier_S','hier_T','global']
    fig,ax=plt.subplots(figsize=(9,4));ax.bar(methods,[float(one(z,method=m)['brier_cal']) for m in methods]);ax.set_ylabel('2025 event Brier; n=65');ax.set_title('E4c Apple-only: calibration is not timing evidence');fig.tight_layout();fig.savefig(out/'E4c_news.png',dpi=160);plt.close(fig)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--no-figures',action='store_true');a=p.parse_args()
    result=verify_evidence()
    if a.output_dir.exists():raise FileExistsError('Choose a new output directory; refuse overwrite')
    a.output_dir.mkdir(parents=True)
    if not a.no_figures:figures(a.output_dir)
    (a.output_dir/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
