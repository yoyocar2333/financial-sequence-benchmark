"""Descriptive development-input diagnostics, never H1/H3 forecast inference."""
import datetime as dt,json,os
from pathlib import Path
import numpy as np
import pandas as pd
from e7b_setup import OUT as DEFAULT_OUT,dump
OUT=Path(os.environ.get('E7B_OUTPUT',DEFAULT_OUT)).resolve()

def run(plots=True):
    cohort=pd.read_csv(OUT/'tables/company_PIT_coverage.csv');m=pd.read_csv(OUT/'tables/market_quality_by_company.csv');idx=pd.read_csv(OUT/'tables/filing_index_metadata.csv')
    delays=idx[['prototype_id','accession','period_end','filing_date','accepted_display_local_unverified_timezone','source_url']].copy()
    delays['period_end_to_displayed_acceptance_date_days']=(pd.to_datetime(delays.accepted_display_local_unverified_timezone.str[:10])-pd.to_datetime(delays.period_end)).dt.days
    delays['displayed_clock_after17_unverified_timezone']=delays.accepted_display_local_unverified_timezone.str[11:]>'17:00:00'
    delays['acceptance_display_date_differs_from_filing_date']=delays.accepted_display_local_unverified_timezone.str[:10]!=delays.filing_date
    delays['not_first_earnings_publication_time']=True;delays.to_csv(OUT/'tables/source_timing_diagnostics.csv',index=False)
    streams={};legacy={'CHK_legacy','DELL_legacy','SHLD_legacy','YHOO_legacy'}
    for p in sorted((OUT/'raw/prices').glob('*_historical_sanitized.json')):
        z=json.loads(p.read_text());symbol=z['prototype_id']
        if symbol in legacy:continue
        x=pd.Series(z['indicators']['quote'][0]['close'],index=pd.to_datetime(z['timestamp'],unit='s',utc=True).tz_convert('America/New_York').date.astype(str),name=symbol,dtype=float)
        streams[symbol]=np.log(x).diff()
    data=pd.DataFrame(streams).sort_index().dropna();corr=data.corr();pairs=[]
    for a in corr:
        for b in corr:
            if a<b:pairs.append({'symbol_a':a,'symbol_b':b,'shared_development_dates':len(data),'pearson_vendor_close_logreturn':float(corr.loc[a,b]),'not_forecast_loss_correlation':True,'not_used_for_stock_selection_or_power_gate':True})
    pd.DataFrame(pairs).to_csv(OUT/'tables/diagnostic_price_return_correlations.csv',index=False)
    # A factual share-basis witness; ex-date is not record/payment date.
    z=json.loads((OUT/'raw/prices/AAPL_historical_sanitized.json').read_text());first=min(z['events']['dividends'].values(),key=lambda v:v['date'])
    div={'issuer':'AAPL','issuer_declaration_date':'2012-07-24','issuer_record_date':'2012-08-13','issuer_payment_date':'2012-08-16','issuer_cash_per_historical_share':2.65,'vendor_ex_date_UTC':dt.datetime.fromtimestamp(first['date'],dt.timezone.utc).date().isoformat(),'vendor_cash_amount':first['amount'],'issuer_to_vendor_amount_ratio':2.65/first['amount'],'later_split_multiplier_2014x2020':28,'source_url':'https://investor.apple.com/dividend-history/default.aspx','interpretation':'different share units and different clock meanings; not a cash-dividend discrepancy or cash return test'}
    pd.DataFrame([div]).to_csv(OUT/'tables/cash_dividend_share_basis_witness.csv',index=False)
    stats={'timing_source_documents':len(idx),'display_acceptance_later_than17_clock':int(delays.displayed_clock_after17_unverified_timezone.sum()),'date_mismatch_count':int(delays.acceptance_display_date_differs_from_filing_date.sum()),'median_period_end_to_display_acceptance_days':float(delays.period_end_to_displayed_acceptance_date_days.median()),'correlation_descriptive_symbols':len(streams),'correlation_shared_development_dates':len(data),'median_pairwise_price_return_correlation':float(pd.DataFrame(pairs).pearson_vendor_close_logreturn.median()),'financial_loss_covariance_estimated':False,'source_or_market_PIT_gates_passed':False,'prior_E7a_power_not_refitted':True}
    dump(OUT/'audits/descriptive_diagnostics.json',stats)
    if plots:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.rcParams.update({'font.size':10,'figure.dpi':140,'axes.spines.top':False,'axes.spines.right':False})
        cv=cohort.merge(m[['prototype_id','historical_rows']],on='prototype_id',suffixes=('','_market'))
        columns=['CIK_verified_from_at_least_one_SEC_index','rendered_financial_tables','historical_rows','raw_original_SEC_documents','strict_PIT_eligible_quarters','as_traded_price_verified']
        matrix=np.column_stack([cv[c].astype(float).to_numpy()>0 for c in columns]).astype(int)
        fig,ax=plt.subplots(figsize=(10,7));ax.imshow(matrix,aspect='auto',cmap='Blues',vmin=0,vmax=1)
        ax.set_yticks(range(20),cv.prototype_id);ax.set_xticks(range(6),['SEC index\nidentity','Any rendered\nfinancial page','Vendor historical\narray','Original SEC\nbody','Strict PIT\nquarter','As-traded\ncertified']);ax.set_title('Evidence acquired vs qualification (purposive prototype, not a population sample)')
        for i in range(20):
            for j in range(6):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j] else 'black',fontsize=8)
        fig.tight_layout();fig.savefig(OUT/'figures/evidence_acquisition_vs_qualification.png');plt.close(fig)
        fig,ax=plt.subplots(figsize=(9,6));labels=delays.prototype_id+' '+delays.period_end
        ax.barh(range(len(delays)),delays.period_end_to_displayed_acceptance_date_days,color='#527f9a');ax.set_yticks(range(len(delays)),labels,fontsize=8);ax.invert_yaxis();ax.set(xlabel='Calendar days: period end to displayed SEC acceptance date',title='Source-specific delay; not the first earnings announcement time');fig.tight_layout();fig.savefig(OUT/'figures/period_end_is_not_availability.png');plt.close(fig)
        fig,ax=plt.subplots(figsize=(8,6));im=ax.imshow(corr,vmin=-1,vmax=1,cmap='coolwarm');ax.set_xticks(range(len(corr)),corr.columns,rotation=90);ax.set_yticks(range(len(corr)),corr.columns);ax.set_title('Vendor Close log-return correlation, development2012-2022\nDescriptive only; not H1/H3 loss correlation or PIT certification');fig.colorbar(im,ax=ax);fig.tight_layout();fig.savefig(OUT/'figures/development_price_correlation_diagnostic.png');plt.close(fig)
    print(json.dumps(stats,indent=2));return stats
if __name__=='__main__':run('--no-plots' not in __import__('sys').argv)
