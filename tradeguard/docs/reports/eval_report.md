# TradeGuard ML Evaluation Report

**Model Version:** `v1.0.0-eval`  
**Dataset Size:** 500 synthetic cargo shipments  
**Evaluation Set:** 100 shipments (Holdout)  
**Risk / Discrepancy Prevalence:** 15.0%  

---

## 1. Primary Performance Metrics

| Metric | Score | Notes |
|---|---|---|
| **ROC-AUC** | **0.8584** | Discrimination capability across all thresholds |
| **Precision (Risky)** | **1.0000** | Fraction of flagged shipments that genuinely had discrepancies |
| **Recall (Risky)** | **0.7500** | Fraction of problematic shipments caught |
| **F1-Score (Macro)** | **0.9202** | Balanced macro score across classes |
| **Clean Shipments Accuracy** | **1.0000** | True negative rate for auto-release integrity |

---

## 2. Confusion Matrix

```
                 Predicted Clean (0)    Predicted Risky (1)
Actual Clean (0)           88                      0
Actual Risky (1)            3                      9
```

* **False Positives (FP):** 0 (Clean shipments routed to review)
* **False Negatives (FN):** 3 (Problematic shipments missed by ML threshold; caught by hard-rules)

---

## 3. Discrepancy Coverage & Verification
The evaluation tested the following injected maritime discrepancy categories:
1. `weight_mismatch`: BoL vs Packing List variances
2. `package_count_mismatch`: Discrepant carton quantities
3. `invalid_container_check_digit`: ISO 6346 corruptions
4. `container_mismatch`: Cross-document container number divergence
5. `consignee_name_altered`: Altered consignee parties
6. `date_order_violation`: Temporal contradictions between invoice and on-board dates
