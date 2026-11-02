"""Editorial interpretation of fixed result tables; never modifies estimates."""
import pandas as pd


def interpretation(out,tests):
    event=pd.read_csv(out/'tables/event_statistics.csv')
    base=event[(event.split=='test')&(event.kind=='raw')&(event.past_horizon==5)&(event['sample']=='nonoverlap')]
    robust=pd.read_csv(out/'tables/robustness.csv')
    mamba=pd.read_csv(out/'tables/mamba_event_metrics.csv')
    rules=pd.read_csv(out/'tables/direction_baselines.csv')
    def e(t,s,h,g='all'):return base[(base.ticker==t)&(base.side==s)&(base.horizon==h)&(base.group==g)].iloc[0]
    def r(t,s,h,v,g='all'):return robust[(robust.ticker==t)&(robust.side==s)&(robust.horizon==h)&(robust.variant==v)&(robust.group==g)].iloc[0]
    def m(t,a,g):return mamba[(mamba.ticker==t)&(mamba.arm==a)&(mamba.group==g)].iloc[0]
    def rule(t,h,g):return rules[(rules.ticker==t)&(rules.horizon==h)&(rules.split=='test')&(rules.rule==g)].iloc[0]
    a=e('AAPL',-1,5);a20=e('AAPL',-1,20);t=e('TSLA',-1,5);t20=e('TSLA',1,20)
    ac=e('AAPL',1,5,'long_down');aa=e('AAPL',1,5,'long_up')
    tc=e('TSLA',1,5,'long_down');ta=e('TSLA',1,5,'long_up')
    az=r('AAPL',-1,5,'normalized_quantiles');ay24=r('AAPL',-1,5,'year2024');ay25=r('AAPL',-1,5,'year2025')
    ts=r('TSLA',-1,5,'q05q95');to=r('TSLA',1,5,'all_candidates');tp=e('TSLA',1,5)
    market=r('AAPL',-1,5,'market_excess')
    main=tests[tests.bandwidth==60];primary=main[main.family=='primary'];valid=main.inference_status.eq('OK')
    lines=['### 結果的具體解讀（固定估計完成後撰寫）','',
        f'**1. 有反彈線索，但不是通用均值回歸規律。** AAPL急跌後5日平均報酬為{a.forward_pct_mean:+.2f}%，反向率{100*a.reversal_mean:.1f}%（n={int(a.n_events)}）；後20日平均{a20.forward_pct_mean:+.2f}%，反向率{100*a20.reversal_mean:.1f}%（n={int(a20.n_events)}）。但後5日完全收復之前5日跌幅的只有{100*a.full_retracement_mean:.1f}%，後20日為{100*a20.full_retracement_mean:.1f}%。反彈和完全收復是不同現象。', '',
        f'TSLA急跌後5日平均{t.forward_pct_mean:+.2f}%，反向率{100*t.reversal_mean:.1f}%（n={int(t.n_events)}），與AAPL不一致。TSLA急漲後20日則有{100*t20.continuation_mean:.1f}%繼續上漲、平均報酬{t20.forward_pct_mean:+.2f}%（n={int(t20.n_events)}），比較像動能延續，不能預設急漲後必回落。', '',
        f'**2. 長期下跌＋短期急漲值得列為後續假說，但樣本不足。** AAPL這類衝突事件後5日回檔率{100*ac.reversal_mean:.1f}%（n={int(ac.n_events)}），長期上漲＋短期急漲則為{100*aa.reversal_mean:.1f}%（n={int(aa.n_events)}）。TSLA對應為{100*tc.reversal_mean:.1f}%（n={int(tc.n_events)}）對{100*ta.reversal_mean:.1f}%（n={int(ta.n_events)}）。兩股方向相似，但差異大小不同，而且至少一格少於10件，均不能據此宣稱穩定反轉訊號。長期上漲＋短期急跌在5日尺度的差異較小，也沒有全域校正後證據。', '',
        f'**3. 效果依事件定義、抽樣及年份而改變。** AAPL急跌後5日反向率在raw門檻為{100*a.reversal_mean:.1f}%，改成相對先前波動率的分位門檻後為{100*az.reversal_mean:.1f}%（n={int(az.n_events)}）；2024為{100*ay24.reversal_mean:.1f}%（n={int(ay24.n_events)}），2025為{100*ay25.reversal_mean:.1f}%（n={int(ay25.n_events)}）。以train-only QQQ市場模型調整後，AAPL的反向機率提升只剩{100*market.reversal_probability_gain:+.1f}pp，顯示廣泛市場共同走勢可能解釋部分原始關聯，但不是因果分解。', '',
        f'TSLA急跌由10%尾端改成5%尾端後，後5日反向率從{100*t.reversal_mean:.1f}%變成{100*ts.reversal_mean:.1f}%（n={int(ts.n_events)}）。TSLA急漲後5日，非重疊抽樣為{100*tp.reversal_mean:.1f}%，保留所有重疊極端日則為{100*to.reversal_mean:.1f}%。冷卻抽樣會改變研究對象：第一個衝擊事件與持續極端狀態中的所有日期不同。這些不穩定性支持後續嚴格驗證，不支持挑選最好門檻。', '',
        '**4. 高低波動狀態尚無可靠排序。** 例如AAPL急跌後5日，在低VXN組反向率100%，但僅3件；高VXN組58.8%，有17件。TSLA相應為33.3%（3件）與43.8%（16件）。低波動尾端事件太少，不能把這種百分比差異解讀成已確認的狀態效應。完整VIX、VXN及長短期結果均保留，不把看起來最有利的一格作結論。', '',
        '**5. Mamba目前較明確的問題是特定情境下幅度低估，不能推論方向能力失敗。**']
    for ticker in ('AAPL','TSLA'):
        all_=m(ticker,'E1','all');down=m(ticker,'E1','shock_down');down2=m(ticker,'E2b','shock_down')
        rev=m(ticker,'E1','expost_reversal');cont=m(ticker,'E1','expost_continuation')
        lines+=['',f'{ticker}：E1的全部日期幅度MAE為{all_.mae_pp_mean:.3f}pp，急跌後為{down.mae_pp_mean:.3f}pp，E2b為{down2.mae_pp_mean:.3f}pp；急跌後rolling20幅度基準MAE為{down.rolling20_mae_mean:.3f}pp。急跌後E1偏差為{down.bias_pp_mean:+.3f}pp（負值表示低估）。但事後反向日E1 MAE為{rev.mae_pp_mean:.3f}pp，延續日為{cont.mae_pp_mean:.3f}pp，沒有一致的「反轉日必然更差」排序。這是幅度條件誤差，不是方向分類表現。']
    lines+=['', '**6. 簡單衝突gate的全日期增益有限，需與基準公平比較。**']
    for ticker in ('AAPL','TSLA'):
        gate=rule(ticker,5,'conflict_gate');maj=rule(ticker,5,'train_majority');mr=rule(ticker,5,'mean_reversion5')
        lines+=['',f'{ticker}後5日方向：衝突gate Accuracy {100*gate.accuracy:.1f}%、train-majority {100*maj.accuracy:.1f}%、簡單均值回歸{100*mr.accuracy:.1f}%；gate Balanced accuracy為{100*gate.balanced_accuracy:.1f}%。這些同日期差異未通過全域校正，不應把Accuracy略升直接當可交易訊號。']
    lines+=['',f'98項中{int(valid.sum())}項達最低推論條件；主要48項中{int(primary.inference_status.eq("OK").sum())}項可推論。其餘因事件過少或區塊樣本缺少其中一組而只作描述。主要家族最小未校正HAC p={primary.hac_p.min():.4f}；個別bootstrap p稍低於0.05也不能取代事先指定方法或多重校正。未顯著不等於效果為零，這個短測試期對稀疏事件的檢定力有限。','']
    lines+=['最長尺度還有支持範圍限制：TSLA的120日急漲訓練上10%條件，在共同測試日期沒有事件，因此圖中標為No events，而非0%反轉率。研究沒有為了補樣本而下調該門檻，也不能對這個格子作推論。','']
    return '\n'.join(lines)
