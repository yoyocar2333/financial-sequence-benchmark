"""E9b frozen-plan helpers; supplementary results never alter earlier artifacts."""
import hashlib,json,os,datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import roc_auc_score
R=Path(os.environ.get('E9B_SOURCE_ROOT',Path(__file__).resolve().parents[1])).resolve();O=Path(os.environ.get('E9B_OUTPUT',R/'outputs/e9b_20261115')).resolve()
PLAN=json.loads((O/'ANALYSIS_PLAN_LOCKED.json').read_text()) if (O/'ANALYSIS_PLAN_LOCKED.json').exists() else None
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(v):
 if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [clean(x) for x in v]
 if isinstance(v,np.ndarray):return clean(v.tolist())
 if isinstance(v,(np.integer,)):return int(v)
 if isinstance(v,(np.floating,float)):return float(v) if np.isfinite(v) else None
 if isinstance(v,np.bool_):return bool(v)
 return v

def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(clean(v),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def save(df,path):
 path.parent.mkdir(parents=True,exist_ok=True);df.to_csv(path,index=False,lineterminator='\n',compression={'method':'gzip','mtime':0} if path.name.endswith('.gz') else None)
def start(component,files):
 lock=json.loads((O/'audits/plan_lock.json').read_text());assert sha(O/'ANALYSIS_PLAN_LOCKED.json')==lock['sha256']
 for name,h in json.loads((O/'audits/derived_development_hashes.json').read_text()).items():assert sha(O/name)==h,name
 for name in files:
  source=R/name;assert source.exists(),name
  expected=json.loads((O/'audits/analysis_input_hashes.json').read_text()).get(name)
  if expected:assert sha(source)==expected,name
 at=dt.datetime.now(dt.timezone.utc).isoformat();tag=at.replace(':','').replace('.','')
 dump(O/'audits/executions'/f'{component}_{tag}.json',dict(component=component,at=at,plan_sha256=lock['sha256'],inputs={name:sha(R/name) for name in files},code={p.name:sha(p) for p in (R/'scripts').glob('e9b_*.py')},exploratory=True))

def metrics(y,p):
 y=np.asarray(y,float);p=np.asarray(p,float);q=np.clip(p,1e-6,1-1e-6)
 return dict(n=len(y),positive=int(y.sum()),negative=int(len(y)-y.sum()),prevalence=float(y.mean()),mean_probability=float(p.mean()),sd_probability=float(p.std()),brier=float(np.mean((p-y)**2)),log_loss=float(-np.mean(y*np.log(q)+(1-y)*np.log(1-q))),AUC=float(roc_auc_score(y,p)) if len(np.unique(y))==2 else np.nan,calibration_bias=float((p-y).mean()),extreme_10_90=float(((p<.1)|(p>.9)).mean()),extreme_25_75=float(((p<.25)|(p>.75)).mean()),mean_abs_from_half=float(np.abs(p-.5).mean()),**{'q%02d'%int(v*100):float(np.quantile(p,v)) for v in [.01,.05,.5,.95,.99]})

def decomposition(y,p,bins=10):
 y=np.asarray(y,float);p=np.asarray(p,float);k=np.minimum((p*bins).astype(int),bins-1);rel=0.;res=0.;g=0.;bsbin=0.;details=[]
 for b in range(bins):
  m=k==b
  if not m.any():continue
  pp=p[m];yy=y[m];q=pp.mean();o=yy.mean();w=m.mean()
  rel+=w*(q-o)**2;res+=w*(o-y.mean())**2
  g+=w*np.mean((pp-q)**2-2*(pp-q)*(yy-o));bsbin+=w*np.mean((q-yy)**2)
  details.append(dict(bin=b,n=int(m.sum()),mean_probability=float(q),observed_rate=float(o)))
 unc=y.mean()*(1-y.mean());bs=np.mean((p-y)**2)
 assert abs(bs-(rel-res+unc+g))<1e-12
 assert abs(bsbin-(rel-res+unc))<1e-12
 return dict(bins=bins,brier=float(bs),reliability=float(rel),resolution=float(res),uncertainty=float(unc),grouping_remainder=float(g),binned_brier=float(bsbin),identity_residual=float(bs-(rel-res+unc+g))),details

def counts(n,block,reps=4999,seed=20261115):
 rng=np.random.default_rng(seed);ans=np.zeros((reps,n),np.int16);offset=np.arange(block)
 for r in range(reps):
  starts=rng.integers(0,n,size=int(np.ceil(n/block)));idx=((starts[:,None]+offset)%n).ravel()[:n];ans[r]=np.bincount(idx,minlength=n)
 return ans

def inference(d,mask,block,seed):
 """Date-paired conditional-on-stocks inference with synchronized calendar blocks.
 d: stock x full-calendar x contrast; missing eligibility is explicit in mask.
 """
 d=np.asarray(d,float);mask=np.asarray(mask,float)
 if d.ndim==2:d=d[:,:,None]
 S,T,K=d.shape;assert mask.shape==(S,T)
 per=np.sum(d*mask[:,:,None],axis=1)/mask.sum(axis=1)[:,None];mean=per.mean(axis=0)
 inf=np.mean(mask[:,:,None]/mask.mean(axis=1)[:,None,None]*(d-per[:,None,:]),axis=0)
 inf-=inf.mean(axis=0);lrv=(inf*inf).mean(axis=0)
 for lag in range(1,min(block,T-1)+1):lrv+=2*(1-lag/(block+1))*(inf[lag:]*inf[:-lag]).sum(axis=0)/T
 se=np.sqrt(np.maximum(lrv,0)/T);hac=np.where(se>0,2*norm.sf(np.abs(mean)/np.maximum(se,1e-300)),np.where(abs(mean)<1e-14,1.,0.))
 c=counts(T,block,4999,seed);boot=[];valid=np.ones(len(c),bool)
 for s in range(S):
  den=c@mask[s];valid&=den>0;boot.append((c@(d[s]*mask[s,:,None]))/np.maximum(den[:,None],1))
 b=np.stack(boot).mean(axis=0)[valid];low,high=np.quantile(b,[.025,.975],axis=0)
 p=(1+(np.abs(b-mean)>=np.abs(mean)).sum(axis=0))/(len(b)+1)
 return [dict(n_observed=int(mask.sum()),calendar_sessions=T,stocks=S,difference=float(mean[k]),hac_se=float(se[k]),hac_p=float(hac[k]),bootstrap_p=float(p[k]),bootstrap_ci_low=float(2*mean[k]-high[k]),bootstrap_ci_high=float(2*mean[k]-low[k]),bootstrap_valid_fraction=float(valid.mean())) for k in range(K)]

def holm(p):
 a=np.asarray(p,float);order=np.argsort(a);v=np.maximum.accumulate((len(a)-np.arange(len(a)))*a[order]);out=np.empty(len(a));out[order]=np.minimum(v,1);return out

def load_dev(ticker):
 import e3b_protocol as bp,e5_core as e5
 source=O/'inputs/market_development'
 # Adapt the immutable cutoff files to the legacy loader's bundle/inputs contract.
 import shutil
 bundle=O/'inputs/development_loader_bundle';(bundle/'inputs').mkdir(parents=True,exist_ok=True)
 for original in source.glob('*.csv'):
  target=bundle/'inputs'/original.name
  if not target.exists():shutil.copy2(original,target)
  assert sha(original)==sha(target)
 f=bp.load_frame(ticker,source=bundle)
 s=bp.read_pre2026(source/f'{ticker}_adjusted_through2025.csv');q=bp.read_pre2026(source/'QQQ_adjusted_through2025.csv')
 assert f.index.max()<=pd.Timestamp('2022-12-31')
 extra=e5.indicators(s,q)
 f=pd.concat([f.drop(columns=list(extra.columns),errors='ignore'),extra],axis=1)
 return f
