"""User-selected policy: retain our allocation and run through other GPU work.

No external-allocation, utilization or runtime free-memory preemption. The
unchanged trainer stops on actual CUDA/OOM failures. Its 2 GiB admission
requirement, one-training-process lock, allocator cap and pacing are retained.
"""
import atexit
import fcntl
import json
import os
from pathlib import Path
import time
from mamba_resource_guard import ResourceGuard as OriginalGuard, gpu_snapshot

POLICY={'name':'own_safety_v1','admission_min_free_mib':2048,
        'external_allocation_stop':False,'utilization_stop':False,'runtime_free_memory_stop':False,
        'cuda_or_oom_error':'stop own run and remaining queue; no automatic retry',
        'allocator_fraction':0.10,'duty_cycle':0.25,'check_seconds':5}


def admission_reason(snapshot):
    if snapshot['free_mib']<POLICY['admission_min_free_mib']:
        return 'GPU admission refused: unchanged trainer requires at least 2048 MiB free'
    return None


class ResourceGuard(OriginalGuard):
    def __init__(self,root,output,fraction=.10,duty=.25):
        self.root,self.output=Path(root),Path(output)
        self.fraction,self.duty=fraction,duty
        self.lock=(self.root/'logs/mamba-gpu-training.lock').open('a+')
        try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise RuntimeError('Another stock_prediction GPU training process holds the lock')
        atexit.register(self.close)
        self.baseline=gpu_snapshot()
        reason=admission_reason(self.baseline)
        if reason:raise RuntimeError(reason)
        self.external_baseline=sum(v for p,v in self.baseline['processes_mib'].items() if p!=os.getpid())
        self.last_check=0.
        self.log_path=self.root/'logs'/f'gpu-resource-{os.getpid()}.jsonl'
        import torch
        self.torch=torch
        torch.cuda.set_per_process_memory_fraction(fraction,device=0)
        self.check(force=True)

    def check(self,force=False):
        now=time.monotonic()
        if not force and now-self.last_check<POLICY['check_seconds']:return
        s=gpu_snapshot()
        external=sum(v for p,v in s['processes_mib'].items() if p!=os.getpid())
        s.update(pid=os.getpid(),output=str(self.output),allocator_fraction=self.fraction,
                 duty_cycle_target=self.duty,allocated_bytes=self.torch.cuda.memory_allocated(0),
                 reserved_bytes=self.torch.cuda.memory_reserved(0),resource_policy=POLICY,
                 external_memory_growth_mib=external-self.external_baseline)
        with self.log_path.open('a') as f:f.write(json.dumps(s)+'\n')
        self.last_check=now
