"""Data-contract tests with explicitly synthetic records, no financial fits."""
import copy,datetime as dt,hashlib,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from e7b_pit import acceptance_utc,strict_audit,asof_fact,parse_number,parse_xbrl,latest_features,security_at,executable_wealth_return
from e7b_historical_universe import select

def record(**changes):
    r={'kind':'fundamental_actual','issuer_id':'SYNTHETIC_ISSUER_1','source_document_id':'SYNTHETIC_ORIGINAL_2019Q2','version_sha256':'1'*64,'public_available_utc':'2019-07-31T21:00:00Z','public_time_evidence':'SYNTHETIC_DISSEMINATION_LOG','accepted_at_utc':'2019-07-31T20:59:00Z','acceptance_timezone_verified':True,'retrieved_at_utc':'2026-11-07T01:00:00Z','version_chain_verified':True,'units':'USD','fact_concept':'revenue','context_id':'SYNTHETIC_CONSOLIDATED_2019Q2','period_start':'2019-04-01','period_end':'2019-06-30','fiscal_year':2019,'fiscal_quarter':2,'period_basis':'Q','original_SEC_bytes_verified':True,'source_public_clock_verified':True,'amendment_inventory_verified':True,'context_and_units_verified':True,'CIK_from_original_verified':True,'inventory_verified_through_utc':'2022-12-31T23:59:59Z','source_representation':'ORIGINAL_SEC_BODY','has_dimensions':False,'value':100}
    r.update(changes);return r

class PrototypeTests(unittest.TestCase):
    def test_after_close_source_rejected(self):
        r=record();self.assertFalse(strict_audit(r,'2019-07-31T20:00:00Z')['eligible']);self.assertTrue(strict_audit(r,'2019-08-01T21:00:00Z')['eligible'])
    def test_retrieval_never_first_seen(self):
        self.assertTrue(strict_audit(record(),'2019-08-01T21:00:00Z')['retrieval_is_not_first_seen'])
    def test_rendered_hash_cannot_certify_original(self):
        r=record(source_representation='WEB_RENDERED_EXTRACT');self.assertFalse(strict_audit(r,'2019-08-01T21:00:00Z')['eligible'])
    def test_missing_public_clock_and_revision_inventory(self):
        for name in ['original_SEC_bytes_verified','source_public_clock_verified','amendment_inventory_verified']:
            self.assertFalse(strict_audit(record(**{name:False}),'2019-08-01T21:00:00Z')['eligible'])
    def test_amendment_never_backfilled(self):
        old=record();new=record(source_document_id='SYNTHETIC_AMENDMENT',public_available_utc='2019-10-01T21:00:00Z',accepted_at_utc='2019-10-01T20:59:00Z',version_sha256='2'*64,value=999)
        self.assertEqual(asof_fact([new,old],'2019-08-01T21:00:00Z')['value'],100);self.assertEqual(asof_fact([new,old],'2019-10-02T21:00:00Z')['value'],999)
    def test_vendor_arrival_distinct_from_source(self):
        r=record(provider_received_utc='2019-08-02T12:00:00Z',historical_snapshot_verified=True)
        self.assertTrue(strict_audit(r,'2019-08-01T21:00:00Z','source')['eligible']);self.assertFalse(strict_audit(r,'2019-08-01T21:00:00Z','arrival')['eligible'])
        self.assertFalse(strict_audit(record(),'2019-08-01T21:00:00Z','arrival')['eligible'])
    def test_invalid_receipt_clock(self):
        r=record(provider_received_utc='2019-07-30T21:00:00Z');self.assertFalse(strict_audit(r,'2019-08-01T21:00:00Z')['eligible'])
    def test_coverage_window_not_infinite(self):
        self.assertFalse(strict_audit(record(inventory_verified_through_utc='2019-07-31T23:00:00Z'),'2019-08-02T21:00:00Z')['eligible'])
    def test_annual_not_quarter_and_segment(self):
        self.assertFalse(strict_audit(record(period_start='2018-07-01'),'2019-08-01T21:00:00Z')['eligible']);self.assertFalse(strict_audit(record(has_dimensions=True),'2019-08-01T21:00:00Z')['eligible'])
    def test_context_and_unit_groups_separate(self):
        with self.assertRaises(ValueError):asof_fact([record(),record(units='JPY')],'2019-08-01T21:00:00Z')
    def test_conflicting_equal_time_is_error(self):
        with self.assertRaises(ValueError):asof_fact([record(),record(value=99)],'2019-08-01T21:00:00Z')
    def test_dst_and_unverified_clock(self):
        self.assertEqual(acceptance_utc('20120726161248',True),'2012-07-26T20:12:48+00:00')
        with self.assertRaises(ValueError):acceptance_utc('20121104013000',True)
        with self.assertRaises(ValueError):acceptance_utc('20120311023000',True)
        with self.assertRaises(ValueError):acceptance_utc('20120726161248',False)
    def test_scales_signs_and_unknown_transform(self):
        self.assertEqual(float(parse_number('1,234',6)),1234000000);self.assertEqual(float(parse_number('123',3,'-')),-123000)
        self.assertIsNone(parse_number('—'))
        with self.assertRaises(ValueError):parse_number('1.234',transform='invented')
    def test_native_xbrl_preserves_units_context_and_entity(self):
        raw=b'''<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:g="http://fasb.org/us-gaap/2019-01-31"><context id="Q"><entity><identifier scheme="http://www.sec.gov/CIK">0000000001</identifier></entity><period><startDate>2019-04-01</startDate><endDate>2019-06-30</endDate></period></context><unit id="USD"><measure>iso4217:USD</measure></unit><g:Revenues contextRef="Q" unitRef="USD" decimals="-3">1234000</g:Revenues></xbrl>'''
        result=parse_xbrl(raw,1);f=result['facts'][0];self.assertEqual(f['value'],'1234000');self.assertTrue(f['CIK_matches_expected']);self.assertEqual(f['period_start'],'2019-04-01');self.assertFalse(result['source_time_verified_by_parser'])
        self.assertFalse(parse_xbrl(raw,2)['facts'][0]['CIK_matches_expected'])
    def test_inline_scale_and_sign(self):
        raw=b'''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:x="http://www.xbrl.org/2003/instance" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><x:context id="I"><x:entity><x:identifier scheme="CIK">1</x:identifier></x:entity><x:period><x:instant>2019-06-30</x:instant></x:period></x:context><x:unit id="U"><x:measure>iso4217:USD</x:measure></x:unit><ix:nonFraction name="us-gaap:Assets" contextRef="I" unitRef="U" scale="6" sign="-">1,234</ix:nonFraction></html>'''
        self.assertEqual(parse_xbrl(raw,1)['facts'][0]['value'],'-1234000000')
    def test_entity_expansion_refused(self):
        with self.assertRaises(ValueError):parse_xbrl(b'<!DOCTYPE x [<!ENTITY y "1">]><x/>',1)
    def test_empty_inputs_not_economic_zero(self):
        x=latest_features([],'2019-08-01T21:00:00Z');self.assertTrue(all(v is None for v in x['values'].values()))
    def test_feature_periods_and_share_basis(self):
        rev=record();old=record(source_document_id='SYNTHETIC_2018Q2',period_start='2018-04-01',period_end='2018-06-30',fiscal_year=2018,value=80)
        net=record(fact_concept='net_income',value=10);eps=record(fact_concept='diluted_eps',units='USD/shares',value=2);epsold={**old,'fact_concept':'diluted_eps','units':'USD/shares','value':1}
        x=latest_features([rev,old,net,eps,epsold],'2019-08-01T21:00:00Z');self.assertAlmostEqual(x['values']['revenue_yoy'],.25);self.assertAlmostEqual(x['values']['net_margin'],.1);self.assertIsNone(x['values']['eps_yoy_symmetric'])
        with self.assertRaises(ValueError):latest_features([rev,record(issuer_id='SYNTHETIC_OTHER')],'2019-08-01T21:00:00Z')
    def test_security_ticker_reuse_and_knowledge_clock(self):
        master=[{'security_id':'SYNTHETIC_OLD_DELL','issuer_id':'SYNTHETIC_OLDCO','ticker':'DELL','valid_from':'2010-01-01','valid_to_exclusive':'2013-10-29','known_from_utc':'2010-01-01T00:00:00Z'},{'security_id':'SYNTHETIC_NEW_DELL','issuer_id':'SYNTHETIC_NEWCO','ticker':'DELL','valid_from':'2018-12-28','valid_to_exclusive':'2023-01-01','known_from_utc':'2018-12-28T00:00:00Z'}]
        self.assertIsNone(security_at(master,'SYNTHETIC_NEW_DELL','2012-01-03','2012-01-03T22:00:00Z'));self.assertEqual(security_at(master,'SYNTHETIC_OLD_DELL','2012-01-03','2012-01-03T22:00:00Z')['issuer_id'],'SYNTHETIC_OLDCO')
    def test_split_dividend_accounting_and_entry_exdate(self):
        actions=[{'security_id':'S','kind':'split','effective_date':'2019-08-02','ratio':2,'source_verified':True},{'security_id':'S','kind':'cash_dividend','effective_date':'2019-08-02','amount':1,'amount_basis':'post_split_share','source_verified':True}]
        self.assertAlmostEqual(executable_wealth_return('2019-08-01','2019-08-05',100,50,actions,'S'),.02)
        self.assertAlmostEqual(executable_wealth_return('2019-08-02','2019-08-05',50,50,actions,'S'),0)
    def test_delisting_is_not_silent_zero(self):
        a={'security_id':'S','kind':'delisting','effective_date':'2019-08-02','settlement_per_share':None,'source_verified':True}
        with self.assertRaises(ValueError):executable_wealth_return('2019-08-01','2019-08-05',10,None,[a],'S')
        a['settlement_per_share']=0;self.assertEqual(executable_wealth_return('2019-08-01','2019-08-05',10,None,[a],'S'),-1)
    def test_historical_selection_does_not_use_future_survival(self):
        rows=[]
        for i,sic in enumerate(['1311','3571','5331','7372']):
            for j in range(2):rows.append({'security_id':f'SYNTHETIC_S{i}{j}','issuer_id':f'SYNTHETIC_I{i}{j}','historical_snapshot_verified':True,'security_identity_verified':True,'snapshot_available_utc':'2011-12-30T22:00:00Z','security_valid_from':'2010-01-01','security_valid_to_exclusive':'2023-01-01','instrument_class':'US_PRIMARY_COMMON_STOCK','asof_price_USD':10,'prior60_median_dollar_volume':2e6,'prior_price_observations':500,'past_published_report_versions':8,'SIC_asof':sic,'survives_until2025':bool(j)})
        a=select(rows,'2011-12-30T22:00:00Z',per_stratum=1);changed=copy.deepcopy(rows)
        for r in changed:r['survives_until2025']=not r['survives_until2025']
        b=select(changed,'2011-12-30T22:00:00Z',per_stratum=1)
        self.assertTrue(a['complete_target']);self.assertEqual([r['security_id'] for r in a['selected']],[r['security_id'] for r in b['selected']])
    def test_current_snapshot_and_missing_evidence_refused(self):
        from e7b_build_asof import authenticate
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            r=authenticate([record()],{},d)[0];self.assertFalse(r['original_SEC_bytes_verified']);self.assertFalse(r['context_and_units_verified'])
        self.assertFalse(select([{'security_id':'SYNTHETIC'}],'2011-12-30T22:00:00Z')['complete_target'])

if __name__=='__main__':unittest.main()
