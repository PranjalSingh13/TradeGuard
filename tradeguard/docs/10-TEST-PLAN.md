# 10. Test Plan

## 1. Test layers
| Layer | Tool | What is covered |
|---|---|---|
| Unit | pytest | ISO 6346, normalizers (dates, weights), rule extractors, fuzzy-match features, decision engine, ledger invariants |
| ML tests | pytest | Feature builder determinism, model loads and predicts, schema of outputs, no NaN/inf, thresholds applied correctly |
| Data tests | pytest | Generator seed reproducibility, split leakage checks (no shipment in two splits), label/injection consistency |
| API/integration | pytest + httpx, test DB | Auth/RBAC, upload validation, pipeline trigger, status transitions, review flow |
| Payment | pytest with simulated gateway + recorded sandbox fixtures | Idempotency, webhook signature, duplicate and out-of-order events, concurrency |
| End-to-end | scripted scenario (or Playwright) | Pay, upload, decision, release/refund |
| Load (light) | locust or k6 (optional) | Upload and status polling under modest concurrency |

## 2. Critical test cases
**Safety**
- Pipeline exception never yields `auto_release`.
- Low OCR confidence always yields `manual_review`.
- Any high-severity hard-rule failure never yields `auto_release`.

**Money**
- Two concurrent release attempts: exactly one succeeds.
- Release after refund (or the reverse) is rejected.
- Webhook with a bad signature changes nothing.
- Duplicate webhook is a no-op.
- Tampered client amount is ignored.

**Security**
- Buyer cannot read another buyer's shipment (403/404).
- Seller cannot call reviewer endpoints.
- Upload of a disallowed type or oversized file is rejected.
- Expired or forged JWT is rejected.

**ML correctness**
- `CSQU3054383` is valid; flipping the check digit is invalid.
- Feature builder returns the same vector for the same inputs.
- Model output stays in [0, 1].

## 3. Model quality gates (CI or release checklist)
A model can only be activated if on the held-out test set:
- It beats the logistic-regression baseline on PR-AUC.
- Recall at the chosen operating point is not below the previous active model's.
- It passes the unseen-template and noise-level-3 stress tests with documented numbers.
- Metrics and the dataset version are stored in `model_versions`.

## 4. Coverage and quality targets
- Backend coverage goal: 70 percent or higher, with near-complete coverage of payment and decision modules.
- `ruff` and formatter clean; type hints on public functions.

## 5. Manual exploratory checklist
- [ ] Rotated, blurry and photographed documents
- [ ] Multi-page PDFs
- [ ] Documents with missing sections
- [ ] Two shipments reusing one file
- [ ] Reviewer approves with and without a reason (reason required)
