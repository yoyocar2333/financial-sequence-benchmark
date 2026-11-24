# ICEIB 2027 — professor follow-up revision

Current [paper](ICEIB2027_FULL_PAPER.md), [194-word abstract](ABSTRACT.md), [three-request response](PROFESSOR_FOLLOWUP_RESPONSE.md) and [supplementary diagram/evidence](SUPPLEMENTARY_DESIGN_AND_EVIDENCE.md).

Source template: [PAPER_TEMPLATE.md](PAPER_TEMPLATE.md). Build from unchanged aggregate tables with [builder](../../../scripts/iceib2027_r5_build.py); [source/evidence check](../../../scripts/iceib2027_r5_validate.py), [replay](../../../scripts/iceib2027_r5_reproduce.py), [Word/abstract generator](../../../scripts/iceib2027_r5_docx.py), [PDF renderer](../../../scripts/iceib2027_r5_render_pdf.py) and [layout check](../../../scripts/iceib2027_r5_document_check.py).

```bash
python -B scripts/iceib2027_r5_validate.py --repo . --bundle research/ICEIB2027/round5
python -B scripts/iceib2027_r5_reproduce.py --repo . --bundle research/ICEIB2027/round5 --out /tmp/ICEIB_R5_NEW
python -B scripts/test_iceib2027.py
```

Use existing dependencies. Private Word/PDF export additionally needs the preserved user R4 Word with SHA256 in [baseline record](audits/BASELINE_RECORD.json), python-docx/PyMuPDF, and existing LibreOffice/UNO. The current aggregate-only replay needs no financial data, network, model fitting or GPU.

```bash
python -B scripts/iceib2027_r5_docx.py --template /PRIVATE/R4/ICEIB2027_FULL_PAPER.docx --bundle research/ICEIB2027/round5 --out /PRIVATE/R5
python -B scripts/iceib2027_r5_render_pdf.py --out /PRIVATE/R5 --program /EXISTING/LibreOffice/program --registry /EXISTING/LibreOffice/registry
python -B scripts/iceib2027_r5_document_check.py --template /PRIVATE/R4/ICEIB2027_FULL_PAPER.docx --bundle research/ICEIB2027/round5 --layout /PRIVATE/R5
```

No third-party template/formatted binaries, private raw data or senior example is redistributed. The author-supplied metadata and confirmed declarations remain unchanged. Publisher route, final author approval, portal fields and native-font pagination remain submission checks; this is a professor-review package.
