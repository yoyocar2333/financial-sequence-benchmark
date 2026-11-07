"""Fail-closed as-of and raw XBRL prototype. No network, models or holdout reads.

Evidence declarations are validated, not independently authenticated. A rendered
web extract never has the same provenance status as an original SEC HTTP body.
"""
import copy,datetime as dt,decimal,re,xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
from e7a_pit_contract import audit as old_audit,utc

CORE=('revenue_yoy','eps_yoy_symmetric','gross_margin','net_margin','operating_margin','cfo_margin','cash_asset_ratio')
NS={'x':'http://www.xbrl.org/2003/instance','d':'http://xbrl.org/2006/xbrldi'}

def acceptance_utc(raw,zone_verified,fold=None):
    if not zone_verified:raise ValueError('Acceptance clock has no verified timezone evidence')
    naive=dt.datetime.strptime(raw,'%Y%m%d%H%M%S') if re.fullmatch(r'\d{14}',raw) else dt.datetime.fromisoformat(raw)
    if naive.tzinfo is not None:raise ValueError('Expected original local acceptance clock, not relabeled UTC')
    zone=ZoneInfo('America/New_York');candidates=[]
    for f in [0,1]:
        aware=naive.replace(tzinfo=zone,fold=f)
        if aware.astimezone(dt.timezone.utc).astimezone(zone).replace(tzinfo=None)==naive:
            if aware.utcoffset() not in [v.utcoffset() for v in candidates]:candidates.append(aware)
    if not candidates:raise ValueError('Nonexistent DST local clock')
    if len(candidates)>1 and fold is None:raise ValueError('Ambiguous DST local clock; evidence needed')
    chosen=next((v for v in candidates if v.fold==fold),candidates[0])
    return chosen.astimezone(dt.timezone.utc).isoformat()

def strict_audit(record,cutoff,mode='source'):
    if mode not in ('source','arrival'):raise ValueError(mode)
    r=copy.deepcopy(record);reasons=[]
    for field in ['original_SEC_bytes_verified','source_public_clock_verified','amendment_inventory_verified','context_and_units_verified','CIK_from_original_verified']:
        if r.get(field) is not True:reasons.append('UNVERIFIED:'+field)
    if r.get('source_representation')!='ORIGINAL_SEC_BODY':reasons.append('NOT_ORIGINAL_SEC_BODY')
    if r.get('has_dimensions'):reasons.append('SEGMENT_OR_CLASS_CONTEXT_NOT_CONSOLIDATED')
    if not r.get('context_id') or not r.get('fact_concept'):reasons.append('XBRL_CONTEXT_OR_CONCEPT_MISSING')
    try:
        if r.get('period_basis')=='Q':
            days=(dt.date.fromisoformat(r['period_end'])-dt.date.fromisoformat(r['period_start'])).days
            if not 60<=days<=105:reasons.append('ANNUAL_OR_YTD_MISLABELED_AS_QUARTER')
        if r.get('period_basis')=='I' and r.get('period_start'):reasons.append('INSTANT_HAS_DURATION_START')
        if not r.get('inventory_verified_through_utc') or utc(r['inventory_verified_through_utc'])<utc(cutoff):reasons.append('INVENTORY_DOES_NOT_COVER_DECISION')
        if r.get('provider_received_utc'):
            if utc(r['provider_received_utc'])<utc(r['public_available_utc']):reasons.append('PROVIDER_RECEIPT_PRECEDES_SOURCE_CLOCK')
            if utc(r['provider_received_utc'])>utc(r['retrieved_at_utc']):reasons.append('RECEIPT_AFTER_RETRIEVAL')
    except (ValueError,TypeError,KeyError) as e:reasons.append('CLOCK_ERROR:'+str(e))
    if mode=='source':
        # This estimand is certified source-event availability, explicitly not
        # a claim that a historical vendor or this collector had already seen it.
        r.pop('provider_received_utc',None)
    else:
        if not r.get('provider_received_utc') or not r.get('historical_snapshot_verified'):reasons.append('HISTORICAL_PROVIDER_ARRIVAL_UNVERIFIED')
    base=old_audit(r,cutoff);reasons.extend(base['reasons'])
    return {'eligible':not reasons,'reasons':sorted(set(reasons)),'availability_mode':mode,'grade':('SOURCE_EVENT_NOT_COLLECTOR_ARRIVAL' if mode=='source' else 'HISTORICAL_ARRIVAL') if not reasons else 'QUARANTINED','retrieval_is_not_first_seen':True}

def asof_fact(records,cutoff,mode='source'):
    if not records:return None
    keys={(r['issuer_id'],r.get('fact_concept'),r.get('period_start'),r.get('period_end'),r.get('units'),r.get('fiscal_year'),r.get('fiscal_quarter'),r.get('period_basis')) for r in records}
    if len(keys)!=1:raise ValueError('Separate issuer/concept/period/basis/unit before as-of version selection')
    valid=[r for r in records if strict_audit(r,cutoff,mode)['eligible']]
    if not valid:return None
    clock=lambda r:max(utc(r['public_available_utc']),utc(r['provider_received_utc'])) if mode=='arrival' else utc(r['public_available_utc'])
    latest=max(clock(r) for r in valid);same=[r for r in valid if clock(r)==latest]
    if len({str(r['value']) for r in same})>1:raise ValueError('Conflicting equal-time fact versions; do not pick first')
    return max(same,key=lambda r:r['source_document_id'])

def parse_number(text,scale=0,sign=None,transform=None):
    x=''.join(text.split()).replace('\u2212','-').replace('$','')
    if transform in ['numdash','zerodash'] and x in ['-','–','—']:return decimal.Decimal(0)
    if x in ['','-','–','—']:return None
    if transform and transform not in ['num-dot-decimal','numdotdecimal','numcommadot','num-comma-decimal','numcommadecimal','numdotcomma','numdash','zerodash']:
        raise ValueError('Unimplemented inline transformation '+transform)
    if transform in ['num-comma-decimal','numcommadecimal','numdotcomma']:x=x.replace('.','').replace(',','.')
    else:x=x.replace(',','')
    if x.startswith('(') and x.endswith(')'):x='-'+x[1:-1]
    value=decimal.Decimal(x)*decimal.Decimal(10)**int(scale)
    if not value.is_finite():raise ValueError('Nonfinite numeric fact')
    if sign=='-':value=-value
    return value

def parse_xbrl(data,expected_cik):
    """Parse native XML/XHTML iXBRL; retain contexts, units and quarantines.

    It does not infer publication time, fiscal-quarter meaning, or a revision
    chain from numeric contents. HTML needing repair and unsupported transforms
    must be reviewed rather than silently coerced.
    """
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('DTD/entity input refused')
    root=ET.fromstring(data);contexts={};units={};facts=[];errors=[]
    for c in root.findall('.//x:context',NS):
        ident=c.find('x:entity/x:identifier',NS);p=c.find('x:period',NS)
        if ident is None or p is None:errors.append({'context':c.get('id'),'reason':'missing_entity_or_period'});continue
        ci=(ident.text or '').strip();instant=p.find('x:instant',NS);start=p.find('x:startDate',NS);end=p.find('x:endDate',NS)
        contexts[c.get('id')]={'entity_cik':ci,'CIK_matches_expected':ci.isdigit() and int(ci)==int(expected_cik),'period_start':start.text if start is not None else None,'period_end':instant.text if instant is not None else end.text if end is not None else None,'period_kind':'instant' if instant is not None else 'duration','has_dimensions':any(e.tag.endswith(('explicitMember','typedMember')) for e in c.iter())}
    for u in root.findall('.//x:unit',NS):
        measures=[e.text for e in u.findall('x:measure',NS)];div=u.find('x:divide',NS)
        if div is not None:
            measures=['/'.join(['*'.join(e.text or '' for e in div.findall('x:unitNumerator/x:measure',NS)),'*'.join(e.text or '' for e in div.findall('x:unitDenominator/x:measure',NS))])]
        units[u.get('id')]='*'.join(measures)
    for e in root.iter():
        context=e.get('contextRef')
        if not context or not e.get('unitRef'):continue
        name=e.get('name') if e.tag.endswith('nonFraction') else e.tag
        raw=''.join(e.itertext());nil=e.get('{http://www.w3.org/2001/XMLSchema-instance}nil') in ['true','1']
        try:
            if e.get('continuedAt'):raise ValueError('Continued numeric fact requires explicit continuation handling')
            val=None if nil else parse_number(raw,e.get('scale','0'),e.get('sign'),(e.get('format') or '').split(':')[-1] or None)
            if context not in contexts or e.get('unitRef') not in units:raise ValueError('Unknown context/unit')
            f={'fact_concept':name,'context_id':context,'unit_id':e.get('unitRef'),'units':units[e.get('unitRef')],'value':str(val) if val is not None else None,'raw_display':raw,'decimals':e.get('decimals'),**contexts[context]}
            if not f['CIK_matches_expected']:errors.append({'context':context,'reason':'ENTITY_CIK_MISMATCH'})
            facts.append(f)
        except (ValueError,decimal.InvalidOperation) as err:errors.append({'context':context,'fact_concept':name,'reason':str(err)})
    return {'facts':facts,'errors':errors,'contexts':contexts,'units':units,'source_time_verified_by_parser':False}

def latest_features(records,cutoff,mode='source'):
    """Seven E7 candidate ratios from verified, fiscal-aligned normalized facts.

    Input concept keys are revenue, diluted_eps, gross_profit, net_income,
    operating_income, cfo, cash and assets; their accounting mapping must already
    be reviewed. Annual facts cannot be relabeled as quarterly observations.
    """
    if len({r['issuer_id'] for r in records})>1:raise ValueError('One issuer per feature as-of query')
    groups={}
    for r in records:
        key=(r['issuer_id'],r['fact_concept'],r.get('period_start'),r['period_end'],r['units'],r.get('fiscal_year'),r.get('fiscal_quarter'),r.get('period_basis'))
        groups.setdefault(key,[]).append(r)
    valid=[asof_fact(v,cutoff,mode) for v in groups.values()];valid=[v for v in valid if v and v.get('value') is not None]
    quarters=[v for v in valid if v.get('period_basis')=='Q' and v.get('fiscal_quarter') in [1,2,3,4]]
    result={k:None for k in CORE};reasons={k:'NO_VERIFIED_QUARTERLY_INPUT' for k in CORE};lineage={}
    if not quarters:return {'values':result,'missing_reasons':reasons,'lineage':lineage}
    end=max(v['period_end'] for v in quarters)
    if (utc(cutoff).date()-dt.date.fromisoformat(end)).days>370:return {'values':result,'missing_reasons':{k:'STALE_OVER370DAYS' for k in CORE},'lineage':lineage}
    recent=[v for v in valid if v['period_end']==end];anchor=next(v for v in quarters if v['period_end']==end)
    def pick(concept,pool=recent,basis='Q'):
        x=[v for v in pool if v['fact_concept']==concept and v.get('period_basis')==basis]
        if len(x)!=1:return None
        return x[0]
    def ratio(name,numerator,denominator,minus_one=False):
        if not numerator or not denominator:return
        if numerator['units']!=denominator['units']:reasons[name]='UNIT_MISMATCH';return
        if not minus_one and (numerator.get('period_start'),numerator['period_end'])!=(denominator.get('period_start'),denominator['period_end']):reasons[name]='PERIOD_MISMATCH';return
        den=float(denominator['value'])
        if den==0:reasons[name]='ZERO_DENOMINATOR';return
        result[name]=float(numerator['value'])/den-(1 if minus_one else 0);reasons[name]='';lineage[name]=[numerator['source_document_id'],denominator['source_document_id']]
    rev=pick('revenue');prior=[v for v in valid if v.get('fiscal_year')==anchor.get('fiscal_year',0)-1 and v.get('fiscal_quarter')==anchor.get('fiscal_quarter')]
    ratio('revenue_yoy',rev,pick('revenue',prior),True)
    eps=pick('diluted_eps');old=pick('diluted_eps',prior)
    if eps and old:
        if eps['units']!=old['units']:reasons['eps_yoy_symmetric']='UNIT_MISMATCH'
        elif not eps.get('per_share_basis_id') or eps.get('per_share_basis_id')!=old.get('per_share_basis_id'):reasons['eps_yoy_symmetric']='UNVERIFIED_SPLIT_OR_PER_SHARE_BASIS'
        else:
            a=float(eps['value']);b=float(old['value']);den=abs(a)+abs(b)
            if den:result['eps_yoy_symmetric']=2*(a-b)/den;reasons['eps_yoy_symmetric']='';lineage['eps_yoy_symmetric']=[eps['source_document_id'],old['source_document_id']]
    for name,num in [('gross_margin','gross_profit'),('net_margin','net_income'),('operating_margin','operating_income')]:ratio(name,pick(num),rev)
    cfo=pick('cfo');crev=rev
    if cfo is None:cfo=pick('cfo',basis='YTD');crev=pick('revenue',basis='YTD')
    if cfo and crev and cfo.get('period_start')!=crev.get('period_start'):reasons['cfo_margin']='YTD_OR_DURATION_MISMATCH'
    else:ratio('cfo_margin',cfo,crev)
    ratio('cash_asset_ratio',pick('cash',basis='I'),pick('assets',basis='I'))
    return {'values':result,'missing_reasons':reasons,'lineage':lineage,'asof_period_end':end}

def security_at(master,security_id,valid_date,knowledge_cutoff):
    rows=[r for r in master if r['security_id']==security_id and r['valid_from']<=valid_date<r['valid_to_exclusive'] and utc(r['known_from_utc'])<=utc(knowledge_cutoff)]
    if not rows:return None
    if len({(r['issuer_id'],r['security_id'],r['ticker']) for r in rows})>1:raise ValueError('Ambiguous effective/knowledge-time security identity')
    return max(rows,key=lambda r:utc(r['known_from_utc']))

def executable_wealth_return(entry_date,exit_date,entry_open,exit_close,actions,security_id):
    """Synthetic/authorized as-traded accounting; never assume delisting=zero.

    Actions on entry ex-date confer no dividend to an opening buyer. Combined
    actions require explicit post-split-share dividend units. No price inference.
    """
    if entry_open<=0 or entry_date>exit_date:raise ValueError('Invalid entry or dates')
    shares=1.;cash=0.;terminated=False
    events=[a for a in actions if a['security_id']==security_id and entry_date<a['effective_date']<=exit_date]
    for a in sorted(events,key=lambda v:(v['effective_date'],{'split':0,'cash_dividend':1,'delisting':2}.get(v['kind'],99))):
        if not a.get('source_verified'):raise ValueError('Unverified corporate action')
        if terminated:raise ValueError('Action after security termination')
        if a['kind']=='split':
            if a['ratio']<=0:raise ValueError('Invalid split ratio')
            shares*=a['ratio']
        elif a['kind']=='cash_dividend':
            if a.get('amount_basis')!='post_split_share':raise ValueError('Dividend share basis unknown')
            cash+=shares*a['amount']
        elif a['kind']=='delisting':
            if a.get('settlement_per_share') is None:raise ValueError('Unknown delisting settlement, not zero')
            cash+=shares*a['settlement_per_share'];shares=0.;terminated=True
        else:raise ValueError('Unsupported corporate action')
    if not terminated and exit_close is None:raise ValueError('No tradable exit/settlement')
    return (cash+shares*(exit_close or 0))/entry_open-1
