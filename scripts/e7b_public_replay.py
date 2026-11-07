"""Public aggregate consistency checks, not raw-data reconstruction or PIT proof."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

def check(bundle):
    p=Path(bundle);c=pd.read_csv(p/'tables/company_PIT_coverage.csv');i=pd.read_csv(p/'tables/filing_index_metadata.csv');m=pd.read_csv(p/'tables/market_quality_by_company.csv');g=pd.read_csv(p/'tables/quality_gates.csv');f=pd.read_csv(p/'tables/six_contrast_variance_feasibility.csv')
    assert len(c)==20 and c.prototype_id.nunique()==20 and c.industry.nunique()==4
    assert len(i)==21 and i.CIK_verified_from_index.all()
    assert (c.raw_original_SEC_documents==0).all() and (c.strict_PIT_eligible_quarters==0).all()
    assert (m.historical_rows>0).sum()==17 and m.historical_rows.sum()==45893
    assert not m.strict_market_eligible.any();assert set(f.status)=={'NOT_ESTIMABLE'} and len(f)==6
    assert not g.decision.eq('PASSED').any()
    delays=(pd.to_datetime(i.accepted_display_local_unverified_timezone.str[:10])-pd.to_datetime(i.period_end)).dt.days
    assert delays.median()==50
    qa=pd.read_csv(p/'tables/manual_document_QA_gate.csv');assert qa.independently_human_reviewed_original_documents.sum()==0 and qa.target_independent_original_documents.sum()==200
    pairs=pd.read_csv(p/'tables/diagnostic_price_return_correlations.csv');assert len(pairs)==120
    np.testing.assert_allclose(pairs.pearson_vendor_close_logreturn.median(),.3453622799547186,rtol=1e-12)
    return {'status':'PASSED','companies':20,'source_index_CIK_verified':20,'original_SEC_bodies':0,'strict_PIT_qualified_quarters':0,'public_checks_are_aggregate_consistency_only':True,'new_models':0,'registration_or_validation_executed':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',required=True,type=Path);a=p.parse_args();print(json.dumps(check(a.bundle),indent=2))
