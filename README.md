# Financial Sequence Benchmark — E0–E7b

以AAPL、TSLA為主，研究從隔日股價預測、波動幅度、多尺度趨勢／反轉，到新聞條件與投資者技術分析的可辨識資訊。這是可稽核的研究基準，不預設複雜模型、均值回歸或新聞一定有效。

**整體結果：個別設定有數值改善，但尚未建立跨股票、通過主要多重比較校正且具有同市場狀態排序能力的穩定優勢。2024–2025為已反覆檢視的探索性樣本；2026獨立驗證未執行。**

## 研究路徑

| 階段 | 任務／主要指標 | 方法與主要發現 |
|---|---|---|
| [E0](research/E0/README.md) | 隔日價格／2025-11 MAPE | 保留六模型notebook及既有結果；Naive AAPL .6766%、TSLA 2.6378% |
| [E1–E2](research/E1_E2/README.md) | 隔日絕對log報酬／MAE、RMSE | 真Mamba五seed；加波動特徵MAE僅改善約.42%／.09%，未顯著 |
| [E3a](research/E3a/README.md) | 多尺度急漲跌事件 | AAPL／TSLA反轉與延續不同；主要事件檢定無顯著發現 |
| [E3b](research/E3b/README.md) | 全日期h5反轉／Brier | XGBoost、LightGBM、LSTM、Mamba；趨勢特徵效果跨股不一致 |
| [E3c](research/E3c/README.md) | 事件條件反轉／同狀態排序 | 整體AUC提高不等於時機辨識；8組新方法未通過聯合標準 |
| [E4a](research/E4a/README.md) | 新聞覆蓋與PIT可行性 | 找回52摘要／36 Gemini；不足以支持長期新聞模型 |
| [E4b](research/E4b/README.md) | 歷史新聞恢復與來源品質 | 重建448篇Apple全文；回溯頁面不等於當年PIT |
| [E4c](research/E4c/README.md) | AAPL新聞增量預測 | 2025僅65事件；Logistic情緒增益p=.1512，未證明可靠排序 |
| [E5](research/E5/README.md) | Investor-Inspired Hybrid | 技術規則＋四架構＋狀態Hybrid；8個主要特徵增益均未顯著 |
| [E6](research/E6/README.md) | 基本面資訊與融合 | 反轉H1 0/8、H3 0/20；目前來源未達嚴格PIT |
| [E7a](research/E7a/README.md) | 論文設計與驗證規劃 | 資訊／metadata／校準／收縮六控制；協定候選未註冊，尚缺跨股PIT及獨立驗證 |
| [E7b](research/E7b/README.md) | 20公司PIT資料原型 | 索引／身分／價格調整稽核；嚴格合格季度0，未進入正式推論 |

E0的MAPE、E1的報酬百分點與E3–E5的Brier不能直接橫向排名。E3a收盤至收盤、E3b後next-open標籤、E4c的2023／2024／2025切分也不能混用。[跨實驗摘要](docs/RESEARCH_SUMMARY_ZH_TW.md)整理具體數字與限制。

## 快速重現公開結果（CPU，不訓練、不下載行情）

```bash
python -m venv .venv-public
.venv-public/bin/python -m pip install -r requirements/public-cpu.txt
.venv-public/bin/python scripts/reproduce_public.py --output-dir outputs/public_replay
.venv-public/bin/python -m unittest discover -s tests -p 'test_public*.py' -v
.venv-public/bin/python scripts/validate_publication.py
```

此流程驗證公開CSV的核心結論、重新計算E1五seed平均與SD、重建主要比較圖；不宣稱只憑彙整表已重現所有bootstrap或GPU訓練。完整模型重現需自行合法取得[凍結行情雜湊](docs/FROZEN_INPUTS.csv)所對應資料；新聞研究另需可授權語料。[完整重現說明](docs/REPRODUCIBILITY.md)。

## 新聞研究的分工

[stockllm-pit-news](https://github.com/yoyocar2333/stockllm-pit-news)保存新聞抽取／情緒與PIT方法。本repo保存新聞與市場反轉的整合、增量比較及來源稽核；不轉載新聞全文、逐篇LLM回應或FNSPID原檔。[E4索引](docs/NEWS_RESEARCH.md)。

## 公開範圍與研究完整性

- 公開：研究程式、固定計畫、候選／選定設定、seed／狀態彙整統計、自製圖與來源SHA。
- 不包含：原始OHLCV／新聞、逐篇內容與私人清單、checkpoint／模型權重、完整工作站ZIP、API金鑰或個人工作站路徑。
- 原E0 [notebook](notebooks/stock_market_models.ipynb)、[RESULTS.md](RESULTS.md)及Git歷史保留；原README另存[E0](research/E0/LEGACY_README.md)。舊結果是既有記錄，此次未重跑。
- 真正`mamba_ssm.Mamba`；沒有替代fallback。固定時間切分、purging、同日期配對、seed穩定性與HAC／區塊bootstrap；校準、排序及成本後績效分開。
- 2026原協定不變、不加入E5、不執行驗證；舊新聞彙總與文獻頁附帶2026資訊的接觸如實揭露。[完整性聲明](docs/RESEARCH_INTEGRITY.md)。

[資料與權利邊界](docs/DATA_POLICY.md) · [公開來源索引](provenance/public_sources.csv) · [程式入口索引](scripts/RESEARCH_CODE_INDEX.md) · [發布檢查](docs/PUBLICATION_CHECKS.md)

Financial time-series research artifacts. Exploratory findings are not confirmed model superiority or investment advice. E0 legacy files and history are retained; E1–E6 use distinct targets and evaluation cohorts.

## 最新研究設計與公開重現

[E7a完整設計](research/E7a/E7A_RESEARCH_DESIGN.md)整理E0–E6證據與41篇快速文獻回顧。研究貢獻候選是增益來源的可重現稽核；不宣稱已發現基本面／新聞優勢，亦未完成外部預註冊。200股與未來16季度只是通過資料／功效門檻後的候選方案。

```bash
.venv-public/bin/python scripts/e7a_public_replay.py --bundle research/E7a --output-dir outputs/e7a_replay
E7A_OUTPUT=research/E7a .venv-public/bin/python scripts/test_e7a.py
```

E6過去搜尋曾意外看到2026財報標題數字；已補[完整性揭露](docs/RESEARCH_INTEGRITY.md)，不能宣稱零接觸。E3c舊2026協定不變、未執行、不加入E6/E7。新增原始資料、模型、新聞全文與工作站ZIP不公開。

## E7b公開來源原型

[資料原型報告](research/E7b/E7B_SUMMARY.md)區分取得與資格：20公司CIK核對成功，但原始SEC bytes、完整修訂鏈、as-traded／身分鏈與200文件獨立人工QA尚未通過。未把缺少證據設為合格，也未進行六比較模型搜尋。歷史開發母體不可由2025存活名單倒填，已提供獨立修正selector與[近期工作稿路線](research/E7b/SHORT_TERM_WORKING_PAPER_ROUTE.md)。

```bash
.venv-public/bin/python scripts/e7b_public_replay.py --bundle research/E7b
.venv-public/bin/python scripts/test_e7b.py
```
