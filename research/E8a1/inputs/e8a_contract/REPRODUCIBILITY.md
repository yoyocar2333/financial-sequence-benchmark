# E8a重現與來源索引

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
