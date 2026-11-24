# 教授補充建議核對與修改 — 2026-11-25

本輪以 PR #11 的第四輪 commit `d1f2d8b6c33e87582fe76ed3e26e2dfe5d1fcbe1` 為基準，不從舊工作論文覆寫會議稿。前版私有 Word/PDF 已備份。

| 補充建議 | PR #11 原狀態 | 本輪處理 |
| --- | --- | --- |
| 純摘要先交、摘要與背景再長一些 | 摘要134字、Introduction/Related Work158字；沒有獨立摘要交付檔 | 摘要194字、Introduction/Related Work244字；提供同步的單頁摘要Word/PDF及純文字 |
| Development Controls and Statistical Evaluation 放第二章 | 已經是2.4，不是缺項 | 保留2.4；補充XGBoost/LightGBM零值、重複價格、僅價格控制，以及前期選擇權重與分開校正家族 |
| 正文後段要有更多模型 | 技術表已有四模型；融合主表集中四個神經模型×股票設定，樹模型後文過簡 | 融合主表改列Logistic、XGBoost、LightGBM、LSTM、Mamba共十個股票/模型設定的raw/calibrated增益；解釋兩樹模型負結果，並補回匹配開發期數字 |

## 已補入正文的樹模型證據

所有數字是原表查值、確定性四捨五入，沒有重新選模或重算p-value。

- 校準後融合相對同權重常數：XGBoost AAPL/TSLA增益−0.000476/−0.000470；LightGBM−0.000311/−0.000530。主檢定block20、Holm20，這四個p均為1。主表保留其餘六個設定及全部raw負結果。
- 開發期會計值相對零值控制：XGBoost−0.000332、LightGBM+0.000149，兩個Holm6 p=1；相對重複價格為+0.000095/−0.001027。六個樹對照未出現校正後正增益，並非把模型未敘述當成未實作。
- 兩個AAPL神經模型正點估計及跨零CI、TSLA負結果、初始化限定效果、新聞主要未顯著/次要延遲敏感結果均保留。不同cohort、檢定家族不合併排名。

## 篇幅取捨與來源

維持模板字級、樣式和頁面邊界。為容納擴充文字和五模型比較，將原架構圖移至[補充材料](SUPPLEMENTARY_DESIGN_AND_EVIDENCE.md)；正文仍有四張表，包括跨實驗統整表。完整逐種子校準係數、先前主表及全部CI保留於原補充路徑。把「logits clipped」改成先截斷機率再取logit，明確表達既有實作，沒有變更校準器。

文獻擴充沿用已核實的12篇，沒有增加無法核對的引文。2026-11-25重新查閱[Gu作者論文](https://dachxiu.chicagobooth.edu/download/ML.pdf)、[Xu/Cohen ACL原文紀錄](https://aclanthology.org/P18-1183/)、[Glasserman/Lin預印本](https://arxiv.org/abs/2309.17322)。其他引文之先前驗證見[第四輪文獻稽核](../round4/LITERATURE_EXPANSION_AUDIT.md)。

[Engineering Proceedings instructions](https://www.mdpi.com/journal/engproc/instructions)本次查證仍建議摘要約200字上限；194字的同一段文字用於全文及摘要檔。[ICEIB官網](https://www.iceib.asia/)公開頁未核實單獨摘要欄位/檔案限制；不宣稱已通過尚未開放或未確認的系統驗證。作者、單位、六項聲明沿用已確認版本。

使用者另外授權可新增訓練；本次三項問題已有完整模型及控制組結果可支援，沒有為豐富敘述而新增模型搜尋。所有新增模型/校準器fit及2026金融評估均為0。PR只更新，不合併main或自行投稿。
