# E7b完整與公開重現

完整本機bundle保存來源工具轉出、historical-only行情arrays、來源manifest、設定、audit結果與程式快照。原始Yahoo envelopes可能帶當期quote，留在本機quarantine；ZIP排除所有`.bin`。既有受保護成果與原2026協定不改。

使用現有`.venv-e3b`（Python3.10、numpy／pandas等既有套件），不需安裝或GPU：

```bash
.venv-e3b/bin/python -B scripts/test_e7b.py
.venv-e3b/bin/python -B scripts/e7b_replay.py --bundle outputs/e7b_20261107 --output-dir outputs/e7b_replay_new
```

從完整ZIP解壓後，在bundle目錄：

```bash
python code/e7b_replay.py --bundle . --output-dir ../e7b_replay_new
python code/test_e7b.py
```

replay以保存的web轉出及已排除當期quote欄的2012–2022資料，重算稽核／描述統計與as-of，逐表比對。它不是重新下載原始SEC或證明歷史PIT；raw來源當前未取得，其缺口不可由replay成功填補。

公開GitHub版不包含完整行情、web全文、quarantine或私人環境，提供`e7b_public_replay.py --bundle research/E7b`核對公開彙整、時間診斷、gate狀態與23項合成測試。不能僅靠公開彙整重建完整行情相關或原申報數值；這個範圍明確區分。

原始SEC manifest／時鐘／版本registry將來補齊後，可用`e7b_build_asof.py`產生特徵；工具要求新的輸出目錄、source raw SHA與verification records。當前空facts已生成880個拒用query，沒有填造數據。完整程式例：

```bash
python scripts/e7b_build_asof.py --bundle outputs/e7b_20261107 --facts outputs/e7b_20261107/derived/normalized_verified_facts.json --source-registry outputs/e7b_20261107/derived/authenticated_source_registry.json --queries outputs/e7b_20261107/derived/asof_strict_calendar_queries.csv --output-dir outputs/e7b_asof_new
```

E7a方案、來源SHA、研究成果382份保護檔與E3c2026協定將在finalize時重新逐檔核對。無新模型搜尋、無2024–2025最優組合尋找、無2026驗證、無外部預註冊申報。
