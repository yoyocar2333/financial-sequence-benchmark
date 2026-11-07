"""Generate as-of financial features from authenticated-source input contracts.

The current prototype has zero eligible normalized facts. The CLI deliberately
produces missing-with-reason rows for that case. It never treats rendered display
observations or current retrieval timestamps as historical original facts.
"""
import argparse,csv,hashlib,json
from pathlib import Path
from e7b_pit import latest_features,strict_audit

def authenticate(records,sources,bundle):
    base=Path(bundle).resolve();result=[]
    for item in records:
        r=dict(item);s=sources.get(r['source_document_id'],{});r['original_SEC_bytes_verified']=False
        p=(base/s.get('original_path','__MISSING__')).resolve()
        if not p.is_relative_to(base):raise ValueError('Source path escapes bundle')
        digest=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
        original=(s.get('representation')=='ORIGINAL_SEC_BODY' and s.get('http_status')==200 and s.get('source_url','').startswith('https://www.sec.gov/Archives/edgar/') and digest and digest==s.get('original_sha256')==r.get('version_sha256'))
        if original:r['original_SEC_bytes_verified']=True
        r['source_representation']=s.get('representation','MISSING_SOURCE_EVIDENCE')
        # Fact rows alone cannot turn evidence flags on. Source registry must
        # carry explicit verification records. Their truth still requires audit.
        for flag in ['source_public_clock_verified','amendment_inventory_verified','acceptance_timezone_verified','CIK_from_original_verified','context_and_units_verified']:
            evidence=s.get('verification_records',{}).get(flag,{})
            ep=(base/evidence.get('path','__MISSING__')).resolve()
            if not ep.is_relative_to(base):raise ValueError('Evidence path escapes bundle')
            r[flag]=bool(evidence.get('verified') is True and ep.is_file() and hashlib.sha256(ep.read_bytes()).hexdigest()==evidence.get('sha256'))
        if s.get('issuer_id')!=r['issuer_id']:r['CIK_from_original_verified']=False
        result.append(r)
    return result

def build(bundle,facts,registry,query_file,output):
    dest=Path(output)
    if dest.exists():raise FileExistsError('Choose new as-of output')
    dest.mkdir(parents=True)
    records=authenticate(json.loads(Path(facts).read_text()),json.loads(Path(registry).read_text()),bundle)
    output_rows=[];traces=[]
    with Path(query_file).open(newline='') as f:queries=list(csv.DictReader(f))
    for q in queries:
        cutoff=q['query_utc']
        if not '2012'<=cutoff[:4]<='2022':raise ValueError('Prototype queries limited to development2012-2022')
        issuer=q['prototype_id'];r=[v for v in records if v['issuer_id']==issuer]
        v=latest_features(r,cutoff,mode='source')
        output_rows.append({'prototype_id':issuer,'query_utc':cutoff,**v['values'],'missing_reasons_json':json.dumps(v['missing_reasons'],sort_keys=True),'source_mode_is_not_vendor_arrival':True})
        if not r:traces.append({'prototype_id':issuer,'query_utc':cutoff,'source_document_id':None,'eligible':False,'reasons':'NO_AUTHENTICATED_NORMALIZED_FACT_INPUT'})
        else:
            for x in r:
                a=strict_audit(x,cutoff);traces.append({'prototype_id':issuer,'query_utc':cutoff,'source_document_id':x['source_document_id'],'eligible':a['eligible'],'reasons':'|'.join(a['reasons'])})
    for name,values in [('asof_features.csv',output_rows),('asof_rejection_trace.csv',traces)]:
        with (dest/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(values[0]) if values else ['EMPTY'],lineterminator='\n');w.writeheader();w.writerows(values)
    result={'queries':len(queries),'authenticated_input_facts':len(records),'generated_nonmissing_core_values':sum(v is not None for r in output_rows for k,v in r.items() if k in vkeys()),'no_imputation_or_fits':True,'no2026_queries':True,'qualification':'No nonmissing values is an explicit failed data gate, not an absence of financial events'}
    (dest/'asof_generation_audit.json').write_text(json.dumps(result,indent=2)+'\n');return result

def vkeys():
    from e7b_pit import CORE
    return CORE

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--facts',type=Path,required=True);p.add_argument('--source-registry',type=Path,required=True);p.add_argument('--queries',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.bundle,a.facts,a.source_registry,a.queries,a.output_dir),indent=2))
