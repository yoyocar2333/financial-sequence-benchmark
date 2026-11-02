"""Fixed E4c paired calendar inference, calibration and amplitude diagnostics."""
import argparse
import json
import os
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from e4c_protocol import ROOT,OUT,TIMINGS,PLAN,sha,dump
from e3a_core import calendar_counts,holm,thin
from analyze_e3b import metrics,paired_inference
from analyze_e3c import rank_kernel,within_spread
from run_e4c import verify,savecsv

FAMILIES={'primary_LR_news2':[('lr_S','lr_P'),('lr_T','lr_S')],
 'secondary_hier_news2':[('hier_S','hier_P'),('hier_T','hier_S')],
 'secondary_LR_vs_price_prior2':[('lr_S','hier_P'),('lr_T','hier_P')],
 'secondary_density_sentiment2':[('lr_D','lr_P'),('lr_S','lr_D')],
 'secondary_total_news2':[('lr_S','lr_P'),('lr_T','lr_P')]}

def groups(z):
    e=z.event.to_numpy(bool);d=z.direction.to_numpy();v=z.VIX_high.to_numpy(bool);c=z.conflict.to_numpy(bool);n=z.news_present.to_numpy(bool)
    return {'all':np.ones(len(z),bool),'events':e,'non_events':~e,'surge':d==1,'crash':d==-1,'conflict':e&c,'aligned':e&~c,
      'event_VIX_high':e&v,'event_VIX_low':e&~v,'event_with_retained_news':e&n,'event_without_retained_news':e&~n,'nonoverlap5':thin(e,5)}

def rank_result(y,c,p,mask,counts=None,reference=None):
    pos,neg,same,kernel=rank_kernel(y,c,p,mask);pairs=float(same.sum())
    if reference is not None:
        kernel-=rank_kernel(y,c,reference,mask)[3];null=0.
    else:null=.5
    value=float(kernel.sum()/pairs) if pairs else np.nan
    r={'estimate':value,'n':int(mask.sum()),'positives':len(pos),'negatives':len(neg),'same_state_pairs':int(pairs),'bootstrap_p':np.nan,'ci_low':np.nan,'ci_high':np.nan,'inference_status':'descriptive_no_bootstrap'}
    if counts is None:return r
    if mask.sum()<20 or len(pos)<10 or len(neg)<10 or pairs<20:
        r['inference_status']='insufficient_events_classes_or_pairs';return r
    a=counts[:,pos];b=counts[:,neg];den=((a@same)*b).sum(axis=1);valid=den>0;r['valid_fraction']=float(valid.mean())
    if valid.mean()<.99:r['inference_status']='sparse_bootstrap_pairs';return r
    boot=(((a@kernel)*b).sum(axis=1)[valid]/den[valid]);lo,hi=np.quantile(boot,[.025,.975])
    r.update(bootstrap_p=float((1+(abs(boot-value)>=abs(value-null)).sum())/(len(boot)+1)),ci_low=float(2*value-hi),ci_high=float(2*value-lo),inference_status='OK')
    return r

def analyze(out):
    verify(out);complete=json.loads((out/'predictions/COMPLETE.json').read_text())
    if sha(out/'predictions/all_probabilities.csv.gz')!=complete['probabilities_sha256']:raise RuntimeError('Prediction hashes changed')
    data=pd.read_csv(out/'data/daily_features.csv.gz');allp=pd.read_csv(out/'predictions/all_probabilities.csv.gz');allrows=[];audits=[];aggregate=[]
    # LBFGS is deterministic: equality is verified, not five independent trials.
    for (timing,method),q in allp.groupby(['timing','method'],sort=False):
        zz=[]
        for seed,z in q.groupby('seed'):
            z=z.sort_values('date');zz.append(z)
        base=zz[0].copy()
        for z in zz[1:]:
            for c in ('date','partition','target','event','cell'):np.testing.assert_array_equal(base[c],z[c])
            np.testing.assert_allclose(base[['p_raw','p_calibrated']],z[['p_raw','p_calibrated']],rtol=0,atol=1e-12)
        base['n_seeds']=len(zz);base['seed']='deterministic_average';aggregate.append(base)
        audits.append({'timing':timing,'method':method,'n_seeds':len(zz),'identical_predictions_across_seeds':True,'dates_identical_between_models':True})
        for partition,z in base.groupby('partition',sort=False):
            y=z.target.to_numpy();ms=groups(z)
            for version,col in [('raw','p_raw'),('calibrated','p_calibrated')]:
                p=z[col].to_numpy()
                for group,mask in ms.items():
                    if mask.any():allrows.append({'timing':timing,'method':method,'partition':partition,'version':version,'group':group,'n_seeds':len(zz),'probability_sd':float(p[mask].std()),'within_state_probability_sd':within_spread([p],z.cell.to_numpy(),mask),**metrics(y[mask],p[mask])})
    avg=pd.concat(aggregate,ignore_index=True)
    savecsv(avg,out/'predictions/daily_mean_probabilities.csv.gz');savecsv(pd.DataFrame(audits),out/'audits/prediction_checks.csv');savecsv(pd.DataFrame(allrows),out/'tables/metrics_comparison.csv')
    tests=[];ranks=[];calibration=[];scorebins=[];ampmetrics=[];ampdaily=[];statecoverage=[];daily=[];calgain=[]
    bounds=json.loads((out/'models/validation_event_score_bins.json').read_text());bounds={(b['timing'],b['method']):b['validation_event_quartile_bounds'] for b in bounds}
    for timing in TIMINGS:
        frame=data[data.timing.eq(timing)&data.partition.eq('test')].sort_values('date');train=data[data.timing.eq(timing)&data.partition.eq('train')]
        q=avg[avg.timing.eq(timing)&avg.partition.eq('test')];dates=frame.date.to_numpy();y=frame.target.to_numpy();cell=frame.cell.to_numpy();ms=groups(frame);e=ms['events'];amp=frame.signed_reversal_amplitude_pp.to_numpy()
        ps={}
        for method,z in q.groupby('method'):
            z=z.sort_values('date');np.testing.assert_array_equal(z.date,dates);np.testing.assert_array_equal(z.target,y);np.testing.assert_array_equal(z.cell,cell)
            ps[method]={'raw':z.p_raw.to_numpy(),'calibrated':z.p_calibrated.to_numpy()}
        for group,mask in ms.items():
            statecoverage.append({'timing':timing,'group':group,'n':int(mask.sum()),'positive':int(y[mask].sum()),'negative':int((1-y[mask]).sum()),'reversal_rate':float(y[mask].mean()) if mask.any() else np.nan,'signed_amplitude_mean_pp':float(amp[mask].mean()) if mask.any() else np.nan,'abs_amplitude_mean_pp':float(abs(amp[mask]).mean()) if mask.any() else np.nan})
        # Train-only magnitude projection; descriptive, not a magnitude fit.
        ta=train.signed_reversal_amplitude_pp.to_numpy();ty=train.target.to_numpy();gp=ta[ty==1].mean();gn=(-ta[ty==0]).mean();gm=ta.mean();sp=[];sn=[];hist=[]
        for cc in cell:
            ii=train.cell.to_numpy()==cc;pos=ii&(ty==1);neg=ii&(ty==0)
            sp.append((ta[pos].sum()+30*gp)/(pos.sum()+30));sn.append(((-ta[neg]).sum()+30*gn)/(neg.sum()+30));hist.append((ta[ii].sum()+30*gm)/(ii.sum()+30))
        sp=np.array(sp);sn=np.array(sn);hist=np.array(hist)
        for method,versions in ps.items():
            for version,p in versions.items():
                for i in range(len(y)):daily.append({'timing':timing,'method':method,'version':version,'date':dates[i],'event':int(e[i]),'target':int(y[i]),'cell':int(cell[i]),'p':p[i],'brier_loss':(p[i]-y[i])**2,'log_loss':-y[i]*np.log(np.clip(p[i],1e-6,1-1e-6))-(1-y[i])*np.log(np.clip(1-p[i],1e-6,1-1e-6))})
                ranks.append({'timing':timing,'method':method,'version':version,'block_length':0,'contrast':'AUC_vs_half',**rank_result(y,cell,p,e)})
                for group in ('all','events'):
                    mask=ms[group];bins=np.minimum((p*5).astype(int),4)
                    for b in range(5):
                        use=mask&(bins==b);calibration.append({'timing':timing,'method':method,'version':version,'group':group,'bin':b,'bin_lower':b/5,'bin_upper':(b+1)/5,'n':int(use.sum()),'mean_probability':float(p[use].mean()) if use.any() else np.nan,'reversal_rate':float(y[use].mean()) if use.any() else np.nan})
            p=versions['calibrated'];proj=p*sp-(1-p)*sn;score=np.searchsorted(bounds[(timing,method)],p,side='right')+1
            for b in range(1,5):
                use=e&(score==b);scorebins.append({'timing':timing,'method':method,'score_quartile':b,'bounds_fit':'2024event predictions; no test cutoffs','n':int(use.sum()),'mean_probability':float(p[use].mean()) if use.any() else np.nan,'reversal_rate':float(y[use].mean()) if use.any() else np.nan,'mean_signed_amplitude_pp':float(amp[use].mean()) if use.any() else np.nan,'mean_absolute_amplitude_pp':float(abs(amp[use]).mean()) if use.any() else np.nan})
            for i in np.flatnonzero(e):ampdaily.append({'timing':timing,'method':method,'date':dates[i],'target':int(y[i]),'p':p[i],'signed_actual_pp':amp[i],'two_part_projection_pp':proj[i],'historical_state_mean_pp':hist[i]})
            ampmetrics.append({'timing':timing,'method':method,'n_events':int(e.sum()),'two_part_MAE_pp':float(abs(proj[e]-amp[e]).mean()),'two_part_RMSE_pp':float(np.sqrt(np.mean((proj[e]-amp[e])**2))),'historical_state_mean_MAE_pp':float(abs(hist[e]-amp[e]).mean()),'historical_state_mean_RMSE_pp':float(np.sqrt(np.mean((hist[e]-amp[e])**2))),'spearman_probability_signed_amplitude':float(spearmanr(p[e],amp[e]).statistic) if np.ptp(p[e])>0 else np.nan,'spearman_probability_absolute_amplitude':float(spearmanr(p[e],abs(amp[e])).statistic) if np.ptp(p[e])>0 else np.nan})
        for length in (20,60):
            counts=calendar_counts(len(y),length,reps=PLAN['bootstrap_reps'],seed=PLAN['bootstrap_seed'])
            for version in ('raw','calibrated'):
                loss={m:(v[version]-y)**2 for m,v in ps.items()}
                ll={m:-y*np.log(np.clip(v[version],1e-6,1-1e-6))-(1-y)*np.log(np.clip(1-v[version],1e-6,1-1e-6)) for m,v in ps.items()}
                for group in ('events','all','nonoverlap5'):
                    for family,pairs in FAMILIES.items():
                        for score,l in [('Brier',loss),('LogLoss',ll)]:
                            delta=np.column_stack([l[r]-l[c] for c,r in pairs]);ss=paired_inference(delta,counts,length,ms[group])
                            for (candidate,reference),s in zip(pairs,ss):tests.append({'timing':timing,'version':version,'block_length':length,'group':group,'family':family,'metric':score,'candidate':candidate,'reference':reference,**s})
                for m in ps:
                    r=rank_result(y,cell,ps[m][version],e,counts)
                    ranks.append({'timing':timing,'method':m,'version':version,'block_length':length,'contrast':'AUC_vs_half','within_state_probability_sd':within_spread([ps[m][version]],cell,e),**r})
                for c,r in [('lr_S','lr_P'),('lr_T','lr_S'),('lr_T','lr_P')]:
                    ranks.append({'timing':timing,'method':c,'reference':r,'version':version,'block_length':length,'contrast':'paired_AUC_gain',**rank_result(y,cell,ps[c][version],e,counts,ps[r][version])})
            delta=np.column_stack([(v['raw']-y)**2-(v['calibrated']-y)**2 for v in ps.values()])
            for m,s in zip(ps,paired_inference(delta,counts,length,e)):calgain.append({'timing':timing,'method':m,'block_length':length,**s})
        print('ANALYZED',timing,'events',int(e.sum()),'paired_calendar',len(y),flush=True)
    t=pd.DataFrame(tests)
    for keys,z in t.groupby(['timing','version','block_length','group','family','metric']):
        assert len(z)==2
        for p in ('hac','bootstrap'):t.loc[z.index,p+'_holm2']=holm(z.get(p+'_p',pd.Series(np.nan,index=z.index)).to_numpy())
    savecsv(t,out/'tables/paired_tests.csv')
    rank=pd.DataFrame(ranks)
    # The primary ranking family is LR P/S/T vs half plus S-P/T-S (five).
    # T-P is a separately prespecified total-news diagnostic (family of one).
    for keys,z in rank[rank.block_length.gt(0)].groupby(['timing','version','block_length']):
        use=(z.contrast.eq('AUC_vs_half')&z.method.isin(['lr_P','lr_S','lr_T']))|(z.contrast.eq('paired_AUC_gain')&~(z.method.eq('lr_T')&z.reference.eq('lr_P')))
        ii=z.index[use];assert len(ii)==5;rank.loc[ii,'bootstrap_holm5']=holm(rank.loc[ii,'bootstrap_p'].to_numpy())
        ii=z.index[z.contrast.eq('paired_AUC_gain')&z.method.eq('lr_T')&z.reference.eq('lr_P')];rank.loc[ii,'bootstrap_secondary_total_news_p']=rank.loc[ii,'bootstrap_p']
    savecsv(rank,out/'tables/within_state_ranking.csv')
    cg=pd.DataFrame(calgain)
    for _,z in cg.groupby(['timing','block_length']):
        for p in ('hac','bootstrap'):cg.loc[z.index,p+'_holm9']=holm(z[p+'_p'].to_numpy())
    savecsv(cg,out/'tables/calibration_gain.csv');savecsv(pd.DataFrame(calibration),out/'tables/reliability_bins.csv');savecsv(pd.DataFrame(scorebins),out/'tables/validation_fixed_score_bins_amplitude.csv');savecsv(pd.DataFrame(ampmetrics),out/'tables/amplitude_metrics.csv');savecsv(pd.DataFrame(ampdaily),out/'data/amplitude_daily_projections.csv.gz');savecsv(pd.DataFrame(statecoverage),out/'tables/market_event_support.csv');savecsv(pd.DataFrame(daily),out/'data/daily_paired_losses.csv.gz')
    evidence=[]
    for timing in TIMINGS:
        primary=t[t.timing.eq(timing)&t.version.eq('calibrated')&t.block_length.eq(20)&t.group.eq('events')&t.metric.eq('Brier')]
        ranking=rank[rank.timing.eq(timing)&rank.version.eq('calibrated')&rank.block_length.eq(20)]
        for m in ('lr_S','lr_T'):
            a=primary[primary.family.eq('secondary_total_news2')&primary.candidate.eq(m)].iloc[0];b=primary[primary.family.eq('secondary_LR_vs_price_prior2')&primary.candidate.eq(m)].iloc[0]
            r=ranking[ranking.method.eq(m)&ranking.contrast.eq('AUC_vs_half')].iloc[0]
            gain=ranking[ranking.method.eq(m)&ranking.contrast.eq('paired_AUC_gain')&ranking.reference.eq('lr_P')].iloc[0]
            rp=primary[primary.family.eq('primary_LR_news2')&primary.candidate.eq(m)].iloc[0]
            rankingp=gain.bootstrap_holm5 if m=='lr_S' else gain.bootstrap_secondary_total_news_p
            ok=bool(a.difference>0 and b.difference>0 and max(a.hac_holm2,a.bootstrap_holm2,b.hac_holm2,b.bootstrap_holm2)<.05 and r.estimate>.5 and r.bootstrap_holm5<.05 and gain.estimate>0 and rankingp<.05 and rp.difference>0 and max(rp.hac_holm2,rp.bootstrap_holm2)<.05)
            evidence.append({'timing':timing,'method':m,'Brier_gain_vs_price':a.difference,'Brier_vs_price_HAC_Holm2':a.hac_holm2,'Brier_vs_price_bootstrap_Holm2':a.bootstrap_holm2,'Brier_gain_vs_hier_P':b.difference,'Brier_vs_prior_HAC_Holm2':b.hac_holm2,'Brier_vs_prior_bootstrap_Holm2':b.bootstrap_holm2,'within_state_AUC':r.estimate,'AUC_Holm5':r.bootstrap_holm5,'within_state_AUC_gain_vs_price':gain.estimate,'paired_AUC_gain_p_corrected_or_prespecified_secondary':rankingp,'joint_evidence_beyond_price_and_state_prior':ok})
    savecsv(pd.DataFrame(evidence),out/'tables/signal_vs_average_evidence.csv')
    plot(out)
    dump(out/'audits/analysis_complete.json',{'status':'COMPLETE','protocol_sha256':sha(out/'research_plan.json'),'prediction_rows_verified':len(allp),'test_used_for_fitting':False,'model_hyperparameters_updated_after_test':False,'FNSPID_in_models':False,'2026_validation_executed':False})

def plot(out):
    os.environ.setdefault('MPLCONFIGDIR',str(out/'.matplotlib'))
    # Existing plotting package only; no environment installation/modification.
    sys.path.append(str(Path.home()/'.local/lib/python3.10/site-packages'))
    import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    m=pd.read_csv(out/'tables/metrics_comparison.csv');z=m[m.timing.eq('next_session')&m.partition.eq('test')&m.group.eq('events')]
    methods=['global','event','hier_P','hier_S','hier_T','lr_P','lr_D','lr_S','lr_T'];colors=['#748697','#748697','#6a8e9d','#51a4a3','#c6a051','#667dcc','#929db8','#278e87','#c88345']
    fig,ax=plt.subplots(1,2,figsize=(13,4.6))
    for j,metric in enumerate(('brier','log_loss')):
        a=z[z.version.eq('raw')].set_index('method').reindex(methods);b=z[z.version.eq('calibrated')].set_index('method').reindex(methods);x=np.arange(len(methods))
        ax[j].bar(x-.18,a[metric],.36,color=colors,alpha=.4,label='Raw');ax[j].bar(x+.18,b[metric],.36,color=colors,label='2024-calibrated');ax[j].set(xticks=x,xticklabels=methods,ylabel=metric,title=f'2025 tail events (n={int(b.n.iloc[0])}); lower is better');ax[j].tick_params(axis='x',rotation=45);ax[j].legend()
    fig.tight_layout();fig.savefig(out/'figures/news_gain_scores.png',dpi=180);plt.close(fig)
    rel=pd.read_csv(out/'tables/reliability_bins.csv');fig,ax=plt.subplots(1,2,figsize=(11,4.5))
    for j,version in enumerate(('raw','calibrated')):
        ax[j].plot([0,1],[0,1],ls='--',c='#aaa')
        for method,c in [('hier_P','#748697'),('lr_P','#667dcc'),('lr_S','#278e87'),('lr_T','#c88345')]:
            q=rel[rel.timing.eq('next_session')&rel.version.eq(version)&rel.group.eq('events')&rel.method.eq(method)&rel.n.gt(0)];ax[j].plot(q.mean_probability,q.reversal_rate,'o-',label=method,c=c)
            for r in q.itertuples():ax[j].annotate(str(r.n),(r.mean_probability,r.reversal_rate),fontsize=7)
        ax[j].set(xlim=(0,1),ylim=(0,1),xlabel='Mean predicted probability',ylabel='Observed reversal rate',title=version+' / fixed-width bins; numbers are sample sizes');ax[j].legend()
    fig.tight_layout();fig.savefig(out/'figures/calibration.png',dpi=180);plt.close(fig)
    r=pd.read_csv(out/'tables/within_state_ranking.csv');q=r[r.timing.eq('next_session')&r.version.eq('calibrated')&r.block_length.eq(20)&r.contrast.eq('AUC_vs_half')].set_index('method').reindex(methods)
    fig,ax=plt.subplots(figsize=(10,4.5));x=np.arange(len(q));ax.axhline(.5,c='#aaa',ls='--');ax.scatter(x,q.estimate,c=colors)
    # Basic bootstrap intervals can extend outside the parameter space.
    ax.vlines(x,q.ci_low,q.ci_high,color=colors);ax.set(xticks=x,xticklabels=methods,ylabel='Pair-weighted within-state AUC',title='Same direction / long-trend / VIX cells; 20-session block 95% intervals');ax.tick_params(axis='x',rotation=40);fig.tight_layout();fig.savefig(out/'figures/within_state_ranking.png',dpi=180);plt.close(fig)
    t=pd.read_csv(out/'tables/paired_tests.csv');q=t[t.version.eq('calibrated')&t.block_length.eq(20)&t.group.eq('events')&t.metric.eq('Brier')&t.family.eq('primary_LR_news2')]
    fig,ax=plt.subplots(figsize=(9,4.5))
    for j,candidate in enumerate(('lr_S','lr_T')):
        v=q[q.candidate.eq(candidate)].set_index('timing').reindex(TIMINGS);x=np.arange(3)+(j-.5)*.12;ax.scatter(x,v.difference,label=candidate,c=('#278e87','#c88345')[j]);ax.vlines(x,v.bootstrap_ci_low,v.bootstrap_ci_high,color=('#278e87','#c88345')[j])
    ax.axhline(0,c='#999',ls='--');ax.set(xticks=np.arange(3),xticklabels=TIMINGS,ylabel='Paired Brier gain (positive = improvement)',title='Frozen timing sensitivity; 20-session block 95% intervals');ax.legend();fig.tight_layout();fig.savefig(out/'figures/timing_sensitivity.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.5));gg=['surge','crash','conflict','aligned','event_VIX_high','event_VIX_low']
    for j,method in enumerate(('hier_P','lr_P','lr_S','lr_T')):
        q=m[m.timing.eq('next_session')&m.partition.eq('test')&m.version.eq('calibrated')&m.method.eq(method)].set_index('group').reindex(gg);ax.bar(np.arange(len(gg))+(j-1.5)*.19,q.brier,.19,label=method)
    ax.set(xticks=np.arange(len(gg)),xticklabels=gg,ylabel='Brier score',title='2025 subgroups, descriptive; shared and overlapping events');ax.tick_params(axis='x',rotation=20);ax.legend(ncol=4);fig.tight_layout();fig.savefig(out/'figures/event_regimes.png',dpi=180);plt.close(fig)
    b=pd.read_csv(out/'tables/validation_fixed_score_bins_amplitude.csv');fig,ax=plt.subplots(figsize=(9,4.5))
    for method,c in [('lr_P','#667dcc'),('lr_S','#278e87'),('lr_T','#c88345')]:
        q=b[b.timing.eq('next_session')&b.method.eq(method)];ax.plot(q.score_quartile,q.mean_signed_amplitude_pp,'o-',label=method,c=c)
        for row in q.itertuples():ax.annotate(f'n={row.n}',(row.score_quartile,row.mean_signed_amplitude_pp),fontsize=8)
    ax.axhline(0,ls='--',c='#aaa');ax.set(xticks=[1,2,3,4],xlabel='Score quartile (cutoffs frozen on 2024 events)',ylabel='Signed reversal amplitude (log percentage points)',title='Probability is not a magnitude model; empty/small bins retained');ax.legend();fig.tight_layout();fig.savefig(out/'figures/reversal_amplitude.png',dpi=180);plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT);a=p.parse_args();analyze(a.out.resolve())
