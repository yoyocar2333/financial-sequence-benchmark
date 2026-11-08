"""Render E8a conclusions from audited counts; no performance-based decisions."""
from pathlib import Path
import json
import os
from e8a_core import read_csv

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('E8A_OUTPUT', ROOT / 'outputs/e8a_20261108')).resolve()

def md(rows, keys):
    rows = list(rows)
    return '| ' + ' | '.join(keys) + ' |\n|' + '|'.join('---' for _ in keys) + '|\n' + '\n'.join('| ' + ' | '.join(str(r.get(k, 'NA')) for k in keys) + ' |' for r in rows) + '\n'

def main():
    results = json.loads((OUT / 'tables/analysis_results.json').read_text())
    inventory = json.loads((OUT / 'audits/inventory_scope.json').read_text())
    pit = list(read_csv(OUT / 'tables/PIT_quality_by_source.csv'))
    event = [r for r in read_csv(OUT / 'tables/event_source_overlap.csv')
             if r['source'] == 'Apple_recollected' and r['delay_sessions'] == '0' and r['year'] in ('2023', '2024', '2025')]
    support = [r for r in read_csv(OUT / 'tables/legacy_partition_support.csv')
               if r['source'] in ('Apple_recollected', 'FNSPID_Nasdaq_fullscan', 'StockEmotions_processed')]
    summary = f'''# E8a — 新聞與社群 PIT 資料可行性稽核

研究日期：2026-11-08。狀態：**稽核完成；E8b 正式 PIT 模型比較尚未具備資料條件。** 本階段新訓練模型0、GPU操作0；不修改舊實驗、E3c2026協定或其驗證。這不是新聞／社群無效的實證結果，而是能回答什麼問題的資料邊界。

## 1. 研究問題與稽核範圍

E4c尚未建立新聞相對價格／條件機率的穩定增量排序能力。E8a先區分內容、可得時間、版本、來源監測與合法研究使用，再考慮擴充社群訊號。**沒有以舊模型表現挑來源、門檻、股票或資料版本。** 技術與資料閘門先寫入[AUDIT_PLAN_LOCKED.json](AUDIT_PLAN_LOCKED.json)，屬本機稽核計畫，不是已完成外部預註冊，也不是功效已證明的樣本數。

盤點E4a–E4c全部輸出版本、重播副本、程式、原始資料／特徵／預測／圖表與模型檔案，共 **{inventory['physical_files']:,}個實體檔案**，其中{inventory['fresh_hash_files']:,}個重新計算SHA256，{inventory['repeated_hash_groups']:,}組雜湊出現在多個檔案。重播、ZIP和重複檔案不是新觀測。模型檔僅作檔案稽核，未反序列化或執行。

主分析只從目前canonical E4a、E4b、E4c讀取文章層級輸入。得到 **22,841筆新聞稽核紀錄**，包含100篇metadata、2,816筆E4b版本及19,925筆FNSPID全掃描目標列；它們**不是22,841篇獨立新聞**。另有39,330筆重疊社群視圖metadata，合計62,171筆版本／股票／視圖紀錄；不把這個總數當獨立樣本量。

FNSPID23,232,979,597bytes、15,549,299列的EOF與全檔SHA證據沿用E4c，這一輪**沒有再次完整讀取23GB主檔**。重新hash及逐列分析兩股完整保留匯出，核對既有全掃描證據。詳見完整本機`audits/artifact_inventory.csv`、canonical輸入manifest和[實體檔案分類](tables/artifact_inventory_summary.csv)。

## 2. 新聞資產、特徵與預測核對

| 資料 | 本輪確認內容 | 範圍與限制 |
|---|---:|---|
| Apple Newsroom重建 | 448篇：2023年152、2024年156、2025年140 | 當前回抓版本、AAPL企業自發新聞；不是2012–2022新聞訓練集 |
| 原Phase7A | 52篇2025年1月摘要、36篇Gemini輸出 | 摘要不是全文；18篇smoke已含在36篇內；未補成54篇 |
| E4b局部FNSPID | AAPL441、TSLA1,875 | All_external.csv局部標題；與Nasdaq主檔不能當新增獨立語料 |
| E4c全掃描FNSPID | AAPL9,338、TSLA10,587 | 主檔目標保留列；非空本文AAPL8,865、TSLA8,712，不等於已核實完整全文 |
| StockLLM舊100篇metadata | 100篇2023來源核對清單 | 100個URL及文字hash均與448篇中的對應項重合，不加算新文章 |

本輪重新計算E4b2,816筆title＋空行＋content版本雜湊，錯誤0；3,316列特徵與父文章record_id＋text_sha256接合錯誤0，重複特徵視圖0，每篇恰好一個主要視圖。從4,219個既存chunks重算token加權FinBERT機率，誤差在1e-6內；36筆Gemini仍只接同摘要版本，錯接0。這七項[特徵一致性檢查](tables/feature_integrity.csv)**不是情緒或事件抽取準確率、歷史服務端revision認證，也不是人工語意gold**。

FinBERT仍為`ProsusAI/finbert` revision `0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031`。未重做任何推論。舊Gemini模型字串和cache只能支持當時保存的回溯輸出身分，不能認證歷史訓練截止、服務端實際revision或過去可部署性。

E4c既存機率輸出按檔案、日期切分、timing、method和seed盤點，見[預測資產清單](tables/prior_prediction_inventory.csv)。未重新估計Brier、改選winner或把E4c2025與E3c2024–2025樣本混合；沒有新增預測。

## 3. AAPL／TSLA逐年覆蓋與重複

![來源年度保留列](figures/01_source_year_coverage.png)

FNSPID在2012–2018兩股0筆保留列，AAPL2019也是0；兩股2021、2024、2025均沒有當年保留列。AAPL2020為473筆標題，2022為3,094、2023為5,771；TSLA2019為733、2020為1,142筆標題，2022為3,169、2023為5,543。大量資料集中2022–2023，不能說覆蓋1999–2023的資料庫就一定支援這兩檔完整歷史。

E4b441／1,875個同股票URL全部在FNSPID Nasdaq目標匯出中出現；兩股Nasdaq本身又共享1,061個URL，因此不能把來源／股票關聯當獨立新聞或獨立金融事件。**同URL只表示文件身分重合，不證明摘要、全文、修訂內容相同。** 精確文字hash亦有不同生成慣例，不能將跨慣例未命中當成版本衝突。E8a表內text重複是既定exact hash，不與E4c的NFKC／空白／casefold正規化重複率互換。

[逐股逐年全表](tables/source_stock_year_coverage.csv)對無保留列寫0，但歷史監測比例、完整市場新聞分母及真正無新聞日仍為**NA／UNKNOWN**。0只表示目前固定來源快照沒有保留紀錄，不是市場沒有新聞／貼文。來源選樣、刪除、漏頁、停機、平台移轉與股票實體辨識皆可能造成缺失。

## 4. 社群歷史來源調查與實際核對

| 來源 | 已確認取得途徑／範圍 | 本輪實際取得與判定 |
|---|---|---|
| X | 官方完整搜尋文件描述自2006-03，需開發者帳戶／token與用量或Enterprise權限 | 未呼叫平台搜尋、未購買；兩股逐年量UNKNOWN；created_at／edit IDs不足以證明歷史到達 |
| Reddit | RFR學術申請、機構贊助與倫理審查／豁免、個別研究者權限 | 未代送申請；未取得貼文；歷史範圍及兩股量UNKNOWN；研究刪除與不可轉交規則需先解決 |
| Stocktwits | 官方Firestream每日message／activity備份，需要stream授權 | 未取得授權備份；最早可授權年份／逐股完整度UNKNOWN，不把公開近期stream當歷史全集 |
| Bluesky | 公開GET／firehose值得評估；ATProto明示TID使用者可指定 | 未查即時貼文／未啟動collector；不能從TID或自行填寫createdAt認證過去公開時點 |
| StockNet作者資料 | README描述2014–2016與88股票 | 核到AAPL784個日期檔：2014年341、2015年355、2016年88；最晚2016-03-31。列出股票目錄無TSLA；沒有下載或計數貼文本文 |
| StockEmotions作者資料 | 作者描述2020年篩選語料與10,000標註句 | 固定Git版本4CSV逐一核對blob SHA，僅保留兩股日期／ticker／hash；原CSV與貼文全文未保存或公開 |

官方／作者來源：[X完整搜尋](https://docs.x.com/x-api/posts/search/quickstart/full-archive-search)、[Reddit研究計畫](https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program)、[Stocktwits備份](https://firestream.stocktwits.com/documentation/backups)、[ATProto record key](https://atproto.com/specs/record-key)、[StockNet](https://github.com/yumoxu/stocknet-dataset)、[StockEmotions](https://github.com/adlnlp/StockEmotions)。文件現況截至本輪查核；不是已簽訂的資料權利或歷史查詢成功證據。[來源可行性矩陣](tables/data_source_feasibility.csv)保留取得層級、缺口與下一步。

StockEmotions處理後資料2020年AAPL **8,903**、TSLA **24,341**；另AAPL2019-12-31有1筆、TSLA同日4筆及2021-01-01有19筆，原樣保留日期，沒有未經證據改回2020。這些邊界可能涉及上游日期處理，但本輪無時區證據判定原因。處理後兩股共33,268列；標註視圖另6,062列（AAPL1,721／TSLA4,341），不能加成39,330個獨立貼文。

兩套ID命名空間未核實、沒有ID重合，但原文字hash分別重合1,720／4,335個；標註有1／6個不同文字hash未在處理後資料命中，保留而不強接或刪除。**不以不同ID判定新文章，也不以同文字推定同一金融事件。** train／val／test各檔日期都跨2020多個月、彼此重疊，不能沿用為時序驗證。見[社群逐年與分檔數據](tables/social_author_dataset_coverage.csv)及[視圖重合](tables/social_view_overlap.csv)。這是作者篩選的情緒語料，不是完整Stocktwits訊息流或可直接回測的當時投資者訊號。

## 5. PIT時間與資訊品質

採L0無可用時間、L1日期proxy／未核實午夜、L2有時區發布聲明、L3精確歷史版本＋獨立可得時點證據、L4再加認證供應商到達時間。**L3可用足夠早的獨立歷史capture作保守上界，不要求憑空還原真正第一眼first_seen。** 現在抓取的版本、現在取得時間或未綁定版本的created_at不會升級。

{md(pit, ['source', 'ticker', 'rows', 'L1_DATE_PROXY', 'L2_PUBLISHER_TIME_CLAIM', 'L3_SOURCE_VERSION_VERIFIED', 'L4_ARRIVAL_VERIFIED'])}

![時間品質分級](figures/02_PIT_evidence_levels.png)

FNSPID Nasdaq AAPL9,307／9,338（99.67%）、TSLA10,562／10,587（99.76%）為午夜UTC聲明；只當日期型proxy，不相信格式看似秒級便有真實秒級精度。Phase7A52筆雖有時區時間，也缺歷史版本／到達證據。**本輪L3／L4合格均0**，代表證據未取得，不是認定這些內容當年不存在。

發布、修改、歷史版本首次可見、供應商收到、現在取得、特徵模型release／revision、推論完成、決策cutoff各自分欄。回溯計算本身不必然造成洩漏：若有合格歷史文本與事先固定、可證明當時已可用的語意模型，現在可重算time-consistent backtest；但不能宣稱當年已部署。較晚才訓練的LLM可能帶入未來知識，需獨立控制。推論時間晚於決策只會否定「當時已產出該特徵」的部署主張，不單憑這點否定所有離線回溯研究。

社群likes、retweets、留言數、帳號追蹤數、當前sentiment圖表若是現在取得的累計值，不可當歷史特徵；需每個歷史cutoff的獨立快照。編輯／刪除、repost／thread去重、bot／宣傳選樣、cashtag與Apple／Tesla一般文字的公司相關性也須核對，不以本文hash推定情緒真值或完整度。

## 6. 市場事件支援與時間敏感度

沿用凍結E3c事件及5日標籤，不重估事件門檻。新聞日期型資料延到其日期後第一個實際交易日；可信度仍只是proxy。有發布時區的聲明則按17:00 America/New_York cutoff；另固定延後1／2資訊交易日，不挑最佳結果。**完整行情交易日曆與經purge的評估日期分開**，避免年底錯移；此工程修正和回歸測試記於`audits/calendar_quality_correction.json`，原E4科學產物未改。

{md(event, ['year', 'price_events', 'events_with_retained_source_in_last5', 'snapshot_event_overlap_fraction'])}

上表2023分母29為E8a保留所有既有評估事件的診斷；E4b原報告28為當時完整來源窗口篩選後分母，不能將本輪28／29與原28／28互換。2024的32／36、2025的59／65與同來源原窗口結果對照。兩者都不是市場新聞完整率；跨年過去5交易日可有上一年文章，因此「本年0文章」仍可能有少量年初事件重合。

![事件與保留來源重合](figures/03_event_proxy_overlap.png)

為避免大量重疊事件膨脹樣本，先在完整價格事件日曆固定取每5交易日第一個事件，再檢查來源重合，不能每個來源各挑最有利的事件起點。Apple在舊2023驗證診斷只11個source-overlap非重疊事件，舊2024–2025共34；FNSPID全掃描舊訓練來源支援也遠少於每日新聞列數。StockEmotions數萬貼文則集中單一年、不能獲得多個獨立市場年份。[舊分割支援表](tables/legacy_partition_support.csv)只是可行性診斷，沒有重新定義E4c切分；正式合格事件仍0。事件數也不是功效認證，沒有IID二項檢定、新聞有效性p值或模型增益主張。

## 7. E8b決策與後續路線

**不開始正式新聞＋社群模型比較。** 八項[資料閘門](tables/E8b_readiness_gates.csv)尚未全部通過，特別是歷史版本／時間、來源持續觀測、獨立人工QA與未見驗證。100篇人工文件／版本檢查仍0；25項程式合成契約測試和離線重播不是人工QA或預測證據。

優先取得一個法律與研究使用範圍明確、能提供原始訊息／修改／到達／完整監測資訊的固定來源小樣本，按AAPL／TSLA及年份交叉抽驗，再決定是否擴大；Stocktwits金融cashtag來源可列優先詢樣候選，但尚無授權或實際長期覆蓋承諾。Reddit需要教授／學校的申請與倫理審查，不能自行代為聯繫或假裝已批准。沒有預算／授權時，維持公開作者語料的描述或情緒方法重現，不以短單年資料勉強訓練深度反轉模型。

正式E8b最低篩選目標為固定來源至少2訓練＋1驗證＋1測試年、每段≥90%可證監測session、兩檔各100／40／60個不重疊事件及類別最低量；均是事先固定的工程／可行性screen，不代表已達80%統計功效。仍需開發期配對損失依賴、block長度與共同多重比較功效驗證。未達標可明確另立受限探索方案，不能默默放寬後稱正式通過。

未來設計應固定價格P、新聞／社群metadata-only、情緒／事件訊號、條件機率，以及同權重常數收縮控制，拆開校準與同條件排序增益；不因結果才決定哪個來源有效。完整建議見[E8b可行性決策](E8B_FEASIBILITY_DECISION.md)與[後續優先工作](NEXT_STEPS.md)。目前結論是「歷史PIT證據及來源一致性不足」，**不是新聞／社群缺乏預測力的否定結論**。

## 8. 完整性與可重現性

原E3c2026固定JSON SHA256 `9ffe3c31bbfabb6609ee69dde1deab7a13729b43511a9c045d945b5b03453940`保持不變，未執行；E8模型不加入該協定。2024–2025已多次檢視，E8未來確認需另行預先登錄未見期間。既有2026新聞彙總／其他來源片段接觸紀錄保留，不能聲稱整個研究史零接觸；本輪未要求新的2026金融新聞／社群貼文或行情標籤。讀取當前平台政策文件不等於開啟2026金融驗證。

完整本機包包含content-free逐筆metadata、CSV表、來源文件擷取／API目錄metadata、程式、雜湊、圖與稽核，不重包原新聞全文／貼文、23GB主檔、checkpoint或私人金鑰。公開GitHub只發布程式、彙整資料與自製圖，不發布逐篇／逐貼metadata或本文。原文與研究整合的分工見[stockllm-pit-news](https://github.com/yoyocar2333/stockllm-pit-news)。[重現說明](REPRODUCIBILITY.md)清楚區分彙整檢查、metadata重播與原始來源認證。
'''
    (OUT / 'E8A_SUMMARY.md').write_text(summary)
    (OUT / 'DATA_CONTRACT_AND_PIT.md').write_text('''# E8a資料契約與品質檢查

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
''')
    (OUT / 'E8B_FEASIBILITY_DECISION.md').write_text('''# E8b正式比較可行性：NOT_READY

E8a完成，不等於E8b通過。歷史source-version合格0、arrival合格0、獨立人工QA0、完整監測coverage為NA。尚不能建立「P vs P+新聞 vs P+社群 vs P+兩者」相同合法可得資訊的正式PIT面板。

## 預先固定的screen

1. 取得可核對的研究使用範圍、刪除／再散布政策；未知不是合法或非法的自動判決，但不自動公開第三方內容。
2. 進比較的每筆內容綁定歷史版本與availability，決策cutoff前可得；source與vendor模式分開。
3. 同一固定來源與查詢至少2訓練＋1驗證＋1測試年，每段≥90%有證據的監測session；這是E8b候選screen，不追溯修改E4c的三年探索切分。
4. 每股先按全價格事件日曆取5session首事件，再審查支援；訓練100、驗證40、測試60，兩類最低20/10/20。大量貼文不能替代獨立事件／年份。
5. 100份分層獨立文件／版本核對，跨股／來源／年／cutoff／編輯狀態；關鍵未來資訊錯誤0、公司相關性≥95%。本輪尚未完成，25個程式測試不算人工作業。
6. 開發資料估計配對loss變異、來源／日期／股票clusters與實際MDE；screen不保證功效。正式檢定方案需另外鎖定並外部預註冊。
7. 2024–2025是既檢視探索樣本；2026舊E3c協定不改、不加入E8。另立真正未見期間，資料collector品質通過後才決定收案與單次解盲規則。

## 通過後的精簡模型設計候選，尚未執行

價格固定P、歷史條件機率、P+source/metadata-only、P+情緒、P+事件、新聞/社群分別加入與合併；先收縮條件機率／正則LR，再考慮固定小搜尋樹模型。沒有樣本支持就不加入深度架構。

主要是next-open起算5日反轉配對Brier；同日期LogLoss、校準截距／斜率、同條件AUC及預先指定rank度量分開。H1檢驗semantic features是否超過metadata和價格；H3若融合，必須與同權重常數機率收縮和獨立調權重常數控制比較。H2不升為主要研究問題。固定train-only處理、purging與overlap-aware calendar block inference及整組Holm；不從多來源／延遲中挑最佳test。

嚴格資料不齊時，可另外提受限date-proxy探索case study，必須明確改題、揭露版本／來源缺漏與所有敏感度，不宣稱正式PIT或獨立驗證。E8a沒有執行這些模型。
''')
    (OUT / 'NEXT_STEPS.md').write_text('''# 下一步：先補證據，不先增模型

優先一：固定單一金融社群來源的小樣本資料契約。Stocktwits的cashtag與原生金融使用者標籤有研究動機，但需實際授權樣本確認日期、到達／編輯／刪除、標籤選樣和完整查詢範圍。官方備份端點存在不等於已擁有所有年份；不代購、不代寄信、不提交機構申請。

優先二：若走Reddit，先由教授與校方決定IRB／豁免、學術申請及每位研究者權限。以固定公司alias/subreddit查詢和刪除合規為條件；公開torrent／第三方存檔不能自行視為平台許可或完整原始版本。

優先三：不付費的近期工作，以現有E4、StockNet檔案metadata與StockEmotions的來源／日期／選樣／重複／時間契約稽核，發展可重現方法或資料品質工作稿。StockEmotions可支援有限的情緒標註方法檢查，不能用單年選樣集假裝多年反轉benchmark；StockNet單股舊語料不能替TSLA或2023–2025補齊。

優先四：另擬E8前瞻收集協定，固定來源/query、raw response hash、receipt、CID/version/edit/delete、collector uptime及故障處理；只在新協定明確鎖定後開啟新未見金融期間，先不啟動collector。與E7長期規劃及E3c2026協定各自管理，不事後追加模型。

完成資料與功效gate後才提出E8b正式執行方案；不要以更多新聞列數、增加LLM或任意加延遲取代歷史可得性與獨立樣本。現有證據尚無法回答社群是否有效，不能將來源缺失當負面預測結果。
''')
    (OUT / 'REPRODUCIBILITY.md').write_text('''# E8a重現與來源索引

Python3.10以上。現有環境完成，無新增安裝、無GPU、無model fit。

## 完整本機ZIP：離線metadata重播

解壓後於bundle根目錄：

```bash
python -B code/test_e8a.py
python -B code/e8a_replay.py --bundle . --output-dir ../e8a_replay_NEW
```

metadata輸入hash先核對，重算11份CSV與analysis_results。這不是重新取得原始全文、證明歷史PIT或重訓E4c；包內沒有新聞／貼文本文、原OHLCV或checkpoint。

`inputs/news_metadata.csv.gz`：來源、股票、版本hash、時間聲明及表示；不含標題／本文／URL明文。`social_metadata.csv`只有固定作者版本的股票／日期／hash；處理後／標註視圖不可加總。`stocknet_file_metadata.csv`只含日期檔名、大小和Git blob，不含貼文。`trading_sessions.csv`為凍結行情完整日期；`market_event_metadata.csv`另存purged評估事件及既存label，兩者不可混用。

`e8a_prepare.py`在原工作站由合法E4輸入重建metadata、本文hash與chunk加權檢查，不載入模型；重跑須設定`E8A_OUTPUT=outputs/e8a_NEW`使用新目錄，先以setup建立計畫並放入同hash的sources／social metadata，再執行prepare和analyze。固定來源擷取封包可由本bundle重用，不要求重查動態GitHub目錄。`e8a_fetch_social_metadata.py`為當次固定4作者CSV的有界取得程式，不是通用社群scraper。原資料大型檔與原授權不隨ZIP散布。

`audits/artifact_inventory.csv`：所有E4物理檔案清單與fresh／prior／metadata hash範圍。`canonical_input_manifest.csv`：實際row audit來源SHA。`sources/`：官方文件擷取、GitHub metadata和作者CSV回應hash／blob核對；工具轉出hash不冒充原HTTP。完整23GB主檔E4c EOF與SHA證據位於inputs，這次不重掃主檔。`tables/prior_prediction_inventory.csv`只盤點舊概率輸出，不重估成績。

## 公開GitHub：彙整一致性與合成契約

```bash
python -B scripts/e8a_public_replay.py --bundle research/E8a
python -B scripts/test_e8a.py
```

公開版不包含逐篇／逐貼metadata、本文、私人檔案清單或完整ZIP。只憑彙整不能重建來源真實性。圖表可由pandas/numpy/matplotlib對公開CSV重畫；完整版本記於environment.json。

## 統計範圍與圖表

E8a只做描述性資料稽核，沒有模型新loss、有效性p值、功效通過或因果結論。三圖分別為source-year保留列、PIT級別、價格事件與來源5session proxy重合；0保留列和100%窗口重合均不是觀測完整度。

原E4b／E4c結果仍使用原報告樣本、切分、過濾與統計計畫。E8a所有事件年分母為保留評估事件診斷，與E4b完整窗口分母不同；不回寫任何舊結果。來源與金融事件依賴不因多ticker／seed／視圖而變成獨立。
''')
    (OUT / 'README.md').write_text('''# E8a — News & Social PIT Feasibility Audit

**完成稽核；正式E8b NOT_READY。** 無新模型、無GPU、E3c2026未改未執行。

[完整報告](E8A_SUMMARY.md) · [PIT契約](DATA_CONTRACT_AND_PIT.md) · [E8b決策](E8B_FEASIBILITY_DECISION.md) · [下一步](NEXT_STEPS.md) · [重現](REPRODUCIBILITY.md)

[逐股逐年覆蓋](tables/source_stock_year_coverage.csv) · [PIT級別](tables/PIT_quality_by_source.csv) · [社群樣本](tables/social_author_dataset_coverage.csv) · [來源調查](tables/data_source_feasibility.csv) · [E8b閘門](tables/E8b_readiness_gates.csv)

448Apple、52摘要／36Gemini、FNSPID全掃描目標19,925列；StockEmotions處理後兩股33,268列與標註6,062列高度重合。L3/L4均0，監測coverage為NA，不能用大量列數取代歷史版本證據與獨立事件數。
''')
    print('6 E8a documents rendered')

if __name__ == '__main__':
    main()
