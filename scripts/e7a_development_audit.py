"""E7a training-period-only design/power inputs. No new model fitting.

Only pre2023 market prefixes and existing config0 CV probabilities enter power.
Previously viewed test results are reviewed elsewhere, never used as power
effect estimates or as a new combination selection criterion.
"""
import csv,hashlib,io,json,os,sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm,t

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('E7A_OUTPUT',ROOT/'outputs/e7a_20261106')).resolve()
MODELS=('logistic','xgboost')
FOLDS=[(2016,'2017-01-01','2018-12-31'),(2018,'2019-01-01','2020-12-31'),(2020,'2021-01-01','2022-12-31')]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,a):Path(p).write_text(json.dumps(a,ensure_ascii=False,indent=2,default=str)+'\n')

def prepare():
    if (OUT/'design_audit_lock.json').exists():raise FileExistsError('Use a new E7A_OUTPUT; preserve completed design audit')
    for d in ['inputs','tables','audits','code','figures','logs','development/inputs']:(OUT/d).mkdir(parents=True,exist_ok=True)
    plan={'version':'E7a-design-audit-v1','primary_scope':'H1/H3, H2 deferred','no_new_model_fits':True,'power_market_prefix_max':'2022-12-31','CV_evaluation_years':'2017-2022 only','config':'index0, seed42 only; not chosen by current performance','mixture_weight':.5,'comparisons':['total_vs_P','matched_shrink_increment','F_vs_training_prior'],'effect_sizes_fixed_before_calculation':[.0005,.001,.0025,.005],'future_primary_comparisons':6,'alpha_FWER':.05,'target_power':.8,'planning_stocks':[20,50,100,200,400],'planning_quarters':[4,8,12,20,40],'variance_status':'two-stock development scenario input, not a representative cross-industry variance estimate','future_correlation_assumptions_not_fitted_to_two_stocks':True,'no2024_2025_new_search':True,'no2026_execution':True}
    dump(OUT/'design_audit_lock.json',plan)
    protected={}
    # Artifact hashes preserve all completed stages without reading raw news or
    # any 2026 market dataset. Protect tables/reports/locks/plans, not huge ZIPs.
    stages=['mamba_multiseed_20261020','e3a_20261021','e3b_20261026','e3c_20261026_v1_1','e4a_20261026_phase7a','e4b_20261026','e4c_20261026','e5_20261102','e6_20261106']
    for stage in stages:
        folder=ROOT/'outputs'/stage
        for p in folder.rglob('*'):
            if not p.is_file():continue
            rel=p.relative_to(folder)
            if p.suffix=='.md' or ('tables' in rel.parts and p.suffix=='.csv') or p.name in ['evaluation_plan.json','research_plan.json','plan_locked.json','selection_locked.json','archive_manifest.json','protocol_lock.json','E3C_2026_PROTOCOL.json']:
                protected[str(p.relative_to(ROOT))]=sha(p)
    for p in (ROOT/'outputs').rglob('protocol_lock.json'):
        if 'e7a_' in str(p):continue
        lock=json.loads(p.read_text())
        for n,h in lock.get('files',{}).items():
            f=p.parent/n
            if not f.is_file() or sha(f)!=h:raise RuntimeError('Original protocol changed '+str(f))
            protected[str(f.relative_to(ROOT))]=h
        protected[str(p.relative_to(ROOT))]=sha(p)
    for name in ['E3C_2026_PROTOCOL.md','E6_CURRENT_RUN.json','E5_CURRENT_RUN.json']:
        protected[name]=sha(ROOT/name)
    dump(OUT/'audits/protected_prior_artifacts.json',protected)
    print('DESIGN AUDIT LOCKED; protected',len(protected),'artifacts',flush=True)

def training_inputs():
    manifest=[]
    for ticker in ['AAPL','TSLA','QQQ','VIX','VXN']:
        p=ROOT/'outputs/e5_20261102/inputs'/f'{ticker}_adjusted_through2025.csv'
        dest=OUT/'development/inputs'/p.name
        with p.open(newline='') as f,dest.open('w',newline='') as w:
            rd=csv.reader(f);wr=csv.writer(w,lineterminator='\n');header=next(rd);wr.writerow(header);n=0;last=None
            for row in rd:
                date=row[0][:10]
                if date>'2022-12-31':break
                wr.writerow(row);n+=1;last=date
        manifest.append({'source':str(p.relative_to(ROOT)),'used_file':str(dest.relative_to(OUT)),'used_sha256':sha(dest),'rows':n,'max_date':last,'role':'power_input_training_prefix_only','compatibility_filename':'through2025 suffix retained for old loader; actual rows stop2022'})
    pd.DataFrame(manifest).to_csv(OUT/'audits/power_input_manifest.csv',index=False)

def development_statistics():
    import e3b_protocol as bp
    training_inputs();quarter=[];daily=[];inputs=[]
    for ticker in ['AAPL','TSLA']:
        f=bp.load_frame(ticker,source=OUT/'development')
        assert f.index.max()<=pd.Timestamp('2022-12-31')
        for model in MODELS:
            for year,start,end in FOLDS:
                pp=ROOT/'outputs/e5_20261102/cv'/ticker/'T'/model/f'c0_fold{year}'/'raw_predictions.npz'
                fp=ROOT/'outputs/e6_20261106/cv'/ticker/'F/logistic'/f'c0_fold{year}'/'raw_predictions.npz'
                for p in [pp,fp]:inputs.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'role':'existing_config0_development_CV_no_test_predictions'})
                with np.load(pp) as z:p=z['eval'].astype(float)
                with np.load(fp) as z:fund=z['eval'].astype(float)
                ix=bp.indices(f,start,end);fit=bp.indices(f,'2012-01-01',f'{year}-06-30');y=f.y5.iloc[ix].to_numpy();prior=(f.y5.iloc[fit].sum()+1)/(len(fit)+2)
                if len(ix)!=len(p) or len(p)!=len(fund):raise RuntimeError('Development CV alignment mismatch')
                mix=.5*p+.5*fund;control=.5*p+.5*prior
                d={'total_vs_P':(p-y)**2-(mix-y)**2,'matched_shrink_increment':(control-y)**2-(mix-y)**2,'F_vs_training_prior':(prior-y)**2-(fund-y)**2}
                for comparison,values in d.items():
                    frame=pd.DataFrame({'date':f.index[ix],'difference':values});frame['quarter']=frame.date.dt.to_period('Q').astype(str)
                    for q,g in frame.groupby('quarter'):quarter.append({'ticker':ticker,'price_model':model,'comparison':comparison,'fold_fit_year':year,'quarter':q,'n_dates':len(g),'loss_difference_mean':float(g.difference.mean()),'within_quarter_sd':float(g.difference.std()),'mean_not_an_unseen_test_effect':True})
                    centered=values-values.mean();n=len(values)
                    for lag in [0,5,20,60]:
                        lrv=np.mean(centered**2)
                        for j in range(1,min(lag,n-1)+1):lrv+=2*(1-j/(lag+1))*float(centered[j:]@centered[:-j])/n
                        daily.append({'ticker':ticker,'price_model':model,'comparison':comparison,'fold_fit_year':year,'lag':lag,'n_dates':n,'daily_sd':float(np.std(values,ddof=1)),'LRV':max(lrv,0),'HAC_se_mean':float(np.sqrt(max(lrv,0)/n)),'implied_design_effect':max(lrv,0)/float(np.var(values))})
    q=pd.DataFrame(quarter);q.to_csv(OUT/'tables/development_quarter_statistics.csv',index=False)
    pd.DataFrame(daily).to_csv(OUT/'tables/development_daily_dependence.csv',index=False)
    dump(OUT/'audits/development_prediction_inputs.json',inputs)
    rows=[]
    for (ticker,model,comparison),g in q.groupby(['ticker','price_model','comparison']):
        g=g.sort_values('quarter');v=g.loss_difference_mean.to_numpy();x=v-v.mean();n=len(x)
        for lag in [0,1,2,4]:
            lrv=x@x/n
            for j in range(1,min(lag,n-1)+1):lrv+=2*(1-j/(lag+1))*(x[j:]@x[:-j])/n
            se=np.sqrt(max(lrv,0)/n);critical=t.ppf(1-.05/(2*5),max(n-1,1))
            rows.append({'ticker':ticker,'price_model':model,'comparison':comparison,'quarter_lag':lag,'quarters':n,'daily_rows':int(g.n_dates.sum()),'quarter_sd':float(v.std(ddof=1)),'quarter_LRV':float(max(lrv,0)),'SE_quarter_mean':float(se),'MDE_single80_Bonf5':float((critical+norm.ppf(.8))*se),'MDE_H3_conjunction80_unionbound':float((critical+norm.ppf(1-.2/3))*se),'development_mean_ignored_for_power':float(v.mean())})
    summary=pd.DataFrame(rows);summary.to_csv(OUT/'tables/development_variance_summary.csv',index=False)
    # Cross-stock correlation is diagnostic, not extrapolated as a measured
    # 200-stock/industry correlation parameter from two handpicked issuers.
    pairs=[]
    for (model,comparison),g in q.groupby(['price_model','comparison']):
        pivot=g.pivot(index='quarter',columns='ticker',values='loss_difference_mean').dropna()
        pairs.append({'price_model':model,'comparison':comparison,'paired_quarters':len(pivot),'two_stock_quarter_correlation':float(pivot.AAPL.corr(pivot.TSLA)),'not_a_population_ICC_estimate':True})
    pd.DataFrame(pairs).to_csv(OUT/'tables/two_stock_correlation_diagnostic.csv',index=False)
    print('TRAINING PREFIX AUDIT',len(q),'quarter rows',flush=True)

def ar_mean_factor(q,phi):
    return (q+2*sum((q-j)*phi**j for j in range(1,q)))/q**2

def panel_mean_variance(sigma,j,q,rho_market,rho_issuer,phi):
    if rho_market+rho_issuer>=1:raise ValueError('Variance fractions sum >=1')
    g=ar_mean_factor(q,phi)
    return sigma**2*(rho_market*g+rho_issuer/j+(1-rho_market-rho_issuer)*g/j)

def power_analysis(family=6):
    d=pd.read_csv(OUT/'tables/development_variance_summary.csv')
    # For each control contrast, pool no mean effects: use the MAX individual
    # stock/model quarter SD as a conservative scale within this narrow pilot.
    scale=float(d[d.comparison=='matched_shrink_increment'].quarter_sd.max())
    scenarios=[('independent',0.,0.,0.),('mild',.01,0.,.3),('moderate',.05,.10,.3),('strong',.15,.15,.6),('stress',.30,.20,.6)]
    rows=[]
    for ratio in [.5,1.,2.]:
        sigma=scale*ratio
        for name,rm,ri,phi in scenarios:
            for j in [20,50,100,200,400]:
                for q in [4,8,12,20,40]:
                    var=panel_mean_variance(sigma,j,q,rm,ri,phi);se=np.sqrt(var);df=q-1;crit=t.ppf(1-.05/(2*family),df)
                    rows.append({'scenario':name,'sigma_scale_factor':ratio,'sigma_quarter':sigma,'stocks':j,'quarters':q,'years':q/4,'rho_shared_market':rm,'rho_persistent_issuer':ri,'AR1_phi':phi,'raw_issuer_quarters':j*q,'variance_of_panel_mean':var,'SE':se,'effective_independent_units_scenario':sigma**2/var,'primary_family_n':family,'Bonferroni_t_critical':crit,'MDE_single80':(crit+norm.ppf(.8))*se,'MDE_H1_joint80_unionbound':(crit+norm.ppf(1-.2/3))*se,'MDE_H3_joint80_unionbound':(crit+norm.ppf(1-.2/3))*se,'assumption_not_measured_population':True})
    grid=pd.DataFrame(rows);grid.to_csv(OUT/'tables/power_design_grid.csv',index=False)
    required=[]
    for name,rm,ri,phi in scenarios:
        for effect in [.0005,.001,.0025,.005]:
            minimum=None
            for q in range(4,201):
                se=np.sqrt(panel_mean_variance(scale,200,q,rm,ri,phi));crit=t.ppf(1-.05/(2*family),q-1)
                if (crit+norm.ppf(1-.2/3))*se<=effect:minimum=q;break
            required.append({'scenario':name,'stocks':200,'effect_Brier':effect,'minimum_quarters_up_to200':minimum,'minimum_years':minimum/4 if minimum else None,'status':'scenario_threshold_met' if minimum else 'not_met_within50years','no_claim_of_guaranteed_real_power':True})
    pd.DataFrame(required).to_csv(OUT/'tables/required_period_scenarios.csv',index=False)
    # Gaussian panel-mean simulation with known scenario variance. This checks
    # planning arithmetic under its assumed DGP, NOT real bootstrap coverage.
    sim=[];rng=np.random.default_rng(20261107);reps=20000
    for name in ['independent','moderate','strong']:
        a=grid[(grid.scenario==name)&(grid.sigma_scale_factor==1)&(grid.stocks==200)&(grid.quarters==12)].iloc[0];se=a.SE
        for effect in [0.,.0005,.001,.0025,.005]:
            for corr in [0.,.5,.9]:
                common=rng.normal(size=(reps,1));errors=np.sqrt(corr)*common+np.sqrt(1-corr)*rng.normal(size=(reps,family));means=effect+se*errors
                p=2*t.sf(np.abs(means/se),11);order=np.argsort(p,axis=1);sortedp=np.take_along_axis(p,order,axis=1);adj=np.minimum(1,np.maximum.accumulate(sortedp*np.arange(family,0,-1),axis=1));corrected=np.empty_like(adj);np.put_along_axis(corrected,order,adj,axis=1)
                rejected=(corrected<.05)&(means>0);joint=rejected[:,-3:].all(axis=1);rate=float(joint.mean())
                sim.append({'scenario':name,'stocks':200,'quarters':12,'effect_all_primary_contrasts':effect,'primary_family_n':family,'cross_contrast_error_correlation':corr,'replicates':reps,'H3_joint_power_or_null_rejection':rate,'MC_se':np.sqrt(rate*(1-rate)/reps),'known_variance_Gaussian_planning_only':True})
    pd.DataFrame(sim).to_csv(OUT/'tables/power_simulation.csv',index=False)
    dump(OUT/'audits/power_scale.json',{'quarter_SD_reference':scale,'definition':'maximum pre2023 fixedconfig0 raw matched-shrink contrast quarter SD across two stocks/two price models','no_observed_test_effect_used':True,'population_correlation_unknown':True,'small_Q_and_two_issuers_limit_inference':True})
    print('POWER COMPLETE; quarter SD',scale,flush=True)

def controls():
    rng=np.random.default_rng(20261106);n=200000;x=rng.choice([-1.,1.],n);z=rng.choice([-1.,1.],n);rows=[]
    for case in ['shrink_only_no_new_information','duplicated_price_information','genuine_extra_information']:
        true=.5+.15*x+(.1*z if case=='genuine_extra_information' else 0)
        p=.5+(.30*x if case=='shrink_only_no_new_information' else .15*x)
        f=np.full(n,.5) if case=='shrink_only_no_new_information' else (p.copy() if case=='duplicated_price_information' else .5+.15*x+.20*z)
        y=rng.binomial(1,true);alpha=.5;q=(1-alpha)*p+alpha*f;q0=(1-alpha)*p+alpha*.5
        exact=(q0-y)**2-(q-y)**2;decomp=2*alpha*(f-.5)*(y-q0)-alpha**2*(f-.5)**2
        np.testing.assert_allclose(exact,decomp,atol=3e-16)
        for name,pp in [('P',p),('F',f),('Late',q),('matched_constant_shrink',q0),('oracle_probability',true)]:rows.append({'case':case,'forecast':name,'n_synthetic':n,'Brier':float(np.mean((pp-y)**2)),'forecast_contains_new_information':case=='genuine_extra_information','real_market_data':False})
    pd.DataFrame(rows).to_csv(OUT/'tables/synthetic_method_controls.csv',index=False)
    dump(OUT/'audits/control_identity_tests.json',{'quadratic_loss_identity':'PASSED','synthetic_seed':20261106,'real_model_fits':0,'warning':'Beating a matched constant blend alone does not prove new information: duplicated P can beat an unnecessarily shrunk P. Also require best-single and tuned-shrink controls.'})

def plot():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'figure.dpi':140,'axes.spines.top':False,'axes.spines.right':False})
    grid=pd.read_csv(OUT/'tables/power_design_grid.csv');q=grid[(grid.sigma_scale_factor==1)&(grid.quarters==12)]
    fig,ax=plt.subplots(figsize=(8,5))
    for scenario,g in q.groupby('scenario'):ax.plot(g.stocks,g.MDE_H3_joint80_unionbound,'o-',label=scenario)
    ax.axhline(.001,ls='--',c='black',label='Target gain .001');ax.set(xlabel='Stocks (12 future quarters)',ylabel='Brier MDE for H3 conjunction; scenario, not guarantee');ax.legend();fig.tight_layout();fig.savefig(OUT/'figures/power_vs_stocks.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5))
    for scenario,g in grid[(grid.sigma_scale_factor==1)&(grid.stocks==200)].groupby('scenario'):ax.plot(g.years,g.MDE_H3_joint80_unionbound,'o-',label=scenario)
    ax.axhline(.001,ls='--',c='black');ax.set(xlabel='Future years (200 stocks)',ylabel='Brier MDE; quarter dependence and multiplicity included');ax.legend();fig.tight_layout();fig.savefig(OUT/'figures/power_vs_years.png');plt.close(fig)
    c=pd.read_csv(OUT/'tables/synthetic_method_controls.csv');fig,axs=plt.subplots(1,3,figsize=(12,4))
    for ax,(case,g) in zip(axs,c.groupby('case',sort=False)):
        ax.bar(range(len(g)),g.Brier,color=['#576e89','#a8a8a8','#1e8a89','#d49b51','#b07aa1']);ax.set_xticks(range(len(g)),g.forecast,rotation=70,fontsize=8);ax.set_ylim(0,.29);ax.set_title(case.replace('_','\n'),fontsize=9)
    fig.tight_layout();fig.savefig(OUT/'figures/method_control_counterexamples.png');plt.close(fig)

def verify():
    for rel,h in json.loads((OUT/'audits/protected_prior_artifacts.json').read_text()).items():
        if sha(ROOT/rel)!=h:raise RuntimeError('Prior artifact changed '+rel)

if __name__=='__main__':
    prepare();development_statistics();power_analysis();controls();verify()
    if '--plots' in sys.argv:plot()
