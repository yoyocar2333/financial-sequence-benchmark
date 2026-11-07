"""Freeze a purposive four-industry source/identity stress prototype, not a model search."""
import csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/e7b_20261107'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
COHORT=[
('COP',1163165,'ConocoPhillips','oil_gas_extraction','13','2012 spin-off/identity audit'),
('EOG',821189,'EOG Resources','oil_gas_extraction','13','continuing-issuer control'),
('OXY',797468,'Occidental Petroleum','oil_gas_extraction','13','acquisition and identity audit'),
('DVN',1090012,'Devon Energy','oil_gas_extraction','13','merger and identity audit'),
('CHK_legacy',895126,'Chesapeake Energy legacy equity','oil_gas_extraction','13','bankruptcy/equity cancellation stress case; not current-symbol continuation'),
('AAPL',320193,'Apple','computing_hardware','35_36','legacy study linkage; no performance filter'),
('INTC',50863,'Intel','computing_hardware','35_36','semiconductor control'),
('IBM',51143,'International Business Machines','computing_hardware','35_36','spin-off/corporate-action audit'),
('NVDA',1045810,'NVIDIA','computing_hardware','35_36','splits and historical scaling audit'),
('DELL_legacy',826083,'Dell Inc legacy listed equity','computing_hardware','35_36','2013 buyout; do not splice current Dell Technologies'),
('WMT',104169,'Wal-Mart Stores historical issuer','retail_trade','52_59','fiscal-calendar and split audit'),
('TGT',27419,'Target','retail_trade','52_59','retail inventory and dividend audit'),
('COST',909832,'Costco Wholesale','retail_trade','52_59','special-dividend audit'),
('HD',354950,'Home Depot','retail_trade','52_59','retail corporate-action audit'),
('SHLD_legacy',1310067,'Sears Holdings legacy equity','retail_trade','52_59','bankruptcy/delisting/OTC stress case'),
('MSFT',789019,'Microsoft','software_services','73','continuing software issuer'),
('ORCL',1341439,'Oracle','software_services','73','fiscal-calendar and corporate-identity audit'),
('ADBE',796343,'Adobe','software_services','73','continuing software issuer'),
('CRM',1108524,'salesforce.com historical issuer','software_services','73','fiscal-calendar and split audit'),
('YHOO_legacy',1011006,'Yahoo Inc legacy operating equity','software_services','73','2017 business sale/Altaba conversion; liquidation stress case')]

def setup():
 if (OUT/'prototype_plan_locked.json').exists():raise FileExistsError('Preserve completed run; do not reinitialize')
 for d in ['raw/http','raw/web_extracts','raw/issuer','raw/prices','tables','audits','code','figures','logs','derived']:(OUT/d).mkdir(parents=True,exist_ok=True)
 headers=['prototype_id','cik','historical_company_name','industry','SIC_candidate_group','selection_reason','CIK_evidence_status','population_status']
 rows=[dict(zip(headers,[t,f'{c:010d}',n,i,g,why,'PENDING_PRIMARY_VERIFICATION','PURPOSIVE_FEASIBILITY_NOT_PROBABILITY_SAMPLE'])) for t,c,n,i,g,why in COHORT]
 with (OUT/'cohort_locked.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=headers,lineterminator='\n');w.writeheader();w.writerows(rows)
 plan={'version':'E7b-1.0','date':'2026-11-07','scope':'20issuer/four-industry historical PIT prototype; no model search','development_filing_dates':['2012-01-01','2022-12-31'],'quarter_grid':'2012Q1-2022Q4, 44 calendar quarters; do not force post-exit observations','selection':'Purposive technical/identity stress sample locked before new systematic recovery, not a random historical universe. Four known exit/restructuring cases included deliberately; this does not by itself remove selection bias. No stock chosen by forecast gain.','cohort_sha256':sha(OUT/'cohort_locked.csv'),'contract_source':'outputs/e7a_20261106/protocol_candidate.json','contract_sha256':sha(ROOT/'outputs/e7a_20261106/protocol_candidate.json'),'primary_data_source':'SEC original accession and original XBRL/inline XBRL; official filing detail or SGML acceptance timezone independently verified','clocks':['source public/acceptance','provider received if certified','current retrieval separate'],'fetch_policy':'normal public access only, <=1 request per second, no retries after a repeated explicit403/429; no proxy/header rotation to evade SEC limits; retain response bodies and failures','companyfacts_policy':'Do not download current companyfacts containing2026 numeric facts; use dated original filings or historical FSDS instead','manual_document_gate':200,'manual_sampling':'target10 original/revision documents per company spread across<=2022 filing years; without enough originals mark NOT_EVALUABLE, never count repeated pages/facts as separate documents','numeric_coverage_gate':.8,'common_daily_availability_gate':.9,'critical_time_revision_errors_allowed':0,'numeric_agreement_gate':.99,'market_action_reconciliation_gate':.999,'no_new_model_search':True,'no2024_2025_new_selection':True,'no2026_model_data_or_validation':True,'old_E3c_protocol_unchanged':True,'variance_gate':'Only if authenticated original fundamentals, vintage history, reliable prices/actions/identity and >=six fixed comparison forecast series are available on development dates; otherwise NOT_ESTIMABLE, never impute missing evidence as zero','short_term_output':'honest data/identity/as-of engineering and failure audit working paper, separate from prospective confirmation'}
 dump(OUT/'prototype_plan_locked.json',plan)
 protected=json.loads((ROOT/'outputs/e7a_20261106/audits/protected_prior_artifacts.json').read_text())
 for p in (ROOT/'outputs/e7a_20261106').rglob('*'):
  if p.is_file() and 'development' not in p.relative_to(ROOT/'outputs/e7a_20261106').parts:protected[str(p.relative_to(ROOT))]=sha(p)
 for n in ['E7A_CURRENT_RUN.json','E3C_2026_PROTOCOL.md','outputs/e7a_20261106_complete_design.zip']:protected[n]=sha(ROOT/n)
 dump(OUT/'audits/protected_prior_artifacts.json',protected)
 print('E7b LOCKED',len(rows),'issuers;',len(protected),'protected artifacts')
if __name__=='__main__':setup()
