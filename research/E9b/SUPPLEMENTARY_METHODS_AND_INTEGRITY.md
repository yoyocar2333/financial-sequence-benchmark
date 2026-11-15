# Supplementary methods, evidence and integrity

This supplement supplies the methodological and project records associated with the single revised manuscript. Original research artifacts retain their identifiers and numerical results. The current manuscript is kept at `research/E9a/PAPER_DRAFT.*`; E9b tables contain separately labeled exploratory additions.

## S1. Original study registry

|Original stage|Outcome and cohort|Role in the revised article|
|---|---|---|
|E0|Legacy stock/price forecasting|Historical motivation; original notebook/results retained|
|E1–E2|Next-day100×absolute log return; Mamba E1/E2b, five seeds;501 common dates per stock|Magnitude differs from direction; not pooled with classification losses|
|E3a|Close-to-close post-event returns, fixed training quantiles, horizon-spaced events|Origin of acute-move/trend diagnostics; not the executable classifier label|
|E3b–E3c|Next-open reversal classification;482 common dates per stock; event/within-state evaluation|Task definitions and price baselines;102 primary comparisons inE3b; separate event-study families|
|E4a–E4b|Recovery of52 summaries/36Gemini joins and448 reconstructed Apple articles|Text coverage and version history; original36joins refer to the summary version|
|E4c|2023fit/2024selection+calibration/2025explored;224/232/230dates;28/36/65events|Apple P8/D10/S12/T16 and hierarchical probabilities; two-comparison families remain separate|
|E5|2012–22fit,2023stopping/calibration,2024–25explored;B38/T51/C39|Technical representations, bounded model grid,8main feature comparisons|
|E6|Same market dates,118 issuer vintages,45training vintages per stock,9test-used including8newupdates|Numerical fundamentals, early/late fusion and matched constant;8H1/20H3reversal comparisons|
|E7–E8a.1|Research design,20companyprototype,source/news/social evidence pilot|Temporal/identity/license and human-QA requirements; no E8b prediction evidence|

Original classification neural fits use batch64, unlike the earlier magnitude batch8 experiment. All E9b new fits are CPU-only. The fundamental neural contribution remains the archived genuine price model in late fusion; the original100-vintage gate prevented a new numerical-fundamentals neural encoder. New matched controls use originalLogistic/XGBoost/LightGBM candidate0 settings rather than create a new neural comparison.

E5/E6 use unconstrained C1 ridge Platt calibration on the original2023H2 calibration period. E4c uses its original identity-prior, monotone calibration and reuses2024 for selection and calibration. These differences are retained within their original cohorts. AUC may reverse under a negative calibration slope in E5/E6; raw/calibrated source values are therefore both retained. No calibration is fitted using2024–2025 in the new development controls.

## S2. Technical representation analysis

`ANALYSIS_PLAN_LOCKED.json` predates numerical computation. Original adjusted market snapshots are hashed and cut at2022-12-31 before building features. Pre2012 prices provide causal warm-up. Training-period Spearman uses every finite2012–2022 row; all51 features and all13added targets are retained. Average-linkage distances are1−|rho|; constant correlations remain marked rather than interpreted as independence.

A fixed Ridge penalty10 maps B38 to the contemporaneously available technical feature on the same date. “Forward” describes the time split, not a future technical-indicator target. Training scalers and target scales are fitted per sourcefold; evaluation covers2017–18/2019–20/2021–22. There are six multivariate Ridge fits, with R² and train-SD-normalized RMSE for every target/fold. Negative R² records poor transfer of this fixed linear mapping. High correlation and even high reconstruction do not themselves estimate conditional reversal information.

`technical_representation_joint.csv`, the fullmatrix/linkage tables and seven supplementary graphics preserve all results. `complexity_and_seed_stability.csv` reads100 existing fit-info documents with their original completion hashes; it does not load or retrain neural checkpoints.

## S3. Archived fusion diagnostics

Every retained forecast is validated against its original stock/date/label/version. Recomputed mean Briers agree across88source metric groups. Per-seed losses are principal; ensemble plots are a separate, labeled probability estimator. Seed variability is conditional on the same market path.

Fixed10bins and5bins partition [0,1]. For each bin, the binned probability score satisfies REL−RES+UNC; the original continuous score additionally contains the signed grouping remainderG in Equation(3). Terms are averaged across seeds after individual decomposition. The exact identity residual and binned score are published. These empirical terms depend on bins and sample outcomes; they are not unbiased population information estimates.

Raw Equation(2) is computed on float64 reconstructed mixtures. Source archives can retain float32 intermediate products; `archive_rounding_max` records the discrepancy, constrained to four float32epsilons. The original archived Briers and interval data remain unchanged. Source weights, common compact F, training constant and allten stock/expert combinations are used, with no refitting. Separate calibration maps mean that calibrated outputs are not treated as a linear mixture of calibrated components.

New pointwise block60intervals use4999calendar-block replicates and the same date-paired seed-mean loss estimator; no new hypothesis p-values are created for these archived comparisons. The original corrected p-values and originalblock20intervals remain in their source tables. Full probability concentration, ten-/five-bin components, reliability bins, mixture identities and all settings accompany the neural examples in the article.

## S4. Development-only matched controls

### S4.1 Initial locked analysis

The initial plan was locked2026-11-15T10:22:57UTC. New Logistic fits use C=.001,lbfgs,tol1e−4,seed42,max500iterations. A predeclared convergence-only retry would retain the objective and increase the iteration cap to2000; no such hyperparameter search is allowed. There are18matched input fits plus6compact metadata fits.

P is the archived candidate0 T51 input. Each matched arm appends the same8metadata fields and then7numerical accounting values,7zeros, or the7fixed standardized duplicates past5/20/60/120,RV5/RV20,Close. All arms have60×66 inputs. Numerical/metadata preprocessing uses each training cutoff; the compact metadata expert uses age,flags and common direction. Original producer labels and label-end dates are checked against regenerated development calendars before reusing candidate0P/F predictions.

The three development evaluations contain1450dates per stock and24common calendar quarters. A calendar quarter is not a newly authenticated earnings event. The latest model-fitting origin is2020H1; the latest evaluation is2022. End20purging and all60historical rows follow the source procedure.

Sequential mixture weights and independently tuned constant weights use only preceding folds. The first fold has a fixed.5weight and initialPsingle component. Later best-component choices use preceding-fold losses. All five archived P architectures are shown descriptively. The initial inferential family comprises the six Logistic controls; H1/H3 in the original E6 experiment remain unchanged.

### S4.2 Disclosed tree addendum

The addendum was locked2026-11-15T11:05:12UTC, after the initial Logistic diagnostics and before any new matched tree fit. Its purpose is to complete available controls with both remaining original CPU tree architectures, rather than select a favorable architecture. All36fits use source candidate0, original300roundcap/25patience, seed42,twoCPUthreads and the original development-only stopping half-year. No2024–2025labels select a candidate, weight, threshold or epoch.

All six additional tree contrasts are reported, including unfavorable values. Their Holm6 family is separate; `development_all12_contrasts.csv` also reports Holm12 over the six initial plus six additional contrasts. Original Logistic p-values and intervals are unchanged. Equal input width is an information-format control, not a guarantee of identical effective capacity: duplicated columns can change a regularized learner or a tree's feature sampling.

### S4.3 Inference and cold start

The bootstrap uses the complete2017–2022market calendar, with an eligibility mask for purged gaps. Calendar blocks are synchronized across both stocks; each stock's eligible paired-loss mean is calculated before equal-stock averaging. HAC uses the corresponding ratio influence series. Principalblock60 and prespecified20/120sensitivities use4999replicates. Intervals are pointwise; p-values are centered, two-sided and corrected within the stated families.

The C6difference is confined to2017–2018: initial.5fusion versus initialP. In2019–2022both policies selectFand produce identical predictions. This is directly checked in the dated loss table, rather than inferred from aggregate significance. The result is significant atblock60in its initial family and in combinedHolm12, whileblock120p-values are larger. It is not a comparison against an oracle best expert selected using future outcomes.

Quarterly difference SD,lag1autocorrelation and two-stock correlation are diagnostics for this sample. They do not certify cross-industry dependence, effective earnings-event counts or power for the future E7candidate design.

## S5. Publication density and data qualification

Density counts only matching retained Apple articles in the original5session window. Fixed strata0/1–2/3+are applied to every original partition/timing; no post-result threshold selection occurs. Correlations condition on positive retained coverage so that the artificial numeric zero for an empty window is not treated as neutral language. Absolute mean sentiment is |mean tone|, distinct from mean absolute article tone.

All1152conditional metric rows and720descriptive paired contrasts remain available. AUC is suppressed unless each label has at least10cases; within-state ranking additionally requires20events and20same-cell pairs. Sparse Brier point summaries retain their counts and receive no new hypothesis tests. The original hierarchical p=.028and its fixed timing sensitivities remain source-stage secondary results.

E7b's20companyprototype still has zero strictly qualified quarters and zero original XBRL instance bytes in acquired evidence. E8a.1has zero new real pilot samples, L3/L4and independent manual QA. These counts describe evidence acquisition, not whether a company published or a post existed. Source-version L3and vendor-arrival L4are separate modes. Human original-document targets200financial/100news remain separate from program tests and the30–50record proposed access pilot.

For access decisions, use the retained E9a faculty brief and unsent email draft. E9b sends no inquiries, submits no applications, buys no services, starts no collector and does not run E8b. Source completeness, licensing, edit/delete policies and reviewer access require external evidence before expansion.

## S6. Integrity, versions and reproduction

2024–2025is an already-inspected exploratory period. New financial fits and weight allocation use development information through2022. The existing E3c2026protocol is unchanged and unexecuted, and new models are not added to it. Earlier incidental2026news aggregates/discovery material and the E9a subscription-page market-quote chrome remain disclosed in the original reports; E9b performs no2026financial extraction or label-based selection.

The old private E9a package and Git history retain the19page draft. There is one current manuscript path. Old scientific values, source correction families and original103claim fields remain byte/value verifiable; new claims carry the new plan and addendum. Administrative, testing, file-hash and access records are kept in the supplementary project files, not repeated through the article.

PR7was already merged when E9b began. The same branch continues from the merged main and requires a successor review PR; this is a GitHub-state constraint, not a second competing paper. No merge is authorized in this round.

Public replay checks aggregate results, selectors and current document generation. Full numerical rerunning additionally requires the user's lawful frozen market/fundamental inputs and archived forecasts. Raw prices/text, per-article manifests, checkpoints, credentials and workstationarchives remain outside public GitHub. Synthetic contract tests are labeled engineering checks and do not qualify historical content or independent human review.
