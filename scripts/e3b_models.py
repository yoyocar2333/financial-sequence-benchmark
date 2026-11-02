"""True model fitting, early stopping and recoverable epoch checkpoints."""
import gc
import json
from pathlib import Path
import random
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss
from e3b_protocol import PLAN,write_json,sha


def brier(y,p):return float(np.mean((np.asarray(y)-np.asarray(p))**2))


def fit_cpu(model,config,seed,xtrain,ytrain,xstop,ystop,evals,folder):
    flat=lambda x:x.reshape(len(x),-1)
    history=[];start=time.monotonic()
    if model=='logistic':
        from sklearn.linear_model import LogisticRegression
        from sklearn.exceptions import ConvergenceWarning
        import warnings
        estimator=LogisticRegression(**config,solver='lbfgs',max_iter=500,random_state=seed)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always',ConvergenceWarning)
            estimator.fit(flat(xtrain),ytrain)
        write_json(folder/'warnings.json',{'messages':[str(w.message) for w in caught]})
        joblib.dump(estimator,folder/'model.joblib')
        history=[{'iteration':int(estimator.n_iter_[0]),'stop_brier':brier(ystop,estimator.predict_proba(flat(xstop))[:,1])}]
        best_iter=int(estimator.n_iter_[0])
    elif model=='xgboost':
        import xgboost as xgb
        estimator=xgb.XGBClassifier(**config,n_estimators=300,early_stopping_rounds=25,tree_method='hist',max_bin=64,
            objective='binary:logistic',eval_metric=brier,subsample=.8,colsample_bytree=.8,n_jobs=2,random_state=seed,verbosity=0)
        estimator.fit(flat(xtrain),ytrain,eval_set=[(flat(xstop),ystop)],verbose=False)
        scores=estimator.evals_result()['validation_0']['brier']
        history=[{'iteration':i+1,'stop_brier':v} for i,v in enumerate(scores)]
        best_iter=int(estimator.best_iteration)+1
        estimator.save_model(folder/'model.ubj')
    elif model=='lightgbm':
        import lightgbm as lgb
        result={}
        def metric(y,p):return 'brier',brier(y,p),False
        estimator=lgb.LGBMClassifier(**config,n_estimators=300,objective='binary',metric='None',max_bin=63,
            subsample=.8,subsample_freq=1,colsample_bytree=.8,n_jobs=2,random_state=seed,verbosity=-1,
            deterministic=True,force_col_wise=True)
        estimator.fit(flat(xtrain),ytrain,eval_set=[(flat(xstop),ystop)],eval_metric=metric,
            callbacks=[lgb.early_stopping(25,first_metric_only=True,verbose=False),lgb.record_evaluation(result)])
        scores=result['valid_0']['brier'];history=[{'iteration':i+1,'stop_brier':v} for i,v in enumerate(scores)]
        best_iter=int(estimator.best_iteration_)
        estimator.booster_.save_model(str(folder/'model.txt'))
    else:raise ValueError(model)
    pd.DataFrame(history).to_csv(folder/'training_history.csv',index=False)
    predictions={name:estimator.predict_proba(flat(x))[:,1] for name,x in evals.items()}
    info={'best_iteration':best_iter,'training_seconds':time.monotonic()-start,'train_n':len(xtrain),
          'stop_n':len(xstop),'parameter_count':int(estimator.coef_.size+1) if model=='logistic' else None}
    del estimator;gc.collect()
    return predictions,info


def neural_model(name,n_features,config):
    import torch
    from torch import nn
    width=config['width']
    class Classifier(nn.Module):
        def __init__(self):
            super().__init__();self.proj=nn.Linear(n_features,width)
            if name=='mamba':
                from mamba_ssm import Mamba
                self.encoder=Mamba(d_model=width,d_state=16,d_conv=4,expand=2)
            elif name=='lstm':self.encoder=nn.LSTM(width,width,batch_first=True,num_layers=1)
            else:raise ValueError(name)
            self.norm=nn.LayerNorm(width);self.dropout=nn.Dropout(.1);self.head=nn.Linear(width,1)
        def forward(self,x):
            x=self.proj(x);encoded=self.encoder(x)
            if name=='lstm':encoded=encoded[0]
            return self.head(self.dropout(self.norm(encoded[:,-1,:]))).squeeze(-1)
    return Classifier()


def fit_neural(name,config,seed,xtrain,ytrain,xstop,ystop,evals,folder,guard):
    import torch
    from torch.utils.data import TensorDataset,DataLoader
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
    torch.set_num_threads(2);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.backends.cuda.matmul.allow_tf32=False
    model=neural_model(name,xtrain.shape[2],config).cuda()
    optimizer=torch.optim.AdamW(model.parameters(),lr=config['lr'],weight_decay=config['weight_decay'])
    generator=torch.Generator().manual_seed(seed)
    dataset=TensorDataset(torch.from_numpy(xtrain),torch.from_numpy(ytrain.astype(np.float32)))
    loader=DataLoader(dataset,batch_size=64,shuffle=True,generator=generator,num_workers=0)
    history=[];best=float('inf');best_epoch=0;stale=0;start_epoch=0;start=time.monotonic()
    checkpoint=folder/'checkpoint_latest.pt'
    if checkpoint.exists():
        state=torch.load(checkpoint,map_location='cpu',weights_only=False)
        model.load_state_dict(state['model']);optimizer.load_state_dict(state['optimizer'])
        random.setstate(state['python_rng']);np.random.set_state(state['numpy_rng'])
        torch.set_rng_state(state['torch_rng']);torch.cuda.set_rng_state(state['cuda_rng'])
        generator.set_state(state['loader_rng']);history=state['history'];best=state['best']
        best_epoch=state['best_epoch'];stale=state['stale'];start_epoch=state['epoch']
    criterion=torch.nn.BCEWithLogitsLoss()
    def predict(x):
        model.eval();values=[]
        with torch.no_grad():
            for i in range(0,len(x),64):
                tick=time.monotonic();values.append(torch.sigmoid(model(torch.from_numpy(x[i:i+64]).cuda())).cpu().numpy())
                guard.paced_sync(tick)
        return np.concatenate(values).astype(float)
    for epoch in range(start_epoch,24):
        if stale>=4:break
        model.train();total=0.;seen=0
        for xb,yb in loader:
            tick=time.monotonic();xb=xb.cuda();yb=yb.cuda()
            optimizer.zero_grad(set_to_none=True);loss=criterion(model(xb),yb)
            if not torch.isfinite(loss):raise RuntimeError('Nonfinite classification loss')
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
            total+=float(loss.detach())*len(xb);seen+=len(xb);guard.paced_sync(tick)
        pstop=predict(xstop);score=brier(ystop,pstop)
        history.append({'epoch':epoch+1,'train_log_loss':total/seen,'stop_brier':score,
            'allocated_bytes':int(torch.cuda.memory_allocated()),'reserved_bytes':int(torch.cuda.memory_reserved()),
            'peak_allocated_bytes':int(torch.cuda.max_memory_allocated())})
        if score<best-1e-5:
            best=score;best_epoch=epoch+1;stale=0
            torch.save({k:v.detach().cpu().clone() for k,v in model.state_dict().items()},folder/'best_state.pt.tmp')
            (folder/'best_state.pt.tmp').replace(folder/'best_state.pt')
        else:stale+=1
        pd.DataFrame(history).to_csv(folder/'training_history.csv.tmp',index=False)
        (folder/'training_history.csv.tmp').replace(folder/'training_history.csv')
        state={'epoch':epoch+1,'model':model.state_dict(),'optimizer':optimizer.state_dict(),'history':history,
            'best':best,'best_epoch':best_epoch,'stale':stale,'python_rng':random.getstate(),'numpy_rng':np.random.get_state(),
            'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state(),'loader_rng':generator.get_state(),
            'seed':seed,'config':config}
        torch.save(state,folder/'checkpoint_latest.pt.tmp');(folder/'checkpoint_latest.pt.tmp').replace(checkpoint)
        write_json(folder/'progress.json',{'epoch':epoch+1,'best_epoch':best_epoch,'stop_brier':score})
    model.load_state_dict(torch.load(folder/'best_state.pt',map_location='cpu',weights_only=True))
    predictions={key:predict(x) for key,x in evals.items()}
    info={'best_iteration':best_epoch,'epochs':len(history),'training_seconds':time.monotonic()-start,
          'train_n':len(xtrain),'stop_n':len(xstop),'parameter_count':sum(p.numel() for p in model.parameters()),
          'neural_class':str(type(model.encoder)),'model_output':'reversal logit, not magnitude'}
    del model,optimizer,loader,dataset;gc.collect();torch.cuda.empty_cache()
    return predictions,info


def fit_job(model,config,seed,arrays,folder,metadata,guard=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    signature={'model':model,'config':config,'seed':seed,**metadata}
    if (folder/'config.json').exists() and json.loads((folder/'config.json').read_text())!=signature:
        raise RuntimeError('Refusing to reuse differently configured job: '+str(folder))
    complete=folder/'COMPLETE.json'
    if complete.exists():
        saved=json.loads(complete.read_text())
        for n,h in saved['files'].items():
            if sha(folder/n)!=h:raise RuntimeError('Completed fit changed: '+str(folder/n))
        data=np.load(folder/'raw_predictions.npz')
        return {key:data[key] for key in data.files},saved['info']
    write_json(folder/'config.json',signature)
    evals={k:v[0] for k,v in arrays.items() if k not in ('fit','stop')}
    if model in ('lstm','mamba'):
        if guard is None:raise RuntimeError('A real CUDA guard is mandatory')
        predictions,info=fit_neural(model,config,seed,*arrays['fit'],*arrays['stop'],evals,folder,guard)
    else:predictions,info=fit_cpu(model,config,seed,*arrays['fit'],*arrays['stop'],evals,folder)
    if not all(np.isfinite(p).all() and ((p>=0)&(p<=1)).all() for p in predictions.values()):raise RuntimeError('Invalid probabilities')
    np.savez_compressed(folder/'raw_predictions.npz',**predictions)
    write_json(folder/'fit_info.json',info)
    write_json(complete,{'info':info,'files':{p.name:sha(p) for p in folder.iterdir() if p.is_file() and p.name!='COMPLETE.json'}})
    return predictions,info
