"""CPU-only event metrics, paired time-series inference, interpretation and portable replay."""
import argparse
import datetime as dt
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from e3c_core import ROOT,OUT,SOURCE,SEEDS,FINAL,load_frame,features,blocks,masks,comparisons,sha,write_json
from e3a_core import calendar_counts,holm
from analyze_e3b import metrics,paired_inference,mdtable

RANK_METHODS=('lr_all','lr_event','xgb_all','xgb_event','e3b_logistic_B','e3b_xgboost_B','e3b_lightgbm_B','e3b_lstm_B','e3b_mamba_B')


def rank_kernel(y,cell,probabilities,mask):
    y=np.asarray(y);cell=np.asarray(cell);p=np.atleast_2d(probabilities)
    positive=np.flatnonzero(mask&(y==1));negative=np.flatnonzero(mask&(y==0))
    same=(cell[positive,None]==cell[None,negative]).astype(float)
    kernel=np.zeros_like(same)
    for pp in p:
        a=pp[positive,None];b=pp[None,negative]
        kernel+=((a>b)+.5*(a==b))*same/len(p)
    return positive,negative,same,kernel


def within_state_auc(y,cell,ps,mask,counts=None):
    pos,neg,same,kernel=rank_kernel(y,cell,ps,mask);pairs=same.sum()
    value=float(kernel.sum()/pairs) if pairs else np.nan
    result={'within_state_auc':value,'matched_positive_negative_pairs':int(pairs),'event_n':int(mask.sum()),
        'bootstrap_p':np.nan,'ci_low':np.nan,'ci_high':np.nan,'bootstrap_valid_fraction':np.nan}
    if counts is None or mask.sum()<20 or pairs<20:return result
    wpos=counts[:,pos];wneg=counts[:,neg]
    denominator=((wpos@same)*wneg).sum(axis=1);valid=denominator>0
    result['bootstrap_valid_fraction']=float(valid.mean())
    if valid.mean()<.99:return result
    boot=((wpos@kernel)*wneg).sum(axis=1)[valid]/denominator[valid]
    low,high=np.quantile(boot,[.025,.975]);delta=value-.5
    result.update(ci_low=float(2*value-high),ci_high=float(2*value-low),
        bootstrap_p=float((1+(np.abs(boot-value)>=abs(delta)).sum())/(len(boot)+1)))
    return result


def within_spread(ps,cell,mask):
    means=[]
    for pp in ps:
        total=0.;n=0
        for c in np.unique(cell[mask]):
            ii=mask&(cell==c);total+=len(pp[ii])*float(np.var(pp[ii]));n+=ii.sum()
        means.append(np.sqrt(total/n))
    return float(np.mean(means))


def severity(f,s,train,test):
    amp=-f.reference_sign.to_numpy()*f.nextopen_log5.to_numpy();y=f.y5.to_numpy();outpos=[];outneg=[];outmean=[]
    glob_pos=amp[train][y[train]==1].mean();glob_neg=(-amp[train][y[train]==0]).mean();glob_mean=amp[train].mean()
    for i in test:
        ii=train[s['cell'][train]==s['cell'][i]];pos=ii[y[ii]==1];neg=ii[y[ii]==0]
        outpos.append((amp[pos].sum()+30*glob_pos)/(len(pos)+30))
        outneg.append(((-amp[neg]).sum()+30*glob_neg)/(len(neg)+30))
        outmean.append((amp[ii].sum()+30*glob_mean)/(len(ii)+30))
    return np.array(outpos),np.array(outneg),np.array(outmean)


def archive():
    excluded={'status.json','archive_manifest.json','e3c_complete_results.zip','e3c_complete_results.zip.sha256','logs/e3c_run.log'}
    write_json(OUT/'ARCHIVED_COMPLETION.json',{'status':'COMPLETE','CPU_only':True,'CV_raw_model_fits':72,'final_raw_model_fits':40,'new_neural_weights_trained':False,'mutable_runtime_status_and_active_log_excluded':True})
    files=[p for p in OUT.rglob('*') if p.is_file() and str(p.relative_to(OUT)) not in excluded and not p.name.endswith('.tmp')]
    write_json(OUT/'archive_manifest.json',{'algorithm':'sha256','files':{str(p.relative_to(OUT)):sha(p) for p in files}})
    files.append(OUT/'archive_manifest.json');zp=OUT/'e3c_complete_results.zip'
    with zipfile.ZipFile(zp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3,allowZip64=True) as z:
        for p in sorted(files):z.write(p,str(Path(OUT.name)/p.relative_to(OUT)))
    with zipfile.ZipFile(zp) as z:
        bad=z.testzip()
        if bad:raise RuntimeError('ZIP CRC failed '+bad)
    (OUT/'e3c_complete_results.zip.sha256').write_text(sha(zp)+'  '+zp.name+'\n')


def analyze(replay=False):
    if not replay:
        from run_e3c import verify
        verify()
    lock=json.loads((OUT/'selection_locked.json').read_text())
    if lock['sha256']!=sha(OUT/'selected_configs.json'):raise RuntimeError('Selection lock changed')
    modelaudits=[]
    for phase,n in [('cv',72),('final',40)]:
        files=list((OUT/phase).rglob('COMPLETE.json'))
        if len(files)!=n:raise RuntimeError('Wrong raw fit count '+phase)
        for p in files:
            for name,h in json.loads(p.read_text())['files'].items():
                if sha(p.parent/name)!=h:raise RuntimeError('Model artifact changed '+str(p.parent/name))
            modelaudits.append({'phase':phase,'path':str(p.parent.relative_to(OUT)),'hashes_verified':True})
    pd.DataFrame(modelaudits).to_csv(OUT/'tables/model_integrity_audit.csv',index=False)
    importances=[]
    for p in (OUT/'final').rglob('feature_importance.csv'):
        ticker,family,seed,scope=p.parent.relative_to(OUT/'final').parts
        z=pd.read_csv(p);columns=json.loads((p.parent/'preprocessing.json').read_text())['columns']
        for row in z.itertuples():importances.append({'ticker':ticker,'method':family+'_'+scope,'seed':int(seed[4:]),
            'feature':columns[row.feature_index],'value':row.value,'absolute_value':abs(row.value),'type':row.type})
    importance=pd.DataFrame(importances)
    importance.to_csv(OUT/'tables/training_feature_importance_per_seed.csv',index=False)
    importance.groupby(['ticker','method','feature','type'])[['value','absolute_value']].agg(['mean','std']).to_csv(OUT/'tables/training_feature_importance.csv')
    files=sorted((OUT/'predictions').glob('*.csv'))
    if len(files)!=176:raise RuntimeError(f'Expected176 probability files, found{len(files)}')
    frames={};records=[];groupmetrics=[];reliability=[];eventbins=[];ranking=[];tests=[];subgains=[];states=[];daily=[];histstates=[];ampmetrics=[];audits=[]
    allprob=[];ampdaily=[]
    for ticker in ('AAPL','TSLA'):
        f=load_frame(ticker,OUT);_,s,_=features(f,FINAL['fit_end']);ids=blocks(f,FINAL);ii=ids['test'];ms=masks(f,s,ii)
        y=f.y5.iloc[ii].to_numpy();cell=s['cell'][ii];amp=-f.reference_sign.iloc[ii].to_numpy()*f.nextopen_log5.iloc[ii].to_numpy()
        frames[ticker]=(f,s,ii);loss={};pred={};sigpos,signeg,ampbase=severity(f,s,ids['fit'],ii)
        for part,partids in ids.items():
            for code in range(12):
                use=partids[s['cell'][partids]==code];z=f.iloc[use];signed=-z.reference_sign*z.nextopen_log5
                histstates.append({'ticker':ticker,'partition':part,'cell':code,'direction':code//4-1,'long_up':(code//2)%2,'VIX_high':code%2,'n':len(use),
                    'reversal_rate':float(z.y5.mean()) if len(z) else np.nan,'signed_amplitude_mean_pp':float(signed.mean()) if len(z) else np.nan,
                    'reversal_magnitude_mean_pp':float(signed[signed>0].mean()) if (signed>0).any() else np.nan,
                    'continuation_magnitude_mean_pp':float(-signed[signed<=0].mean()) if (signed<=0).any() else np.nan})
        tickerfiles=[p for p in files if p.name.startswith(ticker+'_')]
        data=pd.concat([pd.read_csv(p) for p in tickerfiles],ignore_index=True);allprob.append(data)
        for method,z in data.groupby('method'):
            ps=[];rawps=[]
            for seed,zz in z.groupby('seed'):
                zz=zz.sort_values('date');np.testing.assert_array_equal(zz.date,f.index[ii].strftime('%Y-%m-%d'))
                np.testing.assert_array_equal(zz.target,y);np.testing.assert_array_equal(zz.cell,cell)
                np.testing.assert_array_equal(zz.event,ms['events'].astype(int))
                np.testing.assert_allclose(zz.signed_reversal_amplitude_pp,amp,atol=1e-12)
                p=zz.p.to_numpy();raw=zz.p_raw.to_numpy();ps.append(p);rawps.append(raw)
                if not np.isfinite(p).all() or not ((p>=0)&(p<=1)).all():raise RuntimeError('Invalid probability')
                meta={'ticker':ticker,'method':method,'seed':seed}
                for group,mask in ms.items():
                    if not mask.any():continue
                    metrics_={**metrics(y[mask],p[mask]),'probability_sd':float(p[mask].std())}
                    groupmetrics.append({**meta,'group':group,**metrics_})
                for version,q in [('primary',p),('raw',raw)]:
                    records.append({**meta,'probability':version,'group':'events',**metrics(y[ms['events']],q[ms['events']],True)})
                e=ms['events'];binid=np.minimum((p[e]*10).astype(int),9)
                for b in range(10):
                    use=binid==b
                    reliability.append({**meta,'bin':b,'n':int(use.sum()),'mean_probability':float(p[e][use].mean()) if use.any() else np.nan,
                        'reversal_rate':float(y[e][use].mean()) if use.any() else np.nan})
                metadata=json.loads((OUT/'predictions'/f'{ticker}_{method}_seed{seed}.json').read_text())
                bounds=metadata['event_score_quintile_bounds'];scorebin=np.searchsorted(bounds,p,side='right')+1
                for b in range(1,6):
                    use=e&(scorebin==b)
                    eventbins.append({**meta,'score_bin':b,'n':int(use.sum()),'bound_source':'2023H2 event predictions only',
                        'mean_probability':float(p[use].mean()) if use.any() else np.nan,'reversal_rate':float(y[use].mean()) if use.any() else np.nan,
                        'signed_amplitude_mean_pp':float(amp[use].mean()) if use.any() else np.nan,
                        'absolute_amplitude_mean_pp':float(np.abs(amp[use]).mean()) if use.any() else np.nan})
                projected=p*sigpos-(1-p)*signeg
                for j in np.flatnonzero(e):ampdaily.append({**meta,'date':zz.date.iloc[j],'actual_signed_amp_pp':amp[j],
                    'two_part_projection_pp':projected[j],'historical_cell_mean_pp':ampbase[j]})
                ampmetrics.append({**meta,'n':int(e.sum()),'two_part_MAE_pp':float(abs(projected[e]-amp[e]).mean()),
                    'two_part_RMSE_pp':float(np.sqrt(np.mean((projected[e]-amp[e])**2))),
                    'historical_cell_mean_MAE_pp':float(abs(ampbase[e]-amp[e]).mean()),'historical_cell_mean_RMSE_pp':float(np.sqrt(np.mean((ampbase[e]-amp[e])**2))),
                    'Spearman_probability_signed_amp':float(spearmanr(p[e],amp[e]).statistic) if np.ptp(p[e]) else np.nan,
                    'Spearman_probability_absolute_amp':float(spearmanr(p[e],abs(amp[e])).statistic) if np.ptp(p[e]) else np.nan})
                audits.append({**meta,'n':len(zz),'identical_dates_labels_events':True})
            if len(ps)>1:np.testing.assert_array_equal(sorted(z.seed.unique()),SEEDS)
            ps=np.stack(ps);pred[method]=ps;loss[method]=np.mean((ps-y)**2,axis=0)
            e=ms['events'];unconditional=float(np.mean([metrics(y[e],pp[e])['roc_auc'] for pp in ps]))
            rank=within_state_auc(y,cell,ps,e)
            ranking.append({'ticker':ticker,'method':method,'block_length':0,'event_ROC_AUC':unconditional,
                'within_state_probability_sd':within_spread(ps,cell,e),**rank})
            for j,date in enumerate(f.index[ii]):daily.append({'ticker':ticker,'date':date.strftime('%Y-%m-%d'),'method':method,'event':int(e[j]),'cell':int(cell[j]),'target':int(y[j]),'mean_seed_Brier_loss':loss[method][j],'mean_probability':float(ps[:,j].mean())})
        pairs=comparisons();deltas=np.column_stack([loss[reference]-loss[candidate] for candidate,reference in pairs])
        for name,mask in ms.items():
            states.append({'ticker':ticker,'group':name,'n':int(mask.sum()),'reversal_rate':float(y[mask].mean()) if mask.any() else np.nan,
                'signed_amplitude_mean_pp':float(amp[mask].mean()) if mask.any() else np.nan})
        for length in (20,60):
            counts=calendar_counts(len(y),length,reps=19999,seed=20261026)
            for group in ('events','nonoverlap5','nonoverlap20'):
                for (candidate,reference),stat in zip(pairs,paired_inference(deltas,counts,length,ms[group])):
                    tests.append({'ticker':ticker,'group':group,'block_length':length,'candidate':candidate,'reference':reference,'positive_difference':'candidate improves Brier',**stat})
            # Fixed-event subgroup diagnostics of specialization; pointwise, no selected-group claims.
            if length==20:
                cols=np.column_stack([loss['lr_all']-loss['lr_event'],loss['xgb_all']-loss['xgb_event']])
                for group,mask in ms.items():
                    for family,stat in zip(('lr','xgb'),paired_inference(cols,counts,length,mask)):
                        subgains.append({'ticker':ticker,'group':group,'family':family,'correction':'pointwise descriptive',**stat})
            for method in RANK_METHODS:
                ranking.append({'ticker':ticker,'method':method,'block_length':length,**within_state_auc(y,cell,pred[method],ms['events'],counts[:9999])})
    pd.concat(allprob,ignore_index=True).to_csv(OUT/'predictions/all_test_probabilities.csv.gz',index=False,compression='gzip')
    pd.DataFrame(audits).to_csv(OUT/'tables/prediction_integrity_audit.csv',index=False)
    pd.DataFrame(records).to_csv(OUT/'tables/event_metrics_per_seed_raw_calibrated.csv',index=False)
    gm=pd.DataFrame(groupmetrics);gm.to_csv(OUT/'tables/metrics_per_seed.csv',index=False)
    fields=['brier','log_loss','roc_auc','pr_auc','balanced_accuracy','mcc','ece10','calibration_bias','mean_probability','probability_sd']
    summary=gm.groupby(['ticker','method','group'])[['n','prevalence']+fields].agg(['mean','std','min','max']).reset_index()
    summary.columns=['_'.join(c).rstrip('_') for c in summary.columns];summary.to_csv(OUT/'tables/metrics_comparison.csv',index=False)
    pd.DataFrame(reliability).to_csv(OUT/'tables/event_reliability.csv',index=False)
    pd.DataFrame(eventbins).to_csv(OUT/'tables/calibration_fixed_score_bins.csv',index=False)
    pd.DataFrame(states).to_csv(OUT/'tables/event_counts_and_amplitude.csv',index=False)
    pd.DataFrame(histstates).to_csv(OUT/'tables/historical_conditional_states.csv',index=False)
    pd.DataFrame(ampmetrics).to_csv(OUT/'tables/amplitude_diagnostics_per_seed.csv',index=False)
    pd.DataFrame(ampdaily).to_csv(OUT/'tables/amplitude_daily_projections.csv.gz',index=False,compression='gzip')
    pd.DataFrame(daily).to_csv(OUT/'tables/daily_paired_losses.csv.gz',index=False,compression='gzip')
    pd.DataFrame(subgains).to_csv(OUT/'tables/subgroup_specialization_pointwise.csv',index=False)
    tests=pd.DataFrame(tests)
    for (group,length),z in tests.groupby(['group','block_length']):
        assert len(z)==48
        for method in ('hac','bootstrap'):tests.loc[z.index,method+'_holm48']=holm(z[method+'_p'].to_numpy())
    tests.to_csv(OUT/'tables/paired_tests.csv',index=False)
    rank=pd.DataFrame(ranking)
    for length in (20,60):
        mask=rank.block_length==length;assert mask.sum()==18
        rank.loc[mask,'bootstrap_holm18']=holm(rank.loc[mask,'bootstrap_p'].to_numpy())
    rank.to_csv(OUT/'tables/within_state_ranking_tests.csv',index=False)
    primary=tests[(tests.group=='events')&(tests.block_length==20)]
    timing=[]
    for ticker in ('AAPL','TSLA'):
        for method in ('lr_all','lr_event','xgb_all','xgb_event'):
            b=primary[(primary.ticker==ticker)&(primary.candidate==method)&(primary.reference=='state_prior')].iloc[0]
            r=rank[(rank.ticker==ticker)&(rank.method==method)&(rank.block_length==20)].iloc[0]
            timing.append({'ticker':ticker,'method':method,'Brier_gain_vs_state':b.difference,'hac_holm48':b.hac_holm48,'bootstrap_holm48':b.bootstrap_holm48,
                'within_state_AUC':r.within_state_auc,'ranking_holm18':r.bootstrap_holm18,
                'joint_timing_evidence':bool(b.difference>0 and b.hac_holm48<.05 and b.bootstrap_holm48<.05 and r.within_state_auc>.5 and r.bootstrap_holm18<.05)})
    timing=pd.DataFrame(timing);timing.to_csv(OUT/'tables/signal_vs_average_evidence.csv',index=False)
    write_json(OUT/'analysis_audit.json',{'probability_files':176,'raw_model_fits_verified':112,'primary_tests':48,'ranking_tests':18,'no2026_prices':True,'seeds_not_independent_dates':True,'prior_results_preserved':True})
    subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('plot_e3c.py')),'--out',str(OUT)],check=True)
    report(summary,tests,rank,timing,pd.DataFrame(states),pd.DataFrame(histstates))
    if not replay:
        from run_e3c import verify
        verify()
        roottext=(OUT/'E3C_SUMMARY.md').read_text().replace('](figures/','](outputs/'+OUT.name+'/figures/')
        (ROOT/'E3C_SUMMARY.md').write_text(roottext)
    archive()


def report(m,t,r,timing,events,hist):
    primary=t[(t.group=='events')&(t.block_length==20)]
    lines=['# E3c — Event-Conditioned Reversal Prediction','',
        '**研究定位：** 這是已檢視2024–2025樣本上的探索性延伸，不能視為獨立確認。2026價格未載入。全部方案、事件規則、模型規模、搜尋與檢定家族先凍結，再產生E3c測試預測。','',
        '## 研究問題：學到了條件訊號，還是歷史平均？','',
        f'以事先指定的聯合條件判斷：新方法中 **{int(timing.joint_timing_evidence.sum())}/8** 同時具備「勝過收縮條件均值的Brier校正後證據」與「同一粗狀態內AUC>0.5的校正後證據」。不能把改善平均機率／校準，直接解讀為辨識了反轉時機。','',
        mdtable(timing,list(timing.columns),6)]
    for ticker in ('AAPL','TSLA'):
        z=m[(m.ticker==ticker)&(m.group=='events')].sort_values('brier_mean')
        new=z[z.method.isin(['global_prior','event_prior','direction_prior','state_prior','recent_event_prior','lr_all','lr_event','xgb_all','xgb_event','recal_lstm_B','recal_mamba_B'])]
        best=new.iloc[0];baseline=z[z.method=='state_prior'].iloc[0]
        lines+=['',f'## {ticker}：事件條件5日結果','',
            f'事件數 **{int(z.iloc[0].n_mean)}**；新增方法與條件基準中最低平均Brier為 **{best.method}: {best.brier_mean:.6f}**。收縮條件均值state_prior為 {baseline.brier_mean:.6f}。以下為逐seed評分後的平均與SD，非平均機率ensemble分數。','',
            mdtable(new,['method','brier_mean','brier_std','log_loss_mean','roc_auc_mean','ece10_mean','mean_probability_mean','probability_sd_mean'],6),
            '', '既有E3b模型完整診斷（A/B均保留，未挑最佳seed）：','',
            mdtable(z[z.method.str.startswith('e3b_')],['method','brier_mean','roc_auc_mean','ece10_mean','mean_probability_mean'],6)]
        gain=primary[(primary.ticker==ticker)&(((primary.candidate=='lr_event')&(primary.reference=='lr_all'))|((primary.candidate=='xgb_event')&(primary.reference=='xgb_all')))]
        lines+=['','同特徵、同超參數規模、同校準程序下，事件專家相對全日期模型（正值為事件專家改善）：','',
            mdtable(gain,['candidate','reference','difference','bootstrap_ci_low','bootstrap_ci_high','hac_holm48','bootstrap_holm48'],6)]
        whole=m[(m.ticker==ticker)&m.group.isin(['all','events','non_events'])&m.method.isin(['state_prior','lr_all','lr_event','xgb_all','xgb_event','e3b_lstm_B','e3b_mamba_B'])]
        lines+=['','同模型的整體／事件／非事件表現：','',mdtable(whole,['method','group','n_mean','brier_mean','roc_auc_mean','ece10_mean'],6)]
        rr=r[(r.ticker==ticker)&(r.block_length==20)]
        lines+=['','同一「急漲跌方向×長期趨勢×VIX狀態」內的排序能力：','',
            mdtable(rr,['method','within_state_auc','matched_positive_negative_pairs','ci_low','ci_high','bootstrap_holm18'],6)]
    lines+=['','## 事件、趨勢與波動狀態','',
        '主要事件是E3a過去5日報酬的訓練q10/q90尾端；長期趨勢為排除最近5日的120日趨勢。下表全部列出，沒有按測試結果修改門檻。','',
        mdtable(events[events.group.isin(['events','surge','crash','conflict','aligned','long_up_crash','long_down_surge','event_VIX_high','event_VIX_low','nonoverlap5','nonoverlap20'])],['ticker','group','n','reversal_rate','signed_amplitude_mean_pp'],4),
        '', 'historical_conditional_states.csv 同時提供訓練、校準、測試12個固定狀態格的樣本數、反轉率與幅度。跨期間的差異是描述性關聯，不能當作單一因素的因果解釋。','',
        'training_feature_importance.csv 提供全部38特徵的標準化Logistic係數／XGBoost訓練gain及跨seed波動。高度相關特徵的權重不能直接作因果解釋，也不等於通過樣本外檢定的預測因子；沒有依測試表現刪選特徵。','',
        '## 模型與資料支持度','',
        '2012–2022訓練期AAPL/TSLA有546/539個事件，5日冷卻後皆202個；最早fold僅228/222個事件，部分校準區段4–10個。最終2023H2事件校準樣本19/22。預先設定新深度事件網路需至少1000訓練事件、300個5日去重事件且各fold至少50校準事件，均未滿足，因此沒有重新訓練LSTM/Mamba事件網路。這是保守的研究規模選擇，不是神經模型必然失效的定理。',
        '新Logistic/XGBoost使用相同38個因果當日狀態特徵：多尺度報酬/z、剔短期長趨勢、波動、成交量相對量、日內/隔夜報酬、均線偏離與8個事件狀態one-hot，全部可在t決策時得知。狀態one-hot讓Logistic也能表達條件均值交互作用。兩者的全日期/事件分支有完全相同欄位與標準化器；事件分支只改fit樣本。事件外使用全日期分支，避免將事件專家外推當整體預測。',
        '每family3個候選，三個expanding folds，以全日期與事件方法outer事件Brier的等權平均選共享設定，使條件化比較保持相同容量；樹輪數固定於候選中，沒有用4個事件的校準區段early stop。總計72個CV原始fits與40個最終原始fits，seeds42–46。',
        '全部新方法採固定identity-prior Platt（slope向1、intercept向0收縮，lambda20），用全日期2023H2校準。兩種事件/全日期管線各自校準，因此事件外機率也可能因全域校準略有改變。完整原始機率亦保留。近期事件prior則用20個歷史pseudo-events加上校準期事件計數，不再重複校準。',
        '既有真正Mamba/LSTM的B模型另加一個lambda50事件logit截距；權重不改、事件外不改，事件內排序在數學上不變。這只能測試平均概率修正，不能稱為學會新時機訊號。E3b既有模型仍用原60日矩陣與原校準，與本輪compact方法的差異是整體方法套件，不是純架構勝負。','',
        '## 方向與幅度的區別','',
        '方向標籤為過去5日方向與下一開盤至t+5收盤調整後對數報酬是否相反；平盤歸不反轉。signed_reversal_amplitude_pp = −sign(past5)×可執行5日log報酬，正值反轉、負值延續，單位為百分點。',
        'amplitude_diagnostics_per_seed.csv 報告概率與正負幅度、絕對幅度的Spearman關聯，以及「概率×訓練期狀態/類別歷史幅度」的two-part投影誤差。這是利用歷史嚴重程度的投影，不是新增的幅度網路；分類概率高不等於反轉幅度大，這些指標沒有用來選模型。',
        'calibration_fixed_score_bins.csv 的分數區間只用2023H2事件預測固定，再比較測試反轉率與幅度；沒有依測試分位數或最有利門檻分組。','',
        '## 統計推論、重疊與穩健性','',
        '48個主要事件Brier比較跨兩股票共同Holm校正，先平均每個交易日的五seed損失；不是把5×事件數視為獨立樣本。HAC Bartlett20及calendar circular block20 bootstrap19999次為主規格，60為敏感性。事件遮罩保留在完整482日曆上，沒有壓縮為相鄰事件來重抽。',
        '另有18個within-state AUC檢定，先平均各seed的配對concordance kernel，bootstrap9999次、同樣日曆區塊，獨立Holm18。狀態內比較只配同格正負標籤，狀態常數baseline必為0.5；這可避免把不同狀態的平均機率差誤認成同狀態時機辨識。它仍只排除了這組粗狀態的均值差，不代表排除所有潛在市場狀態。',
        '所有CI是單項區間，顯著性看校正p。5日冷卻敏感性也列出完整48比較；20日冷卻事件不足20時只描述、不強作p值。其他子群CI未校正，沒有從中挑顯著格作結論。bootstrap條件於已選模型與校準，不涵蓋整個選模程序的不確定性。',
        '',mdtable(pd.DataFrame([{'group':group,'block':length,'tests':len(g),'joint_Holm_significant':int(((g.hac_holm48<.05)&(g.bootstrap_holm48<.05)).sum())} for (group,length),g in t.groupby(['group','block_length'])]),['group','block','tests','joint_Holm_significant'],0),
        '', '## 圖表','',
        '![事件Brier](figures/01_event_brier.png)','',
        '![條件內排序](figures/02_within_state_ranking.png)','',
        '![校準偏差](figures/03_event_calibration.png)','',
        '![條件狀態跨期間](figures/04_state_drift.png)','',
        '![事件專家增益](figures/05_specialization_gain.png)','',
        '![固定分數區間與幅度](figures/06_probability_amplitude.png)','',
        '## 後續一次性獨立驗證方案','',
        '1. 在開啟2026前，把唯一主要候選、事件規則、基準、概率校準、label5、Brier及within-state排序假說寫成不可變更的timestamped protocol。不能拿本輪測試第一名當作已獨立證實。',
        '2. 建議以本輪最簡單且穩定的收縮條件baseline為預設，只有出現聯合訊號證據才納入複雜候選；最多每股一個事先指定候選對一個基準。校準/重訓截止日期固定在2025年末；若採更新，更新規則須先鎖定，不能看2026逐段結果後改。',
        '3. 保留完整2026作一次性評估，末5日標籤仍需留在同保留期間；以兩股票兩個主要Brier假說Holm2，排序為事先指定次要家族；統計區塊與最小事件數事先固定。若全年事件不足，照樣報CI與證據不足，不擴張門檻。',
        '4. 未使用2026調整規則。本輪沒有開啟2026，也沒有啟動該驗證；若先前任何人已用2026挑規則，需改用更晚真正未檢視的期間。','',
        '## 可重現性與資料限制','',
        'README_E3C.md 提供原研究執行及僅以ZIP內概率/輸入重建分析的CPU replay。原始/調整OHLC與VIX/VXN均來自既有E3a/E3b frozen through2025 CSV。調整方式OHLC*=Adj Close/Close，Volume不變；Yahoo來源快照不是point-in-time archive，因此回溯調整與供應商修正限制仍在。',
        '新模型、checkpoint/設定/history、176組概率、來源E3b校準與預測、版本、完整統計表、PDF/PNG及SHA256 manifest均封裝。原E3a/E3b及舊Mamba幅度結果在執行前後核對不變。CPU執行不使用GPU，不修改qua_tum或既有環境。',
        '', '方法文件：[概率校準](https://scikit-learn.org/stable/modules/calibration.html)、[評估指標](https://scikit-learn.org/stable/modules/model_evaluation.html)、[XGBoost3.0](https://xgboost.readthedocs.io/en/release_3.0.0/python/python_api.html)、[時間序列區塊重抽樣](https://stat.ethz.ch/R-manual/R-devel/library/boot/html/tsboot.html)。']
    (OUT/'E3C_SUMMARY.md').write_text('\n'.join(lines)+'\n')


def replay(source,destination):
    if destination.exists():raise FileExistsError('Replay output already exists; refusing overwrite')
    manifest=json.loads((source/'archive_manifest.json').read_text())['files']
    for name,h in manifest.items():
        if sha(source/name)!=h:raise RuntimeError('Replay source corrupt '+name)
    shutil.copytree(source,destination,ignore=shutil.ignore_patterns('e3c_complete_results.zip','e3c_complete_results.zip.sha256','archive_manifest.json','status.json'))
    global OUT
    OUT=destination;analyze(replay=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replay-source',type=Path);p.add_argument('--output',type=Path);args=p.parse_args()
    if args.replay_source:
        if not args.output:p.error('--output required for replay')
        replay(args.replay_source.resolve(),args.output.resolve())
    else:analyze()
