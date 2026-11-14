# E8a.1 — Historical News & Social Data Provenance Pilot

查證日期：2026-11-14。主要依據為GitHub main `3c01d70b4794154bcf1aa776ff45fdce7f78ef55`的E8a文件及固定門檻，逐檔hash保存在`inputs/e8a_main_contract_hashes.json`。

**完成來源／授權與歷史證據先導稽核、空樣本誠實紀錄、QA協定及離線收集器；外部原始內容取得BLOCKED，E8b仍NOT_READY。** 真實新樣本0、L3=0、L4=0、待人工核對真實候選0、獨立人工完成0／100。沒有金融模型、Brier／AUC比較、付費API、申請寄送或前瞻排程。

## 1. 比E8a新增的具體證據

| 發現 | 對研究的意義 | 證據 |
|---|---|---|
| Stocktwits Enterprise提供客製API／研究團隊途徑；一般Edge歷史分數至1年 | 合法商業途徑存在，但不能以一般訂閱補成四年原始貼文／學術授權 | ST01、ST03、ST07 |
| 舊developer頁暫停新註冊 | 公開文件不等於可立即建立API帳戶；不推論Enterprise停服 | ST02 |
| Firestream文件有create/destroy、事件time、message id/body/created_at、parent、symbols與原生Bullish/Bearish/null | 文件證明欄位設計，不是本專案已取得歷史版本；time不是認證arrival | ST04–ST06 |
| stream恢復最多24小時，seq_id不在備份中 | 日備份不能單靠seq_id還原原監測／到達序列；序號不可假設連號 | ST05 |
| Reddit RFR有五年history、六個月延遲、每月最新版本並排除刪除 | 年數表面足夠不表示原始歷史文本可還原；批准後仍需版本稽核 | RD01–RD02 |
| Common Crawl WARC可成歷史capture候選，但原內容另有條款 | 「可以下載archive」不能同時證明使用權、歷史市場完整度或原始首次發布時間 | CC01–CC02 |

全部結論有[來源證據清單](tables/source_access_evidence.csv)、[URL／查證日／hash範圍manifest](tables/source_manifest.csv)。卡片hash是本研究整理的文件證據hash，**不是原HTTP／歷史貼文hash**。本輪沒有取得原貼文HTTP，相關欄位留空。來源文件不作為真實pilot文章。

## 2. 原始樣本取得決策

本會話未提供Stocktwits／Reddit／新聞商的合約、已批准API範圍或其他明確允許本研究用途的原始內容授權。未掃描私人憑證、未嘗試借用未確認用途的key。Stocktwits條款要求授權自動取得或approved API，開發者註冊亦受限，因此停止相應貼文擷取；不是以未授權試打端點後推定沒有資料。

`PILOT_SAMPLE_MANIFEST.csv`保留完整欄位但0資料列，`SAMPLE_ACQUISITION_STATUS.json`列明BLOCKED；`MANUAL_QA_PENDING.csv`也是0列。沒有用舊E4版本、文件的範例AAPL訊息、合成JSON或同文章多次下載冒充30–50筆新真實樣本。

E8a舊2,816新聞版本、3,316特徵和36Gemini接合的重現結論原封不動；本輪不重抓、不重評估舊測試成績。StockEmotions可在權利釐清後作受限回溯情緒方法研究，仍只有日期及篩選樣本，不能升為L3。合法可讀的歷史發布timestamp也不能證明今天看到的版本當時存在。

## 3. 歷史證據驗證原型

沿用L0–L4：L1日期proxy、L2有時區發布聲明、L3精確版本＋獨立歷史可得證據、L4另外有實際供應商arrival。L3不推定L4，retrieved_at不回填first_seen。

新增驗證器要求外部固定hash的證據登錄、原始bytes與分離text檔案hash、同source/record/version/text/raw綁定、審核紀錄與權利文件。直接在資料列填verified=true或任意時間字串不會升級。capture晚於cutoff也不因published_at較早而回填；source與arrival模式分開；今日研究授權有效日與歷史內容可得日分開。

**程式只能檢查綁定、格式與一致性，不能證明第三方聲明真實、審核者身分或時鐘沒有被偽造。** 註冊manifest本身須經機構／研究者另行簽核及外部保存；只在同一資料夾自寫文件和hash不會創造獨立歷史證據。測試fixture有模擬L3／L4路徑，但一律標synthetic並拒絕計入真實研究資格。

## 4. 離線收集器與研究意義

核心無網路adapter、無排程，live設定／外部真實內容匯入均拒絕。已實作固定query/window、原始fixture bytes及request/response時鐘／hash、opaque cursor、EOF／partial response、429與顯式重試、重啟狀態、版本衝突、刪除tombstone、每日manifest與hash-chain完整性。

分母是事前固定的source×query×ticker×session觀測window；未呼叫、限流、未知連續性、晚到或事後補抓保留UNKNOWN，不是無貼文0。HTTP200不等於EOF，空陣列不等於觀測完整；刪除後剩0篇也不等於原來沒有貼文。完整query並不保證整個平台完整。

演示僅用自製2030年虛構時間：2個planned windows中1個query完成、1個429，因此模擬比例0.5；**不是Stocktwits監測率，也不填進E8b90%門檻**。44項單元測試通過是工程證據；0筆人工作業仍0。詳見[收集器設計](FORWARD_COLLECTOR_DESIGN.md)。

## 5. E8b固定門檻判定

| 門檻 | E8a.1狀態 | 原因 |
|---|---|---|
| 研究使用／保存／刪除／重現權限 | BLOCKED | 缺本專案適用的原內容授權 |
| 嚴格歷史版本與availability | FAIL | 真實L3／L4均0 |
| 固定來源2訓練＋1驗證＋1測試年 | NOT_EVALUABLE | 未取得逐股連續合格面板 |
| 各段≥90%可稽核監測交易日 | NOT_EVALUABLE | 沒有歷史收集／翻頁／故障ledger |
| 兩股各100／40／60非重疊事件及類別量 | NOT_EVALUABLE | 不能由文章數或模擬窗口推算 |
| 正式100筆獨立人工QA | BLOCKED | 真實候選0；先導30–50只是材料目標 |
| paired Brier變異／相依／功效 | NOT_EVALUABLE | 本輪不擬合新模型，無合格面板loss |
| 新未見獨立期與預註冊 | BLOCKED | E8另立協定尚未完成；舊E3c2026不納入 |

完整逐閘門原狀態／本輪狀態／證據見[決策表](tables/E8b_readiness_decision.csv)。未放寬任何原門檻，沒有把0筆合格資料解讀為市場沒有訊號。

## 6. 必須回答的七個問題

1. **合法且有可信歷史版本的來源找到了嗎？** 找到官方合法申請／商業授權途徑；尚未取得同時滿足本專案研究權限與原歷史版本證據的新聞／社群來源。這是目前證據範圍，並非宣稱全球沒有此種資料。
2. **L3／L4取得多少？** 各0筆；不存在可指認的真實獨立版本／arrival證據。相關manifest空白，沒有假樣本。
3. **哪些可探索、哪些可嚴格PIT？** 既有Apple／StockEmotions等在使用權釐清後可受限回溯、情緒或品質診斷；嚴格PIT仍須逐版本獨立證據、權利與cutoff資格。原生Bullish/Bearish是自選標記，不是5日反轉真值。
4. **最大瓶頸？** 現階段存取／研究權限是立即阻礙；取得權限後仍有版本歷史與完整監測ledger的結構性缺口，單補發布timestamp不足。Reddit最新版本更新尤其無法自動回復舊本文。
5. **費用與校方協助？** Stocktwits Enterprise需客製quote；一般Edge顯示年價不適用原始歷史API。Reddit核准非商業學術資料免費，但需機構帳號、教授贊助、倫理審查／豁免及個別成員權限；雲端／匯出費未確認。詳見[成本與待辦](tables/source_costs_and_actions.csv)。未寄出任何申請或付款。
6. **最值得投入的路線？** 近期先形成資料品質／時鐘與版本契約方法工作論文，並準備教授可審閱的有限授權詢樣需求；取得來源證據後才擴樣。同時保留前瞻收集設計，尚不部署。不把工程測試本身當新的金融實證貢獻。
7. **E8b是否NOT_READY？** 是。八個準入門檻沒有全部PASS，真實合格面板、QA與推論資料仍缺；幾筆未來合格pilot也不能自動放行整個benchmark。

## 7. 完整性與產物

新目錄包含指定研究文件、空真實樣本／QA清單、schema、來源／成本／readiness CSV、離線程式與測試、manifest及結果ZIP。無第三方原文、原始貼文回應、個資或模型權重公開。獨立人工QA沒有被程式或文件審閱代替。

E3c2026協定未改未執行，不以2024–2025結果選來源，不取得2026報酬標籤選模。須如實揭露：訂閱頁共用導覽夾帶當前quote百分比，較廣來源搜尋夾帶當年金融標題／片段；未開啟該金融報導、未作模型或成績分析，數值未納入研究包／表格。先前2026接觸聲明也保留，不聲稱全研究史零接觸。

[重現說明](REPRODUCIBILITY.md) · [來源稽核](SOURCE_ACCESS_AND_LICENSE_AUDIT.md) · [版本稽核](HISTORICAL_PIT_PROVENANCE_AUDIT.md) · [後續路線](NEXT_STEPS.md)
