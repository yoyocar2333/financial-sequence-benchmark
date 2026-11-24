# Calibration Audit — Archived Coefficients and Frozen Probabilities

六條 AAPL 管線（LSTM/Mamba × Price/Fusion/Constant），各五個 seeds42–46，共30組保存的斜率與截距已核對。這是固定機率的描述性驗證，沒有重新訓練金融模型或擬合校準器，沒有新p-value／CI。

## Evidence and estimator

Coefficients come from the frozen [E6 calibration metadata](../../E6/results/calibration_parameters.csv). Price-pipeline coefficients additionally agree with the contemporaneous E5 per-seed `calibration.json` artifacts. E6's historical metadata-name collision and its already-completed name repair are disclosed in the source audit; we do not rerun that repair or refit its calibrators. Instead, directly applying saved a,b to frozen raw logits reproduces every evaluated probability, maximum absolute error2.220446049250313e−16. No slope is inferred merely from an aggregate AUC change.

Each pipeline uses482 identical AAPL dates,255 reversals/227 nonreversals and106 calibration observations from2023H2. The rule is sigmoid(a×logit(clip(p,1e−6,1−1e−6))+b), using C=1 L2-regularized logistic regression in the historical fit; intercept is unpenalized under that solver. Current validation only applies the saved map.

Overall AUC, Brier and population SD are computed within each seed and then averaged equally across five seeds. They are **not** scores of the seed-mean probability ensemble. The E9b public per-seed and aggregate tables reproduce these values to1e−12. Within-state AUC averages the same-cell concordance kernel across seeds, weighted by the7627 eligible positive-negative pairs in fixed past-direction×long120-ex5×VIX cells; it is not an unweighted mean of cell AUCs. Archived calibrated Price/Fusion values agree. Constant-control and raw within-state entries are descriptive recomputations under the same definition, with no added tests.

## Six-pipeline summary

| method | slope_min | slope_max | negative_slopes | raw_Brier | calibrated_Brier | raw_AUC | calibrated_AUC | raw_SD | calibrated_SD | raw_within_state_AUC | calibrated_within_state_AUC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lstm_Late | 0.066202241 | 0.490017219 | 0 | 0.256221055 | 0.246922197 | 0.583474130 | 0.583474130 | 0.055115728 | 0.019635633 | 0.520047201 | 0.520047201 |
| lstm_P | 0.477750938 | 1.094339367 | 0 | 0.259238287 | 0.251126860 | 0.551472748 | 0.551472748 | 0.102242350 | 0.086365057 | 0.562318081 | 0.562318081 |
| lstm_PriorBlend | 0.260835859 | 1.017081985 | 0 | 0.253386697 | 0.247902173 | 0.551472748 | 0.551472748 | 0.025560588 | 0.021961316 | 0.562318081 | 0.562318081 |
| mamba_Late | -0.159788787 | 0.552359847 | 1 | 0.257093297 | 0.247623148 | 0.573053468 | 0.549748640 | 0.057528777 | 0.021147154 | 0.506516324 | 0.523325030 |
| mamba_P | -0.303688399 | 0.781531726 | 1 | 0.265445059 | 0.252110585 | 0.534324955 | 0.521737929 | 0.114192390 | 0.064149480 | 0.547659630 | 0.545588042 |
| mamba_PriorBlend | -0.234710667 | 1.027238042 | 1 | 0.254174306 | 0.248821546 | 0.534324955 | 0.521737929 | 0.028548097 | 0.021203034 | 0.547659630 | 0.545588042 |

## Ranking interpretation

All fifteen LSTM slopes are positive. Its fusion raw/calibrated mean overall AUC is0.583474129740 in both versions (rounded0.583474). In Mamba, seed46 is negative in **all three** pipelines; seeds42–45 are positive. For Mamba fusion seed46, a=-0.159788786930, b=0.029661492081, raw AUC0.558262 and calibrated AUC0.441738. Its four positive-slope seeds preserve their AUC; averaging those with the reversed seed gives0.573053→0.549749. The exact coefficients, not a mean-AUC guess, verify this account. Every single-seed AUC matches AUC_raw for a>0 or1−AUC_raw for a<0, to1e−12.

For fusion, mean Brier falls0.256221→0.246922 (LSTM) and0.257093→0.247623 (Mamba), but this does not itself isolate new information. Against separately calibrated same-weight constant controls, the familiar benefits remain0.000980/0.001198 with pointwise block60 intervals crossing zero. Overall and within-state ranking measure different comparisons: Mamba fusion within-state mean AUC rises0.506516→0.523325 while its overall mean AUC falls. Neither is a new significance result.

Calibration changes bias/dispersion and can reverse a seed's ranking. We verify the ranking mechanism; we do not causally identify which component causes the sign of the calibrated Brier comparison. Binning, finite-sample calibration estimates and independent complete-pipeline maps prevent that stronger attribution.

## Complete per-seed coefficients and scores

P denotes Price; Late denotes Accounting Fusion; PriorBlend denotes Same-weight Constant Shrinkage. These source codes are only used in complete audit tables.

| method | seed | a | b | raw_Brier | calibrated_Brier | raw_AUC | calibrated_AUC | raw_within_state_AUC | calibrated_within_state_AUC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lstm_Late | 42 | 0.066202241 | 0.093311946 | 0.258119582 | 0.248855315 | 0.562632806 | 0.562632806 | 0.480923037 | 0.480923037 |
| lstm_Late | 43 | 0.490017219 | 0.213447820 | 0.254603174 | 0.246044914 | 0.590826639 | 0.590826639 | 0.541366199 | 0.541366199 |
| lstm_Late | 44 | 0.436946911 | 0.197494294 | 0.259104264 | 0.246916864 | 0.585367539 | 0.585367539 | 0.530352694 | 0.530352694 |
| lstm_Late | 45 | 0.238154361 | 0.135944139 | 0.255277381 | 0.247752791 | 0.559955083 | 0.559955083 | 0.492329881 | 0.492329881 |
| lstm_Late | 46 | 0.457775330 | 0.209487768 | 0.254000875 | 0.245041102 | 0.618588581 | 0.618588581 | 0.555264193 | 0.555264193 |
| lstm_P | 42 | 0.477750938 | 0.145853982 | 0.257617921 | 0.248633309 | 0.540468170 | 0.540468170 | 0.540448407 | 0.540448407 |
| lstm_P | 43 | 1.094339367 | 0.305779571 | 0.258502773 | 0.257097570 | 0.548484063 | 0.548484063 | 0.582404615 | 0.582404615 |
| lstm_P | 44 | 0.717337314 | 0.221210350 | 0.277505293 | 0.258863987 | 0.525386542 | 0.525386542 | 0.565097679 | 0.565097679 |
| lstm_P | 45 | 0.825932621 | 0.148359666 | 0.250967371 | 0.248088201 | 0.544389738 | 0.544389738 | 0.544512915 | 0.544512915 |
| lstm_P | 46 | 0.778985062 | 0.276220840 | 0.251598076 | 0.242951231 | 0.598635225 | 0.598635225 | 0.579126786 | 0.579126786 |
| lstm_PriorBlend | 42 | 0.260835859 | 0.120424337 | 0.254884311 | 0.249091798 | 0.540468170 | 0.540468170 | 0.540448407 | 0.540448407 |
| lstm_PriorBlend | 43 | 1.017081985 | 0.263802076 | 0.252549068 | 0.247782048 | 0.548484063 | 0.548484063 | 0.582404615 | 0.582404615 |
| lstm_PriorBlend | 44 | 0.888026138 | 0.237772736 | 0.256032036 | 0.249143244 | 0.525386542 | 0.525386542 | 0.565097679 | 0.565097679 |
| lstm_PriorBlend | 45 | 0.597076771 | 0.168662792 | 0.252508547 | 0.248465590 | 0.544389738 | 0.544389738 | 0.544512915 | 0.544512915 |
| lstm_PriorBlend | 46 | 1.000413054 | 0.271010156 | 0.250959523 | 0.245028185 | 0.598635225 | 0.598635225 | 0.579126786 | 0.579126786 |
| mamba_Late | 42 | 0.234158795 | 0.132031352 | 0.257080675 | 0.247983443 | 0.568109182 | 0.568109182 | 0.500852235 | 0.500852235 |
| mamba_Late | 43 | 0.213209599 | 0.129557704 | 0.255506277 | 0.247997691 | 0.567660016 | 0.567660016 | 0.499541104 | 0.499541104 |
| mamba_Late | 44 | 0.552028447 | 0.245300402 | 0.257633003 | 0.245133494 | 0.591776799 | 0.591776799 | 0.550937459 | 0.550937459 |
| mamba_Late | 45 | 0.552359847 | 0.209831192 | 0.257818112 | 0.246542986 | 0.579459273 | 0.579459273 | 0.523272584 | 0.523272584 |
| mamba_Late | 46 | -0.159788787 | 0.029661492 | 0.257428417 | 0.250458127 | 0.558262071 | 0.441737929 | 0.457978235 | 0.542021765 |
| mamba_P | 42 | 0.650488358 | 0.105082378 | 0.256627736 | 0.250363848 | 0.522346031 | 0.522346031 | 0.549757441 | 0.549757441 |
| mamba_P | 43 | 0.583849715 | 0.130934727 | 0.254014119 | 0.249181613 | 0.532642308 | 0.532642308 | 0.557362003 | 0.557362003 |
| mamba_P | 44 | 0.368881207 | 0.202685158 | 0.289834458 | 0.249659779 | 0.549641531 | 0.549641531 | 0.560770945 | 0.560770945 |
| mamba_P | 45 | 0.781531726 | 0.119822568 | 0.271109400 | 0.259977420 | 0.535527339 | 0.535527339 | 0.565228792 | 0.565228792 |
| mamba_P | 46 | -0.303688399 | 0.006590898 | 0.255639585 | 0.251370265 | 0.531467565 | 0.468532435 | 0.505178969 | 0.494821031 |
| mamba_PriorBlend | 42 | 0.558832357 | 0.156946604 | 0.254132483 | 0.249041871 | 0.522346031 | 0.522346031 | 0.549757441 | 0.549757441 |
| mamba_PriorBlend | 43 | 0.512804862 | 0.156271879 | 0.253168055 | 0.248853296 | 0.532642308 | 0.532642308 | 0.557362003 | 0.557362003 |
| mamba_PriorBlend | 44 | 0.845024964 | 0.253644891 | 0.254758028 | 0.247524206 | 0.549641531 | 0.549641531 | 0.560770945 | 0.560770945 |
| mamba_PriorBlend | 45 | 1.027238042 | 0.227261320 | 0.254826502 | 0.249110925 | 0.535527339 | 0.535527339 | 0.565228792 | 0.565228792 |
| mamba_PriorBlend | 46 | -0.234710667 | 0.030980593 | 0.253986463 | 0.249577431 | 0.531467565 | 0.468532435 | 0.505178969 | 0.494821031 |

## Binned probability diagnostics and provenance

[CALIBRATION_DECOMPOSITION.csv](tables/CALIBRATION_DECOMPOSITION.csv) preserves120 seed×stage×binning rows (ten/five bins): REL, RES, UNC, signed G and continuous/binned scores. Every component agrees with the archived E9b decomposition to1e−12; per-row identities hold. [Per-seed table](tables/CALIBRATION_PER_SEED.csv) includes probability replay error, status and coefficient-evidence type. [Summary](tables/CALIBRATION_SUMMARY.csv) includes SD and ranking definitions.

[Source manifest](tables/CALIBRATION_SOURCE_MANIFEST.csv) hashes the private frozen prediction archive, named coefficients, price JSONs and relevant methods. Raw daily probabilities/checkpoints remain private. Public aggregate replay can check coefficients and metrics against the source commit; full per-probability replay requires lawful frozen inputs. [Validation report](audits/CALIBRATION_VALIDATION.json) records the actual computation; it is not independent human QA or PIT certification.
