# Current revision

Current manuscript and CLI generation use round2; see [round2 reproduction](round2/REPRODUCIBILITY.md). The historical instructions below describe the preserved first-round source. Current Word generation requires the actual user six-page Word specified in the round2 baseline record; do not substitute the unedited publisher sample.

# Reproduction scopes

## Public, offline synthesis

Requires existing Python, pandas/numpy and (for figures) matplotlib. No raw financial inputs, model fitting or network request.

```bash
python -B scripts/iceib2027_validate.py --repo . --bundle research/ICEIB2027
python -B scripts/test_iceib2027.py
python -B scripts/iceib2027_reproduce.py --repo . --bundle research/ICEIB2027 --out /tmp/iceib2027_replay_NEW --figures
```

The builder uses the current source template, frozen E9b aggregates and verified bibliography. It checks source rows and hashes and recreates author-written Markdown, claim ledger and figures. Original E9b files are read only.

## Private template layout

A lawfully supplied private template is required, SHA256 `184bc15210ba3cc7a9db2540c9eb5661fe982a9b678c786692cd818819db4eda`. The original is not distributed. Use a private output outside this Git checkout. Existing python-docx is required.

```bash
python -B scripts/iceib2027_docx.py --template /PRIVATE/PATH/Engineering_proceedings_Template.docx --bundle research/ICEIB2027 --out /PRIVATE/PATH/iceib2027_layout
```

Existing LibreOffice UNO and fonts are needed for PDF conversion; no automatic installation. `iceib2027_render_pdf.py` takes `--out`, `--program` and optional `--registry`, exports the generated DOCX and refreshes page fields without rewriting its original styles. A local FONTCONFIG_FILE mapped unavailable Palatino to installed P052 for review only. Native Palatino remains a final-submit check.

```bash
python -B scripts/iceib2027_render_pdf.py --out /PRIVATE/PATH/iceib2027_layout --program /PATH/TO/EXISTING/libreoffice/program
python -B scripts/iceib2027_document_check.py --template /PRIVATE/PATH/Engineering_proceedings_Template.docx --bundle research/ICEIB2027 --layout /PRIVATE/PATH/iceib2027_layout
```

The document checker needs existing PyMuPDF and pdffonts. Metadata transport checks are separate explicit operations, not part of replay. `iceib2027_source_check.py` is limited to conference/publisher format pages; raw HTML/templates remain private and embedded base64 must be omitted from public evidence. None of these checks performs historical PIT qualification or independent human scientific QA.
