"""Explicit recovery after RESOURCE_STOP; frozen trainer/statistics remain unchanged.

Default is CPU-only planning. Execution needs --execute-plan PATH on the host.
Completed runs are reused. One interrupted run is archived, then restarted with
the identical seed/configuration because the original checkpoint lacks RNG state.
"""
import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

from multiseed_common import (ROOT,OUT,MARKET,TASKS,OLD,case_root,leaf,
                              check_protected,sha256,write_json)
from mamba_resource_guard import gpu_snapshot


def policy_trainer(policy):
    original=ROOT/'scripts/run_mamba_e1_e2b.py'
    if policy=='original':return original
    if policy not in ('headroom','own-safety'):raise ValueError('Unknown resource policy')
    suffix='headroom' if policy=='headroom' else 'own_safety'
    modified=ROOT/f'scripts/run_mamba_e1_e2b_{suffix}.py'
    text=original.read_text()
    old='from mamba_resource_guard import ResourceGuard'
    new=f'from mamba_resource_guard_{suffix} import ResourceGuard'
    if text.count(old)!=1 or modified.read_text()!=text.replace(old,new):
        raise RuntimeError('Alternate runner must differ ONLY by resource guard import')
    return modified


def admission_reason(snapshot,policy):
    if policy=='own-safety':
        from mamba_resource_guard_own_safety import admission_reason as own_reason
        return own_reason(snapshot)
    if snapshot['free_mib']<4096 or snapshot['utilization_pct']>=90:
        return 'GPU admission refused: require 4096 MiB free and utilization<90%'
    return None


def tree_hashes(folder):
    return {str(p.relative_to(folder)):sha256(p) for p in folder.rglob('*') if p.is_file()}


def pending_tasks(status):
    names=[f'seed{s}_{t}_{a}' for s,t,a in TASKS]
    done=status['completed']
    if status['status']!='STOPPED' or done!=names[:len(done)] or len(done)>=len(names):
        raise ValueError('Need a stopped suite with an exact completed prefix')
    if status['current']!=names[len(done)]:raise ValueError('Failed case does not match queue')
    return TASKS[len(done):]


def validate_case(seed,ticker,arm):
    import numpy as np
    import pandas as pd
    folder=leaf(seed,ticker,arm)
    for name in ('predictions.csv','metrics.csv','training_history.csv','best_state.pt',
                 'checkpoint_latest.pt','training.json','environment.json','config.json','training.log'):
        if not (folder/name).is_file() or not (folder/name).stat().st_size:
            raise RuntimeError('Missing completed artifact: '+str(folder/name))
    config=json.loads((folder/'config.json').read_text())
    reference=json.loads((leaf(42,ticker,arm)/'config.json').read_text())
    if {k:v for k,v in config.items() if k not in ('out','seed')}!={k:v for k,v in reference.items() if k not in ('out','seed')}:
        raise RuntimeError('Configuration differs from seed42')
    if config['seed']!=seed:raise RuntimeError('Seed mismatch')
    pred=pd.read_csv(folder/'predictions.csv');states=pd.read_csv(OUT/f'{ticker}_frozen_states.csv')
    if pred.date.tolist()!=states.date.tolist() or set(pred['split'])!={'test'} or not pred.date.is_unique:
        raise RuntimeError('Frozen test calendar mismatch')
    if pred.label_date.tolist()!=pd.to_datetime(states.LabelDate).dt.strftime('%Y-%m-%d').tolist():
        raise RuntimeError('Frozen label calendar mismatch')
    np.testing.assert_allclose(pred.actual_mag_pct,states.TargetMagnitudePct,rtol=1e-12,atol=1e-12)
    metric=pd.read_csv(folder/'metrics.csv')
    hist=pd.read_csv(folder/'training_history.csv')
    if not 1<=len(hist)<=30 or not (hist.train_batches==346).all():raise RuntimeError('Incomplete epochs')
    for arr in (pred[['actual_mag_pct','forecast_mag_pct']].to_numpy(),
                metric[['mae_pp','rmse_pp']].to_numpy(),hist.select_dtypes(include='number').to_numpy()):
        if not np.isfinite(arr).all():raise RuntimeError('Nonfinite completed artifacts')
    if int(hist.cuda_reserved_bytes.max())>24564*1024**2*.10:raise RuntimeError('Allocator exceeded limit')


def make_plan(policy='own-safety'):
    check_protected()
    status_path=OUT/'suite_status.json';status=json.loads(status_path.read_text())
    todo=pending_tasks(status)
    for task in TASKS[:len(status['completed'])]:validate_case(*task)
    first=case_root(*todo[0]);failed_leaf=leaf(*todo[0])
    failure=json.loads((failed_leaf/'failure.json').read_text())
    if 'RESOURCE_STOP:' not in json.dumps(failure):raise RuntimeError('Only explicit resource-stop recovery is supported')
    if (failed_leaf/'predictions.csv').exists():raise RuntimeError('Refusing to restart a case with test predictions')
    for task in todo[1:]:
        if case_root(*task).exists():raise RuntimeError('Unexpected future case exists')
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    recovery=OUT/'recovery'/stamp
    recovery.mkdir(parents=True,exist_ok=False)
    trainer=policy_trainer(policy)
    infrastructure=[trainer,Path(__file__),ROOT/'scripts/start_mamba_recovery.sh',ROOT/'scripts/launch_mamba_recovery.py']
    if policy=='headroom':infrastructure.append(ROOT/'scripts/mamba_resource_guard_headroom.py')
    if policy=='own-safety':
        infrastructure.extend([ROOT/'scripts/mamba_resource_guard_own_safety.py',ROOT/'GPU_RESOURCE_POLICY.md',ROOT/'AGENTS.md'])
    prior_archives={}
    for previous in (OUT/'recovery').glob('*/plan.json'):
        old=json.loads(previous.read_text());saved=ROOT/old['archive_case']
        if saved.exists():
            if tree_hashes(saved)!=old['failed_files']:raise RuntimeError('Previous interrupted archive changed')
            prior_archives[old['archive_case']]=old['failed_files']
    plan={'status_sha256':sha256(status_path),'script_sha256':sha256(Path(__file__)),
          'resource_policy':policy,'trainer':str(trainer.relative_to(ROOT)),
          'infrastructure_sha256':{str(p.relative_to(ROOT)):sha256(p) for p in infrastructure},
          'prior_archives':prior_archives,
          'completed':status['completed'],'pending':[list(x) for x in todo],
          'failed_case':str(first.relative_to(ROOT)),
          'archive_case':str((recovery/'interrupted_case').relative_to(ROOT)),
          'failed_files':tree_hashes(first),
          'completed_files':{str(case_root(*task).relative_to(ROOT)):tree_hashes(case_root(*task))
                             for task in TASKS[:len(status['completed'])]},
          'reason':failure,'recovery_dir':str(recovery.relative_to(ROOT)),
          'strategy':'Restart only interrupted run from identical seed; no RNG state was stored. Preserve every original partial artifact. Reuse all complete runs.',
          'resource_strategy':('UNCHANGED: 10% allocator, 25% pacing, batch8, original admission/stop rules; 3 stable host GPU samples before recovery' if policy=='original' else
                               'USER-SELECTED own_safety_v1: same batch8/10% allocator/25% pacing/lock; trainer admission free>=2048MiB; no runtime preemption for external allocations, utilization or free-memory levels; actual CUDA/OOM/device-query errors stop own run and queue; no automatic retry' if policy=='own-safety' else
                               'OPT-IN headroom_v1: same batch8/10% allocator/25% pacing/lock; stop free<4096MiB or utilization>=90% for 30s; no stop solely on external allocation growth; no automatic retry'),
          'frozen_training_statistics_unchanged':True}
    write_json(recovery/'plan.json',plan)
    (recovery/'resume_source.py').write_bytes(Path(__file__).read_bytes())
    if policy=='own-safety':
        (recovery/'GPU_RESOURCE_POLICY.md').write_bytes((ROOT/'GPU_RESOURCE_POLICY.md').read_bytes())
        (recovery/'project_instructions.md').write_bytes((ROOT/'AGENTS.md').read_bytes())
    print('CPU-only plan:',recovery/'plan.json',flush=True)
    print('Complete cases reused:',len(plan['completed']),'remaining:',len(todo),flush=True)
    print(plan['strategy'],flush=True)
    return recovery/'plan.json'


def execute(plan_path):
    check_protected()
    plan_path=plan_path.resolve()
    if not plan_path.is_relative_to(OUT/'recovery'):raise ValueError('Plan must reside within project recovery directory')
    plan=json.loads(plan_path.read_text());status_path=OUT/'suite_status.json'
    if sha256(Path(__file__))!=plan['script_sha256'] or sha256(status_path)!=plan['status_sha256']:
        raise RuntimeError('Recovery plan is stale; no changes made')
    status=json.loads(status_path.read_text());todo=pending_tasks(status)
    if [list(x) for x in todo]!=plan['pending']:raise RuntimeError('Queue changed')
    recovery=ROOT/plan['recovery_dir']
    first=ROOT/plan['failed_case'];archive=ROOT/plan['archive_case']
    trainer=policy_trainer(plan.get('resource_policy','original'))
    policy=plan.get('resource_policy','original')
    def protected_completed():
        check_protected()
        for name,h in plan.get('infrastructure_sha256',{}).items():
            if sha256(ROOT/name)!=h:raise RuntimeError('Approved recovery infrastructure changed: '+name)
        for name,h in plan.get('prior_archives',{}).items():
            if tree_hashes(ROOT/name)!=h:raise RuntimeError('Previous interrupted archive changed: '+name)
        for name,expected in plan['completed_files'].items():
            if tree_hashes(ROOT/name)!=expected:raise RuntimeError('Previously completed case changed: '+name)
    protected_completed()
    if tree_hashes(first)!=plan['failed_files'] or archive.exists():raise RuntimeError('Interrupted case changed or archive exists')
    samples=[]
    for i in range(3):
        s=gpu_snapshot();samples.append(s)
        write_json(recovery/'gpu_admission_samples.json',samples)
        reason=admission_reason(s,policy)
        if reason:raise RuntimeError(reason+'; original files unchanged')
        if i<2:time.sleep(5)
    external=[sum(s['processes_mib'].values()) for s in samples]
    if policy=='original' and max(external)-min(external)>1024:
        raise RuntimeError('GPU workloads are still growing; original files unchanged')
    (recovery/'original_suite_status.json').write_bytes(status_path.read_bytes())
    first.rename(archive)
    if tree_hashes(archive)!=plan['failed_files']:raise RuntimeError('Interrupted archive integrity failure')
    status.update(status='RECOVERING',pid=os.getpid(),recovery_plan=str(plan_path.relative_to(ROOT)),
                  recovery_started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  interrupted_run_restart=True)
    status['resource_policy']=policy
    status.pop('traceback',None)
    write_json(status_path,status)
    try:
        for seed,ticker,arm in todo:
            protected_completed()
            name=f'seed{seed}_{ticker}_{arm}';before=gpu_snapshot()
            write_json(recovery/f'{name}_gpu_before.json',before)
            reason=admission_reason(before,policy)
            if reason:raise RuntimeError(reason+'; stopping recovery')
            with (recovery/f'{name}_nvidia_before.txt').open('w') as f:
                subprocess.run(['nvidia-smi'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=20)
            cmd=[sys.executable,'-B','-u',str(trainer),
                 '--tickers',ticker,'--arms',arm,'--seed',str(seed),'--batch-size','8','--eval-batch-size','8',
                 '--memory-fraction','0.10','--gpu-duty-cycle','0.25','--market-dir',str(MARKET),
                 '--csv-price-policy','adjusted','--out',str(case_root(seed,ticker,arm)),'--execute-training']
            status.update(status='TRAINING',current=name,command=cmd)
            write_json(status_path,status)
            print('Starting',name,flush=True)
            with (recovery/f'{name}_stdout.log').open('w') as f:
                child=subprocess.Popen(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
                status['child_pid']=child.pid;write_json(status_path,status)
                code=child.wait()
            status.pop('child_pid',None)
            if code:raise RuntimeError(f'{name} exited {code}; recovery stops without retry; see {recovery}')
            validate_case(seed,ticker,arm);protected_completed()
            status['completed'].append(name)
            write_json(status_path,status)
            print('Completed',name,flush=True)
        status.update(status='ANALYZING',current=None);write_json(status_path,status)
        cpu_env={**os.environ,'CUDA_VISIBLE_DEVICES':''}
        with (recovery/'analysis.log').open('w') as f:
            subprocess.run([sys.executable,'-B','-u',str(ROOT/'scripts/analyze_mamba_multiseed.py')],cwd=ROOT,env=cpu_env,stdout=f,stderr=subprocess.STDOUT,check=True)
        with (OUT/'MULTISEED_SUMMARY.md').open('a') as f:f.write(recovery_note())
        protected_completed()
        if tree_hashes(archive)!=plan['failed_files']:raise RuntimeError('Interrupted archive changed')
        with (recovery/'package.log').open('w') as f:
            subprocess.run([sys.executable,'-B','-u',str(ROOT/'scripts/analyze_mamba_multiseed.py'),'--package-only'],cwd=ROOT,env=cpu_env,stdout=f,stderr=subprocess.STDOUT,check=True)
        protected_completed()
        status.update(status='COMPLETE',finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                      archive=str(OUT/'mamba_multiseed_complete.zip'),
                      archive_sha256=(OUT/'archive_sha256.txt').read_text().split()[0])
        write_json(status_path,status)
        print('COMPLETE',flush=True)
    except BaseException:
        status.update(status='STOPPED',traceback=traceback.format_exc())
        write_json(status_path,status)
        print(status['traceback'],file=sys.stderr,flush=True)
        raise


def recovery_note():
    import pandas as pd
    lines=['','## 資源中斷與恢復紀錄','',
           '未保存完整RNG／洗牌狀態的中斷組以相同seed／參數從頭重跑；已完成組與seed42保留，未依測試表現選擇重跑。所有中斷歷史與checkpoint均封存並核對雜湊。',
           '凍結的原訓練程式、模型、資料及統計計畫不變。替代版本與原訓練程式的差異僅為資源guard匯入；資源策略變更逐次列在下表。使用者已指定後續不因他人顯存增加或單純GPU忙碌而中斷，own_safety_v1據此取消執行中的全GPU占用代理停止條件，實際CUDA／OOM與裝置查詢錯誤仍停止本輪。','',
           '|恢復批次|中斷組|保存epoch數|該次資源策略|','|---|---|---:|---|']
    for file in sorted((OUT/'recovery').glob('*/plan.json')):
        p=json.loads(file.read_text());archive=ROOT/p['archive_case']
        if not archive.exists():continue
        if tree_hashes(archive)!=p['failed_files']:raise RuntimeError('Interrupted archive verification failed')
        case=Path(p['failed_case']);history=archive/case.name/'training_history.csv'
        epochs=len(pd.read_csv(history)) if history.exists() else 0
        lines.append(f"|{file.parent.name}|{case.parent.name}/{case.name}|{epochs}|{p['resource_strategy']}|")
    lines+=['','所有版本的10% allocator與25% pacing相同，均非整張GPU的硬體上限；資源策略只改變停止判斷，不以此保證其他工作的延遲不受影響。完整計畫、原停止狀態、基礎設施版本與日誌均隨ZIP保存。','']
    return '\n'.join(lines)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute-plan',type=Path)
    parser.add_argument('--resource-policy',choices=['original','headroom','own-safety'],default='own-safety',help='CPU-only plan selection; execution uses the saved plan; user-selected default is own-safety')
    args=parser.parse_args()
    with (ROOT/'logs/mamba-suite.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.execute_plan:execute(args.execute_plan)
        else:make_plan(args.resource_policy)
