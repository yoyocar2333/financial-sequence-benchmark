# 文獻定位與實際閱讀範圍

查證日期：2026-11-15。保留 E9a 原32項引用，加8項，共40項。原文獻與 DOI 修正紀錄保留；新增六筆 Crossref metadata 的標題、作者與 primary record 比對，另兩筆依作者／正式 proceedings。這是問題導向補充查閱，並非有登錄搜尋式、雙人篩選的系統性回顧。

|議題／最接近研究|已知內容|本研究完成的比較與差異|閱讀證據與界線|
|---|---|---|---|
|R33 Ranjan & Gneiting (2010)|線性機率池與校準關係；概率合併並非新方法|同權重常數混合、raw/calibrated、逐seed、metadata與同維價格對照一起呈現|[出版社](https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-9868.2009.00726.x) abstract／作者 primary 摘要；不宣稱發明收縮|
|R34 Claeskens et al. (2016)|估計合併權重的不確定性及組合謎題|將固定開發期分支選擇拆為冷啟動與後續相同component，揭示C6來源|[出版社](https://www.sciencedirect.com/science/article/pii/S0169207016000327)摘要與metadata；不是因果機制識別|
|R35 Bröcker (2008)、R36 Dimitriadis et al. (2021)|機率可靠度估計、可靠度圖穩定性|以固定5/10bin保留連續預測的signed grouping remainder；逐seed及ensemble分開|[AMS](https://journals.ametsoc.org/abstract/journals/mwre/136/11/2008mwr2329.1.xml)、[作者稿](https://arxiv.org/abs/2008.03033)；沒有執行CORP或聲稱提出新分解|
|R39 Xu & Cohen (2018)、R40 Ding et al. (2015)|價格與tweets聯合、事件驅動股票預測已有先例|Apple issuer-news中的密度→情緒→事件結構控制，對照時間敏感性與歷史版本證據|[ACL](https://aclanthology.org/P18-1183/)、[IJCAI](https://ijcai.org/proceedings/2015/329)正式摘要／方法段；不同資料、任務，沒有直接模型排名|
|R37 Drinkall et al. (2024)、R38 Glasserman & Lin (2023)|時間特定語言模型與金融GPT情緒的look-ahead問題|內容版本、來源public時間、vendor arrival、retrieval及參數訓練截止分開記錄|[ACL](https://aclanthology.org/2024.findings-naacl.208/)、[作者預印本](https://arxiv.org/abs/2309.17322)；本研究沒有重新測量LLM參數污染|

## 新穎性的合理範圍

貢獻是跨三個具名cohort的實證控制與診斷：技術表示的相關／前向重建落差；基本面raw/calibration及同權重常數、同維metadata／重複價格控制；密度與情緒增量及版本資格的連結。個別工具、機率收縮、合併、校準與PIT概念均有既有研究。未建立全球首次、普遍無效或新演算法的主張。不同任務不合併分數排行。

## 書目界線

R38引用實際查閱的2023 arXiv版本，其DOI為預印本DOI；作者頁另列2024 Journal of Financial Data Science 6(1),25–42，未補入未核對的journal DOI。R40使用正式proceedings URL、不造DOI。R18原未解析識別仍不冒充DOI。全文40項狀態、URL、日期見 `../E9a/literature/citation_audit.csv`。metadata核對不等於全文重現，也不是獨立同儕審查。
