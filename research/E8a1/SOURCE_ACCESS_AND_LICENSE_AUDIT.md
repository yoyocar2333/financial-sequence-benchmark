# 來源存取、授權與成本稽核

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
