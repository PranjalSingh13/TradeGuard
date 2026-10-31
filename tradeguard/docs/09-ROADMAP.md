# 09. Roadmap

Six-week plan assuming part-time effort alongside studies. Adjust durations to your schedule; the order matters more than the dates.

**Application-ready checkpoint: end of Week 3** (OCR + classifier + risk model + evaluation report on GitHub). You can apply then and keep building.

## Week 1: Foundations and data
- [ ] Repo, `pyproject.toml`, pre-commit, Makefile, CI skeleton
- [ ] Synthetic generator: entities, 4 document types, 3+ templates each
- [ ] Discrepancy injection with labels; scan-noise augmentation
- [ ] Dataset v1 (a few thousand shipments), grouped splits, dataset README
- **Done when:** `make data` produces a reproducible dataset and a sample gallery

## Week 2: OCR and classification
- [ ] Preprocessing + Tesseract OCR with confidence; compare PaddleOCR on a sample
- [ ] Document classifier: rules vs LR vs XGBoost
- [ ] Evaluation: macro-F1, confusion matrix, noise and template stress tests
- [ ] MLflow tracking set up
- **Done when:** classifier report in `docs/reports/` with honest numbers

## Week 3: Extraction, validation, risk model (MVP ML)
- [ ] Rules-based field extractor with per-field metrics
- [ ] Validation checks + ISO 6346 + feature builder
- [ ] XGBoost risk model, baselines, imbalance handling, calibration, thresholds
- [ ] SHAP and the evaluation checklist from [07-ML-SPEC.md](07-ML-SPEC.md)
- [ ] README with problem, results table, failure cases, disclaimers
- **Done when:** end-to-end CLI runs from documents to risk score and decision

## Week 4: Backend platform
- [ ] FastAPI app: auth/RBAC, shipments, documents, process, risk endpoints
- [ ] PostgreSQL + Alembic migrations per [05-DATABASE-SCHEMA.md](05-DATABASE-SCHEMA.md)
- [ ] S3/MinIO storage, async processing, audit logging
- [ ] Stateless `/ml/classify` and `/ml/extract`
- [ ] Docker + docker-compose, pytest suite for API
- **Done when:** upload documents through the API and get a risk decision

## Week 5: Payments, review and UI
- [ ] Gateway interface + simulated gateway + Razorpay test mode
- [ ] Order, verify, webhook, ledger, release/refund, idempotency
- [ ] Reviewer queue and decision endpoints
- [ ] React dashboard: shipments, upload, risk result with reasons, payment status, review console
- **Done when:** all escrow scenarios in [08-PAYMENT-ESCROW.md](08-PAYMENT-ESCROW.md) pass

## Week 6: Hardening, deploy, polish
- [ ] GitHub Actions CI (lint, tests, build)
- [ ] AWS deploy: EC2 + S3 (+ RDS optional), environment config
- [ ] P2 choice: LayoutLMv3 comparison **or** reviewer-feedback export **or** drift report
- [ ] Demo video (2 to 3 minutes), architecture diagram, final README and model card
- **Done when:** live demo link (or video) and a clean repo anyone can run with one command

## Scope-cut order (if time runs short)
1. LayoutLMv3 comparison
2. Celery/Redis workers
3. Drift report and reviewer-feedback export
4. RDS (use Postgres container) and Stripe support
5. UI polish (keep the review console and risk explanation)

Never cut: evaluation report, honest README, idempotent payment handling, tests.

## Weekly routine
- Commit small and often with meaningful messages.
- Update the experiment log after each training run.
- Keep a `CHANGELOG.md` and tag milestones (`v0.1-ml`, `v0.2-api`, `v1.0`).
