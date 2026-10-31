# 07. ML Specification

Three models plus a deterministic validation layer:

1. **Document classifier**: which document type is this?
2. **Field extractor**: what are the key values?
3. **Shipment risk model (XGBoost)**: how likely is this shipment to have a problem?

## 1. Synthetic data generation
Real labeled shipping documents with discrepancy labels are not publicly available, so data is generated.

**Entities:** companies (Faker), ports (UN/LOCODE-style codes), vessels, Incoterms, goods categories with HS-code prefixes and typical value-per-kg ranges, container numbers (valid ISO 6346 by construction).

**Per shipment (the "truth"):** one consistent record: parties, ports, container(s), packages, gross/net weight, goods, value, dates.

**Documents:** render the truth into 4 document types, with **several visual templates per type** (HTML/CSS via Jinja2, converted to PDF, rasterized). Variation: fonts, layouts, field labels ("Gross Wt." vs "Gross Weight"), date formats, languages kept to English.

**Discrepancy injection:** for roughly 8 to 12 percent of shipments, apply one or more discrepancy types (see [02-FEATURES.md](02-FEATURES.md) section 4) to one or more documents. Store: `is_risky`, injected types, severity.

**Scan noise:** blur, rotation, skew, JPEG compression, salt-and-pepper, low contrast, partial shadows. Levels 0 to 3, stored per document.

**Field labels for extraction:** ground-truth values are known; auto-label OCR tokens by matching ground-truth strings to OCR output, then hand-check a sample.

**Splits:** by shipment so no shipment crosses splits. Also hold out **entire templates** and **the highest noise level** as stress-test sets.

**Reproducibility:** fixed seeds, config file for generator parameters, dataset version tag saved with every experiment.

## 2. Model 1: Document classifier
| Item | Plan |
|---|---|
| Input | OCR text (word + char n-gram TF-IDF), plus simple layout features (page count, text density) |
| Baselines | Keyword rules; TF-IDF + Logistic Regression |
| Main model | TF-IDF + **XGBoost** (sparse input) |
| Optional | Image-based CNN or LayoutLMv3 sequence classification (P2) |
| Metrics | Accuracy, macro-F1, per-class precision/recall, confusion matrix |
| Stress tests | Unseen templates, noise level 3, OCR engine swap |
| Reject option | Confidence below gate leads to manual review |

## 3. Model 2: Field extraction
| Item | Plan |
|---|---|
| Baseline | Regex + keyword-anchor rules per document type, normalization (dates, weights, units) |
| P2 model | LayoutLMv3 token classification (BIO tags) fine-tuned on synthetic documents; compare to baseline |
| Target fields | doc number, date, shipper, consignee, container no., gross weight, net weight, package count, ports, goods description, declared value, HS code |
| Metrics | Field-level exact match and token-level F1, per field and per document type; error breakdown (OCR error vs rule miss vs label noise) |

## 4. Validation layer (deterministic)
Checks produce both pass/fail results and numeric features.

| Check | Output feature |
|---|---|
| Weight agreement across BoL, packing list, invoice | `weight_diff_pct` |
| Package count agreement | `pkg_diff_abs`, `pkg_diff_pct` |
| Consignee/shipper name similarity (rapidfuzz) | `consignee_similarity`, `shipper_similarity` |
| Container number identical across documents | `container_mismatch_flag` |
| ISO 6346 check digit valid | `container_checkdigit_valid` |
| Port agreement | `port_mismatch_flag` |
| Date ordering (invoice date vs shipped-on-board) | `date_gap_days`, `date_order_violation` |
| Declared value per kg vs category/lane median | `value_per_kg_zscore` |
| Required fields present | `missing_required_count` |
| Duplicate file hash or BoL number seen before | `duplicate_doc_flag` |
| OCR quality | `ocr_conf_mean`, `ocr_conf_min`, `low_conf_field_count` |
| Classifier confidence | `cls_conf_min` |

ISO 6346 reference implementation (verified against the well-known valid example `CSQU3054383`):
```python
import string

def _letter_values():
    vals, v = {}, 10
    for ch in string.ascii_uppercase:
        if v % 11 == 0:      # values that are multiples of 11 are skipped
            v += 1
        vals[ch] = v
        v += 1
    return vals

LETTER = _letter_values()

def iso6346_check_digit(first10: str) -> int:
    total = 0
    for i, ch in enumerate(first10):
        val = LETTER[ch] if ch.isalpha() else int(ch)
        total += val * (2 ** i)
    return (total % 11) % 10

def is_valid_container(num: str) -> bool:
    num = num.replace(" ", "").upper()
    if len(num) != 11 or not num[:3].isalpha() or num[3] not in "UJZ" or not num[4:].isdigit():
        return False
    return iso6346_check_digit(num[:10]) == int(num[10])
```

## 5. Model 3: XGBoost risk model
| Item | Plan |
|---|---|
| Task | Binary classification: `is_risky` (any injected discrepancy of medium or higher severity) |
| Optional extension | Multi-label head or separate model predicting discrepancy type |
| Features | The table in section 4, plus ratio/interaction features where useful |
| Baselines | Rules-only score; logistic regression; random forest |
| Imbalance | `scale_pos_weight`, stratified shipment-level splits, PR-AUC as primary metric |
| Tuning | Randomized or Optuna search on validation set; early stopping; record all runs in MLflow |
| Calibration | Isotonic or Platt calibration on a separate calibration split; report Brier score and reliability curve |
| Thresholds | Choose `T_LOW` and `T_HIGH` from a cost matrix (false release cost is much higher than review cost); document the matrix and results |
| Explainability | SHAP per prediction; map top features to human-readable sentences |
| Robustness | Evaluate on unseen templates and noise level 3; ablation: remove OCR-quality features and see the change |
| Missing data | Keep missing values as NaN (XGBoost handles them) and add explicit `missing_*` flags |

### Evaluation checklist
- [ ] PR-AUC, ROC-AUC, F1 at chosen threshold
- [ ] Recall at fixed precision (for example precision 0.95)
- [ ] Confusion matrix at `T_LOW` and `T_HIGH`
- [ ] Share of shipments in each decision bucket
- [ ] Calibration plot and Brier score
- [ ] Comparison table: rules vs logistic regression vs random forest vs XGBoost
- [ ] Ablations and stress tests
- [ ] Error analysis: 20 worst false negatives and false positives reviewed by hand, with causes
- [ ] SHAP summary plot and 3 worked examples

## 6. Experiment tracking and reproducibility
- MLflow experiment per model; log params, metrics, dataset version, git commit, artifacts (model, plots).
- Save models with `joblib`/native XGBoost JSON; store metrics in `model_versions.metrics`.
- `make train-risk`, `make eval` reproduce reported numbers from a seed.

## 7. Model card template
```
Model: risk-xgb-<version>
Intended use: decision support for shipping-document consistency in a prototype escrow flow.
Not intended for: real fraud adjudication, legal/compliance decisions, real payments.
Training data: synthetic, dataset vX, N shipments, injected discrepancy types [...].
Metrics: PR-AUC __, recall@precision0.95 __, Brier __ (test); unseen-template __; noise-level-3 __.
Limitations: labels come from a generator; real-world documents will differ; OCR errors on poor scans.
Ethical/operational notes: low-confidence inputs always go to manual review.
Retraining: reviewer decisions can be collected as new labels (P2).
```

## 8. Honest-reporting rules
1. Always state that data is synthetic.
2. Report results on the hardest held-out sets, not only the easy test set.
3. Include failure cases in the README.
4. Never claim real-world fraud detection performance.
