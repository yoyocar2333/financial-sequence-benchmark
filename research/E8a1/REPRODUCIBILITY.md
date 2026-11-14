# E8a.1重現說明

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
