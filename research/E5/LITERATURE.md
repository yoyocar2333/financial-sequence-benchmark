# E5 文獻依據與固定研究選擇

查核日期：2026-11-02。文獻用來制定可重現的假說，不把其他市場／年代的結果當作本研究有效性的證明。

1. Brock, Lakonishok & LeBaron (1992). *Simple Technical Trading Rules and the Stochastic Properties of Stock Returns*. Journal of Finance 47,1731–1764. https://doi.org/10.1111/j.1540-6261.1992.tb04681.x
   以均線及交易區間突破提供可程式化基準的動機；本研究選20/60均線與前20日高低點，不宣稱精確重現其1897–1986 DJIA結果。
2. Lo, Mamaysky & Wang (2000). *Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation*. Journal of Finance55,1705–1765; NBER7613. https://www.nber.org/papers/w7613
   支持將主觀圖形轉成明確算法，再比較條件與無條件分布。其局部條件資訊不等於本研究已證明交易獲利。
3. Sullivan, Timmermann & White (1999). *Data-Snooping, Technical Trading Rule Performance, and the Bootstrap*. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=160330
   技術規則搜尋會產生選擇偏誤；本研究不搜尋規則門檻，只用固定小型集合，並報所有比較及多重校正。
4. Bajgrowicz & Scaillet (2012). *Technical trading revisited: False discoveries, persistence tests, and transaction costs*. Journal of Financial Economics106,473–491. https://doi.org/10.1016/j.jfineco.2012.06.001
   動機是分開處理預測差異、持續性與成本後績效；不把毛報酬當淨超額獲利。
5. Fidelity RSI technical definition: https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/RSI
   固定Wilder14與70/30，不針對股票或測試年改80/20；強趨勢可能持續超買超賣，因此加入狀態對照。
6. Fidelity MACD: https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/macd
   固定EMA12/26、signal9；同時保留規則方向與ATR標準化連續histogram。
7. Fidelity Bollinger Bands: https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/bollinger-bands
   固定20日均線±2個population SD；帶外不是必然反轉，與動能規則並列而非預設回歸。
8. Fidelity ADX generic definition: https://www.fidelity.com/viewpoints/active-investor/average-directional-index-ADX
   僅用一般定義：ADX>=25趨勢、<20盤整、20–25過渡；本研究不宣稱ADX代表漲跌方向。

## 有限、可識別的比較

- B：既有38維多尺度價格／波動資訊。T：B+12個價格／成交量技術表示+相對QQQ強弱1維。
- C：B+相對QQQ強弱。T與C的Logistic／XGBoost比較隔離新增來源與價格表示。
- 四種架構使用相同60日T序列資訊、相同候選數和expanding folds；B的已完成候選搜尋與預測只讀重用。
- Hybrid只用2個平滑專家、固定ADX gate及低維正則化Logistic；另用無interaction對照，不因測試結果擴大架構。
- 技術指標是歷史資料的轉換，不是獨立外生資訊；改善可能只是有限模型較容易利用的表示，不能直接解釋為新因果訊號。

## 文獻瀏覽中的保留期接觸紀錄

ADX網址由一般指標頁重新導向動態教育文章；工具在查核通用20/25門檻時，亦回傳一段關於2026年3月S&P500的行情敘述。該段不保存成研究行情、不作特徵、不用於模型、門檻或選模；本輪未讀取2026 AAPL／TSLA市場資料、新聞或驗證標籤。保留此事實供研究團隊存取稽核，不能聲稱所有2026公開敘述完全未接觸。既有E3c協定保持原雜湊。
