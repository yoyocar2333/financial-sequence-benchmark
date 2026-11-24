# Format and Page Validation — ICEIB2027 Round 2

## Measured result

**Professor-review rendering: PASS, 8 pages total**, including all figures, tables, back matter and twelve references. Page count is from the actual exported PDF, not word-count estimation. The six-page user baseline remains unchanged and privately preserved. New files are named `ICEIB2027_REVISED_FULL_PAPER.docx` and `.pdf`.

Generated from [the revised source](ICEIB2027_REVISED_FULL_PAPER.md) using the actual user-edited Word as template. DOCX is editable; PDF is exported from that same DOCX, with page fields refreshed. No PDF text patching or return to the long E9b paper is used.

## Template fidelity and rendering

| Check | Result |
| --- | --- |
| Original styles XML compared byte-for-byte with user baseline Word | Identical |
| A4 page geometry and margins | Identical; approximately210×297mm; top24.994/bottom15.998/left12.7/right12.7mm |
| Original font declarations and inherited sizes | Retained, no smaller fonts or narrower margins |
| Body heading/reference styles | Retained; H1 12pt, references9pt; inherited Latin body size not replaced with an invented11pt |
| Paragraph pagination | Keep-with-next on new headings; no orphan section title at page1 foot |
| Native editable equations | Three; full normalized expressions present in PDF, including complete relative-gain denominator |
| Main data tables | Three; captions/table ends on same page; no split table rows |
| Main original figures | Two; zero baseline and complete existing CI range in uncertainty plot |
| Source/PDF consistency |71 source paragraphs and85 distinct scientific decimal tokens checked; table cells also checked against DOCX |
| Fonts in PDF | All embedded, no replacement characters |
| Page fields | Correct1–8 of8 |
| Auxiliary line numbers |11 header/footer paragraphs suppressed; no repeated bottom-left3; body setting retained |
| Text bounds | No outside-page text blocks; formula clipping specifically checked |
| Placeholders | Real baseline author preserved; affiliation/order/correspondence/conference/funding declarations pending; no fake email/date |
| Template examples/review designation | Dummy publication details and “review draft” removed |

The original Word declares Palatino Linotype. That proprietary font is unavailable in the Linux renderer; the review PDF uses installed **P052**, with DejaVu fallback for math/symbols. DOCX retains the actual template declarations and styles and is not saved back through LibreOffice. Consequently **exact native-font export and pagination are still a final submission check**. Eight pages is the measured supplied review PDF, not a claim that every Word installation must paginate identically. No font was extracted from the user's PDF or installed.

## Page-by-page assistant layout review

| Page | Contents checked |
| --- | --- |
|1|Title/real author/pending affiliations;100-word abstract, keywords, integrated contribution; no orphan method heading|
|2|Task, three cohort definitions, full equations1–2; formerly long equation2 shortened without changing definition|
|3|Platt equation3/negative-slope rule, development controls, original resample counts/families, Results overview|
|4|Design diagram plus technical interpretation, correlation/reconstruction explanation, fusion question and effect sizes|
|5|Complete neural summary table, zero-line CI plot, calibration/reliability interpretation and secondary directional exception|
|6|Initialization caveat; news reference/difference table, historical prior and delay/ranking limits|
|7|Cross-experiment synthesis table; consistent discussion and important scientific limitations|
|8|Conclusion, supplement/data/declaration information and all twelve references|

Each final rendered page was visually inspected by the assistant. This is **layout inspection**, not independent human scientific/document QA. Machine detail is in [DOCUMENT_VALIDATION.json](audits/DOCUMENT_VALIDATION.json); provenance/arithmetic is separately checked in [EVIDENCE_VALIDATION.json](audits/EVIDENCE_VALIDATION.json).

## Remaining professor/submission checks

Publication route (provided Engineering Proceedings template versus another ICEIB channel), author list/order/affiliation/corresponding author, conference presentation details, funding/ethics/conflicts, actual submission-system fields/limits and native-font export remain to be confirmed. The original official-source record is preserved in [submission checklist](../ICEIB2027_SUBMISSION_CHECKLIST.md). No IEEE route or indexing guarantee is asserted.

Publisher template and template-formatted binaries stay private under [MDPI terms](https://www.mdpi.com/journal/engproc/instructions). Author-written Markdown, original plots, aggregates, audit results and code are public. No manuscript is submitted or merged in this round.
