"""Offline evidence audit of recovered prototype artifacts; no model fitting."""
import calendar,csv,datetime as dt,hashlib,json,os,re
from pathlib import Path
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo
from e7b_setup import ROOT,OUT as DEFAULT_OUT,sha,dump
from e7b_pit import CORE,latest_features
OUT=Path(os.environ.get('E7B_OUTPUT',DEFAULT_OUT)).resolve()

def save(name,rows,columns=None):
    x=pd.DataFrame(rows,columns=columns);x.to_csv(OUT/'tables'/name,index=False);return x
def clean(s):
    return re.sub(r'【[^†】]+†([^】]*)】',r'\1',s).replace('\xa0',' ')
def blocks(packet):
    for block in re.split(r'-{30,}\n',packet['response']):
        m=re.search(r'Source: open\(\{"ref_id"\s*:\s*"(https?[^" ]+)"',block)
        if not m:continue
        lines=[clean(re.sub(r'^L\d+:\s?','',s)) for s in block.splitlines() if re.match(r'L\d+:',s)]
        yield m.group(1),block,lines

def source_inventory():
    manifest=[];indexes=[];listed=[];tables=[];observations=[]
    cohort=pd.read_csv(OUT/'cohort_locked.csv',dtype={'cik':str});bycik=dict(zip(cohort.cik.astype(int),cohort.prototype_id))
    for p in sorted((OUT/'raw/web_extracts').glob('*.json')):
        packet=json.loads(p.read_text())
        for url,block,lines in blocks(packet):
            text='\n'.join(lines);m=re.search(r'/edgar/data/(\d+)/',url);cik=int(m[1]) if m else None
            row={'source_url':url,'retrieval_recorded_utc':packet['retrieval_recorded_utc'],'prototype_id':bycik.get(cik,packet.get('prototype_id','METHOD_OR_DISCOVERY')),'local_extract_path':str(p.relative_to(OUT)),'extract_file_sha256':sha(p),'representation':packet['kind'],'readable_lines':len(lines),'status':'RENDERED_TEXT_ACQUIRED' if lines else 'UNAVAILABLE_WEB_CACHE_OR_RENDERER','original_SEC_bytes_acquired':False,'original_body_sha256':None,'response_is_raw_HTTP_body':False}
            manifest.append(row)
            if 'SEC Accession No.' in text:
                get=lambda label:re.search(re.escape(label)+r'\s*\n\s*(\d{4}-\d\d-\d\d(?: \d\d:\d\d:\d\d)?)',text)
                ac=re.search(r'SEC Accession No\. (\d{10}-\d{2}-\d{6})',text);fd=get('Filing Date');at=get('Accepted');period=get('Period of Report');sic=re.search(r'SIC:\s*(\d{4})',text)
                cm=re.search(r'\(Filer\) CIK:\s*(\d+)',text)
                idx={**row,'cik':f'{cik:010d}' if cik else None,'accession':ac[1] if ac else None,'form':'10-K/A' if 'Form 10-K/A' in text else '10-K','filing_date':fd[1] if fd else None,'accepted_display_local_unverified_timezone':at[1] if at else None,'period_end':period[1] if period else None,'SIC_from_filing':sic[1] if sic else None,'CIK_verified_from_index':bool(cm and int(cm[1])==cik),'acceptance_timezone_verified':False,'provider_received_utc':None,'historical_first_seen_verified':False,'revision_inventory_complete':False,'strict_PIT_eligible':False}
                indexes.append(idx)
                for line in lines:
                    cols=[v.strip() for v in line.split('|')]
                    if len(cols)>=4 and cols[-1].isdigit():
                        f=next((v for v in cols if re.fullmatch(r'[\w.\-]+\.(?:htm|html|xml|pdf|txt|xsd)',v)),None)
                        if f:listed.append({'prototype_id':idx['prototype_id'],'accession':idx['accession'],'sequence':cols[0] if cols[0].isdigit() else None,'document_filename':f,'document_type':cols[-2],'listed_bytes':int(cols[-1]),'source_index_url':url,'artifact_url':url.rsplit('/',1)[0]+'/'+f,'file_retrieved_as_original':False})
            if packet['kind']=='SEC_RENDERED_XBRL_TABLE_NOT_RAW_INSTANCE':
                heading=' | '.join(v for v in lines[:7] if re.search('statement|balance|income|cash flow',v,re.I))
                actual=bool(heading);tables.append({'prototype_id':packet['prototype_id'],'source_url':url,'accession':packet.get('accession'),'rendered_financial_table_readable':actual,'heading':heading[:300],'original_instance_acquired':False,'context_units_authenticated':False})
                if actual:
                    # Candidate display observations ONLY. No unverified mapping
                    # to original contexts, fiscal-quarter facts or scaled units.
                    for line in lines:
                        if re.match(r'-?\s*Definition|\+ References|\+ Details|- Details',line):break
                        if '|' not in line:continue
                        cols=[v.strip() for v in line.split('|')]
                        if not cols[0] or not re.search('[A-Za-z]',cols[0]) or len(cols)<2:continue
                        if re.search(r'(?:12|3|6|9) Months|In (?:Millions|Thousands)|(?:Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d',cols[0]):continue
                        if not any(re.search(r'\d',v) for v in cols[1:]):continue
                        observations.append({'prototype_id':packet['prototype_id'],'source_url':url,'field_label':cols[0],'display_cells_json':json.dumps(cols[1:]),'period_header_not_inferred':True,'numeric_fact_status':'RENDERED_DISPLAY_ONLY_NOT_AUTHENTICATED_XBRL_FACT','strict_PIT_eligible':False})
    # Discovery is separately hashed, never promoted to acquired source evidence.
    for p in sorted((OUT/'raw/web_extracts').glob('*.json')):
        j=json.loads(p.read_text())
        if j['kind'].startswith('DISCOVERY') or 'FIND' in j['kind']:
            manifest.append({'source_url':'DISCOVERY_PACKET_MULTIPLE_URLS','retrieval_recorded_utc':j['retrieval_recorded_utc'],'prototype_id':'DISCOVERY_ONLY','local_extract_path':str(p.relative_to(OUT)),'extract_file_sha256':sha(p),'representation':j['kind'],'readable_lines':0,'status':'NOT_PRIMARY_ACQUISITION','original_SEC_bytes_acquired':False,'original_body_sha256':None,'response_is_raw_HTTP_body':False})
    idx=pd.DataFrame(indexes).drop_duplicates(['accession'],keep='first');ls=pd.DataFrame(listed).drop_duplicates(['accession','document_filename']);tb=pd.DataFrame(tables).drop_duplicates('source_url');ob=pd.DataFrame(observations).drop_duplicates(['source_url','field_label','display_cells_json'])
    for r in json.loads((OUT/'audits/price_fetch_manifest.json').read_text()):
        manifest.append({'source_url':r['url'],'retrieval_recorded_utc':r['retrieved_at_utc'],'prototype_id':r['prototype_id'],'local_extract_path':r.get('quarantined_response_path'),'extract_file_sha256':None,'representation':'YAHOO_HTTP_ENVELOPE_QUARANTINED_CURRENT_METADATA','readable_lines':0,'status':r['status'],'original_SEC_bytes_acquired':False,'original_body_sha256':r.get('response_sha256'),'response_is_raw_HTTP_body':True,'sanitized_historical_path':r.get('sanitized_path'),'sanitized_historical_sha256':r.get('sanitized_sha256')})
    for r in json.loads((OUT/'audits/direct_SEC_access_failures.json').read_text())['outside_sandbox_public_probes']:
        manifest.append({'source_url':r['url'],'retrieval_recorded_utc':None,'prototype_id':'SEC_ACCESS_PROBE','local_extract_path':'audits/direct_SEC_access_failures.json','extract_file_sha256':sha(OUT/'audits/direct_SEC_access_failures.json'),'representation':'HTTP_FAILURE_OBSERVED_STDOUT_NOT_RAW_BODY','readable_lines':0,'status':'HTTP403','original_SEC_bytes_acquired':False,'original_body_sha256':None,'response_is_raw_HTTP_body':False})
    save('source_manifest.csv',manifest);idx.to_csv(OUT/'tables/filing_index_metadata.csv',index=False);ls.to_csv(OUT/'tables/SEC_listed_artifact_manifest.csv',index=False);tb.to_csv(OUT/'tables/rendered_table_accessibility.csv',index=False);ob.to_csv(OUT/'tables/rendered_display_observations.csv',index=False)
    return cohort,idx,ls,tb,ob

def price_audit():
    fetch=json.loads((OUT/'audits/price_fetch_manifest.json').read_text());rows=[];annual=[];splitrows=[];safefields={'symbol','currency','exchangeName','instrumentType','timezone','exchangeTimezoneName','firstTradeDate','shortName'}
    for r in fetch:
        p=OUT/r.get('sanitized_path','DOES_NOT_EXIST');row={'prototype_id':r['prototype_id'],'queried_symbol':r['queried_symbol'],'HTTP_status':r.get('http_status'),'historical_rows':0,'valid_OHLC_rows':0,'first_date':None,'last_date':None,'within_2012_2022':False,'duplicate_timestamps':None,'split_events':0,'cash_dividend_events':0,'historical_security_mapping_verified':False,'as_traded_price_verified':False,'complete_delisting_settlement_verified':False,'strict_market_eligible':False,'failure_reason':'PRICE_ACCESS_FAILED_OR_LEGACY_ID_UNMAPPED'}
        if p.is_file():
            x=json.loads(p.read_text());assert set(x['identity_metadata'])<=safefields
            ts=np.asarray(x['timestamp']);assert ((ts>=1325376000)&(ts<1672531200)).all();q=x['indicators']['quote'][0]
            dates=pd.to_datetime(ts,unit='s',utc=True).tz_convert('America/New_York').date.astype(str)
            frame=pd.DataFrame({k:q.get(k,[None]*len(ts)) for k in ['open','high','low','close','volume']});frame['date']=dates
            valid=frame[['open','high','low','close']].notna().all(axis=1)&(frame[['open','high','low','close']]>0).all(axis=1)
            valid&=(frame.high>=frame[['open','close','low']].max(axis=1))&(frame.low<=frame[['open','close','high']].min(axis=1))
            valid&=frame.volume.fillna(-1)>=0
            row.update(historical_rows=len(ts),valid_OHLC_rows=int(valid.sum()),first_date=min(dates),last_date=max(dates),within_2012_2022=True,duplicate_timestamps=int(pd.Series(ts).duplicated().sum()),split_events=len(x['events'].get('splits',{})),cash_dividend_events=len(x['events'].get('dividends',{})),failure_reason='CURRENT_VENDOR_SNAPSHOT_SPLIT_ADJUSTED_OR_UNVERIFIED_AS_TRADED; NO_HISTORICAL_SECURITY_MASTER; DELISTING_NOT_RECONCILED')
            if r['prototype_id']=='DELL_legacy':row['failure_reason']='WRONG_OR_UNPROVEN_SECURITY_CONTINUITY: legacyCIK826083 is not DellTechnologiesCIK1571996; current query begins2016, not2012'
            for year,g in frame.groupby(frame.date.str[:4]):annual.append({'prototype_id':r['prototype_id'],'year':int(year),'historical_quote_rows':len(g),'raw_or_as_traded_verified':False,'security_link_verified':False})
            for event in x['events'].get('splits',{}).values():
                day=dt.datetime.fromtimestamp(event['date'],dt.timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York')).date().isoformat();before=frame[frame.date<day];after=frame[frame.date>=day]
                if len(before) and len(after):
                    a=float(before.close.iloc[-1]);b=float(after.close.iloc[0]);ratio=event['numerator']/event['denominator'];observed=a/b
                    splitrows.append({'prototype_id':r['prototype_id'],'ex_date_vendor':day,'vendor_split_ratio':ratio,'quote_close_before':a,'quote_close_after':b,'observed_before_after_ratio':observed,'ratio_if_as_traded_without_market_move':ratio,'flag_consistent_with_already_split_adjusted':abs(np.log(observed))<abs(np.log(observed/ratio)),'interpretation':'diagnostic, not independent corporate-action certification'})
        rows.append(row)
    save('market_quality_by_company.csv',rows);save('market_quote_coverage_by_year.csv',annual);save('split_adjustment_diagnostics.csv',splitrows)
    return pd.DataFrame(rows)

def run():
    cohort,idx,listed,tables,obs=source_inventory();markets=price_audit();coverage=[];calendarrows=[];queries=[];manual=[]
    for r in cohort.to_dict('records'):
        name=r['prototype_id'];g=idx[idx.prototype_id.eq(name)];tb=tables[tables.prototype_id.eq(name)];ob=obs[obs.prototype_id.eq(name)];m=markets[markets.prototype_id.eq(name)].iloc[0]
        row={**r,'CIK_verified_from_at_least_one_SEC_index':bool(g.CIK_verified_from_index.any()) if len(g) else False,'readable_unique_filing_indexes':len(g),'accepted_local_displays_acquired':int(g.accepted_display_local_unverified_timezone.notna().sum()),'raw_original_SEC_documents':0,'raw_original_XBRL_instances':0,'complete_revision_inventory':False,'verified_acceptance_timezone_chain':False,'historical_vendor_arrival_verified':False,'rendered_financial_tables':int(tb.rendered_financial_table_readable.sum()),'rendered_display_candidate_rows':len(ob),'historical_price_rows':int(m.historical_rows),'as_traded_price_verified':False,'strict_PIT_eligible_quarters':0,'strict_PIT_state':'NOT_ELIGIBLE_UNVERIFIED_SOURCE_VERSION_AND_TIME','SIC_from_sample_filings':'|'.join(sorted(set(g.SIC_from_filing.dropna().astype(str))))}
        row['classification_warning']='FILING_SIC2911_OUTSIDE_PREDECLARED13; economic energy group only, do not silently relabel or drop issuer' if name=='COP' else ''
        row['initial_CIK_evidence_status']=row.pop('CIK_evidence_status')
        coverage.append(row)
        for year in range(2012,2023):
            for quarter in range(1,5):
                end=f'{year}-{quarter*3:02d}-{calendar.monthrange(year,quarter*3)[1]}'
                calendarrows.append({'prototype_id':name,'calendar_quarter':f'{year}Q{quarter}','metadata_filings_in_calendar_quarter':int(g.filing_date.fillna('').between(f'{year}-{(quarter-1)*3+1:02d}-01',end).sum()),'source_inventory_complete':False,'strict_eligible_core_cells':0,'fixed_core_cells_target':7,'coverage_interpretation':'NOT_ACQUIRED_OR_UNVERIFIED; not evidence that no financial report/economic event existed','membership_in_quarter_verified':False})
                cutoff=dt.datetime.fromisoformat(end+'T17:00:00').replace(tzinfo=ZoneInfo('America/New_York')).astimezone(dt.timezone.utc).isoformat()
                values=latest_features([],cutoff)
                queries.append({'prototype_id':name,'query_calendar_date':end,'query_utc':cutoff,'is_verified_trading_decision':False,**values['values'],'query_status':'NO_VERIFIED_FACT_INPUTS_NOT_ECONOMIC_ZERO','availability_mode':'source_event; historical_vendor_arrival separately unavailable'})
        manual.append({'prototype_id':name,'target_independent_original_documents':10,'original_documents_obtained':0,'independently_human_reviewed_original_documents':0,'assistant_index_metadata_reading_done':bool(len(g)),'numeric_agreement_rate':None,'status':'NOT_EVALUABLE_ORIGINALS_MISSING; no claim assistant/automated checks equal independent human QA'})
    cv=save('company_PIT_coverage.csv',coverage);save('company_calendar_quarter_coverage.csv',calendarrows);save('manual_document_QA_gate.csv',manual)
    pd.DataFrame(queries).to_csv(OUT/'derived/asof_strict_calendar_queries.csv',index=False)
    gates=[
      ['original_traceability','100% of used facts with original bytes/version/clock',0,'NO_QUALIFIED_INPUTS','No used primary facts; do not call empty dataset100% compliant'],
      ['numeric_coverage','>=80% each of seven fixed core fields',0,'NOT_EVALUABLE','No raw authenticated quarter facts; 0/6160 prototype target cells eligible, membership denominator unresolved'],
      ['common_trading_date_availability','>=90% eligible dates',None,'NOT_EVALUABLE','As-traded/security-master/date universe not verified'],
      ['independent_manual_documents','200 original documents; zero critical errors',0,'NOT_COMPLETED','Metadata reading and table rendering do not count as200 original documents reviewed'],
      ['numeric_agreement','>=99% against original documents',None,'NOT_EVALUABLE','No independent raw-XBRL/original-document paired checks'],
      ['market_action_reconciliation','>=99.9% returns reconciled',None,'NOT_EVALUABLE','17 query symbols acquired, no20-security as-traded/delisting master'],
      ['PIT_time_quality','verified timezone+version history for all used facts',0,'NOT_PASSED','20issuer acceptance displays recovered, timezone chain/dissemination/arrival not certified']]
    save('quality_gates.csv',gates,['gate','locked_rule','observed_value','decision','failure_reason'])
    contrasts=json.loads((OUT/'inputs_E7a_protocol_candidate.json').read_text())['primary_contrasts']
    save('six_contrast_variance_feasibility.csv',[{**c,'development_only':True,'variance':None,'cross_stock_dependence':None,'test_size':None,'status':'NOT_ESTIMABLE','reason':'No qualified20-company PIT market/fundamental panel or six aligned fixed forecast series. No model search or fake zero variance.'} for c in contrasts])
    costs=[]
    for typ in ['10-K','EX-101.INS','XML']:
        x=listed[listed.document_type.eq(typ)]
        if typ=='10-K':x=x[x.sequence.eq('1')]
        if len(x):
            for scale,filings in [('20company_x44quarter_upper_bound',880),('100company_x40quarter_nominal',4000)]:
                costs.append({'artifact_type':typ,'observed_index_listed_files':len(x),'sample_median_bytes':float(x.listed_bytes.median()),'sample_max_bytes':int(x.listed_bytes.max()),'scenario':scale,'nominal_filings':filings,'median_bytes_times_filings':float(x.listed_bytes.median()*filings),'scope_limit':'index-listed nominal sizes; selected annual source sample, not actual throughput/quarterly population estimate; excludes exhibits/revisions/market license'})
    save('acquisition_size_scenarios.csv',costs)
    status={'prototype_companies':20,'industries_predeclared':4,'CIK_verified_from_indexes':int(cv.CIK_verified_from_at_least_one_SEC_index.sum()),'readable_unique_filing_indexes_total':len(idx),'companies_with_rendered_financial_tables':int((cv.rendered_financial_tables>0).sum()),'readable_rendered_financial_table_pages':int(cv.rendered_financial_tables.sum()),'rendered_display_candidate_rows':len(obs),'original_SEC_bodies':0,'original_XBRL_instances':0,'strict_PIT_eligible_quarters':0,'nominal_calendar_company_quarters':880,'nominal_core_cells':6160,'market_symbols_with_arrays':int((markets.historical_rows>0).sum()),'historical_market_rows_unverified':int(markets.historical_rows.sum()),'market_symbols_with_full_2012_2022_span':int((markets.first_date.fillna('').str.startswith('2012')&markets.last_date.fillna('').str.startswith('2022')).sum()),'as_traded_certified_securities':0,'new_model_fits':0,'real_six_contrast_inference':'NOT_ESTIMABLE','external_registration':'NOT_REGISTERED','E3c2026_validation':'NOT_EXECUTED'}
    dump(OUT/'audits/audit_results.json',status);print(json.dumps(status,indent=2))
    return status
if __name__=='__main__':run()
