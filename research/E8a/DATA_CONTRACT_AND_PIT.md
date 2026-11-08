# E8a資料契約與品質檢查

所有檢查分開：文字版本、來源時鐘、供應商時鐘、語意模型與特徵時鐘、來源觀測完整度、公司相關性、合法研究使用、驗證獨立性。不用單一pit=true遮蔽缺失。

## 必要欄位

| 群組 | 欄位／證據 |
|---|---|
| 文件與表示 | source、dataset_revision、record_id、canonical URL hash、精確text hash、full/summary/title/repost/thread、parent/version_id |
| 時間 | 原始發布字串、時區／精度、edited_at、版本公開時點或獨立capture、provider_arrival、retrieved_at |
| 證據 | 原HTTP／API bytes hash、擷取時間、不可變版本、時鐘語意文件、獨立核對紀錄；工具轉出hash不能冒充HTTP原檔hash |
| 觀測 | 固定股票／cashtag／alias查詢、頁次／cursor、EOF、查詢範圍、停機／缺漏／限流／補抓記錄、source universe版本 |
| 語意模型 | model identifier/revision、release或訓練截止證據、prompt、input text hash、inference_finished、cache及抽取品質 |
| 使用與刪除 | 資料用途／授權範圍、來源刪除／withdrawal與合規紀錄、只允許的再散布；不保存不必要個資 |

L1/L2只是發布proxy。L3須獨立證據綁定**同一歷史內容版本**，可用有證據的public-version時間或足夠早的歷史capture；無歷史arrival時只稱source PIT，不能稱vendor-arrival PIT。L4再要求arrival。當前抓取不會反推過去first_seen；未核對的來源聲明和CSV字串True不認證。

`e8a_core.py`接收的verified欄位必須來自獨立審核證據登錄，不是可自填的資格。E8a匯入路徑不提供自動升級：所有未取得證據欄位空白／false。合成測試中的True只是工程fixture，不能算歷史合格記錄。未實作全自動證據真偽鑑定；將來匯入L3前仍需原始證據hash綁定與人工簽核。

發布日期型資料採嚴格晚於所列日期的下一個實際股票交易日；日內聲明採17NY cutoff。DST、假日及年底依原始完整行情calendar，**不依purged evaluation rows計算**。延後1/2交易日只是敏感度，不補回內容修訂或當時模型權重的證據。事件label與特徵不得跨資料切分，不把label成熟日當特徵日。

`feature_ready`只檢查「當時實際產出」的部署clock。離線回溯另可採固定歷史可得語意模型在合格舊文本重算，但必須揭露，不可把晚出現的Gemini知識當原年可得資訊。

社群歷史likes/reposts/followers若沒有當時快照，禁止進主特徵。對tweets/posts的刪除、帳號存活和不同ID命名空間分開稽核；不還原個人身分。去重需保留發布與修訂鏈，一文多股以同一文件cluster處理依賴。

監測coverage = 有可稽核固定查詢、翻頁完整與收集狀態的session / 預先指定session。Retained article dates及新聞窗口重合不能代替這個分母；沒有ledger就NA。當來源缺席不得補sentiment=0或news_count=0；零只在已證明來源觀測完整的日子才有真正no-news意義。
