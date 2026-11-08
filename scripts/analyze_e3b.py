"""CPU-only E3b audit, paired calendar inference and final research archive."""
import itertools
import json
import math
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import (roc_auc_score,average_precision_score,balanced_accuracy_score,
                            matthews_corrcoef,log_loss)
from sklearn.linear_model import LogisticRegression
from e3b_protocol import ROOT,OUT,SEEDS,HORIZONS,MODELS,MAIN_MODELS,FINAL,load_frame,indices,write_json,sha,logit
from e3a_core import calendar_counts,holm,thin


def metrics(y,p,calibration=False):
    y=np.asarray(y,int);p=np.asarray(p,float);hard=p>=.5
    if not len(y):return {}
    bins=np.minimum((p*10).astype(int),9)
    ece=sum(abs(p[bins==b].mean()-y[bins==b].mean())*(bins==b).mean() for b in range(10) if (bins==b).any())
    both=len(np.unique(y))==2
    d={'n':len(y),'prevalence':float(y.mean()),'mean_probability':float(p.mean()),
       'brier':float(np.mean((p-y)**2)),'log_loss':float(log_loss(y,np.clip(p,1e-6,1-1e-6),labels=[0,1])),
       'roc_auc':float(roc_auc_score(y,p)) if both else np.nan,
       'pr_auc':float(average_precision_score(y,p)) if both else np.nan,
       'balanced_accuracy':float(balanced_accuracy_score(y,hard)) if both else np.nan,
       'mcc':float(matthews_corrcoef(y,hard)) if both else np.nan,
       'accuracy':float(np.mean(hard==y)),'ece10':float(ece),'calibration_bias':float(p.mean()-y.mean())}
    tp=int(((y==1)&hard).sum());fp=int(((y==0)&hard).sum());tn=int(((y==0)&~hard).sum());fn=int(((y==1)&~hard).sum())
    d.update(tp=tp,fp=fp,tn=tn,fn=fn,precision=tp/(tp+fp) if tp+fp else 0.,recall=tp/(tp+fn) if tp+fn else np.nan)
    if calibration and both:
        # Diagnostic ONLY: this test regression never changes any saved probability.
        fit=LogisticRegression(C=1e6,max_iter=1000).fit(logit(p).reshape(-1,1),y)
        d.update(calibration_slope=float(fit.coef_[0,0]),calibration_intercept=float(fit.intercept_[0]))
    return d


def groups(f,t):
    up=(f.past5>=t['past5']['0.9']).to_numpy();down=(f.past5<=t['past5']['0.1']).to_numpy()
    long=f.context120_ex5.to_numpy();extreme=up|down
    cu=(long>0)&down;cd=(long<0)&up
    ans={'all':np.ones(len(f),bool),'extreme5_up':up,'extreme5_down':down,'extreme5_any':extreme,
         'conflict_up':cu,'conflict_down':cd,'conflict_any':cu|cd,
         'aligned_extreme':extreme&(np.sign(long)==np.sign(f.past5.to_numpy())),
         'nonoverlap_extreme':thin(extreme,20),'year2024':f.index.year==2024,'year2025':f.index.year==2025}
    for n in ('VIX','VXN'):
        high=(f[n]>=t[n+'_median']).to_numpy();ans[n+'_high']=high;ans[n+'_low']=~high
    return ans


def paired_inference(deltas,counts,lag,mask=None):
    """Columns are paired seed-averaged loss differences on the FULL trading calendar."""
    d=np.asarray(deltas,float)
    if d.ndim==1:d=d[:,None]
    n,k=d.shape;a=np.ones(n) if mask is None else np.asarray(mask,float);na=a.sum()
    if na<20:return [{'inference_status':'insufficient_events','n':int(na)} for _ in range(k)]
    mean=(a[:,None]*d).sum(axis=0)/na
    influence=a[:,None]/(na/n)*(d-mean)
    influence-=influence.mean(axis=0)
    lrv=(influence*influence).sum(axis=0)/n
    for j in range(1,min(lag,n-1)+1):
        lrv+=2*(1-j/(lag+1))*(influence[j:]*influence[:-j]).sum(axis=0)/n
    se=np.sqrt(np.maximum(lrv,0)/n)
    p=np.where(se>0,2*norm.sf(np.abs(mean/np.maximum(se,1e-300))),np.where(abs(mean)<1e-14,1.,0.))
    denominator=counts@a;valid=denominator>0
    good=valid.mean()>=.99
    boot=(counts@(a[:,None]*d))[valid]/denominator[valid,None]
    low,high=np.quantile(boot,[.025,.975],axis=0)
    bp=(1+(np.abs(boot-mean)>=np.abs(mean)).sum(axis=0))/(len(boot)+1)
    result=[]
    for c in range(k):
        result.append({'n':int(na),'difference':float(mean[c]),'hac_se':float(se[c]),'hac_p':float(p[c]) if good else np.nan,
            'hac_ci_low':float(mean[c]-1.95996398454*se[c]),'hac_ci_high':float(mean[c]+1.95996398454*se[c]),
            'bootstrap_p':float(bp[c]) if good else np.nan,'bootstrap_ci_low':float(2*mean[c]-high[c]),
            'bootstrap_ci_high':float(2*mean[c]-low[c]),'bootstrap_valid_fraction':float(valid.mean()),
            'inference_status':'OK' if good else 'sparse_bootstrap_groups'})
    return result


def comparison_vectors(loss):
    """Exactly 51 prespecified comparisons per stock/horizon (102 for both stocks)."""
    rows=[];d=[]
    def add(kind,candidate,reference,delta,**kw):
        rows.append({'comparison':kind,'candidate':candidate,'reference':reference,**kw});d.append(delta)
    for arm in ('A','B'):
        for ref,can in itertools.combinations(MAIN_MODELS,2):
            add('model_pair',can,ref,loss[(ref,arm)]-loss[(can,arm)],arm=arm)
    for model in MAIN_MODELS:
        add('feature_gain',model+'_B',model+'_A',loss[(model,'A')]-loss[(model,'B')],model=model,arm='B-A')
        for arm in ('A','B'):
            for base in ('logistic','cal_prior','momentum20','mean_reversion5'):
                add('vs_baseline',model,base,loss[(base,arm if base=='logistic' else 'shared')]-loss[(model,arm)],arm=arm)
    gm=loss[('mamba','A')]-loss[('mamba','B')]
    for model in ('xgboost','lightgbm','lstm'):
        add('gain_interaction','mamba',model,gm-(loss[(model,'A')]-loss[(model,'B')]),arm='B-A')
    assert len(rows)==51
    return rows,np.column_stack(d)


def audit_and_load():
    files=sorted((OUT/'predictions').glob('*.csv'))
    if len(files)!=336:raise RuntimeError(f'Expected300 fitted+36 baseline probability files, found{len(files)}')
    allpred=pd.concat([pd.read_csv(p) for p in files],ignore_index=True)
    if not (allpred.usage=='test').all():raise RuntimeError('Non-test predictions in test table')
    if not np.isfinite(allpred[['p_raw','p_calibrated']]).all().all():raise RuntimeError('Invalid probabilities')
    if not allpred[['p_raw','p_calibrated']].ge(0).all().all() or not allpred[['p_raw','p_calibrated']].le(1).all().all():raise RuntimeError('Out of range probabilities')
    frames={};thresholds=json.loads((OUT/'inputs/e3a_training_thresholds.json').read_text())
    audits=[]
    for t in ('AAPL','TSLA'):
        f=load_frame(t,source=OUT);ids=indices(f,FINAL['test_start'],FINAL['test_end']);frames[t]=f.iloc[ids]
        dates=f.index[ids].strftime('%Y-%m-%d').to_numpy()
        for h in HORIZONS:
            for (model,arm,seed),z in allpred[(allpred.ticker==t)&(allpred.horizon==h)].groupby(['model','arm','seed']):
                z=z.sort_values('date');np.testing.assert_array_equal(z.date.to_numpy(),dates)
                np.testing.assert_array_equal(z.target_reversal.to_numpy(),f[f'y{h}'].iloc[ids].to_numpy())
                np.testing.assert_allclose(z.executable_log_return_pp,f[f'nextopen_log{h}'].iloc[ids],atol=1e-12)
                if model in MODELS and seed not in SEEDS:raise RuntimeError('Unexpected seed')
                audits.append({'ticker':t,'horizon':h,'model':model,'arm':arm,'seed':seed,'n':len(z),'same_calendar_and_labels':True})
    pd.DataFrame(audits).to_csv(OUT/'tables/prediction_integrity_audit.csv',index=False)
    allpred.to_csv(OUT/'predictions/all_test_probabilities.csv.gz',index=False,compression='gzip')
    return allpred,frames,thresholds


def analysis():
    from run_e3b import verify_code,verify_protected
    verify_code();verify_protected()
    selected=json.loads((OUT/'selection_locked.json').read_text())
    if selected['selected_sha256']!=sha(OUT/'selected_configs.json'):raise RuntimeError('Selection lock changed')
    if len(list((OUT/'cv').rglob('COMPLETE.json')))!=540 or len(list((OUT/'final').rglob('COMPLETE.json')))!=300:
        raise RuntimeError('Missing completed fits')
    allpred,frames,thresholds=audit_and_load()
    rows=[];sub=[];reliability=[];ensembles=[];state=[];lossrows=[];tests=[];subtests=[]
    count_cache={}
    for (ticker,h),z in allpred.groupby(['ticker','horizon']):
        f=frames[ticker];g=groups(f,thresholds[ticker]);n=len(f)
        ys=f[f'y{h}'].to_numpy();loss={};means={}
        for (model,arm),zz in z.groupby(['model','arm']):
            zz=zz.sort_values(['seed','date']);seeds=sorted(zz.seed.unique())
            if model in MODELS:np.testing.assert_array_equal(seeds,SEEDS)
            ps=[]
            for seed,sss in zz.groupby('seed'):
                sss=sss.sort_values('date');p=sss.p_calibrated.to_numpy();ps.append(p)
                meta={'ticker':ticker,'horizon':h,'model':model,'arm':arm,'seed':seed}
                for version,col in [('calibrated','p_calibrated'),('raw','p_raw')]:
                    rows.append({**meta,'probability':version,**metrics(ys,sss[col],True)})
                for name,mask in g.items():
                    if not mask.any():continue
                    sub.append({**meta,'group':name,**metrics(ys[mask],p[mask])})
            pseed=np.stack(ps);loss[(model,arm)]=np.mean((pseed-ys)**2,axis=0);means[(model,arm)]=pseed.mean(axis=0)
            ensembles.append({'ticker':ticker,'horizon':h,'model':model,'arm':arm,'probability':'mean_probability_ensemble',**metrics(ys,pseed.mean(axis=0),True)})
            # Reliability points average seed-specific bin sums; five seeds are not five dates.
            for binid in range(10):
                mask=np.minimum((pseed*10).astype(int),9)==binid
                reliability.append({'ticker':ticker,'horizon':h,'model':model,'arm':arm,'bin':binid,
                    'mean_seed_count':mask.sum()/len(seeds),
                    'mean_probability':float(pseed[mask].mean()) if mask.any() else np.nan,
                    'observed_frequency':float(np.broadcast_to(ys,pseed.shape)[mask].mean()) if mask.any() else np.nan})
            for i,date in enumerate(f.index):
                lossrows.append({'ticker':ticker,'horizon':h,'model':model,'arm':arm,'date':date.strftime('%Y-%m-%d'),
                    'target':int(ys[i]),'mean_seed_brier_loss':loss[(model,arm)][i],'mean_seed_probability':means[(model,arm)][i]})
        for name,mask in g.items():
            state.append({'ticker':ticker,'horizon':h,'group':name,'n':int(mask.sum()),'reversal_rate':float(ys[mask].mean()) if mask.any() else np.nan})
        comparisons,deltas=comparison_vectors(loss)
        for length in (20,60):
            key=(n,length)
            if key not in count_cache:count_cache[key]=calendar_counts(n,length,reps=4999,seed=20261026)
            c=count_cache[key]
            for meta,stat in zip(comparisons,paired_inference(deltas,c,length)):
                tests.append({'ticker':ticker,'horizon':h,'block_length':length,'sign':'positive favors candidate; gain interaction positive favors Mamba gain',**meta,**stat})
            if length==20:
                gd=np.column_stack([loss[(m,'A')]-loss[(m,'B')] for m in MAIN_MODELS])
                for group,mask in g.items():
                    for model,stat in zip(MAIN_MODELS,paired_inference(gd,c,length,mask)):
                        subtests.append({'ticker':ticker,'horizon':h,'group':group,'model':model,'inference':'pointwise exploratory, NOT multiplicity-adjusted',**stat})
    m=pd.DataFrame(rows);m.to_csv(OUT/'tables/metrics_per_seed.csv',index=False)
    fields=['brier','log_loss','roc_auc','pr_auc','balanced_accuracy','mcc','accuracy','ece10','calibration_bias','calibration_slope']
    summary=m.groupby(['ticker','horizon','model','arm','probability'])[fields].agg(['mean','std','min','max']).reset_index()
    summary.columns=['_'.join(c).rstrip('_') if isinstance(c,tuple) else c for c in summary.columns]
    summary.to_csv(OUT/'tables/metrics_comparison.csv',index=False)
    sm=pd.DataFrame(sub);sm.to_csv(OUT/'tables/state_metrics_per_seed.csv',index=False)
    sg=sm.groupby(['ticker','horizon','model','arm','group'])[['n','prevalence']+fields[:9]].agg(['mean','std']).reset_index()
    sg.columns=['_'.join(c).rstrip('_') if isinstance(c,tuple) else c for c in sg.columns]
    sg.to_csv(OUT/'tables/state_metrics.csv',index=False)
    pd.DataFrame(reliability).to_csv(OUT/'tables/reliability.csv',index=False)
    pd.DataFrame(ensembles).to_csv(OUT/'tables/ensemble_metrics_separate.csv',index=False)
    pd.DataFrame(state).to_csv(OUT/'tables/event_counts.csv',index=False)
    pd.DataFrame(lossrows).to_csv(OUT/'tables/daily_paired_losses.csv.gz',index=False,compression='gzip')
    pd.DataFrame(subtests).to_csv(OUT/'tables/state_feature_gains_pointwise.csv',index=False)
    t=pd.DataFrame(tests)
    for length in (20,60):
        mask=t.block_length==length
        assert mask.sum()==306
        for method in ('hac','bootstrap'):
            t.loc[mask,method+'_holm_global306']=holm(t.loc[mask,method+'_p'].to_numpy())
            for primary in (True,False):
                submask=mask&((t.horizon==5) if primary else (t.horizon!=5))
                assert submask.sum()==(102 if primary else 204)
                t.loc[submask,method+'_holm_family']=holm(t.loc[submask,method+'_p'].to_numpy())
    t.to_csv(OUT/'tables/paired_tests.csv',index=False)
    t[t.comparison=='feature_gain'].to_csv(OUT/'tables/feature_gains.csv',index=False)
    write_json(OUT/'analysis_audit.json',{'test_dates':{k:len(v) for k,v in frames.items()},'CV_fits':540,'final_fits':300,
        'test_probability_files':336,'tests_per_bandwidth':306,'primary_family':102,'secondary_family':204,
        'test_data_only_used_after_selection_lock':True,'prior_files_unchanged':True})
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/plot_e3b.py'),'--out',str(OUT)],check=True)
    report(summary,t,sg,pd.DataFrame(state))
    shutil.copyfile(OUT/'E3B_SUMMARY.md',ROOT/'E3B_SUMMARY.md')
    shutil.copyfile(ROOT/'README_E3B.md',OUT/'README_E3B.md')
    verify_code();verify_protected();archive()


def mdtable(df,columns,decimals=5):
    lines=['| '+' | '.join(columns)+' |','| '+' | '.join(['---']*len(columns))+' |']
    for _,row in df.iterrows():
        vals=[]
        for col in columns:
            v=row[col];vals.append(f'{v:.{decimals}f}' if isinstance(v,(float,np.floating)) else str(v))
        lines.append('| '+' | '.join(vals)+' |')
    return '\n'.join(lines)


def report(m,t,sg,events):
    primary=m[(m.horizon==5)&(m.probability=='calibrated')&(~m.model.str.startswith('hard_'))].copy()
    main=t[(t.horizon==5)&(t.block_length==20)]
    significant=(main.hac_holm_family<.05)&(main.bootstrap_holm_family<.05)
    lines=['# E3b — Multi-Horizon Reversal Prediction Benchmark','',
        '本輪已完成固定方案的 540 組 expanding-window 搜尋與 300 組最終訓練（含 Logistic）。這是已檢視過 2024–2025 樣本上的探索性延伸，不是新的獨立確認性測試。2026 價格未載入。','',
        '## 主要結論與五個研究問題','',
        '以下以校準後、逐 seed 評分再平均的 Brier 為主要依據；數字較小較好。表中的標準差是訓練隨機性的描述，沒有把五個 seeds 當成五倍獨立交易日。']
    for ticker in ('AAPL','TSLA'):
        z=primary[primary.ticker==ticker].sort_values('brier_mean');complexz=z[z.model.isin(MAIN_MODELS)]
        best=z.iloc[0];bestc=complexz.iloc[0];prior=z[z.model=='cal_prior'].iloc[0]
        lines+=['',f'### {ticker}：5 日主要任務','',
            f'所有可比較基準中最低平均 Brier：**{best.model}/{best.arm} = {best.brier_mean:.6f}**。四類主要模型中最低為 **{bestc.model}/{bestc.arm} = {bestc.brier_mean:.6f} ± {bestc.brier_std:.6f}**；近期無條件機率基準為 {prior.brier_mean:.6f}。',
            '',mdtable(z,['model','arm','brier_mean','brier_std','log_loss_mean','roc_auc_mean','balanced_accuracy_mean','mcc_mean','ece10_mean'],6)]
        for model in MAIN_MODELS:
            x=main[(main.ticker==ticker)&(main.comparison=='feature_gain')&(main.model==model)].iloc[0]
            lines+=['',f'- {model} 新增 B 特徵的 Brier 改善 A−B：{x.difference:+.6f}；區塊 bootstrap 95% CI [{x.bootstrap_ci_low:+.6f}, {x.bootstrap_ci_high:+.6f}]；Holm 校正 HAC p={x.hac_holm_family:.4f}、bootstrap p={x.bootstrap_holm_family:.4f}。']
        interactions=main[(main.ticker==ticker)&(main.comparison=='gain_interaction')]
        lines+=['','Mamba 是否更會利用長短期資訊，須看「Mamba 的 A−B 增益」減去另一模型的增益，而不能只看 B 組排名：','',
            mdtable(interactions,['candidate','reference','difference','bootstrap_ci_low','bootstrap_ci_high','hac_holm_family','bootstrap_holm_family'],6)]
        vb=main[(main.ticker==ticker)&(main.comparison=='vs_baseline')].copy()
        vb['robust_corrected_win']=(vb.difference>0)&(vb.hac_holm_family<.05)&(vb.bootstrap_holm_family<.05)
        lines+=['',f'複雜模型相對 Logistic、近期無條件機率、軟動能與軟均值回歸的 {len(vb)} 項事先指定比較中，{int(vb.robust_corrected_win.sum())} 項同時通過兩種方法的 Holm 校正且方向為改善。完整正負結果見 paired_tests.csv；沒有通過不等於效果必然為零。']
    lines+=['','## 急漲急跌、訊號衝突與波動狀態','',
        '這些模型在所有合格交易日訓練；下表是在事件子樣本評估同一個整體模型，不是另外訓練的事件條件分類器。conflict_up 指較長期上漲而短期急跌，conflict_down 反之。長期使用剔除最近 5 日的 120 日趨勢。',
        '',mdtable(events[(events.horizon==5)&events.group.isin(['all','extreme5_up','extreme5_down','conflict_up','conflict_down','VIX_high','VIX_low','nonoverlap_extreme'])],['ticker','group','n','reversal_rate'],4)]
    for ticker in ('AAPL','TSLA'):
        best=primary[(primary.ticker==ticker)&primary.model.isin(MAIN_MODELS)].sort_values('brier_mean').iloc[0]
        z=sg[(sg.ticker==ticker)&(sg.horizon==5)&(sg.model==best.model)&(sg.arm==best.arm)&sg.group.isin(['all','extreme5_any','conflict_any','aligned_extreme','VIX_high','VIX_low','VXN_high','VXN_low'])]
        base=sg[(sg.ticker==ticker)&(sg.horizon==5)&(sg.model=='cal_prior')][['group','brier_mean']].rename(columns={'brier_mean':'prior_brier'})
        z=z.merge(base,on='group',validate='one_to_one');z['skill_vs_prior']=1-z.brier_mean/z.prior_brier
        lines+=['',f'{ticker} 最低平均 Brier 主要模型 {best.model}/{best.arm}（依測試排名展示，不能當作再次選模的依據）：','',
            mdtable(z,['group','n_mean','brier_mean','prior_brier','skill_vs_prior','roc_auc_mean','ece10_mean'],5)]
    lines+=['','事件樣本少、重疊多，低 Brier 也可能只是低熵事件較容易猜；必須與同一事件的無條件機率基準比較。state_feature_gains_pointwise.csv 的子群 CI 是未校正探索性診斷，禁止挑顯著子群當確認性發現。nonoverlap_extreme 使用 20 交易日冷卻規則。','',
        '## 1 日與 20 日次要結果','']
    secondary=m[(m.horizon!=5)&(m.probability=='calibrated')&m.model.isin(list(MAIN_MODELS)+['logistic','cal_prior','momentum20','mean_reversion5'])]
    for (ticker,h),z in secondary.groupby(['ticker','horizon']):
        z=z.sort_values('brier_mean');lines+=[f'- {ticker} h={h} 最低平均 Brier 為 {z.iloc[0].model}/{z.iloc[0].arm}：{z.iloc[0].brier_mean:.6f}；全部數字與 204 項次要比較的 Holm 校正在 CSV。']
    lines+=['','## 圖表','',
        '![5 日 Brier](figures/01_brier_h5.png)','',
        '![多尺度特徵增益](figures/02_feature_gains.png)','',
        '![概率校準](figures/03_reliability.png)','',
        '![市場狀態](figures/04_state_skill.png)','',
        '![跨 seed 穩定性](figures/05_seed_stability.png)','',
        '![多時間尺度](figures/06_horizon_skill.png)','',
        '## 鎖定的方法與公平性','',
        '- 標籤：在 t 日資訊到齊後，以 sign(過去 5 日收盤對數報酬) 定義原方向；下一交易日調整後開盤至 t+h 調整後收盤的對數報酬與其反向即為反轉。恰好為零的未來報酬算不反轉；原方向恰好為零的已知日期剔除。這是方向概率模型，與 E1/E2b 幅度模型不同。',
        '- A 為原 E2b 的 14 個市場／波動特徵，加兩組共用的 reference_sign；B 新增 23 個多尺度趨勢、歷史波動標準化衝擊與狀態特徵。每個模型看到相同的 60 日矩陣；樹與 Logistic 展平，LSTM/Mamba 保留時間軸。A 的歷史價格本來就能隱含趨勢，B 測的是顯式表達與更長回溯的增益，不能宣稱新增完全未知資訊。',
        '- 每模型每股票每 arm 每 horizon 只有 3 候選、3 expanding folds，選模 seed42。2016/18/20 上半年以前 fit、該年下半年 early stop、其後兩年 outer validation；用三個 outer 原始 Brier 平均選參數。所有閾值、標準化器每 fold 只用其 fit 日曆資料建立。',
        '- 最終模型 fit2012–2022、2023上半年 early stop、2023下半年固定 ridge Platt 概率校準、2024–2025測試。所有區段刪除最後20日以防標籤跨界，三種 horizon 共用評估日。無條件機率同時報告訓練 prior 與公平使用相同近期校準資料的 cal_prior。',
        '- 延用Yahoo Finance/yfinance既有快照；OHLC乘Adj Close/Close，成交量不調整。inputs/保留原始/調整CSV、企業行動資料、來源版本與雜湊。這不是歷史當時取得的point-in-time archive，回溯調整與供應商事後修正限制仍存在；凍結快照可重現不等於消除該限制。2026價格列完全不進入本輪輸入。',
        '- 兩類神經模型皆單層、width32/64、投影與分類頭相同、dropout0.1、AdamW、BCE、clip1、最多24epoch/patience4，batch64。Mamba 為真正 mamba_ssm.Mamba(d_state16,d_conv4,expand2)，GPU_SMOKE.json 記錄原生 extension 與真正 CUDA forward/backward。參數量不完全相同，完整搜尋與參數量均保存。',
        '- 相對前一個幅度實驗，本輪是新的分類任務，事先採 batch64（原先8）與 duty0.50（原先0.25）；LSTM/Mamba 的 A/B 與各seed一律相同。未修改舊模型、舊seed42、qua_tum 或系統CUDA。GPU同時一個訓練程序，allocator0.10；實際CUDA/OOM錯誤即停止。',
        '- 主要評估校準後機率；原始機率及其指標完整保留，不根據測試挑是否校準。分類閾值固定0.5，ECE固定10格；ROC-AUC/PR-AUC不適用單一標籤子群，會留NaN。校準斜率是測試診斷，未用來重新校準模型。','',
        '## 統計推論及可解釋範圍','',
        f'5 日事先指定 102 項比較中，同時通過 HAC 與 bootstrap 的家族 Holm<0.05：{int(significant.sum())} 項（包括正負方向，詳見CSV）。每項先在相同交易日平均五個seed的 Brier loss，再進行 HAC Bartlett lag20 及完整日曆 circular block20 bootstrap 4,999次。另做 lag/block60 敏感性；不是重抽事件清單，也不是將seeds作獨立觀測。',
        '主要家族102項、兩個次要horizon合計204項分別校正，另報全部306項整體Holm。模型配對、特徵增益、對簡單基準與Mamba增益交互作用都在看測試前指定。正difference代表candidate較好；interaction正值表示Mamba的B增益更大。95% CI為未校正單項區間，顯著性以校正p值為準。',
        '本輪只有兩支股票、一次歷史路徑、有限搜尋預算、約半年校準資料。即使測試排名第一，也不代表普遍優於其他架構；若優勢未通過校正應報告證據不足。Brier與排序能力並非同一事，校準使模型接近prior也可能降低Brier但未學到可交易方向。沒有交易成本、滑價或投資績效宣稱。','',
        '## 下一階段建議','',
        '1. 先依完整表區分「Brier改善但AUC接近0.5」與「排序與校準皆改善」；保留無條件近期prior作強基準。不要依本輪測試重新調參。',
        '2. 事件條件預測需另設訓練任務與巢狀選模，採共享訓練日、足夠事件樣本與預先指定的條件對比；目前只評估整體模型在事件附近的誤差。',
        '3. 若研究者事先鎖定候選與事件假說，可在未來獨立驗證階段一次性評估2026；本輪未開啟該資料，也未用測試表現更新架構。','',
        '## 可重現與檔案','',
        'README_E3B.md 提供環境、執行與重建分析方式；evaluation_plan.json/code_manifest.json 在任何搜尋前凍結。inputs/ 有截至2025的原始與調整CSV、標籤和因果特徵。cv/ 有完整搜尋歷程與模型；final/ 有300組checkpoint、history、設定、原始校準機率與逐日測試機率。predictions/ 為336組完整測試預測與合併gzip。tables/ 有逐seed、平均/標準差/最小/最大值、逐日配對loss、校準與統計檢定。',
        'archive_manifest.json 對封裝檔逐一SHA256，ZIP附SHA256。原E3a、幅度模型結果、資料快照與套件鎖定檔在訓練前後驗證不變。',
        '', '方法參考：'+', '.join(f'[{name}]({url})' for name,url in [
            ('Mamba官方實作','https://github.com/state-spaces/mamba'),
            ('機率校準','https://scikit-learn.org/stable/modules/calibration.html'),
            ('時間序列切分','https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html'),
            ('XGBoost','https://xgboost.readthedocs.io/en/stable/python/python_api.html'),
            ('LightGBM','https://lightgbm.readthedocs.io/en/stable/Parameters.html')])]
    (OUT/'E3B_SUMMARY.md').write_text('\n'.join(lines)+'\n')


def archive():
    excluded={'status.json','archive_manifest.json','e3b_complete_results.zip','e3b_complete_results.zip.sha256','logs/analysis.log'}
    paths=[p for p in OUT.rglob('*') if p.is_file() and str(p.relative_to(OUT)) not in excluded and not p.name.endswith('.tmp')]
    write_json(OUT/'ARCHIVED_COMPLETION.json',{'status':'COMPLETE','analysis_and_training_complete':True,'mutable_status_and_active_analysis_log_excluded':True})
    paths.append(OUT/'ARCHIVED_COMPLETION.json') if OUT/'ARCHIVED_COMPLETION.json' not in paths else None
    manifest={str(p.relative_to(OUT)):sha(p) for p in paths}
    write_json(OUT/'archive_manifest.json',{'algorithm':'sha256','files':manifest})
    paths.append(OUT/'archive_manifest.json')
    zip_path=OUT/'e3b_complete_results.zip'
    with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3,allowZip64=True) as z:
        for p in sorted(paths):z.write(p,arcname=str(Path(OUT.name)/p.relative_to(OUT)))
    with zipfile.ZipFile(zip_path) as z:
        bad=z.testzip()
        if bad:raise RuntimeError('Corrupt archive '+bad)
    (OUT/'e3b_complete_results.zip.sha256').write_text(sha(zip_path)+'  '+zip_path.name+'\n')


if __name__=='__main__':analysis()
