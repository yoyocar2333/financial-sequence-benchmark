"""Extend exposition and restore all five expert families from frozen aggregate scores."""
import argparse, contextlib, io, json, shutil, tempfile
from pathlib import Path
from decimal import Decimal as D
from iceib2027_r4_build import rows, table, main as previous_build


def main(repo, bundle):
    source = repo / 'research/ICEIB2027/round2/tables/R2_SCORE_INTERPRETATION.csv'
    byid = {r['comparison_id']: r for r in rows(source)}
    values = []
    for model, name in [('logistic', 'Logistic'), ('xgboost', 'XGBoost'),
                        ('lightgbm', 'LightGBM'), ('lstm', 'LSTM'), ('mamba', 'Mamba')]:
        row = [name]
        for stock in ['AAPL', 'TSLA']:
            raw = byid[f'fusion_{stock}_{model}_raw']
            cal = byid[f'fusion_{stock}_{model}_calibrated']
            row += [f"{D(cal['reference_Brier']):.6f}",
                    f"{1000*D(raw['delta_Brier']):+.3f}→{1000*D(cal['delta_Brier']):+.3f}"]
        values.append(row)
    full = table(['Price expert', 'AAPL ref.', 'AAPL raw→cal.',
                  'TSLA ref.', 'TSLA raw→cal.'], values)
    template = (bundle / 'PAPER_TEMPLATE.md').read_text().replace('{{ALL_FUSION_TABLE}}', full)
    with tempfile.TemporaryDirectory(prefix='iceib_r5_build_') as tmp:
        work = Path(tmp); (work/'audits').mkdir()
        (work/'PAPER_TEMPLATE.md').write_text(template)
        for name in ['ABSTRACT.md', 'EVIDENCE_VERSION.json']:
            shutil.copy2(bundle/name, work/name)
        with contextlib.redirect_stdout(io.StringIO()): previous_build(repo, work)
        shutil.copy2(work/'ICEIB2027_FULL_PAPER.md', bundle/'ICEIB2027_FULL_PAPER.md')
        metadata = json.loads((work/'audits/MANUSCRIPT_METADATA.json').read_text())
    text = (bundle/'ICEIB2027_FULL_PAPER.md').read_text()
    intro = text.split('## 1. Introduction and Related Work\n\n')[1].split('\n## 2.')[0]
    metadata.update(stage='ICEIB2027_R5', introduction_words=len(intro.split()),
                    fusion_settings=10, standalone_abstract=True, main_figures=0, supplementary_design_figures=1)
    (bundle/'audits/MANUSCRIPT_METADATA.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--bundle',type=Path,required=True); a=p.parse_args(); main(a.repo,a.bundle)
