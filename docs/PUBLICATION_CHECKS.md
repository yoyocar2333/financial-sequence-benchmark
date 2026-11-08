# Public release checks

```bash
python scripts/validate_publication.py
python scripts/reproduce_public.py --output-dir outputs/public_replay
python -m unittest discover -s tests -p 'test_public*.py' -v
git diff --check
```

檢查範圍包括：來源及公開檔案hash、E0原檔未變、Python語法／本地import依賴、相對Markdown連結、檔案大小／類型、私有路徑／秘密格式、逐篇新聞欄位排除、公開資料數字與主要結論一致性。這不是對歷史科學結果的獨立再訓練驗證，也不能保證所有未知敏感格式均被工具發現，仍需人工審閱。

公開原圖均為研究者生成的統計圖；PNG文字metadata另作檢查。沒有原始新聞截圖、文章正文、金融網站圖片或附帶checkpoint的ZIP。

PR的驗證記錄應註明實際通過項目。2026協定只保留原文與SHA，沒有用2026資料做本次檢查。原E0 notebook、RESULTS.md與requirements.txt沒有改寫，README舊版另存E0。

## 本次執行記錄（2026-11-02）

- 5個CPU測試通過：公開數字重聚合、Wilder／未來擾動不變性、合成行情下單模型adapter與原array路徑等價、無GPU旗標與不同資料hash拒絕、配對日曆推論。
- 公開重建程式通過，重畫E1／E2、E3b、E4c、E5共4張核心圖；沒有訓練模型或下載資料。
- 190個複製來源hash核對、156個相對Markdown連結及67個Python檔案語法檢查通過；公開檔案約7.2MB。
- 原E0三個科學檔案byte-identical；原2026協定核對12個locked檔案通過，回報FROZEN_NOT_EXECUTED、2026_data_loaded=false。
- 27張原研究PNG只含Software／dpi metadata；沒有工作站路徑、文章圖片或原始資料。
- 外部新聞Repository與兩個固定revision已確認可讀。外部金融／論文網址保留來源，不宣稱所有網站均容許自動HEAD或下載。

這些是發布與算法回歸檢查，不是E0–E5模型重新訓練或獨立確認性驗證。
