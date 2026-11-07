"""Full offline audit replay from captured historical-only source artifacts."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
import pandas as pd

def replay(bundle,output):
    bundle=Path(bundle).resolve();out=Path(output).resolve()
    if out.exists():raise FileExistsError('Use a new replay directory')
    for d in ['raw/web_extracts','raw/prices','audits','tables','derived','figures']:(out/d).mkdir(parents=True,exist_ok=True)
    for p in (bundle/'raw/web_extracts').glob('*.json'):shutil.copy2(p,out/'raw/web_extracts'/p.name)
    for p in (bundle/'raw/prices').glob('*_historical_sanitized.json'):shutil.copy2(p,out/'raw/prices'/p.name)
    for n in ['cohort_locked.csv','inputs_E7a_protocol_candidate.json']:shutil.copy2(bundle/n,out/n)
    for n in ['price_fetch_manifest.json','direct_SEC_access_failures.json']:shutil.copy2(bundle/'audits'/n,out/'audits'/n)
    for n in ['normalized_verified_facts.json','authenticated_source_registry.json']:shutil.copy2(bundle/'derived'/n,out/'derived'/n)
    os.environ['E7B_OUTPUT']=str(out)
    import e7b_audit,e7b_diagnostics
    from e7b_build_asof import build
    e7b_audit.OUT=out;e7b_diagnostics.OUT=out
    e7b_audit.run();e7b_diagnostics.run(plots=False)
    build(out,out/'derived/normalized_verified_facts.json',out/'derived/authenticated_source_registry.json',out/'derived/asof_strict_calendar_queries.csv',out/'derived/asof_build_v1_1')
    checked=[]
    for actual in sorted((out/'tables').glob('*.csv')):
        expected=bundle/'tables'/actual.name
        a=pd.read_csv(actual);b=pd.read_csv(expected)
        pd.testing.assert_frame_equal(a,b,check_dtype=False,check_exact=False,rtol=1e-12,atol=1e-14);checked.append(actual.name)
    for name in ['asof_features.csv','asof_rejection_trace.csv']:
        a=pd.read_csv(out/'derived/asof_build_v1_1'/name);b=pd.read_csv(bundle/'derived/asof_build_v1_1'/name)
        pd.testing.assert_frame_equal(a,b,check_dtype=False);checked.append(name)
    result={'status':'PASSED','recomputed_tables':checked,'source_material':'rendered historical captures and sanitized vendor arrays, not authenticated original SEC bodies','no_network':True,'new_model_fits':0,'GPU_used':False,'PIT_gates_remain_not_passed':True,'validation2026_executed':False}
    (out/'replay_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',required=True,type=Path);p.add_argument('--output-dir',required=True,type=Path);a=p.parse_args();replay(a.bundle,a.output_dir)
