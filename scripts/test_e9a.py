"""Scientific-artifact regression checks; tests never imply raw-data qualification."""
import csv,io,json,tempfile,unittest
from pathlib import Path
from e9a_build import Evidence
from e9a_validate import validate
from validate_publication import check_own_report,OWN_REPORTS
import re

REPO=Path(__file__).resolve().parents[1]
class SourceAttributionTests(unittest.TestCase):
 def test_published_claims_match_exact_source_cells(self):
  result=validate(REPO/'research/E9a',REPO)
  self.assertEqual(result['status'],'PASSED');self.assertFalse(result['historical_PIT_certification'])
 def test_ambiguous_source_selection_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'x.csv').write_text('ticker,value\nAAPL,1\nAAPL,2\n')
   with self.assertRaises(ValueError):Evidence(p).one('x.csv',ticker='AAPL')
 def test_wrong_scope_is_not_the_news_cohort(self):
  a=list(csv.DictReader(io.StringIO((REPO/'research/E9a/CLAIM_EVIDENCE_MATRIX.csv').read_text())))
  news=next(x for x in a if x['claim_id']=='E4C_lr_P');tech=next(x for x in a if x['claim_id']=='E5_AAPL_xgboost')
  self.assertEqual(json.loads(news['fields'])['n'],'65');self.assertEqual(json.loads(tech['fields'])['n'],'482')
  self.assertIn('2023',news['sample_limitations']);self.assertIn('2024',tech['sample_limitations'])
 def test_secondary_significance_is_retained_with_scope(self):
  a={r['claim_id']:r for r in csv.DictReader(io.StringIO((REPO/'research/E9a/CLAIM_EVIDENCE_MATRIX.csv').read_text()))}
  self.assertEqual(float(json.loads(a['E4C_DIFF_HIER_S_P']['fields'])['bootstrap_holm2']),.028)
  self.assertIn('secondary_hier',a['E4C_DIFF_HIER_S_P']['selector'])
  self.assertEqual(float(json.loads(a['E6_UP_SIGNIFICANT']['fields'])['bootstrap_p_holm_global_primary']),.004)
 def test_unresolved_identifier_not_published_as_doi(self):
  refs=json.loads((REPO/'research/E9a/literature/citation_catalog.json').read_text());r=next(x for x in refs if x['id']=='R18')
  self.assertEqual(r['doi'],'');self.assertTrue(r['url'].startswith('https://www.jstor.org/'))
class ReportBoundaryTests(unittest.TestCase):
 def test_extra_binary_path_is_not_whitelisted(self):
  with self.assertRaisesRegex(ValueError,'approved report path'):
   check_own_report(Path('other.pdf'),'research/E9a/other.pdf',re.compile('IMPOSSIBLE'),'/private-root/')
 def test_report_tampering_without_pin_update_is_rejected(self):
  import shutil
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'PAPER_DRAFT.pdf';shutil.copy2(REPO/'research/E9a/PAPER_DRAFT.pdf',p)
   p.write_bytes(p.read_bytes()+b'changed')
   with self.assertRaisesRegex(ValueError,'pinned'):
    check_own_report(p,'research/E9a/PAPER_DRAFT.pdf',re.compile('IMPOSSIBLE'),'/private-root/')
if __name__=='__main__':unittest.main(verbosity=2)
