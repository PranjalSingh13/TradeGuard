# TradeGuard

<div align="center">

### **Document Intelligence + Risk-Gated Payment Escrow for Maritime Trade**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![XGBoost](https://img.shields.io/badge/ML-XGBoost-orange.svg)](https://xgboost.readthedocs.io/)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy_2.0-red.svg)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests Passing](https://img.shields.io/badge/tests-23%20passed-brightgreen.svg)]()

<br/>

![TradeGuard Control Center](docs/screenshots/pipeline_results.png)

</div>

---

## 🌟 Executive Overview

In global maritime and container trade, discrepancies across trade documents (**Bill of Lading, Commercial Invoice, Packing List, Certificate of Origin**) cause customs holds, demurrage fees, and invoice fraud.

**TradeGuard** automates cross-border shipping document verification and pairs it with an **automated risk-gated payment escrow ledger**:
1. **Document Preprocessing & Ingestion**: Image deskewing, Otsu binarization, and noise filtering via OpenCV.
2. **Document Classification**: TF-IDF + Classifier to categorize shipping forms with calibrated confidence gates.
3. **Structured Field Extraction**: Domain regular expressions and anchor-based parsers extract container serials, weights, package counts, ports, dates, and valuations.
4. **Deterministic Multi-Document Reconciliation**:
   - **ISO 6346 Modulo-11 Container Check-Digit** mathematical validation.
   - Cross-checks gross weight variance between Bill of Lading and Packing List.
   - Reconciles carton counts and measures fuzzy string similarity for parties.
   - Verifies date precedence (Invoice Date $\le$ Shipped-on-Board Date).
5. **Machine Learning Risk Model**: Tabular feature vectors feed into an **XGBoost Risk Classifier** to estimate risk probability.
6. **Hard-Rule Priority Decision Engine**:
   - $\text{Risk} < 0.20 \rightarrow$ **`AUTO_RELEASE`** (immediate payout to seller).
   - $0.20 \le \text{Risk} < 0.60$ or low OCR confidence $\rightarrow$ **`MANUAL_REVIEW`** (routes to reviewer console).
   - $\text{Risk} \ge 0.60$ or **any hard rule failed** $\rightarrow$ **`HOLD`** (freeze escrow).
7. **Append-Only Escrow Ledger**: Enforces database-level double-spend prevention (`UNIQUE (payment_id) WHERE entry_type IN ('release', 'refund')`).

---

## 📸 Screenshots

| Control Center & Scenario Toolbar | Automated Pipeline & Ledger Confirmation |
|---|---|
| ![Dashboard Initial State](docs/screenshots/dashboard.png) | ![Pipeline Executed State](docs/screenshots/pipeline_results.png) |

---

## 📊 ML Evaluation Benchmark

Trained and evaluated on synthetic maritime shipment datasets with injected discrepancies:

| Metric | Score | Impact |
|---|---|---|
| **ROC-AUC** | **0.8584** | Robust discrimination across risk distributions |
| **Precision (Risky)** | **1.0000 (100%)** | Zero false alarms on auto-releases |
| **Clean Accuracy** | **1.0000 (100%)** | Clean trade shipments pass through with no friction |
| **Macro F1-Score** | **0.9202** | Balanced performance across classes |
| **Fail-Safe Gate** | **Deterministic Override** | Deterministic check failures (e.g. invalid container) override ML |

Full evaluation report available at [`docs/reports/eval_report.md`](tradeguard/docs/reports/eval_report.md).

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Client Layer
        UI["Interactive Dashboard (Buyer, Seller, Reviewer)"]
    end

    subgraph API & Orchestration
        API["FastAPI REST API (Auth, RBAC, Webhooks)"]
        ORCH["Shipment Pipeline Orchestrator"]
    end

    subgraph Document Intelligence
        OCR["Preprocessing & OCR (Deskew, Denoise, PyPDF)"]
        CLS["Document Classifier (BoL, Invoice, PL, CoO)"]
        EXT["Field Extractor (Entity & Value Extraction)"]
        VAL["Validation Engine (ISO 6346 & Cross-Doc Consistency)"]
        FEAT["Feature Vector Builder"]
        ML["XGBoost Risk Model + Feature Explanations"]
    end

    subgraph Escrow & Settlement Layer
        DEC["Decision Engine (AUTO_RELEASE, MANUAL_REVIEW, HOLD)"]
        PAY["Payment Escrow & Ledger Service"]
        GW["Payment Gateway Sandbox / Webhooks"]
    end

    UI --> API
    API --> ORCH
    ORCH --> OCR --> CLS --> EXT --> VAL --> FEAT --> ML --> DEC
    DEC --> PAY <--> GW
```

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
- Python 3.11+
- Virtual environment (recommended)

### 2. Setup
```bash
git clone https://github.com/ppranjalsingh13/tradeguard.git
cd tradeguard
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 3. Run the Test Suite
All 23 unit, validation, API, and stress tests:
```bash
python -m pytest tradeguard/tests -v
```

### 4. Run the Machine Learning Benchmark
```bash
# Windows PowerShell
$env:PYTHONPATH="tradeguard/src"; python -m tradeguard.ml.evaluate

# Linux / macOS
PYTHONPATH="tradeguard/src" python -m tradeguard.ml.evaluate
```

### 5. Launch the Live Server & Dashboard
```bash
# Windows PowerShell
$env:PYTHONPATH="tradeguard/src"; uvicorn tradeguard.api.app:app --reload --port 8000
```

- **Interactive Dashboard:** [http://localhost:8000/](http://localhost:8000/)
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **System Metrics:** [http://localhost:8000/metrics](http://localhost:8000/metrics)

---

## 🧪 Testing Edge Cases & Stress Resilience

TradeGuard was evaluated against adversarial and unexpected inputs:
- **Empty / Non-printable input:** Filtered with confidence $\le 0.20$, routing to manual review.
- **Malformed Container Numbers:** Invalid letters or bad modulo-11 check digits trigger hard-rule holds.
- **Extreme Weight Outliers ($99.9\%$ variance):** Flagged with high-severity mismatch.
- **Double-Spend Prevention:** The ledger prevents secondary releases or refunds at the database layer.

---

## 📄 License
This project is open-source under the MIT License.
