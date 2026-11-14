"""Write evidence-scoped Traditional Chinese E8a.1 research documents."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/e8a1_20261114'

def main():
    docs = {}
    docs['E8A1_SUMMARY.md'] = '''# E8a.1 — Historical News & Social Data Provenance Pilot

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
'''
    docs['SOURCE_ACCESS_AND_LICENSE_AUDIT.md'] = '''# 來源存取、授權與成本稽核

查證日2026-11-14。文件證據卡ST01–ST07、RD01–RD02、BZ01–BZ02、CC01–CC02、AU01–AU02見[sources/evidence_cards.json](sources/evidence_cards.json)與[來源manifest](tables/source_manifest.csv)。作者資料結論沿用E8a固定版本，不宣稱本輪重新取得內容。原始貼文／新聞取得0；未寄信、申請、支付、註冊帳戶或使用未知用途憑證。

## Stocktwits七項問題

| 問題 | 可證明的事實與尚缺資料 | 證據 |
|---|---|---|
| 合法歷史內容 | 有平台授權／approved API的取得途徑；沒有本專案合約，因此停止貼文擷取 | ST01、ST03–ST06 |
| API／學術／第三方 | Firestream與Enterprise有官方文件；舊developer註冊暫停；未找到可核實涵蓋本用途的公開學術免申請授權或原始歷史貼文第三方再授權文件 | ST02–ST06 |
| 四年兩股連續性 | 舊日備份路徑不證明最早日期／AAPL／TSLA每年完整；Edge一般分數歷史至1年，不足四年raw資料證明 | ST03、ST06 |
| 時間、內容、版本 | 文件列created_at、message body/id、parent、symbols、create/destroy事件time；未證明完整edit版本鏈、刪除備份保留與歷史arrival | ST05 |
| 獨立capture | 本專案未取得舊原始回應或可獨立核對的逐版本capture；文件示例不算pilot | ST05–ST06 |
| 查詢／監測 | stream seq_id恢復期最多24小時，備份不含seq_id；未取得過往query、uptime、漏抓及page ledger | ST05 |
| 用途／保存／公開／價格 | 一般服務條款不是研究資料集授權；Enterprise客製報價，原文保存／刪除／派生成果與審稿重現仍待明確約定 | ST01、ST03、ST07 |

官方：[服務條款](https://stocktwits.com/about/legal/terms/)（頁面2026-07-10修訂）、[developer註冊](https://api.stocktwits.com/developers)、[方案比較](https://help.stocktwits.com/c/stocktwits-edge/stocktwits-edge/plans-compared)、[Firestream](https://firestream.stocktwits.com/documentation)、[stream欄位](https://firestream.stocktwits.com/documentation/stream)、[backup](https://firestream.stocktwits.com/documentation/backups)、[訂閱價頁](https://stocktwits.com/subscriptions)。

Edge頁顯示US$229.50/年促銷價，只是查核時的一般訂閱顯示，不能當原始歷史API／研究授權quote。Enterprise費用／學術折扣沒有公開確認數字。平台合作、app訂閱、作者code license、可下載的第三方資料夾均不能自行推論為Stocktwits貼文轉授權。本輪未驗證任何可供本研究使用的Stocktwits歷史raw reseller；不推論其全球不存在。

## Reddit官方後備路線

[RFR](https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program)與[Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy)（皆2026-10-05更新）提供學術申請規格：合格機構／教授贊助、倫理審查或豁免、研究計畫與個別成員權限；核准非商業學術資料存取免費。BQAH雲端／匯出費、允許匯出內容及派生物保存須依入選合約再確認。未代送申請。

官方說明是五年rolling history、六個月延遲、每月採最新內容並排除已刪除項。可涵蓋四個歷年不代表舊版本還在，也不證明兩股的query/session completeness。現在的最新版本不可掛到舊created_at；若有獨立舊capture，最多從capture時點起證明該版本可見，不能倒推原建立時已是同文。刪除、禁止轉交與重查要求將影響審稿重現與長期保存，必須先設計權利一致流程。

## 新聞與歷史archive後備路線

[Benzinga](https://www.benzinga.com/apis/)與[Massive的Benzinga feed說明](https://massive.com/knowledge-base/article/what-does-massives-benzinga-news-feed-contain)證明商業歷史新聞途徑，後者描述自2009-04-27的出版項目與ticker欄。出版時間不是上游事件／press release原時間，部分只有標題、無原生sentiment。沒有本專案權利、逐版本樣本、receipt及完整監測證據，因此未連線內容端點；不是Stocktwits歷史轉授權商的證明。

[Common Crawl取得說明](https://commoncrawl.org/get-started)顯示archive可免費讀取；[條款](https://commoncrawl.org/terms-of-use)（2024-03-07）指出crawled content可能有另行使用條款。WARC可以提供歷史時點／payload候選證據，但需原發布者使用條件及精確版本核對；不得用archive繞過原來源授權。本輪未查詢／擷取金融內容WARC。

## 供教授／校方審閱的詢樣需求，未寄送

1. 專案非商業用途、AAPL／TSLA、候選四年歷史區間、只先30–50筆及涵蓋樣本規則；不得包含2026凍結驗證。
2. 要求原文、版本識別／修訂／刪除證據、原發布與供應商到達clock語意及完整原始回應；可匿名化，不索取不必要個資。
3. 要求同ticker固定query與pagination／EOF／stream gap／backup範圍、資料來源變更、時區與歷史監測分母證明。
4. 詢問本機／備份保存、刪除及derivative失效、多人研究、審稿讀取、只公開aggregate／程式／hash的權利。
5. 分開報價：一次pilot、四年歷史、後續stream、研究席次、儲存／API用量／審稿存取；未確認費用維持UNKNOWN，不自填0。

這是來源條件與研究可行性稽核，不對未取得的合約作法律認證。現有舊資料只保留既有狀態，沒有重新發布第三方內容。
'''
    docs['HISTORICAL_PIT_PROVENANCE_AUDIT.md'] = '''# 歷史內容版本與時間證據稽核

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
'''
    docs['MANUAL_QA_PROTOCOL.md'] = '''# 人工QA先導協定與待簽核材料

目前：真實候選0、材料包0、獨立人工完成0；`MANUAL_QA_PENDING.csv`僅表頭。先導30–50筆材料目標與E8b正式100份獨立文件QA分開，沒有預填通過或捏造reviewer。

## 有授權資料後的固定抽樣

目標40份文件／版本：兩股各20，橫跨至少四年（2train、1val、1test角色），每股每年5。資料充分才依年度分層；稀少年份／無修改刪除情形保留欠額，不以複製或合成補齊。版本組視為同一文件cluster，不能用一篇多次擷取抵100份文件。

分層固定含日內／日期／午夜品質、17NY前後、假日、parent／reshare、ticker歧義；若來源有真實edit/delete，以同文件版本對照保留。依source+stableID+version的固定SHA256排序抽取，拒用未來label、收益／模型誤差挑樣。缺少某種層就標NOT_AVAILABLE，不發明刪除證據。

## 每筆核對

1. 來源、原始bytes hash、document/version/parent、公司實體／cashtag；Apple一般名詞與ticker要分開。
2. 原始日期與時區語意、發布／修改／刪除／捕獲／到達是否分清；UTC午夜是否只是日期占位。
3. 證據是否同內容版本、是否可獨立核對；該版本在本次decision cutoff前的可得上界。
4. 重複、轉發、thread、一文多股、刪除與版本更新；不可把今天新內容接到舊created_at。
5. 原文情緒、原生bull/bear或模型輸出的語意差異及未提供狀態；這不是5日反轉gold。
6. 使用／保存／再散布是否在本專案範圍、刪除是否已遵循。

reviewer須填獨立研究者識別、實際審核時間、具體證據URI/hash、判定PASS/FAIL/UNRESOLVED與理由。建議另一位研究者複核關鍵時間錯誤；人工工具生成建議不算review。未填reviewer／time／evidence或未解決的重要錯誤不得計完成。

E8b100份要求、零關鍵前視／版本錯誤及reviewed entity relevance≥95%不變；40份pilot即使完成也不代表100份gate通過。真實授權證據尚缺，本輪不能評估實際一致率／語意正確率，也不把0審查寫成0錯誤率。
'''
    docs['FORWARD_COLLECTOR_DESIGN.md'] = '''# 前瞻收集器設計與觀測契約

狀態：可離線測試的核心；**沒有network adapter、排程或真實來源啟動**。真正部署需另行授權、時鐘／資安／故障實測和E8獨立協定，不能因unit tests通過宣稱production-ready。E3c2026不變。

```mermaid
flowchart LR
    A[Approved source + fixed query + calendar] --> B[Disabled live adapter / offline fixture injection]
    B --> C[Request/response clock + raw hash]
    C --> D[Identity, version, cursor, errors]
    D --> E[Append journal + retained external head]
    D --> F[Private content-addressed payload]
    E --> G[Planned-window observation ledger]
    F --> H[Daily manifest + deletion tombstones]
    H --> I[Independent review + evidence registry]
    I --> J[As-of eligibility; no automatic PIT upgrade]
```

## 固定資訊與權限

部署候選固定AAPL／TSLA、source namespace、cashtag與經核對historical entity map；每個query記版本與hash。query與實際交易日曆於收集前鎖定，禁止由實際回傳日期反造分母，也不依模型成績增加alias。消息ID只在來源namespace內唯一。原生symbol關聯仍需公司相關性QA。

每個source/ticker/session window明列start/end與17NY資訊cutoff，完整交易日曆與purged評估日期分開。密鑰僅由部署時的核准secret引用注入adapter，request logs只存非敏感參數hash，不記Authorization、cookies、URLtoken或個人資料。此版不讀環境key、不實作HTTP或collector scheduler。

## 原回應、時鐘、版本與生命週期

核心只接收顯式synthetic fixture bytes，保留內容位址hash、request_started/response_received、query/window、cursor和原status。real envelope被拒絕。成功／錯誤／schema拒絕與顯式retry都記錄；partial HTTP200不能當完成。

created/edit/delete有原事件時間與獨立version ID，同ID/version不同text會拒用；parent、reshare／thread由adapter映射到版本schema，保留source關聯。當前followers/likes不作歷史特徵；如未來需要，只使用當cutoff實際捕獲的版本。事件時間不等於實際arrival，collector自己的receipt亦不能認證之前供應商arrival。

## Pagination、故障與分母

opaque cursor原值保留、重啟重建狀態並核對同plan；循環或錯頁拒用。只有完整terminal、無errors、明示連續觀測證據、在cutoff前收到且非事後backfill才記query complete。本離線核心對出錯窗口保守維持UNKNOWN；真實恢復需另外核准的可追溯gap reconciliation，不由後一次200抹掉舊失敗。

分母D為事前固定的source×query×ticker×session windows；分子為有完整收集與時鐘證據的windows。分割／股別各自算，實際取樣分母不是「有貼文的天數」。uptime要獨立heartbeat、cursor/checkpoint、429/timeout/重連、漏抓起訖／重補來源及時間。每次補抓記original_observation與recovered_at，後補不冒充原持續觀測。Stocktwits24h恢復界限是供應商特定限制，不能藉任意重試繞過。

空完整query只表示該固定查詢／來源在該次回應沒有紀錄，不保證整平台沒有貼文；零retained可能是刪除後的狀態，不能稱原來沒貼文。缺失時count、情緒及完整率保留NA。demo2windows的1/2僅工程例，不是正式90%達成情況。

## 每日manifest、不可變性與刪除

UTC每日manifest記當日response objects、hash、plan及journal head，使用create-exclusive拒絕覆寫；journal hash-chain及raw bytes修改會被核對。但本地hash chain不是WORM／外部可信timestamp，攻擊者可重寫整條鏈；需將每日head由研究機構獨立保存／簽章或object-lock，而本輪沒有實作或認證此服務。

原內容置私有可刪除儲存；不可將原文放進不可刪journal。收到刪除／撤回政策觸發後，刪受影響payload並記最小tombstone，標示相關特徵／分析須失效重算。核心示範保守刪除包含該紀錄的整個response blob；其餘紀錄保留性可能下降，不能默默填0。需一併處理備份、派生物與retention期限；此版未宣稱完成雲端所有副本刪除。hash／tombstone本身也須依授權與隱私政策最小化。

## Schema與證據資格

[record schema](tables/provenance_record.schema.json)及[offline plan schema](tables/collector_config.schema.json)供adapter contract使用。它們是描述性JSON Schema與核心欄位檢查，不是完整生產adapter／完整JSON Schema驗證套件。L3/L4仍須人工認證的外部證據registry；記錄一致和工程收集成功都不自動升級。
'''
    docs['E8B_READINESS_DECISION.md'] = '''# E8b Readiness：NOT_READY

主要依據仍為main固定E8a門檻，原件與hash在inputs/e8a_contract；[本輪逐閘門CSV](tables/E8b_readiness_decision.csv)保留舊狀態與新的PASS/FAIL/NOT_EVALUABLE/BLOCKED標記。沒有新建較寬鬆規則。

| Gate | 狀態 | 不能通過的證據 |
|---|---|---|
| permitted_research_and_reproduction | BLOCKED | 沒有本專案適用的研究／保存／刪除及重現授權 |
| strict_historical_content_and_availability | FAIL | PILOT_SAMPLE_MANIFEST只有表頭，真實L3=0、L4=0 |
| same_source_2train_1validation_1test_years | NOT_EVALUABLE | 未取得合格逐股面板；官方服務history不是實際連續樣本 |
| documented_session_monitoring_at_least90percent | NOT_EVALUABLE | 沒有歷史固定query／完整監測ledger；synthetic比例不使用 |
| nonoverlap_event_and_class_support | NOT_EVALUABLE | 真實合格panel0，不能計算兩股100/40/60與類別20/10/20支持 |
| 100_independent_manual_version_and_relevance_QA | BLOCKED | 人工候選0、完成0；30–50材料先導與100要求分開 |
| development_only_paired_loss_power_and_size | NOT_EVALUABLE | 無新paired losses、跨股／時間變異或檢定功效，不製造估計 |
| unseen_preregistered_E8_validation | BLOCKED | 2024–2025早已探索；2026舊E3c不能改作E8保留集；新協定未註冊 |

來源完整度每段≥90%、每股100/40/60非重疊事件與最低類別量、100文件QA與零關鍵錯誤／95%公司相關性維持原要求；它們仍只是screen，不能保證足夠joint power。即使日後40筆全有L3，也不能替整個年度／股票面板認證。

只有八gate全部具實際證據PASS後才考慮另立E8b執行計畫。現在完成的是資料可行性與工程先導，沒有比較金融模型、搜尋較佳測試樣本，亦不對新聞／社群預測力作肯定或否定結論。
'''
    docs['NEXT_STEPS.md'] = '''# 建議下一步與投入順序

## 近期可完成：來源／版本品質方法工作論文

用E4、E7、E8既有真實稽核個案，加上本輪官方政策、時間語意與fail-closed工程，討論「歷史發布時間、內容版本、到達、監測與權利」五項如何分開。把已觀察失敗、機構待辦及synthetic反例分欄。這是一條可撰工作稿的路線，尚須獨立人工對照和至少一批真實外部證據pilot，才可主張方法經外部資料驗證；不宣稱已證明H1/H3或新方法優於既有研究。

## 取得教授同意後的有限詢樣，尚未寄送

優先Stocktwits Enterprise：一次30–50筆，明列兩股／跨年／原始版本與刪除arrival證明／query完整性，不先買Edge。不需要一次購買多年庫。費用和允許研究派生物保存必須由平台實際quote，沒有可靠數字前維持UNKNOWN。

同時由教授評估Reddit RFR的校方與倫理申請成本；其資料免費仍不等於舊版本可得。若平台不能提供原版本或可信capture，應將問題改成最新／長延遲可得文字研究，不能不改研究定義就聲稱原始事件PIT。

新聞後備詢Benzinga／合約供應商；Common Crawl只在相關內容使用範圍釐清後做歷史capture查核，不能當免費的授權替代。先證據、後擴樣，來源選擇不依2024–2025成績。

## 前瞻設計準備，但不部署

保留offline核心，預備權利／clock／secret／監測與資料刪除的部署review。只有另立E8預註冊、真正未見區間與來源品質合格後，才另行核准啟動。E3c2026與E7長期計畫分開，不事後追加本輪模型。未來時間與股票樣本不得由目前受限資料的結果挑選。

不建議現在增加Mamba／LLM或訓練深度融合；立即障礙是權限，後續根本障礙是版本與監測證據。授權不能補造資料品質，工程測試也不能補造獨立金融效果。
'''
    docs['REPRODUCIBILITY.md'] = '''# E8a.1重現說明

Python3.10以上，所有核心、稽核表與單元測試只用標準函式庫；無套件安裝、無GPU。沒有現場API adapter或長期排程。

公開repo或完整ZIP的對應code路徑：

```bash
python -B scripts/test_e8a1.py
python -B scripts/e8a1_build.py --bundle research/E8a1 --output-dir outputs/e8a1_tables_NEW
python -B scripts/e8a1_build.py --demo --output-dir outputs/e8a1_demo_NEW
python -B scripts/e8a1_validate.py --bundle research/E8a1
```

ZIP解壓後把scripts/換成code/、bundle換成`.`；table replay會從文件證據卡與原E8a固定gate重建5份CSV、2個schema及audit_results，無需原文或金融labels。demo產生的response、journal及manifest全部自製synthetic且位於獨立工程目錄；不要放進PILOT_SAMPLE_MANIFEST。

15張卡是人工整理的官方／作者文件證據；程式重播證明整理和表格一致，不是重新查證網站現況或認證歷史資料。source_manifest的hash_scope明示整理卡片，original_HTTP_sha256為空；並無原貼文HTTP可供本輪驗證。來源最新頁面可能改動，重新查證應另建版本、保留查證日而不覆蓋本輪。

原E8a契約逐檔hash和main commit固定；舊研究與協定另有完整保護manifest。真實樣本／QA檔案為空，檢查器拒絕將synthetic填入真實sample。未執行新Brier/AUC、沒有新模型成績。預註冊、未見期間與外部證據保管仍是人工待辦。
'''
    docs['README.md'] = '''# E8a.1 — Historical News & Social Data Provenance Pilot

**先導稽核完成；真實資料取得BLOCKED，E8b NOT_READY。** 新真實樣本0、L3/L4各0、人工候選與完成各0。來源途徑不等於已授權或歷史版本合格。

[繁中總結](E8A1_SUMMARY.md) · [來源／授權](SOURCE_ACCESS_AND_LICENSE_AUDIT.md) · [版本／時鐘](HISTORICAL_PIT_PROVENANCE_AUDIT.md) · [QA協定](MANUAL_QA_PROTOCOL.md) · [離線收集器](FORWARD_COLLECTOR_DESIGN.md) · [E8b決策](E8B_READINESS_DECISION.md) · [下一步](NEXT_STEPS.md) · [重現](REPRODUCIBILITY.md)

[真實sample空清單](PILOT_SAMPLE_MANIFEST.csv) · [待簽核空表](MANUAL_QA_PENDING.csv) · [來源manifest](tables/source_manifest.csv) · [readiness CSV](tables/E8b_readiness_decision.csv)

無新金融模型、無付費／申請／寄送、無live collector，E3c2026未改未執行；synthetic工程例不得用作真實樣本或100QA。與[stockllm-pit-news](https://github.com/yoyocar2333/stockllm-pit-news)的新聞抽取研究交叉連結，公開repo不含第三方內容。
'''
    for name, text in docs.items(): (OUT / name).write_text(text.rstrip() + '\n')
    print('Documents:', len(docs))

if __name__ == '__main__': main()
