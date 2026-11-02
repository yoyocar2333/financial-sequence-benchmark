"""Own-process GPU admission, allocator limit, pacing, and stop conditions."""
import atexit
import csv
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time


def gpu_snapshot():
    output = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,memory.total,memory.used,memory.free,utilization.gpu',
                                      '--format=csv,noheader,nounits'], text=True, timeout=15)
    fields = next(row for row in csv.reader(output.splitlines()) if row[0].strip() == '0')
    index, uuid, total, used, free, util = [s.strip() for s in fields]
    raw = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid,used_gpu_memory',
                                   '--format=csv,noheader,nounits'], text=True, timeout=15)
    processes = {}
    for row in csv.reader(raw.splitlines()):
        if len(row) == 3 and row[0].strip() == uuid:
            processes[int(row[1].strip())] = int(row[2].strip())
    return {'time': time.time(), 'uuid': uuid, 'total_mib': int(total), 'used_mib': int(used),
            'free_mib': int(free), 'utilization_pct': int(util), 'processes_mib': processes}


class ResourceGuard:
    def __init__(self, root, output, fraction=0.10, duty=0.25):
        self.root, self.output = Path(root), Path(output)
        self.fraction, self.duty = fraction, duty
        self.lock = (self.root / 'logs/mamba-gpu-training.lock').open('a+')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise RuntimeError('Another stock_prediction GPU training process holds the lock')
        atexit.register(self.close)
        self.baseline = gpu_snapshot()
        if self.baseline['free_mib'] < 4096 or self.baseline['utilization_pct'] >= 90:
            raise RuntimeError('GPU admission refused: require >=4096 MiB free and utilization <90%')
        self.external_baseline = sum(v for p, v in self.baseline['processes_mib'].items() if p != os.getpid())
        self.last_check, self.high_util_since = 0.0, None
        self.log_path = self.root / 'logs' / f'gpu-resource-{os.getpid()}.jsonl'
        import torch
        torch.cuda.set_per_process_memory_fraction(fraction, device=0)
        self.torch = torch
        self.check(force=True)

    def check(self, force=False):
        now = time.monotonic()
        if not force and now - self.last_check < 5:
            return
        s = gpu_snapshot()
        s.update(pid=os.getpid(), output=str(self.output), allocator_fraction=self.fraction,
                 duty_cycle_target=self.duty, allocated_bytes=self.torch.cuda.memory_allocated(0),
                 reserved_bytes=self.torch.cuda.memory_reserved(0))
        with self.log_path.open('a') as f:
            f.write(json.dumps(s) + '\n')
        self.last_check = now
        external = sum(v for p, v in s['processes_mib'].items() if p != os.getpid())
        if s['free_mib'] < 2048:
            raise RuntimeError('RESOURCE_STOP: free GPU memory below 2048 MiB')
        if external - self.external_baseline > 1024:
            raise RuntimeError('RESOURCE_STOP: other workloads grew by more than 1024 MiB')
        if s['utilization_pct'] >= 95:
            self.high_util_since = now if self.high_util_since is None else self.high_util_since
            if now - self.high_util_since >= 30:
                raise RuntimeError('RESOURCE_STOP: sustained GPU utilization >=95% for 30 seconds')
        else:
            self.high_util_since = None

    def paced_sync(self, start):
        self.torch.cuda.synchronize()
        active = time.monotonic() - start
        time.sleep(active * (1 / self.duty - 1))
        self.check()

    def close(self):
        if not self.lock.closed:
            self.lock.close()
