# 資料層與欄位字典

- `cohort_locked.csv`：20個目的性prototype ID及候選CIK／產業組，鎖定前不是已驗證歷史母體。初始PENDING旗標保留不回改；後驗查核另列company表的verified欄。
- `filing_index_metadata.csv`：21個唯一accession、SEC index來源、filing／period date及Accepted原顯示鐘面。`accepted_display_local_unverified_timezone`不等於已認證UTC；provider received未知留空。
- `SEC_listed_artifact_manifest.csv`：官方索引列出的文件名、type、sequence、大小與預計URL。列示不等於檔案已下載；`file_retrieved_as_original=False`。
- `source_manifest.csv`：所有web來源／discovery與價格HTTP記錄。`extract_file_sha256`只驗證工具轉出檔；不填入原SEC body hash。web的retrieval_recorded是本次工具回應保存時間，非上游首次HTTP抓取；工具Crawled也不是當年first-seen。Yahoo原envelope SHA是真實回應hash，但原envelope隔離，不作歷史可得或SEC原文證明。
- `rendered_display_observations.csv`：90個候選顯示列，保留source URL／label／display cells；沒有自動聲稱其period、unit、taxonomy context或數值與原XML認證。不混入normalized facts。
- `market_quality_by_company.csv`及year表：17個symbol成功、3個HTTP失敗；歷史array與CIK／security歸屬分開。quote Close不是已認證as-traded。數值格式檢查不等於99.9%回報對帳。
- `company_calendar_quarter_coverage.csv`：880個名義日曆格，membership與完整申報清單未知；`strict_eligible_core_cells=0`指目前沒有合格輸入，不是公司0營收或沒有財報。
- `derived/normalized_verified_facts.json`與`authenticated_source_registry.json`：當前`[]`／`{}`，沒有把顯示觀測、合成樣本或缺失塞成真facts。
- `derived/asof_strict_calendar_queries.csv`：各公司44個季末17:00紐約時間（DST轉UTC）查詢，週末等尚非核對交易日。七特徵null及拒用原因；新版輸出為`derived/asof_build_v1_1/`。
- `asof_rejection_trace.csv`：每query因缺原始認證輸入而拒用；未獲資料不是經濟0。不以當年財年結束日作public時點。
- `quality_gates.csv`與`manual_document_QA_gate.csv`：200人工作業未完成、agreement不可評估；不因沒有受檢資料就填100%一致或0錯誤合格。
- `diagnostic_price_return_correlations.csv`：16個非legacy查詢代號的split-adjusted Close log報酬配對相關；不是預測損失相關／母體ICC。
- `cash_dividend_share_basis_witness.csv`：來源amount單位與declaration／record／ex／payment不同；沒有計算投資績效。
- `six_contrast_variance_feasibility.csv`：沿用E7a C1–C6，真變異／依賴／尺寸均null與NOT_ESTIMABLE。

raw web extract可讀與否不能推論公司是否披露；原SHA與轉出SHA、source public與vendor received、retrieval與historical first-seen分開。`source_event`可得模式不宣稱當年collector已收到；`arrival`模式需額外歷史received證明。合成測試全部以SYNTHETIC ID標示，永不計入20家資料。

解析器支援原生XBRL XML及well-formed XHTML iXBRL的有限數值transform、scale、sign、nil、entity、period與units；DTD／entity、continued numeric及未知格式拒用。並非完整SEC taxonomy mapping／HTML修復／quarter reconstruction產品；其輸出不會自動認證發布時間或修訂歷史。
