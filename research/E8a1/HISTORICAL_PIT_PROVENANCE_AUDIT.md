# 歷史內容版本與時間證據稽核

## 實際結果

真實新原始樣本0；`PILOT_SAMPLE_MANIFEST.csv`0列且狀態BLOCKED；L3／L4各0。文件卡15張不是15篇新聞，官方示例也不是候選貼文。既有E8a數萬列作者資料不轉計成本輪pilot。

## 分級與證據鏈

- L0：時間無法使用；L1：日期／未核實午夜；L2：發布時區timestamp聲明。以上不稱嚴格歷史版本PIT。
- L3：同一record/version的精確內容經獨立歷史capture或經獨立審核的原來源版本紀錄支持，時間不晚於資訊cutoff；足夠早的capture是保守可得上界，不是原首次發布時刻。
- L4：L3之外再有供應商實際arrival證明。source模式與arrival模式分開，較晚到達不能反推來源未公開，較早來源也不能反推供應商已收到。

三類clock不得混淆：歷史公開／capture／arrival、現在retrieval／研究審核、現在研究使用授權有效期。研究授權在今天核准可涵蓋舊資料，無須假設歷史當天已簽合約；反之今日授權不創造舊版本存在的證據。

## 原型檢查

`assess_provenance`不讀資料列自行填的verified=true來升級。外部hash pin指定的registry才可提供證據；驗證原raw bytes與分離text檔、證據artifact、source/record/version/hash綁定、review artifact和使用權利artifact。所有artifact若變更或錯接，拒用。資料時鐘必須有時區；非完整供應商收到時間不得標L4。synthetic永遠不是real as-of eligible。

外部manifest固定、審核人員認證、證據發行者獨立性和時鐘真實性仍需人工／機構保管。hash只能證明檔案一致性；若所有文件在今天自造，數字再一致也不是歷史證據。程式不是簽章PKI、權利審查服務或歷史truth oracle。

Stocktwits事件envelope的time有建立／destroy語意，不能直接當provider received；seq_id是opaque，不能以相鄰數字判斷漏抓。備份不含seq_id，無法僅憑備份現在下載成功證明原arrival／持續監測。Reddit每月最新版本導致created_at早於現版本形成的風險，不能以補延遲一天修復。

## 私有證據儲存與分享

將來如取得授權，原文／原API回應放專案私有儲存，來源權利依約分區；公開只允許aggregate、schema、程式和經允許的不可識別audit。私人record列表、作者／使用者資料、原文與可回復個人內容的索引不公開。刪除要求優先於保留原文的方便：保留允許的最少tombstone與稽核，不把原文抄入immutable log。

目前沒有取得此類真實內容，故沒有可供研究者簽核的真實原始證據包。工程demo獨立命名synthetic，不得改名為PILOT_SAMPLE_MANIFEST。
