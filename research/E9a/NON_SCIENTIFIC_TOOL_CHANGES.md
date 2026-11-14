# 公開文件檢查器的限定變更

本輪保留舊有科學成果。唯一變動的既有程式為 `scripts/validate_publication.py`，屬發布工程，不是模型或統計方法。

新增精確白名單只有兩個自製文件：`research/E9a/PAPER_DRAFT.docx` 及 `research/E9a/PAPER_DRAFT.pdf`。仍維持2MB單檔與20MB總量限制；核對文件manifest SHA及品質檢查，拒絕未列文件、雜湊變動、DOCX宏、危險路徑及私人file URI。其他binary、raw資料、checkpoint與完整ZIP原限制不變。新增測試確認額外PDF路徑與未更新pin的竄改均被拒絕。

這是允許本次自製學術文件公開所需的狹窄例外，不是放寬原始資料政策，亦不是把PDF內容檢查當成科學真實性認證。舊研究來源的原SHA及E3c2026凍結協定保持；完整保護數見 `checks/prior_artifact_preservation.json`。
