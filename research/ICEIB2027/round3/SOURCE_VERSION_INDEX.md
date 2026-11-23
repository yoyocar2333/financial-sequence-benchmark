# Fixed Source and Reproducibility Index

## Evidence version

`EVIDENCE_VERSION.json` gives the **actual immutable Git commit** cited by the short paper. Before final export it is updated to the third-round evidence commit containing the calibration tables, source code and scientific audit. This commit is a reproducibility anchor; it is not a DOI or independent-validation registration. A subsequent formatting/citation commit may contain the final submission files' authored source without changing scientific evidence.

The preserved second-round manuscript/evidence origin is commit `bfe6ea950b785880dfb48ed0a32e663940a6f11d`. It contains the full original E4c/E5/E6/E9b public tables and the protected Results synthesis; R3 does not overwrite these. The actual8-page baseline PDF has SHA256 `e93c5ad133ddb7dde44c76e80baca55829d82d4313e0c1b9195af2c2812071a3`; matching Word `297d7b3379a71b7d878f3ff4cc7cad91796e3f16ff8ef1c30a6e52a4691aff37`. User clarified there was no separate6-page revised copy.

## Current authored sources

- [PAPER_TEMPLATE.md](PAPER_TEMPLATE.md) → [ICEIB2027_FULL_PAPER.md](ICEIB2027_FULL_PAPER.md) via [builder](../../../scripts/iceib2027_r3_build.py).
- Private baseline Word styles → new editable Word via [DOCX generator](../../../scripts/iceib2027_r3_docx.py); that same Word → PDF through [isolated renderer](../../../scripts/iceib2027_r3_render_pdf.py).
- [CALIBRATION_SOURCE_MANIFEST.csv](tables/CALIBRATION_SOURCE_MANIFEST.csv): actual archived coefficients, probability source hashes, price JSON evidence and method code. Full private replay applies saved coefficients only.
- [Protected source hashes](audits/PROTECTED_SOURCE_HASHES.json):264 original scientific and R2 files unchanged.
- [ARTIFACT_MANIFEST.csv](ARTIFACT_MANIFEST.csv): public authored sources, tables and code digests; no publisher binaries. The manifest excludes itself to avoid a self-hash cycle.

## Public aggregate reproduction

```bash
python -B scripts/iceib2027_r3_validate.py --repo . --bundle research/ICEIB2027/round3
python -B scripts/iceib2027_r3_reproduce.py --repo . --bundle research/ICEIB2027/round3 --out /tmp/ICEIB_R3_NEW
python -B scripts/test_iceib2027.py
```

These compare saved slopes to the source E6 coefficients, validate score/component conservation and regenerate the Markdown byte for byte. They do not recreate private per-date probabilities or fit a model.

## Private archive replay and Word/PDF

```bash
python -B scripts/iceib2027_r3_calibration_audit.py --root /PRIVATE/stock_prediction --repo /PUBLIC/financial-sequence-benchmark --out /PRIVATE/NEW_AUDIT
python -B scripts/iceib2027_r3_docx.py --template /PRIVATE/BASELINE/ICEIB2027_REVISED_FULL_PAPER.docx --bundle research/ICEIB2027/round3 --out /PRIVATE/R3_LAYOUT
python -B scripts/iceib2027_r3_render_pdf.py --out /PRIVATE/R3_LAYOUT --program /EXISTING/LibreOffice/program --registry /EXISTING/LibreOffice/registry
python -B scripts/iceib2027_r3_document_check.py --template /PRIVATE/BASELINE/ICEIB2027_REVISED_FULL_PAPER.docx --bundle research/ICEIB2027/round3 --layout /PRIVATE/R3_LAYOUT
```

Requires existing numpy/pandas/scipy/sklearn, python-docx, PyMuPDF, pdffonts and UNO-enabled LibreOffice; no automatic installation. E9b Ridge no-refit replay uses its archived six coefficient/scaler artifacts; this revision does not execute that fitting path. The main bibliography remains the twelve verified references at the protected source version.

Publisher-template DOCX/PDF remain private under the established template terms. Native Palatino export, author/declaration fields and publication route remain submission checks. No source tag or DOI is fabricated, and no conference submission or merge is performed.
