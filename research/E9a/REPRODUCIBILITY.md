# Current E9b manuscript reproduction

## 1. Public aggregate replay

只讀公開aggregate，重建目前論文、319主張及40文獻。無下載、金融訓練或2026資料。需要已有Python3.10、numpy/pandas/scipy/scikit-learn；`--figures`另需既有matplotlib。版本見E9b checks/environment.json。不要在frozen bundle內執行舊擷取器。

```bash
python -B scripts/e9a_validate.py --bundle research/E9a
python -B scripts/test_e9a.py
python -B scripts/test_e9b.py
python -B scripts/e9a_reproduce.py --bundle research/E9a --out /tmp/e9b_replay_NEW --figures
```

舊入口依 `MANUSCRIPT_VERSION.json` 轉到E9b。`e9a_build.py`拒絕覆寫目前E9b；下次建稿會繼續用目前模板與新分析，不會恢復E9a。

Word從同一Markdown重建（既有python-docx）；PDF需要已有LibreOffice UNO及中文字型。工具不自動安裝。例：

```bash
python -B scripts/e9b_docx.py --out /tmp/e9b_replay_NEW
python -B scripts/e9a_render_pdf.py --out /tmp/e9b_replay_NEW --program /PATH/TO/EXISTING/libreoffice/program
python -B scripts/e9b_document_check.py --bundle /tmp/e9b_replay_NEW
```

## 2. Private frozen-source no-refit replay

公開表格可核對逐格來源，但不能獨立由公開資料重算所有私人逐日結果。工作站合法保存的frozen snapshots、原預測及新fit係數／native模型供 `e9b_full_replay.py` 重算35張表、24LR／36tree／6Ridge預測並重建稿件；此replay不新增fit。已執行紀錄在E9b checks/full_replay_report.json。需要原私有資料，不會自行下載或造資料。

```bash
python -B scripts/e9b_full_replay.py --source-root /PATH/TO/PRIVATE/PROJECT --private-frozen-run /PATH/TO/e9b_20261115 --out /tmp/e9b_private_replay_NEW --repo .
```

## 3. Supplementary fit reproduction

新模型僅使用截至2022的cutoff inputs；分析計畫先鎖定，樹模型addendum在LR診斷後、樹模型fit前鎖定，完整保留時序。`e9b_technical.py`、`e9b_development.py`與`e9b_tree_controls.py`需私有來源與計畫hash；不允許無來源時虛構重現。設定環境 `E9B_SOURCE_ROOT`、`E9B_OUTPUT`，依計畫重建至新輸出；本輪對既有輸出重播一律用 `E9B_NO_REFIT=1`。沒有新神經訓練／GPU／2026驗證。

## 公開邊界

程式、作者撰寫論文、aggregate表及原創PNG可公開。原始行情／新聞／社群、逐文章manifest、逐日私有預測、checkpoint、係數／native weights及完整工作站archive不公開。檔案完整性與工程測試不等於歷史PIT或獨立人工QA認證。
