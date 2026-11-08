"""Secondary, fixed long/cash schedules with next-open execution and explicit costs."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import e3b_protocol as bp
from e5_core import OUT,FINAL,RULES,rule_scores


def simulate(f,signal_ids,pu,offset,cost_bps,buyhold=False):
    chosen=np.arange(offset,len(signal_ids),5)
    times=signal_ids[chosen]
    start=int(times[0]+1);finish=int(times[-1]+5)
    assert finish<len(f)
    cost=cost_bps/1e4
    nav=np.full(finish-start+1,np.nan);held=np.zeros(len(nav),bool)
    capital=1.;cursor=start;trades=[];turnover=0.
    entries=[(start,finish,1.,f.index[times[0]])] if buyhold else [(int(t+1),int(t+5),float(pu[j]),f.index[t]) for j,t in zip(chosen,times)]
    for entry,exit,p,decision in entries:
        assert entry>=cursor,'Overlapping five-day trades'
        nav[cursor-start:entry-start]=capital
        if p>=.55:
            initial=capital;open_price=float(f.Open.iloc[entry]);close_price=float(f.Close.iloc[exit])
            units=capital/(open_price*(1+cost))
            nav[entry-start:exit-start+1]=units*f.Close.iloc[entry:exit+1].to_numpy()
            held[entry-start:exit-start+1]=True
            gross=(close_price/open_price)-1
            capital=units*close_price*(1-cost);nav[exit-start]=capital
            one_turn=(units*open_price+units*close_price)/initial;turnover+=one_turn
            trades.append({'decision_date':str(decision.date()),'entry_date':str(f.index[entry].date()),'exit_date':str(f.index[exit].date()),'p_up':p,'entry_adjusted_open':open_price,'exit_adjusted_close':close_price,'capital_before':initial,'capital_after':capital,'gross_return':gross,'net_return':capital/initial-1,'roundtrip_notional_over_pretrade_NAV':one_turn})
        else:nav[entry-start:exit-start+1]=capital
        cursor=exit+1
    nav[cursor-start:]=capital
    assert np.isfinite(nav).all() and (nav>0).all()
    ret=np.diff(np.r_[1.,nav])/np.r_[1.,nav[:-1]]
    peak=np.maximum.accumulate(np.r_[1.,nav])[1:]
    years=(f.index[finish]-f.index[start]).days/365.25
    record={'start':str(f.index[start].date()),'end':str(f.index[finish].date()),'n_days':len(nav),'trades':len(trades),'total_return':float(capital-1),'annualized_return':float(capital**(1/years)-1),'daily_sharpe_cash0':float(np.mean(ret)/np.std(ret,ddof=1)*np.sqrt(252)) if np.std(ret)>1e-12 else np.nan,'max_drawdown':float(np.min(nav/peak-1)),'turnover_NAV_units':float(turnover),'annualized_turnover_NAV_units':float(turnover/years),'held_session_fraction':float(held.mean()),'cost_each_side_bps':cost_bps,'offset':offset,'shorts':False,'leverage':False}
    path=pd.DataFrame({'date':f.index[start:finish+1].strftime('%Y-%m-%d'),'nav':nav,'held_during_session':held.astype(int),'daily_return':ret})
    return record,path,trades


def run():
    data=pd.read_csv(OUT/'predictions/all_test_probabilities.csv.gz')
    records=[];navs=[];trades=[]
    for ticker in ['AAPL','TSLA']:
        f=pd.read_csv(OUT/'inputs'/f'{ticker}_technical_and_labels.csv',parse_dates=['Date']).set_index('Date')
        ii=bp.indices(f,FINAL['test_start'],FINAL['test_end'])
        probabilities={}
        for method,z in data[data.ticker==ticker].groupby('method'):
            p=z.groupby('date').p_up.mean().reindex(f.index[ii].strftime('%Y-%m-%d')).to_numpy()
            probabilities[method]=p
        # Literal standalone investor rules retain fixed directions, without calibration inversion.
        scores=rule_scores(f)
        for rule in RULES:probabilities['literal_'+rule]=bp.sigmoid(2*scores[rule].iloc[ii].to_numpy())
        probabilities['buy_hold']=np.ones(len(ii))
        for method,pu in probabilities.items():
            for offset in range(5):
                for cost in [5,10,20]:
                    result,path,ts=simulate(f,ii,pu,offset,cost,buyhold=method=='buy_hold')
                    meta={'ticker':ticker,'method':method,'offset':offset,'cost_each_side_bps':cost}
                    records.append({**meta,**result})
                    if cost==10:navs.append(path.assign(**meta))
                    for t in ts:trades.append({**meta,**t})
    r=pd.DataFrame(records)
    bh=r[r.method=='buy_hold'][['ticker','offset','cost_each_side_bps','total_return']].rename(columns={'total_return':'buy_hold_total_return'})
    r=r.merge(bh,on=['ticker','offset','cost_each_side_bps'],validate='many_to_one')
    r['excess_total_return_vs_buy_hold']=r.total_return-r.buy_hold_total_return
    r.to_csv(OUT/'tables/trading_per_schedule.csv',index=False)
    fields=['total_return','annualized_return','daily_sharpe_cash0','max_drawdown','annualized_turnover_NAV_units','held_session_fraction','excess_total_return_vs_buy_hold','trades']
    agg=r.groupby(['ticker','method','cost_each_side_bps'])[fields].agg(['mean','std','min','max']);agg.columns=['_'.join(c) for c in agg.columns]
    agg.reset_index().to_csv(OUT/'tables/trading_comparison.csv',index=False)
    pd.concat(navs,ignore_index=True).to_csv(OUT/'tables/trading_daily_NAV_primarycost.csv.gz',index=False,compression='gzip')
    pd.DataFrame(trades).to_csv(OUT/'tables/trades.csv.gz',index=False,compression='gzip')
    # Validate exact one-trade accounting independently of NAV summaries.
    z=pd.DataFrame(trades)
    np.testing.assert_allclose(z.capital_after/z.capital_before,(z.exit_adjusted_close/z.entry_adjusted_open)*(1-z.cost_each_side_bps/1e4)/(1+z.cost_each_side_bps/1e4),rtol=1e-12)
    assert (pd.to_datetime(z.entry_date)>pd.to_datetime(z.decision_date)).all()
    assert (pd.to_datetime(z.exit_date)>=pd.to_datetime(z.entry_date)).all()
    bp.write_json(OUT/'audits/trading_integrity.json',{'status':'PASSED','schedules':len(r),'costs_each_side_bps':[5,10,20],'primary_cost':'fee5bps+slippage5bps EACH SIDE; roundtrip about20bps','all5_offsets_reported':True,'no_overlapping_or_levered_positions':True,'test_ensemble_not_mean_seed_metrics':True,'cash_rate':0,'price_proxy':'retrospectively adjusted OHLC, not actual fill/quote records','no_statistical_profitability_claim':True})
    print('E5 SECONDARY BACKTEST PASSED:',len(r),'schedule/cost cases',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path);a=p.parse_args()
    if a.directory:OUT=a.directory.resolve()
    run()
