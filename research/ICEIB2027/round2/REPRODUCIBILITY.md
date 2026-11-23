# Round 2 Reproduction

The active conference source is registered in [ACTIVE_MANUSCRIPT.json](../ACTIVE_MANUSCRIPT.json). The old conference Markdown remains a preserved baseline; original E9b is evidence, not the current short-paper source. Older conference CLI entry points now resolve round2, so rebuilding does not silently restore the earlier text. Imported historical functions remain for baseline regression checks.

## Public offline evidence and editorial replay

Requires existing Python3, numpy/pandas and matplotlib for figures. No raw market/news inputs, model fitting, new statistical resampling or network access.

```bash
python -B scripts/iceib2027_r2_validate.py --repo . --bundle research/ICEIB2027/round2
python -B scripts/iceib2027_r2_reproduce.py --repo . --bundle research/ICEIB2027/round2 --out /tmp/ICEIB_R2_REPLAY_NEW --figures
python -B scripts/test_iceib2027.py
```

Validation checks596 original rows, exact SHA/row selectors,73 descriptive differences/percentages, all original comparison families,237 protected source hashes,100-word abstract and twelve inherited references. Replay regenerates the manuscript, main/supplementary tables and original plots, checking byte identity. It does not certify historical PIT, independent human review or new predictive ability.

## Private Word and PDF

The revised Word uses the **actual user-supplied six-page baseline Word**, SHA256 `0435ab6f50a61dc311bcda094133bc92f770ef382e37b84147ef9ce51299a31a`. Its original table/equation samples are located by style, avoiding assumptions about numeric table indices after human editing. Styles, font sizes, A4 geometry and body line-number settings are retained. Local paragraph keep-with-next avoids orphan headings; auxiliary header/footer line numbers are suppressed.

```bash
python -B scripts/iceib2027_r2_docx.py --template /PRIVATE/BASELINE/ICEIB2027_FULL_PAPER.docx --bundle research/ICEIB2027/round2 --out /PRIVATE/ICEIB_R2_LAYOUT
python -B scripts/iceib2027_r2_render_pdf.py --out /PRIVATE/ICEIB_R2_LAYOUT --program /EXISTING/LibreOffice/program --registry /EXISTING/LibreOffice/registry
python -B scripts/iceib2027_r2_document_check.py --template /PRIVATE/BASELINE/ICEIB2027_FULL_PAPER.docx --bundle research/ICEIB2027/round2 --layout /PRIVATE/ICEIB_R2_LAYOUT
```

UNO-enabled Python, python-docx, PyMuPDF and pdffonts must already be installed. Renderer updates PAGE/NUMPAGES and exports PDF without saving the imported Word over the source. It creates only its isolated application profile. No automatic installation or system change is performed.

The local review PDF uses installed P052 for unavailable Palatino Linotype, with explicit private fontconfig. DOCX retains the original Palatino declaration and inherited sizes. The final official-font Word export must be rechecked before actual submission; this8-page PDF is the measured review rendering, not a guarantee of all renderer pagination.

Publisher template and all template-formatted DOCX/PDF files remain private under the [MDPI template terms](https://www.mdpi.com/journal/engproc/instructions). GitHub includes author-written text, original figures, aggregate evidence and code only. The six-page baseline is hash-recorded rather than uploaded. See [format checks](FORMAT_AND_PAGE_VALIDATION.md) and [integrity supplement](SUPPLEMENTARY_INTEGRITY.md).
