"""Explicit versioned recovery; original failed source/results stay byte-identical."""
import argparse
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import run_e3c as run
from e3c_core import ROOT,OUT as ORIGINAL_OUT,PLAN,sha,write_json
from e3c_calibration_v1_1 import shrink_calibrate

OUT=ROOT/'outputs/e3c_20261026_v1_1'
run.OUT=OUT;run.shrink_calibrate=shrink_calibrate
run.PLAN={**PLAN,'version':'E3c-1.0 numerical solver revision1.1','numerical_repair':{
    'original_output':str(ORIGINAL_OUT.relative_to(ROOT)),'original_error':'L-BFGS-B ABNORMAL with gradient8.57e-7',
    'change':'projected damped Newton for identical strictly convex 2-parameter objective, penalty20 and slope bounds0..3; no research/model/statistics changes',
    'test_predictions_before_repair':0,'verified_raw_model_fits_reused':66}}
run.CODE=run.CODE+('e3c_calibration_v1_1.py','recover_e3c_v1_1.py','test_e3c_calibration_v1_1.py','E3C_NUMERICAL_RECOVERY.md')


def prepare():
    fresh=not (OUT/'prepared.json').exists();run.prepare()
    if fresh:
        oldstatus=json.loads((ORIGINAL_OUT/'status.json').read_text())
        if oldstatus['status']!='STOPPED' or oldstatus['final_raw_fits']!=0:raise RuntimeError('Unexpected original recovery state')
        files=list((ORIGINAL_OUT/'cv').rglob('COMPLETE.json'))
        if len(files)!=66:raise RuntimeError('Unexpected cached fit count')
        for p in files:
            for name,h in json.loads(p.read_text())['files'].items():
                if sha(p.parent/name)!=h:raise RuntimeError('Old cached model changed')
        shutil.copytree(ORIGINAL_OUT/'cv',OUT/'cv',dirs_exist_ok=True)
        protected=json.loads((OUT/'protected_previous_files.json').read_text())
        for p in ORIGINAL_OUT.rglob('*'):
            if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
        write_json(OUT/'protected_previous_files.json',protected)
        shutil.copyfile(ROOT/'scripts/E3C_NUMERICAL_RECOVERY.md',OUT/'NUMERICAL_RECOVERY.md')
        shutil.copyfile(ROOT/'logs/e3c_numerical_preflight.log',OUT/'logs/numerical_preflight.log')
        shutil.copyfile(ORIGINAL_OUT/'status.json',OUT/'logs/original_stopped_status.json')
        shutil.copyfile(ORIGINAL_OUT/'logs/e3c_run.log',OUT/'logs/original_failed_run.log')
        write_json(OUT/'recovery_provenance.json',run.PLAN['numerical_repair'])
    run.verify()


def child(command,**kwargs):
    if str(ROOT/'scripts/analyze_e3c.py') in command:
        command=[sys.executable,'-B','-u',str(Path(__file__).resolve()),'--analyze']
    return subprocess.run(command,**kwargs)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--analyze',action='store_true');args=p.parse_args()
    if args.analyze:
        import analyze_e3c as analysis
        analysis.OUT=OUT
        original_report=analysis.report
        def versioned_report(*arguments):
            original_report(*arguments)
            with (OUT/'E3C_SUMMARY.md').open('a') as report:
                report.write('\n## 執行版本與數值修復\n\n原始版本在66/72個CV原始模型後，L-BFGS-B於近似最優點回報ABNORMAL，尚未產生任何最終測試預測。失敗資料夾、原凍結程式與完整錯誤均保留。此版本只以受限Newton求解同一校準目標，lambda20、先驗、邊界、事件、模型和統計設定均相同；66個歷史校準案例通過KKT檢查，65個原求解器成功案例的概率最大差8.61e-9。原始模型共112組，其中66組核對雜湊後重用，新增6個CV及40個最終原始模型。[完整數值修復紀錄](NUMERICAL_RECOVERY.md)。\n')
        analysis.report=versioned_report;analysis.analyze()
        p=ROOT/'E3C_SUMMARY.md'
        p.write_text(p.read_text().replace('](NUMERICAL_RECOVERY.md)','](outputs/'+OUT.name+'/NUMERICAL_RECOVERY.md)'))
    else:
        with (ROOT/'logs/e3c-suite.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);prepare()
            if args.execute:
                run.subprocess=SimpleNamespace(run=child,check_output=subprocess.check_output)
                run.execute()
