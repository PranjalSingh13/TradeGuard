# 02. Features

Priority: **P0** must have, **P1** should have, **P2** stretch.

## 1. Feature list

| ID | Feature | Priority | Area |
|---|---|---|---|
| F-01 | User registration, login (JWT), roles: buyer, seller, reviewer, admin | P0 | Auth |
| F-02 | Create and list shipments with parties, ports, Incoterm, declared value | P0 | Shipments |
| F-03 | Upload documents (PDF/PNG/JPG) with type, size and hash validation | P0 | Ingestion |
| F-04 | Image preprocessing (deskew, denoise, binarize) and OCR with confidence | P0 | OCR |
| F-05 | Document-type classification (BoL, invoice, packing list, CoO, other) | P0 | ML |
| F-06 | Field extraction from each document type (rules baseline) | P0 | NLP |
| F-07 | Cross-document validation checks (weights, counts, names, dates, ports) | P0 | Validation |
| F-08 | ISO 6346 container number check-digit validation | P0 | Validation |
| F-09 | XGBoost shipment risk score from validation features | P0 | ML |
| F-10 | Decision engine: auto-release / manual review / hold, with hard-rule overrides | P0 | Decision |
| F-11 | Escrow payment: create order, verify, hold funds (sandbox) | P0 | Payments |
| F-12 | Release or refund based on decision; ledger entries; webhooks | P0 | Payments |
| F-13 | Reviewer queue: discrepancy list, approve/reject with reason | P0 | Review |
| F-14 | Shipment status timeline and audit log | P0 | Platform |
| F-15 | Dashboard (React): shipments, upload, risk result, payment status | P0 | UI |
| F-16 | Synthetic data generator with injected discrepancies and scan noise | P0 | Data |
| F-17 | Evaluation report: metrics, confusion matrix, PR curve, error analysis | P0 | ML |
| F-18 | SHAP explanations: top reasons per decision shown in UI | P1 | Explainability |
| F-19 | Probability calibration and threshold tuning by cost | P1 | ML |
| F-20 | Model registry: versioned artifacts, metrics, active-model switch | P1 | MLOps |
| F-21 | Stateless API: `/classify` and `/extract` for single documents | P1 | API |
| F-22 | Duplicate-document detection via file hash and BoL number reuse | P1 | Validation |
| F-23 | CI pipeline: lint, tests, build image | P1 | DevOps |
| F-24 | AWS deployment (EC2 + S3, optional RDS) | P1 | DevOps |
| F-25 | LayoutLMv3 field extractor compared with the rules baseline | P2 | ML |
| F-26 | Reviewer decisions exported as labeled data for retraining | P2 | MLOps |
| F-27 | Celery/Redis workers for processing | P2 | Platform |
| F-28 | Data/prediction drift report | P2 | MLOps |

## 2. Acceptance criteria (P0)

**F-01 Auth**
- Given valid credentials, login returns a JWT; invalid returns 401.
- A buyer cannot call reviewer endpoints (403).

**F-03 Upload**
- Only PDF/PNG/JPG up to the configured size limit are accepted; others return 422.
- Each file's SHA-256 is stored.

**F-04 OCR**
- Each processed page stores text, word boxes and a mean confidence score.
- Unreadable files mark the document `failed` with a reason, and never block the API.

**F-05 Classification**
- Returns predicted type and confidence; confidence below the threshold routes to manual review.

**F-06 Extraction**
- Extracts at minimum: document number, date, shipper, consignee, container number(s), gross weight, package count, port of loading, port of discharge, goods description, declared value (invoice).
- Each field carries a confidence value or a "missing" flag.

**F-07/F-08 Validation**
- Each check outputs pass/fail, severity (low/medium/high) and a human-readable detail.
- `CSQU3054383` validates; changing any digit makes the check fail.

**F-09 Risk score**
- Score in [0, 1] stored with model version, features and thresholds.
- Same inputs and model version always give the same score.

**F-10 Decision engine**
- Score below the low threshold and no hard-rule failure and OCR confidence above gate gives `AUTO_RELEASE`.
- Between thresholds, or any low-confidence input, gives `MANUAL_REVIEW`.
- Above the high threshold, or any high-severity hard rule, gives `HOLD`.
- If any ML/OCR step fails, the decision is `MANUAL_REVIEW`; never `AUTO_RELEASE`.

**F-11/F-12 Payments**
- Funds can only move from HELD to RELEASED or REFUNDED, exactly once (idempotent).
- Webhook signatures are verified; invalid signatures are rejected and logged.
- Amounts are computed server-side; client-supplied amounts are ignored.

**F-13 Review**
- Reviewer sees extracted fields, failed checks and reasons; decision requires a reason; decision triggers release or refund and writes an audit entry.

**F-16/F-17 Data and evaluation**
- Generator is seeded and reproducible; produces train/val/test splits grouped by shipment and by template.
- Evaluation script outputs a markdown report with metrics and plots.

## 3. User stories
- As a **buyer**, I want to fund a shipment into escrow so that the seller is paid only when documents are consistent.
- As a **seller**, I want to see which documents have problems immediately so I can fix them before review.
- As a **reviewer**, I want a ranked list of discrepancies with reasons so I can decide quickly.
- As an **admin**, I want to see the active model version and its metrics so I can trust the decisions.
- As a **developer integrating with TradeGuard**, I want a documented REST API so I can classify and extract documents from my own system.

## 4. Discrepancy types the generator will inject
| Type | Severity | Example |
|---|---|---|
| Gross weight mismatch | Medium/High | BoL 18,400 kg vs packing list 17,900 kg |
| Package count mismatch | Medium | 420 vs 402 cartons |
| Consignee name altered | Medium/High | Small typo vs a different company |
| Invalid container check digit | High | Typo in container number |
| Container number differs across documents | High | Different containers on BoL and packing list |
| Value per kg outlier | Medium/High | Declared value far from lane/category norm |
| Missing mandatory field | Medium | No port of discharge |
| Date inconsistency | Low/Medium | Invoice dated after shipped-on-board date |
| Port mismatch | Medium | Discharge port differs across documents |
| Duplicate document reuse | High | Same BoL number or file hash in another shipment |

## 5. Out of scope
Real customs/regulatory filing, real money, KYC, multi-currency, mobile apps, multi-tenant admin.
