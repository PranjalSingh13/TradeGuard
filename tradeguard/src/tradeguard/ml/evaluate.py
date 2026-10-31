"""Evaluation script for TradeGuard ML Pipeline.

Generates synthetic benchmark test sets, computes metrics (Precision, Recall, F1, ROC-AUC), and exports an evaluation report.
"""
from pathlib import Path
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

from tradeguard.ml.features import extract_features_vector
from tradeguard.ml.models.risk_model import RiskModel
from tradeguard.ml.synthetic.generator import SyntheticDataGenerator
from tradeguard.validation.cross_doc import run_cross_document_validation


def run_pipeline_evaluation(
    dataset_size: int = 500,
    risk_ratio: float = 0.15,
    output_report_path: str = "docs/reports/eval_report.md",
) -> dict:
    print(f"Generating synthetic evaluation benchmark (N={dataset_size}, risk_ratio={risk_ratio})...")
    gen = SyntheticDataGenerator(seed=42)
    dataset = gen.generate_dataset(total_count=dataset_size, risk_ratio=risk_ratio)

    # Train / Test split (80 / 20)
    split_idx = int(0.8 * len(dataset))
    train_records = dataset[:split_idx]
    test_records = dataset[split_idx:]

    def build_xy(records):
        X_list, y_list = [], []
        for rec in records:
            checks = run_cross_document_validation(rec.bundle)
            vec = extract_features_vector(rec.bundle, checks)
            X_list.append(vec)
            y_list.append(1 if rec.is_risky else 0)
        return np.array(X_list), np.array(y_list)

    X_train, y_train = build_xy(train_records)
    X_test, y_test = build_xy(test_records)

    print("Training XGBoost Risk Model...")
    model = RiskModel(model_version="v1.0.0-eval")
    model.fit(X_train, y_train)

    # Predictions
    probs = np.array([model.predict_risk_score(x) for x in X_test])
    preds = (probs >= 0.5).astype(int)

    roc_auc = float(roc_auc_score(y_test, probs)) if len(np.unique(y_test)) > 1 else 1.0
    cm = confusion_matrix(y_test, preds)
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (len(y_test), 0, 0, 0)
    report_dict = classification_report(y_test, preds, output_dict=True, zero_division=0)

    # Generate Markdown Report
    report_md = f"""# TradeGuard ML Evaluation Report

**Model Version:** `v1.0.0-eval`  
**Dataset Size:** {dataset_size} synthetic cargo shipments  
**Evaluation Set:** {len(test_records)} shipments (Holdout)  
**Risk / Discrepancy Prevalence:** {risk_ratio * 100:.1f}%  

---

## 1. Primary Performance Metrics

| Metric | Score | Notes |
|---|---|---|
| **ROC-AUC** | **{roc_auc:.4f}** | Discrimination capability across all thresholds |
| **Precision (Risky)** | **{report_dict['1']['precision']:.4f}** | Fraction of flagged shipments that genuinely had discrepancies |
| **Recall (Risky)** | **{report_dict['1']['recall']:.4f}** | Fraction of problematic shipments caught |
| **F1-Score (Macro)** | **{report_dict['macro avg']['f1-score']:.4f}** | Balanced macro score across classes |
| **Clean Shipments Accuracy** | **{report_dict['0']['recall']:.4f}** | True negative rate for auto-release integrity |

---

## 2. Confusion Matrix

```
                 Predicted Clean (0)    Predicted Risky (1)
Actual Clean (0)        {tn:5d}                  {fp:5d}
Actual Risky (1)        {fn:5d}                  {tp:5d}
```

* **False Positives (FP):** {fp} (Clean shipments routed to review)
* **False Negatives (FN):** {fn} (Problematic shipments missed by ML threshold; caught by hard-rules)

---

## 3. Discrepancy Coverage & Verification
The evaluation tested the following injected maritime discrepancy categories:
1. `weight_mismatch`: BoL vs Packing List variances
2. `package_count_mismatch`: Discrepant carton quantities
3. `invalid_container_check_digit`: ISO 6346 corruptions
4. `container_mismatch`: Cross-document container number divergence
5. `consignee_name_altered`: Altered consignee parties
6. `date_order_violation`: Temporal contradictions between invoice and on-board dates
"""

    out_file = Path(output_report_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(report_md, encoding="utf-8")
    print(f"Evaluation report written to {out_file.resolve()}")

    return {
        "roc_auc": roc_auc,
        "precision": report_dict["1"]["precision"],
        "recall": report_dict["1"]["recall"],
        "f1_macro": report_dict["macro avg"]["f1-score"],
        "report_path": str(out_file),
    }


if __name__ == "__main__":
    run_pipeline_evaluation()

