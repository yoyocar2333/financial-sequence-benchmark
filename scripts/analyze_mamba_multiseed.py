"""Paired time-series inference, five-seed stability, and complete result archive."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

import numpy as np
import pandas as pd
from scipy.stats import norm
from multiseed_common import (ROOT,OUT,OLD,MARKET,SEEDS,PAIRS,STAT_PLAN,leaf,case_root,check_protected,sha256,write_json)


def holm(pvalues):
    p=np.asarray(pvalues,float)
    if not np.isfinite(p).all() or np.any((p<0)|(p>1)):raise ValueError('Invalid p-values')
    order=np.argsort(p,kind='stable');out=np.empty(len(p))
    out[order]=np.minimum(1,np.maximum.accumulate(p[order]*(len(p)-np.arange(len(p)))))
    return out


def hac_mean(values,lag=10):
    x=np.asarray(values,float);n=len(x)
    if x.ndim!=1 or n<=lag or not np.isfinite(x).all():raise ValueError('Invalid HAC series')
    mean=float(x.mean());e=x-mean
    lrv=float(e@e/n)
    for k in range(1,lag+1):lrv+=2*(1-k/(lag+1))*float(e[k:]@e[:-k]/n)
    if lrv < -1e-12:raise ArithmeticError('Negative Bartlett long-run variance')
    se=math.sqrt(max(0,lrv)/n)
    z=mean/se if se else (0. if abs(mean)<1e-14 else math.copysign(float('inf'),mean))
    return {'mean_gain_pp':mean,'hac_se':se,'hac_z':z,'hac_p':float(2*norm.sf(abs(z))),
            'hac_ci95_low':mean-1.959963984540054*se,'hac_ci95_high':mean+1.959963984540054*se}


def circular_indices(n,block,reps=9999,seed=20261020):
    if n<2 or not 1<=block<=n or reps<1:raise ValueError('Invalid bootstrap size')
    rng=np.random.default_rng(seed)
    starts=rng.integers(0,n,size=(reps,math.ceil(n/block)))
    return ((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]


def block_mean(values,indices):
    x=np.asarray(values,float);observed=float(x.mean())
    boot=x[indices].mean(axis=1)
    delta=boot-observed
    p=(1+np.count_nonzero(np.abs(delta)>=abs(observed)))/(len(boot)+1)
    low,high=np.quantile(boot,[.025,.975])
    return {'bootstrap_p':float(p),'bootstrap_ci95_low':float(2*observed-high),
            'bootstrap_ci95_high':float(2*observed-low)}


def load_cases():
    import torch
    check_protected()
    cases={};metrics=[];regimes=[];loss_rows=[]
    for ticker,arm in PAIRS:
        states=pd.read_csv(OUT/f'{ticker}_frozen_states.csv')
        for seed in SEEDS:
            p=leaf(seed,ticker,arm)
            required=['predictions.csv','metrics.csv','training_history.csv','best_state.pt','checkpoint_latest.pt','config.json','environment.json','training.log','training.json']
            if not all((p/f).is_file() and (p/f).stat().st_size for f in required):raise RuntimeError('Missing case outputs: '+str(p))
            config=json.loads((p/'config.json').read_text())
            reference=json.loads((leaf(42,ticker,arm)/'config.json').read_text())
            for key in reference.keys()-{'out','seed'}:
                if config[key]!=reference[key]:raise RuntimeError(f'Configuration changed: seed{seed} {ticker} {arm} {key}')
            if config['seed']!=seed or config['validation_only'] or config['max_train_batches'] is not None:raise RuntimeError('Incorrect seed or partial training')
            pred=pd.read_csv(p/'predictions.csv')
            if pred.date.tolist()!=states.date.tolist() or set(pred['split'])!={'test'} or not pred.date.is_unique:raise RuntimeError('Unpaired or non-test dates')
            if pred.label_date.tolist()!=pd.to_datetime(states.LabelDate).dt.strftime('%Y-%m-%d').tolist():raise RuntimeError('Target dates changed')
            np.testing.assert_allclose(pred.actual_mag_pct,states.TargetMagnitudePct,rtol=1e-12,atol=1e-12)
            if set(pred.seed)!={seed} or set(pred.arm)!={arm} or set(pred.ticker)!={ticker}:raise RuntimeError('Prediction metadata changed')
            err=pred.forecast_mag_pct.to_numpy()-pred.actual_mag_pct.to_numpy()
            if not np.isfinite(err).all():raise RuntimeError('Nonfinite forecast')
            actual_metric=pd.read_csv(p/'metrics.csv').iloc[0]
            mae=float(np.abs(err).mean());rmse=float(np.sqrt(np.square(err).mean()))
            np.testing.assert_allclose([mae,rmse],[actual_metric.mae_pp,actual_metric.rmse_pp],rtol=1e-10)
            history=pd.read_csv(p/'training_history.csv');training=json.loads((p/'training.json').read_text())
            original_training=json.loads((leaf(42,ticker,arm)/'training.json').read_text())
            for key in ('architecture','optimizer','loss','x_scaler','y_scaler','parameter_count','batch_size','memory_fraction','gpu_duty_cycle'):
                if training[key]!=original_training[key]:raise RuntimeError('Training protocol changed: '+key)
            environment=json.loads((p/'environment.json').read_text())
            original_environment=json.loads((leaf(42,ticker,arm)/'environment.json').read_text())
            for key in ('python','versions','torch_cuda','gpu','allocator_fraction'):
                if environment[key]!=original_environment[key]:raise RuntimeError('Validated environment changed: '+key)
            weights=torch.load(p/'best_state.pt',map_location='cpu',weights_only=True)
            checkpoint=torch.load(p/'checkpoint_latest.pt',map_location='cpu',weights_only=True)
            if checkpoint['seed']!=seed or checkpoint['batch_size']!=8 or checkpoint['epoch']!=len(history):
                raise RuntimeError('Checkpoint metadata mismatch')
            if sum(v.numel() for v in weights.values())!=training['parameter_count']:
                raise RuntimeError('Checkpoint parameter count mismatch')
            if not all(torch.isfinite(v).all().item() for v in weights.values()):raise RuntimeError('Nonfinite checkpoint')
            del weights,checkpoint
            if not 1<=len(history)<=30 or not (history.train_batches==346).all():raise RuntimeError('Incomplete epochs')
            if not np.isfinite(history.select_dtypes(include='number').to_numpy()).all():raise RuntimeError('Nonfinite history')
            row={'ticker':ticker,'arm':arm,'seed':seed,'n_test':len(err),'mae_pp':mae,'rmse_pp':rmse,
                 'mae_improvement_vs_mean20_pct':float(actual_metric.improvement_vs_mean20_pct),
                 'epochs':len(history),'best_epoch':training['best_epoch'],'output':str(p.relative_to(ROOT))}
            for name,mask in [('extreme',states.extreme.to_numpy(bool)),('non_extreme',~states.extreme.to_numpy(bool)),
                              ('high_vxn',states.high_vxn.to_numpy(bool)),('lower_vxn',~states.high_vxn.to_numpy(bool)),
                              ('year2024',states.year.to_numpy()==2024),('year2025',states.year.to_numpy()==2025)]:
                r={'ticker':ticker,'arm':arm,'seed':seed,'regime':name,'n_days':int(mask.sum()),
                   'mae_pp':float(np.abs(err[mask]).mean()) if mask.any() else np.nan,
                   'rmse_pp':float(np.sqrt(np.square(err[mask]).mean())) if mask.any() else np.nan}
                regimes.append(r)
                if name=='extreme':row.update(extreme_n=r['n_days'],extreme_mae_pp=r['mae_pp'],extreme_rmse_pp=r['rmse_pp'])
            metrics.append(row);cases[ticker,seed,arm]=(pred,err)
    gains={}
    for ticker in ('AAPL','TSLA'):
        for seed in SEEDS:
            a,e1=cases[ticker,seed,'E1'];b,e2=cases[ticker,seed,'E2b']
            if not a[['date','label_date','actual_mag_pct']].equals(b[['date','label_date','actual_mag_pct']]):raise RuntimeError('Pair mismatch')
            d=np.abs(e1)-np.abs(e2);gains[ticker,seed]=d
            loss_rows.extend({'ticker':ticker,'seed':seed,'date':date,'loss_gain_pp':float(value)} for date,value in zip(a.date,d))
        gains[ticker,'seed_average']=np.mean([gains[ticker,s] for s in SEEDS],axis=0)
    return pd.DataFrame(metrics),pd.DataFrame(regimes),pd.DataFrame(loss_rows),gains


def analyze():
    metrics,regimes,daily,gains=load_cases()
    metrics.to_csv(OUT/'metrics_multiseed.csv',index=False)
    daily.to_csv(OUT/'paired_daily_losses.csv',index=False)
    regimes.to_csv(OUT/'regime_metrics.csv',index=False)
    summary=metrics.groupby(['ticker','arm'],sort=False).agg(
        seeds=('seed','count'),mae_mean=('mae_pp','mean'),mae_std=('mae_pp','std'),mae_min=('mae_pp','min'),mae_max=('mae_pp','max'),
        rmse_mean=('rmse_pp','mean'),rmse_std=('rmse_pp','std'),rmse_min=('rmse_pp','min'),rmse_max=('rmse_pp','max'),
        extreme_mae_mean=('extreme_mae_pp','mean'),extreme_mae_std=('extreme_mae_pp','std'),
        extreme_rmse_mean=('extreme_rmse_pp','mean'),extreme_rmse_std=('extreme_rmse_pp','std')).reset_index()
    if not (summary.seeds==5).all():raise RuntimeError('Need all five seeds')
    summary.to_csv(OUT/'metrics_stability.csv',index=False)
    rsummary=regimes.groupby(['ticker','arm','regime'],sort=False).agg(
        seeds=('seed','count'),n_days=('n_days','first'),mae_mean=('mae_pp','mean'),mae_std=('mae_pp','std'),
        rmse_mean=('rmse_pp','mean'),rmse_std=('rmse_pp','std')).reset_index()
    rsummary.to_csv(OUT/'regime_summary.csv',index=False)
    comparisons=[]
    for (ticker,regime),group in rsummary.groupby(['ticker','regime'],sort=False):
        a=group[group.arm=='E1'].iloc[0];b=group[group.arm=='E2b'].iloc[0]
        per=regimes[(regimes.ticker==ticker)&(regimes.regime==regime)].pivot(index='seed',columns='arm',values='mae_pp')
        comparisons.append({'ticker':ticker,'regime':regime,'n_days':int(a.n_days),
            'mae_E1_mean':float(a.mae_mean),'mae_E2b_mean':float(b.mae_mean),'mean_gain_pp':float(a.mae_mean-b.mae_mean),
            'relative_gain_pct':100*float(a.mae_mean-b.mae_mean)/float(a.mae_mean),
            'contribution_to_full_mean_gain_pp':float(a.mae_mean-b.mae_mean)*int(a.n_days)/501,
            'seeds_E2b_better':int((per.E1>per.E2b).sum()),'inference':'descriptive; no regime significance claims'})
    pd.DataFrame(comparisons).to_csv(OUT/'regime_comparisons.csv',index=False)
    tests=[]
    for length in (10,5,20):
        indices=circular_indices(501,length,STAT_PLAN['bootstrap_replicates'],STAT_PLAN['bootstrap_rng_seed'])
        for (ticker,seed),d in gains.items():
            tests.append({'ticker':ticker,'seed':seed,'n_dates':len(d),'seed_count':5 if seed=='seed_average' else 1,
                'comparison':'E2b versus E1','loss':'absolute error','bandwidth':length,'primary':length==10,
                'family_size':12,**hac_mean(d,length),**block_mean(d,indices)})
    tests=pd.DataFrame(tests)
    for length in (10,5,20):
        select=tests.bandwidth==length
        tests.loc[select,'hac_p_holm12']=holm(tests.loc[select,'hac_p'])
        tests.loc[select,'bootstrap_p_holm12']=holm(tests.loc[select,'bootstrap_p'])
    tests.to_csv(OUT/'paired_tests.csv',index=False)
    lines=['# Mamba 多 seed 探索性穩定性與統計驗證','',
        '完成 seeds 42、43、44、45、46 × AAPL/TSLA × E1/E2b，共20組；本階段新增16組，seed42原始檔未改動、未重訓。',
        '沿用同一凍結市場快照；batch 8、sequence 60、Mamba架構、AdamW 8e-4、SmoothL1 beta .35、patience 6、最多30 epochs均不變。',
        '訓練2012–2022、驗證2023、測試2024–2025。每組501個相同測試日期。這是已檢視樣本上的探索性延伸，不是新獨立確認性測試；未進行2026評估。','',
        '## 五 seed 穩定性','', '誤差單位：報酬百分點。標準差為五個seed的樣本標準差（ddof=1），不是測試平均誤差的標準誤。', '',
        '|股票|設定|MAE平均|MAE標準差|MAE最小|MAE最大|RMSE平均|RMSE標準差|',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in summary.itertuples():lines.append(f'|{r.ticker}|{r.arm}|{r.mae_mean:.6f}|{r.mae_std:.6f}|{r.mae_min:.6f}|{r.mae_max:.6f}|{r.rmse_mean:.6f}|{r.rmse_std:.6f}|')
    lines+=['','## 預先指定的逐日配對比較','',
        '差值 = E1絕對誤差 − E2b絕對誤差，正值有利E2b。主要方法為Bartlett/Newey–West HAC lag10；循環區塊bootstrap長度10、9999次作為穩健性檢查。',
        '每個bandwidth的12個比較（2股票 × [5同seed比較 + 1跨seed日平均比較]）分別以Holm校正。主要結論使用HAC lag10校正p值，不能在不同方法或敏感度結果中選較顯著者。',
        '跨seed比較先在每個日期平均五個seed的loss差，再對501日期推論；沒有把2505列當獨立樣本。這是條件於既有訓練模型的日期不確定性，不是完整重新訓練bootstrap。',
        'Bootstrap同時保留配對與時間區塊，95% basic區間是名目區間，不是多重比較同時信賴區間；p值採null-centering及plus-one校正。', '',
        '|股票|比較單位|平均誤差改善pp|HAC p|HAC Holm p|Bootstrap p|Bootstrap Holm p|Bootstrap 95% CI|',
        '|---|---|---:|---:|---:|---:|---:|---|']
    for r in tests[tests.primary].itertuples():lines.append(f'|{r.ticker}|{r.seed}|{r.mean_gain_pp:+.6f}|{r.hac_p:.4g}|{r.hac_p_holm12:.4g}|{r.bootstrap_p:.4g}|{r.bootstrap_p_holm12:.4g}|[{r.bootstrap_ci95_low:+.6f}, {r.bootstrap_ci95_high:+.6f}]|')
    lines+=['','5/20日HAC與區塊長度敏感度均完整保留在 paired_tests.csv；它們不是額外挑選顯著性的機會。', '',
        '## 極端波動日與市場狀態','',
        '極端日沿用訓練目標p95：AAPL約3.63067、TSLA約7.35140；屬事後真實幅度分層，不能當作可事前辨識的交易條件。高VXN門檻為各股票訓練日期的VXN p75，於新增訓練前凍結。',
        '另外固定比較非極端日、較低VXN日、2024年與2025年。這些是描述性分解，未挑選市場時期或宣稱分層顯著性。', '',
        '|股票|狀態|日期數|E1 MAE平均|E2b MAE平均|MAE改善pp|E2b較佳seed數/5|',
        '|---|---|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(comparisons).itertuples():lines.append(f'|{r.ticker}|{r.regime}|{r.n_days}|{r.mae_E1_mean:.6f}|{r.mae_E2b_mean:.6f}|{r.mean_gain_pp:+.6f}|{r.seeds_E2b_better}/5|')
    lines+=['','各狀態的MAE/RMSE與跨seed標準差見 regime_summary.csv，20組各自數值見 regime_metrics.csv。狀態可能互相重疊，只有各二分法內的加權貢獻可相加。尾部僅23/26天，不能由此斷言跨時期穩定效果。', '',
        '## 完整性與限制','',
        '分析前重新核對原始/調整資料hash、seed42全部原始檔、相同日期與標籤、參數及完整訓練歷史；未覆蓋或重訓seed42。seed42與新增seeds同列，且不隱藏不利結果。',
        '一次一個GPU訓練程序；沿用10% PyTorch allocator與25% pacing，OOM或既有資源警戒會停止後續工作。allocator限制不涵蓋所有CUDA/driver分配。',
        'HAC與區塊bootstrap依賴近似弱平穩/弱依賴條件；結構轉換、小尾部樣本、單一已檢視期間及5個初始化seed均限制外推。自訂CUDA核心也不保證跨硬體逐bit重現。',
        '市場來源是保存的Yahoo回傳與既有調整規則，不是point-in-time資料庫；VIX/VXN日期戳無法證明精確發布時刻。', '',
        '方法參考：', '', *['- '+u for u in STAT_PLAN['references']], '',
        '檔案：metrics_multiseed.csv、metrics_stability.csv、paired_tests.csv、paired_daily_losses.csv、regime_metrics.csv、regime_summary.csv、regime_comparisons.csv、statistical_plan.json。',
        '完整ZIP包含20組結果、checkpoint、日誌、凍結CSV/雜湊、程式與環境lock；不打包虛擬環境本體。']
    (OUT/'MULTISEED_SUMMARY.md').write_text('\n'.join(lines)+'\n')
    check_protected()
    write_json(OUT/'analysis_verification.json',{'status':'PASSED','cases':len(metrics),'primary_comparisons':12,
        'test_years':[2024,2025],'seed42_unchanged':True,'all_dates_and_targets_paired':True,
        'complete_training_histories':True,'configuration_equal_except_seed_and_output':True,
        'checkpoint_cpu_load_finite_weights_verified':True,'environment_and_scalers_identical':True})


def package():
    check_protected()
    archive=OUT/'mamba_multiseed_complete.zip'
    files={}
    for folder in (OUT,OLD,MARKET):
        for p in folder.rglob('*'):
            if p.is_file() and p.suffix not in ('.zip','.tmp') and p.name not in ('archive_manifest.json','archive_sha256.txt') and p!=OUT/'suite_status.json':
                files['stock_prediction/'+str(p.relative_to(ROOT))]=p
    for p in (ROOT/'scripts').glob('*'):
        if p.is_file():files['stock_prediction/'+str(p.relative_to(ROOT))]=p
    for name in ['requirements-mamba.lock.txt','README_MAMBA_SETUP.md','REVIEW_E1_E2.md','LOW_RESOURCE_RUN.md']:
        files['stock_prediction/'+name]=ROOT/name
    for folder in (ROOT/'volatility_e1_e2',ROOT/'tests'):
        for p in folder.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts:
                files['stock_prediction/'+str(p.relative_to(ROOT))]=p
    for p in [ROOT/'volatility_e1_e2.zip',ROOT/'logs/original-archive-manifest.json',ROOT/'MULTISEED_PLAN.md',
              ROOT/'logs/multiseed-tests.log',ROOT/'logs/multiseed-tests.xml']:
        if p.is_file():files['stock_prediction/'+str(p.relative_to(ROOT))]=p
    for p in (ROOT/'logs').glob('gpu-resource-*.jsonl'):
        files['stock_prediction/'+str(p.relative_to(ROOT))]=p
    for p in (OUT.parent/OUT.name).glob('*stdout.log'):
        files['stock_prediction/'+str(p.relative_to(ROOT))]=p
    manifest={name:sha256(p) for name,p in files.items()}
    write_json(OUT/'archive_manifest.json',{'files':manifest})
    temporary=archive.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,p in sorted(files.items()):z.write(p,name)
        z.write(OUT/'archive_manifest.json','stock_prediction/'+str((OUT/'archive_manifest.json').relative_to(ROOT)))
        z.writestr('stock_prediction/outputs/mamba_multiseed_20261020/ARCHIVED_COMPLETION.json',json.dumps({'status':'COMPLETE','new_cases':16,'total_cases':20,'seed42_unchanged':True}))
    with zipfile.ZipFile(temporary) as z:
        if z.testzip() is not None:raise RuntimeError('Archive CRC failure')
        for name,h in manifest.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=h:raise RuntimeError('Archive hash mismatch: '+name)
    temporary.replace(archive)
    (OUT/'archive_sha256.txt').write_text(sha256(archive)+'  '+archive.name+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--package-only',action='store_true')
    args=parser.parse_args()
    if not args.package_only:analyze()
    else:package()
