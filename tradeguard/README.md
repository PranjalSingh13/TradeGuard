# TradeGuard

**Document intelligence + risk-gated escrow for cargo trade.**

TradeGuard ingests shipping documents (Bill of Lading, Commercial Invoice, Packing List, Certificate of Origin), classifies them, extracts key fields with OCR/NLP rules, validates consistency across documents, and scores each shipment's risk with **XGBoost**. The risk decision controls a **payment-gateway escrow flow**: low-risk shipments auto-release funds, borderline ones go to a human reviewer queue, and high-risk shipments are held.

---

## Architecture Overview

```
                      +-----------------------------+
                      |   React Dashboard / UI      |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |    FastAPI REST Backend     |
                      |   (Auth, RBAC, Webhooks)    |
                      +--------------+--------------+
                                     |
              +----------------------+----------------------+
              |                                             |
              v                                             v
+-----------------------------+               +-----------------------------+
|    Document Intelligence    |               |  Escrow & Ledger Engine     |
| - OCR & Preprocessing       |               | - Sandbox Gateway           |
| - Doc Classifier            |               | - Append-only Ledger        |
| - Rules Field Extractor     |               | - Anti-Double-Spend Check   |
| - ISO 6346 & Cross-Doc Val  |               +-----------------------------+
| - XGBoost Risk Model        |                             ^
| - Tri-State Decision Engine |-----------------------------+
+-----------------------------+   (AUTO_RELEASE / REVIEW / HOLD)
```

---

## Performance & Evaluation Benchmark

Trained and evaluated on synthetic maritime shipment datasets with injected discrepancies:

| Metric | Score | Notes |
|---|---|---|
| **ROC-AUC** | **0.8584** | Robust discrimination between clean and fraudulent shipments |
| **Precision (Risky)** | **1.0000 (100%)** | Zero false alarms on auto-releases |
| **Recall (Risky)** | **0.7500** | Borderline cases caught by deterministic hard rules |
| **F1-Score (Macro)** | **0.9202** | High balanced performance across classes |
| **Clean True Negative Rate** | **1.0000 (100%)** | Clean trade shipments pass without friction |

Full evaluation report available at [`docs/reports/eval_report.md`](docs/reports/eval_report.md).

---

## Quick Start

### 1. Run Tests
```bash
python -m pytest tradeguard/tests
```
*(All 13 test suites pass across ISO 6346, cross-validation, XGBoost, ledger invariants, and FastAPI endpoints).*

### 2. Generate Synthetic Benchmark & Evaluate
```bash
$env:PYTHONPATH="tradeguard/src"; python -m tradeguard.ml.evaluate
```

### 3. Start the FastAPI API Server
```bash
uvicorn tradeguard.api.app:app --reload --port 8000
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Control Dashboard: `tradeguard/frontend/index.html` (open in browser)
