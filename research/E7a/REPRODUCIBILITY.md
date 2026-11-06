# E7a重現與稽核邊界

本階段沒有新的金融模型訓練、GPU工作、2026驗證或2024–2025選模。可公開重現：季度彙整輸入的功效算術、合成控制、PIT契約測試、文獻及主張帳本。不能僅靠彙整CSV重建全部舊模型、驗證vendor承諾或取得原始授權資料。

本地既有環境（不需安裝）：

```bash
.venv-e3b/bin/python -B scripts/test_e7a.py
E7A_OUTPUT=outputs/e7a_20261106 .venv-e3b/bin/python -B scripts/e7a_public_replay.py --bundle outputs/e7a_20261106 --output-dir outputs/e7a_replay_new
```

完整從既有開發期結果重算需原E5／E6受限輸入與固定CV檔：使用新的`E7A_OUTPUT`執行`e7a_development_audit.py`，再執行literature、evidence與write_design；不可覆寫已封存目錄。來源CSV副本只有≤2022，雖檔名保留through2025以相容舊loader。`audits/power_input_manifest.csv`記錄實際日期與SHA。公開版只帶季度彙整，不帶市場／新聞／checkpoint。

315份舊報告／結果／protocol成員由`protected_prior_artifacts.json`逐檔驗證；既有E3c2026協定不變。本輪設計初稿5對比與改成6的原因均保留。CPU測試涵蓋時鐘、版本修訂、重疊標籤、共同衝擊功效下界及假資訊增益反例；這些測試不是新市場訊號的證據。
