# Current source and reproduction

Scientific evidence remains pinned to real commit `6f29a9f8375b21ac2894878aa424f12b8d6fa138`. This professor-requested revision changes writing, presentation and author declarations, with no new fit, calibration choice, p-value/CI or2026 evaluation. The original third-round manuscript is commit `0ab251fe002b4c61eb25da8756d6db43062608b8`;291 protected research/previous-revision files remain unchanged.

Current sources: [PAPER_TEMPLATE.md](PAPER_TEMPLATE.md), [ABSTRACT.md](ABSTRACT.md), [author/declaration metadata](audits/AUTHOR_METADATA_AND_DECLARATIONS.json), [builder](../../../scripts/iceib2027_r4_build.py) and [Word generator](../../../scripts/iceib2027_r4_docx.py). The publication artifact manifest hashes current text, code, diagram and aggregate checks, excluding itself to avoid a hash cycle.

```bash
python -B scripts/iceib2027_r4_validate.py --repo . --bundle research/ICEIB2027/round4
python -B scripts/iceib2027_r4_reproduce.py --repo . --bundle research/ICEIB2027/round4 --out /tmp/ICEIB_R4_NEW
python -B scripts/test_iceib2027.py
```

Raw-probability calibration audits and all30 seed coefficients/120 component rows are unchanged in [round3](../round3/CALIBRATION_AUDIT.md). The full eight technical/ten raw-calibrated fusion/twelve development/news families remain in the protected [round2 supplement](../round2/SUPPLEMENTARY_RESULTS.md). Renumbering Results to3.1–3.6 does not change that evidence or the synthesis.

Private layout uses the preserved third-round Word, SHA256 `b16001a15b21f5bc564497ca3f73c4f45b6ff37afff9ed15843f3c994acd2fc1`:

```bash
python -B scripts/iceib2027_r4_docx.py --template /PRIVATE/BASELINE/ICEIB2027_FULL_PAPER.docx --bundle research/ICEIB2027/round4 --out /PRIVATE/R4_LAYOUT
python -B scripts/iceib2027_r4_render_pdf.py --out /PRIVATE/R4_LAYOUT --program /EXISTING/LibreOffice/program --registry /EXISTING/LibreOffice/registry
python -B scripts/iceib2027_r4_document_check.py --template /PRIVATE/BASELINE/ICEIB2027_FULL_PAPER.docx --bundle research/ICEIB2027/round4 --layout /PRIVATE/R4_LAYOUT
```

Existing dependencies only; no installation, training or collection. Word stays editable and is not overwritten through LibreOffice import. The localPDF uses P052 fallback; native-font pagination and final author approval remain submission checks. Publisher-template DOCX/PDF and the private senior paper are not posted online. Self-authored Markdown, diagram, metadata and audit code are public. No main merge or conference submission is performed.
