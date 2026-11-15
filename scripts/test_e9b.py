"""Meaningful accounting and inference-boundary checks; synthetic fixtures are engineering only."""
import csv,io,json,unittest
from pathlib import Path
import numpy as np
from e9b_core import decomposition,holm,inference
from e9b_validate import validate
R=Path(__file__).resolve().parents[1]
class AccountingTests(unittest.TestCase):
 def test_continuous_score_requires_grouping_remainder(self):
  y=np.array([0,1,1,0,1,0]);p=np.array([.31,.39,.44,.46,.48,.49]);d,_=decomposition(y,p,5)
  self.assertAlmostEqual(d['brier'],d['reliability']-d['resolution']+d['uncertainty']+d['grouping_remainder'],places=14)
  self.assertGreater(abs(d['grouping_remainder']),1e-4)
 def test_constant_forecast_zero_resolution(self):
  d,_=decomposition([0,1,1,0],[.4]*4,10);self.assertEqual(d['resolution'],0);self.assertAlmostEqual(d['brier'],.26)
 def test_raw_fusion_identity_for_boundary_weights(self):
  y=np.array([0.,1.,0.,1.]);p=np.array([.1,.3,.6,.8]);f=np.array([.7,.6,.4,.5]);c=.49
  for w in [0,.25,.5,.75,1]:
   q=(1-w)*p+w*f;q0=(1-w)*p+w*c
   np.testing.assert_allclose((q0-y)**2-(q-y)**2,2*w*(f-c)*(y-q0)-w*w*(f-c)**2,atol=1e-15)
 def test_holm_accounts_for_family_and_order(self):
  np.testing.assert_allclose(holm([.02,.001,.1]),[.04,.003,.1])
 def test_identical_stock_paths_do_not_create_extra_independence(self):
  path=np.sin(np.arange(80)/7)[:,None];one=inference(path[None,:,:],np.ones((1,80)),20,17)[0];two=inference(np.repeat(path[None,:,:],2,axis=0),np.ones((2,80)),20,17)[0]
  self.assertAlmostEqual(one['hac_se'],two['hac_se']);self.assertAlmostEqual(one['bootstrap_ci_low'],two['bootstrap_ci_low'])
 def test_original_and_new_evidence_cells(self):
  self.assertEqual(validate(R/'research/E9a',R)['original_claim_fields_preserved'],103)
 def test_all_prequential_choices_use_prior_folds(self):
  rows=list(csv.DictReader(io.StringIO((R/'research/E9b/tables/development_prequential_weights.csv').read_text())))
  self.assertTrue(all(r['selection_uses_current_outer_labels']=='False' for r in rows))
  self.assertTrue(all(r['best_single']=='F' and float(r['F_weight'])==1 for r in rows if r['fold']!='2016' and r['model']=='logistic'))
if __name__=='__main__':unittest.main(verbosity=2)
