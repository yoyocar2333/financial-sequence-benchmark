"""Evidence and manuscript-boundary tests; not independent scientific QA."""
import csv,io,json,re,unittest
from pathlib import Path
from iceib2027_validate import validate,rows
R=Path(__file__).resolve().parents[1];D=R/'research/ICEIB2027'
class ConferenceEvidenceTests(unittest.TestCase):
 def test_source_scope_and_abstract(self):self.assertEqual(validate(R,D)['abstract_words'],100)
 def test_all_eight_primary_technical_contrasts_survive(self):
  records=rows(D/'audits/SOURCE_CLAIM_LEDGER.csv');s=[r for r in records if r['source_file'].endswith('E5_technical_increments.csv')]
  self.assertEqual(len(s),8);self.assertEqual({json.loads(r['selector'])['ticker'] for r in s},{'AAPL','TSLA'})
 def test_all_twelve_development_comparisons_retained(self):
  r=[r for r in rows(D/'tables/development_all12_contrasts.csv') if r['block']=='60'];self.assertEqual(len(r),12)
  text=(D/'ICEIB2027_FULL_PAPER.md').read_text();self.assertIn('−0.001027',text);self.assertIn('p≥0.4032',text)
 def test_positive_exceptions_keep_qualification(self):
  s=(D/'ICEIB2027_FULL_PAPER.md').read_text()
  for token in ['initialization','0.0744','0.028','0.1894/0.3714','F-only','0.004','repeatedly inspected']:self.assertIn(token,s)
 def test_public_bundle_excludes_template_documents(self):
  self.assertFalse(list(D.rglob('*.docx')));self.assertFalse(list(D.rglob('*.pdf')))
 def test_official_template_match_is_evidence_based(self):
  checks=json.loads((D/'audits/OFFICIAL_SOURCE_CHECKS.json').read_text());link=next(x for c in checks for x in c.get('links',[]) if 'decoded_template_sha256' in x)
  self.assertTrue(link['matches_user_template']);self.assertNotIn('UEsDB',json.dumps(checks))
 def test_cohorts_remain_distinct(self):
  t=(D/'ICEIB2027_FULL_PAPER.md').read_text();self.assertIn('482 common dates',t);self.assertIn('224/232/230',t);self.assertIn('Different cohorts are evaluated separately',t)
if __name__=='__main__':unittest.main(verbosity=2)
