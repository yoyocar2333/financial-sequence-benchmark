"""Offline E7a aggregate/synthetic replay; no financial data or model fitting."""
import argparse,json,shutil,sys
from pathlib import Path
import numpy as np
import pandas as pd
import e7a_development_audit as design

def replay(bundle,output):
    bundle=Path(bundle).resolve();output=Path(output).resolve()
    if output.exists():raise FileExistsError('Choose a new replay directory')
    for name in ['tables','audits','figures']:(output/name).mkdir(parents=True)
    q=pd.read_csv(bundle/'tables/development_quarter_statistics.csv')
    assert q.quarter.between('2017Q1','2022Q4').all()
    assert len(q)==288 and q.quarter.nunique()==24 and q.ticker.nunique()==2
    scale=q[q.comparison.eq('matched_shrink_increment')].groupby(['ticker','price_model']).loss_difference_mean.std().max()
    reference=json.loads((bundle/'audits/power_scale.json').read_text())['quarter_SD_reference']
    np.testing.assert_allclose(scale,reference,rtol=1e-13)
    shutil.copy2(bundle/'tables/development_variance_summary.csv',output/'tables/development_variance_summary.csv')
    design.OUT=output;design.power_analysis(6);design.controls()
    names=['power_design_grid.csv','power_simulation.csv','required_period_scenarios.csv','synthetic_method_controls.csv']
    for name in names:
        a=pd.read_csv(bundle/'tables'/name);b=pd.read_csv(output/'tables'/name)
        pd.testing.assert_frame_equal(a,b,check_exact=False,rtol=1e-12,atol=1e-14)
    protocol=json.loads((bundle/'protocol_candidate.json').read_text())
    assert protocol['status']=='NOT_EXTERNALLY_REGISTERED_NOT_EXECUTED'
    assert len(protocol['primary_contrasts'])==6 and protocol['H2_primary'] is False
    assert protocol['E3c_2026']=='UNCHANGED_NOT_EXECUTED_NOT_EXTENDED_TO_E6_E7'
    result={'status':'PASSED','reproduced_tables':names,'development_quarters':24,'issuers':2,'new_financial_fits':0,'raw_market_data_read':False,'GPU_initialized':False,'validation2026_executed':False,'registration_completed':False}
    (output/'replay_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',required=True,type=Path);p.add_argument('--output-dir',required=True,type=Path);a=p.parse_args();replay(a.bundle,a.output_dir)
