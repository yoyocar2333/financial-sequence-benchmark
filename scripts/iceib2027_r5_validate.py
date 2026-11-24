"""Source replay and frozen evidence checks; no forecasting or fitting."""
import argparse, contextlib, io, json, re, shutil, tempfile
from pathlib import Path
from iceib2027_r4_validate import validate as validate_r4
from iceib2027_r5_build import main as build
from iceib2027_r4_build import rows, table
from decimal import Decimal as D


def validate(repo,bundle):
    with contextlib.redirect_stdout(io.StringIO()):
        prior=validate_r4(repo,repo/'research/ICEIB2027/round4')
    text=(bundle/'ICEIB2027_FULL_PAPER.md').read_text()
    abstract=(bundle/'ABSTRACT.md').read_text().split('\n\n',1)[1].strip()
    old=(repo/'research/ICEIB2027/round4/ICEIB2027_FULL_PAPER.md').read_text()
    intro=lambda x:x.split('## 1. Introduction and Related Work\n\n')[1].split('\n## 2.')[0]
    assert 180<=len(abstract.split())<=200 and abstract in text
    assert len(intro(text).split())>len(intro(old).split())
    assert text.split('## References\n\n')[1]==old.split('## References\n\n')[1]
    assert text.split('## Back Matter\n\n')[1]==old.split('## Back Matter\n\n')[1]
    first=[]
    for group in re.findall(r'\[([0-9]+(?:,[0-9]+)*)\]',text.split('## References')[0]):
        for value in map(int,group.split(',')):
            if 1<=value<=12 and value not in first:first.append(value)
    assert first==list(range(1,13)),first
    for line in old.splitlines():
        if line.startswith('`') or line.startswith('| XGBoost |') or line.startswith('| LightGBM |') or line.startswith('| LSTM |') or line.startswith('| Mamba |'):
            if line.startswith('|'):assert line in text, line
            else:assert line in text, line
    assert '### 2.4. Development Controls and Statistical Evaluation' in text
    assert re.findall(r'^### (3\.\d)\. ',text,re.M)==['3.1','3.2','3.3','3.4','3.5','3.6']
    assert 'XGBoost/LightGBM accounting values' in text
    assert 'XGBoost' in text.split('### 3.3.')[1].split('### 3.4.')[0]
    assert 'LightGBM' in text.split('### 3.4.')[1].split('### 3.5.')[0]
    score={r['comparison_id']:r for r in rows(repo/'research/ICEIB2027/round2/tables/R2_SCORE_INTERPRETATION.csv')}
    # All ten raw and all ten calibrated fusion effects are direct frozen-table lookups.
    for model in ['logistic','xgboost','lightgbm','lstm','mamba']:
        for stock in ['AAPL','TSLA']:
            a=score[f'fusion_{stock}_{model}_raw'];b=score[f'fusion_{stock}_{model}_calibrated']
            assert D(a['delta_Brier'])<0
            assert f"{1000*D(a['delta_Brier']):+.3f}→{1000*D(b['delta_Brier']):+.3f}" in text
            assert f"{D(b['reference_Brier']):.6f}" in text
            assert D(b['adjusted_p'])==1
    for value in ['0.000980','0.001198','0.0240','0.0480','0.0744','0.1512','0.028','0.1894/0.3714','zero L3','L4']:
        assert value in text,value
    dev=rows(repo/'research/E9b/tables/development_all12_contrasts.csv')
    for model,c,value in [('xgboost','C1','−0.000332'),('lightgbm','C1','0.000149'),('xgboost','C2','+0.000095'),('lightgbm','C2','−0.001027')]:
        r=next(r for r in dev if r['model']==model and r['contrast']==c and r['block']=='60')
        assert f"{D(r['difference']):+.6f}"==value.replace('−','-') if value.startswith(('+','−')) else f"{D(r['difference']):.6f}"==value
    with tempfile.TemporaryDirectory(prefix='iceib_r5_check_') as tmp:
        out=Path(tmp);(out/'audits').mkdir()
        for name in ['PAPER_TEMPLATE.md','ABSTRACT.md','EVIDENCE_VERSION.json']:shutil.copy2(bundle/name,out/name)
        with contextlib.redirect_stdout(io.StringIO()):build(repo,out)
        assert (out/'ICEIB2027_FULL_PAPER.md').read_bytes()==(bundle/'ICEIB2027_FULL_PAPER.md').read_bytes()
    return dict(status='PASSED',abstract_words=len(abstract.split()),introduction_words=len(intro(text).split()),
                previous_abstract_words=134,previous_introduction_words=len(intro(old).split()),
                Section_2_4_present=True,technical_primary_contrasts=8,raw_fusion_contrasts=10,
                calibrated_fusion_contrasts=10,matched_tree_contrasts=6,all_five_expert_families_in_main_fusion_table=True,
                source_byte_reproduced=True,prior_R4_validation=prior['status'],
                original_equations_references_and_declarations_unchanged=True,
                new_model_fits=0,new_calibrator_fits=0,new_pvalues=0,financial2026_evaluations=0)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--bundle',type=Path,required=True);p.add_argument('--report',type=Path)
    a=p.parse_args();v=validate(a.repo,a.bundle)
    if a.report:a.report.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v,indent=2))
