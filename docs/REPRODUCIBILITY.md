# 重現層級與可執行入口

## 1. 公開表格與圖表：clone後可直接重建

使用Python3.10或相容版本與[public-cpu.txt](../requirements/public-cpu.txt)。這是本次CPU檢查使用的套件組合；不需要torch、GPU、API金鑰或下載資料。

```bash
python scripts/reproduce_public.py --output-dir outputs/public_replay
python -m unittest discover -s tests -p 'test_public*.py' -v
python scripts/validate_publication.py
```

`reproduce_public.py`重新由20筆E1 seed指標計算均值／樣本SD，核對E3b／E3c／E4c／E5主要數字、檢定家族與FNSPID總數，重畫四張核心比較圖。輸出目錄須不存在，避免覆寫。它不訓練，也不宣稱從彙整表重跑出原始模型或bootstrap。

## 2. E3b／E5單模型完整重現：需合法凍結行情

自行提供[凍結雜湊清單](FROZEN_INPUTS.csv)的市場檔案於repo外的目錄，包括股票與QQQ／VIX／VXN的`*_adjusted_through2025.csv`。欄位為Date、Open、High、Low、Close、Volume（依來源可少部分非股票欄），日期不得超過2025。原始未調整檔的hash亦列供獨立稽核；本入口驗證所需調整檔，沒有偷偷以重新下載替代。

```bash
# 另用測試過的樹模型環境（見下），指向自己的外部行情目錄。
python scripts/run_public_model.py --stage E5 --ticker AAPL \
  --model xgboost --arm T --seed 42 \
  --market-dir /path/to/authorized/frozen-market \
  --output outputs/e5_AAPL_xgboost_T_seed42
```

此公開adapter不需要舊checkpoint或原工作站絕對路徑；用已固定selected_configs、同一因果特徵／日期／早停／校準重新fit一個模型，保存完整輸出至忽略目錄。E3b可選A／B，E5可選B／T；輸出必須全新。資料hash不同即停止，不能稱原實驗重現。

LSTM／Mamba另需相容CUDA環境，並明確加`--allow-gpu`；不支援fallback或靜默CPU Mamba。使用單一GPU鎖、10% allocator、duty50%，實際CUDA錯誤停止自己的run，沒有永久提權、sudo或終止他人程序。新資料或不同硬體可有浮點差異，不能保證跨GPU逐bit一致。

## 3. 原完整研究流程與新聞處理：需非公開研究資產

[程式入口索引](../scripts/RESEARCH_CODE_INDEX.md)保留各階段原研究runner與分析。它們有保護舊結果及來源hash的設計，不能在空repo自動重建那些私有依賴；若擁有完整合法工作站archive，可按其相對inputs／outputs結構使用。不要修改manifest使新資料冒充舊快照，也不要刪除原成果來強迫重訓。

- E1單模型可用`run_mamba_e1_e2b_own_safety.py --plan`先查看；實訓另需原market-dir、所有特徵與CLI明確參數，見原runner。batch8／seq60／loss等不能換成E3b設定。
- E3a、E3c原runner保護前階段模型及輸出；`e3a_core`／`e3c_core`與公開設定保留算法，可在自有資料上建立新研究，但不等於原日期／版本重現。
- E4a／E4b需要合法新聞語料、外部stockllm方法程式及凍結FinBERT特徵；文章與API輸出沒有附在repo。
- E4c原`replay_e4c.py`在有原合法archive時會重訓CPU模型，不適用只有此公開repo的情況。
- E5原`replay_e5.py`需要完整私有archive與checkpoint作完整性檢查；本次已在工作站通過CPU重播，但checkpoint未公開。空repo改用第1層，單模型重fit用第2層。

## 測試過的環境與安裝限制

原GPU／模型環境：Python3.10.12、torch2.6.0+cu124、mamba_ssm2.2.4、causal_conv1d1.5.0.post8、triton3.2.0、numpy1.26.4、pandas2.2.3、scipy1.15.2、scikit-learn1.6.1、xgboost-cpu3.0.5、LightGBM4.6.0。RTX4090真Mamba CUDA forward/backward已通過原研究smoke。

[gpu-tested.txt](../requirements/gpu-tested.txt)是版本記錄，不是通用的一行安裝保證。torch的cu124 wheel需正確官方index，Mamba／causal-conv1d extension需匹配Python／torch／CUDA／C++ ABI；依官方套件說明在獨立環境準備，不修改既有環境或系統CUDA。樹模型CPU重現只需public-cpu加已列的XGBoost／LightGBM，不必安裝Mamba。

原E0的[requirements.txt](../requirements.txt)與notebook原樣保留，不能當E1–E5的精確lock。新聞抽取的transformers／spaCy等為可選資料處理依賴，不影響第1層檢查。

## 未執行事項

此次GitHub整理不重新訓練模型、不重新下載行情／新聞、不載入checkpoint、不執行2026。單模型adapter只是新增重現入口，其GPU及資料fit功能須由使用者明確呼叫；本次僅用合成資料驗證其計算／日期路徑，沒有將新fit混入已完成結果。


## E6／E7a公開版

E6報告、主要彙整、設定、圖表與程式已加入；原始文件／私有預測／checkpoint不公開，完整模型重現仍需合法相同輸入。E7a不訓練新模型，使用公開季度彙整可離線重算power_design_grid、power_simulation、required_period_scenarios、synthetic_method_controls四表；`scripts/e7a_public_replay.py --bundle research/E7a --output-dir outputs/e7a_replay`。PIT原型八測試：`E7A_OUTPUT=research/E7a python scripts/test_e7a.py`。

E7a development_audit／evidence_audit腳本需舊工作站資產，不是從公開repo直接下載完整資料的工具。E7a文件、功效及合成反例重現不等於完成外部預註冊／驗證。
