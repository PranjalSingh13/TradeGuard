# 01. Product Requirements Document (PRD)

| Field | Value |
|---|---|
| Product | TradeGuard |
| Version | 0.1 (draft) |
| Date | 2026-10-31 |
| Author | Pranjal Singh |
| Status | Draft for build |

## 1. Problem statement
In cargo trade, payment and release decisions depend on several documents agreeing with each other: the bill of lading, commercial invoice, packing list and certificate of origin. Checking them is mostly manual, slow and error-prone. Small mismatches (weights, package counts, consignee names, container numbers) cause delays, disputes and extra charges, and deliberate tampering is hard to spot by eye.

## 2. Product vision
A service that reads shipping documents like an operations analyst would, flags inconsistencies with explainable reasons, and uses that assessment to automate the safe cases and escalate the risky ones, with the payment flow wired directly to the decision.

## 3. Goals
1. Classify uploaded shipping documents into their types.
2. Extract key fields from scanned/PDF documents using OCR and NLP.
3. Cross-validate fields across documents and against domain rules (e.g. ISO 6346 container check digit).
4. Produce a calibrated, explainable shipment risk score with **XGBoost**.
5. Drive an escrow-style payment flow (**payment gateway, sandbox**) from the risk decision.
6. Expose everything through documented REST APIs and a small dashboard.
7. Report honest, reproducible evaluation metrics.

## 4. Non-goals
- Real money movement, real escrow licensing, KYC/AML.
- Customs filing or legal compliance guarantees.
- Claims about real-world fraud detection accuracy.
- Multi-currency settlement, multi-tenant enterprise features, mobile apps.

## 5. Personas
| Persona | Description | Main needs |
|---|---|---|
| Buyer (importer) | Pays for goods and wants assurance documents are consistent before funds release | Create shipment, fund escrow, track status |
| Seller (exporter) | Ships goods and wants quick payment release | Upload documents, see issues early, get paid faster |
| Reviewer (trade-ops analyst) | Handles borderline cases | Clear discrepancy list, side-by-side documents, approve/reject |
| Admin | Operates the system | Model versions, thresholds, audit logs |

## 6. Core user journey
1. Buyer creates a shipment and pays into escrow (sandbox checkout).
2. Seller uploads the document set.
3. System runs OCR, classification, extraction, cross-document validation and risk scoring.
4. Decision engine outputs one of:
   - **Auto-release**: funds released to the seller.
   - **Manual review**: a reviewer inspects the discrepancies and approves or rejects.
   - **Hold/Reject**: funds stay held or are refunded, with reasons shown.
5. Everyone sees the status timeline and an explanation of the decision.

## 7. Scope
**MVP (P0):** synthetic data generator, OCR pipeline, document classifier, field extraction (rules baseline), cross-document checks, XGBoost risk model with evaluation, decision engine, FastAPI backend with auth and Postgres, payment hold/release/refund in sandbox with webhooks, reviewer queue, basic dashboard, Docker.

**Next (P1):** SHAP explanations in UI, probability calibration, model registry/versioning, CI, AWS deployment, stateless classify/extract API.

**Stretch (P2):** LayoutLMv3 extraction vs. rules baseline, active-learning loop from reviewer decisions, Celery workers, drift monitoring.

See [02-FEATURES.md](02-FEATURES.md) for the full list.

## 8. Non-functional requirements
| Area | Requirement |
|---|---|
| Performance | Single document processed end-to-end on CPU in a few seconds (target p95 under 10 s for a 1-2 page document); processing is asynchronous so the UI never blocks |
| Reliability | Payment and webhook handling idempotent; a failed ML step must never auto-release funds |
| Security | JWT auth, RBAC, hashed passwords, signed webhook verification, upload validation (type, size), no secrets in repo |
| Explainability | Every decision stores features, score, thresholds and top contributing reasons |
| Auditability | All state changes and decisions written to an audit log |
| Reproducibility | Seeded data generation, pinned dependencies, tracked experiments, versioned models |
| Privacy | Synthetic data only; no real personal or commercial documents |

## 9. Success metrics
These are **planning targets**, to be replaced with measured results in the README.

| Metric | Target | Notes |
|---|---|---|
| Document classifier macro-F1 | 0.95 or higher | On held-out synthetic test set incl. noisy scans |
| Field extraction exact-match | 85 percent or higher on key fields | Report per-field, rules vs. LayoutLM if built |
| Risk model PR-AUC | 0.90 or higher | Also report recall at fixed precision; check on unseen templates |
| Calibration | Brier score and reliability curve reported | Thresholds depend on calibrated probabilities |
| Auto-release safety | Zero injected high-severity cases auto-released in test set | Hard-rule overrides count toward this |
| Demo completeness | End-to-end flow from payment to release works in sandbox | Recorded demo |

## 10. Assumptions and constraints
- Labels for the risk model come from a synthetic generator, so the model partly learns the generator's rules. Mitigated with unseen-template and noise-shift test sets plus an honest README.
- LayoutLMv3 fine-tuning needs a GPU (free Colab/Kaggle is enough); serving on CPU is possible but memory-heavy.
- Gateway features for holding/transferring funds vary by account type and region; the design includes a ledger-only fallback.

## 11. Risks and mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| Synthetic data too easy, inflated metrics | Misleading results | Add noise/template shift, hand-checked realistic set, error analysis, explicit disclaimer |
| OCR errors on noisy scans | Wrong features | Gate on OCR confidence; low confidence goes to manual review |
| Scope creep | Project never finishes | Strict P0/P1/P2 list; drop LayoutLM first |
| Gateway sandbox limitations | Escrow flow incomplete | Ledger-based fallback; abstract gateway behind an interface |
| Heavy models on small servers | Slow or crashing deploy | Use classical models in production path; LayoutLM optional/offline |
| Class imbalance | Poor recall on risky cases | Stratified/grouped splits, PR-AUC, class weights, threshold tuning |

## 12. Milestones
See [09-ROADMAP.md](09-ROADMAP.md). Application-ready checkpoint: OCR, classifier and evaluation report on GitHub with a clear README.

## 13. Open questions
- Which gateway to use first: Razorpay (INR, India) or Stripe? Default: Razorpay test mode, behind a gateway interface.
- Is a LayoutLMv3 comparison worth the time versus deeper error analysis? Decide after Week 3.
