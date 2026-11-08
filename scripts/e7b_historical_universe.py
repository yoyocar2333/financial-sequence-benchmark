"""Ex-ante cohort selection from an audited historical security snapshot.

No current ticker list, future survival field, forecast gain or balanced-panel
requirement enters this function. This is an implementation contract; the
licensed/verified historical master needed to run it has not been obtained.
"""
import hashlib
from e7a_pit_contract import utc
STRATA=((10,19),(20,39),(40,59),(70,89))

def select(rows,asof_utc,per_stratum=25,seed=20261106,max_per_SIC2=20):
    ledger=[];eligible=[]
    for item in rows:
        r=dict(item);reasons=[]
        if r.get('historical_snapshot_verified') is not True or r.get('security_identity_verified') is not True:reasons.append('HISTORICAL_IDENTITY_SNAPSHOT_UNVERIFIED')
        try:
            if utc(r['snapshot_available_utc'])>utc(asof_utc):reasons.append('SNAPSHOT_NOT_AVAILABLE_ASOF')
            if not (r['security_valid_from']<=asof_utc[:10]<r['security_valid_to_exclusive']):reasons.append('NOT_ACTIVE_AT_INCEPTION')
            if r['instrument_class']!='US_PRIMARY_COMMON_STOCK':reasons.append('NOT_PRIMARY_US_COMMON_STOCK')
            if r['asof_price_USD']<5 or r['prior60_median_dollar_volume']<1e6:reasons.append('EXANTE_PRICE_OR_LIQUIDITY')
            if r['prior_price_observations']<250 or r['past_published_report_versions']<4:reasons.append('INSUFFICIENT_PAST_HISTORY')
            sic2=int(str(r['SIC_asof']).zfill(4)[:2]);stratum=next((i for i,(a,b) in enumerate(STRATA) if a<=sic2<=b),None)
            if stratum is None:reasons.append('OUTSIDE_FIXED_NONFINANCIAL_STRATA')
        except (KeyError,ValueError,TypeError):reasons.append('MISSING_OR_INVALID_EXANTE_FIELD');stratum=None;sic2=None
        entry={'security_id':r.get('security_id'),'issuer_id':r.get('issuer_id'),'asof_utc':asof_utc,'stratum':stratum,'SIC2':sic2,'eligible':not reasons,'reasons':'|'.join(reasons),'selected':False}
        ledger.append(entry)
        if not reasons:eligible.append((r,entry))
    # One listed equity class per issuer, chosen by prior liquidity, not by a
    # future class conversion or market performance. Ties use stable identity.
    unique={}
    for r,entry in sorted(eligible,key=lambda v:(-v[0]['prior60_median_dollar_volume'],v[0]['security_id'])):
        if r['issuer_id'] in unique:entry['reasons']='OTHER_MORE_LIQUID_CLASS_SAME_ISSUER';entry['eligible']=False
        else:unique[r['issuer_id']]=(r,entry)
    chosen=[];counts={i:0 for i in range(4)};siccounts={}
    for r,entry in sorted(unique.values(),key=lambda v:hashlib.sha256(f'E7Bv2|{seed}|{asof_utc}|{v[0]["security_id"]}'.encode()).hexdigest()):
        i=entry['stratum'];sic=entry['SIC2']
        if counts[i]>=per_stratum or siccounts.get(sic,0)>=max_per_SIC2:continue
        chosen.append(r);entry['selected']=True;counts[i]+=1;siccounts[sic]=siccounts.get(sic,0)+1
    return {'selected':chosen,'selection_ledger':ledger,'counts':counts,'complete_target':all(n==per_stratum for n in counts.values()),'future_survival_used':False,'future_forty_quarter_completion_required':False}
