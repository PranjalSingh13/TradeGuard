# 12. JD Alignment and Portfolio Notes

Maps the Integrated Maritime Exchange (IME) Machine Learning Intern job description to this project, and gives guidance for presenting it honestly.

## 1. JD responsibility to project mapping
| JD item | Where TradeGuard covers it |
|---|---|
| Build, train, evaluate ML models for document and cargo classification | Document classifier (LR vs XGBoost), risk model; see [07-ML-SPEC.md](07-ML-SPEC.md) |
| Information extraction using OCR, NLP, document parsing | OCR pipeline, rules extractor, optional LayoutLMv3 |
| Integrate trained models into systems via APIs and data pipelines | FastAPI service, async pipeline, stateless `/ml/*` endpoints |
| Clean, preprocess, label datasets | Synthetic generator, auto-labeling, scan-noise preprocessing |
| Test, benchmark and improve accuracy and reliability | Baselines, stress tests, calibration, ablations, error analysis |
| Document experiments, models, processes; collaborate | MLflow, model card, this docs folder, CHANGELOG |

| JD requirement | Evidence in the project |
|---|---|
| Python and an ML library (scikit-learn, PyTorch, TensorFlow) | scikit-learn, XGBoost, optional PyTorch |
| Classification, NLP or computer vision | Document classification, OCR/NLP extraction, image preprocessing |
| Analytical and problem-solving skills | Error analysis, cost-based thresholds |
| Communication | README, docs set, demo video |
| OCR/document tools (Tesseract, LayoutLM) | Tesseract/PaddleOCR; LayoutLMv3 comparison (P2) |
| REST APIs and basic deployment | FastAPI, Docker, AWS |
| Cloud and Git | AWS deploy, GitHub Actions, clean history |
| Interest in maritime/trade documents | BoL, invoice, packing list, ISO 6346, Incoterms, ports |

## 2. Resume bullets (fill in blanks only with measured results)
- Built **TradeGuard**, a document-intelligence service that classifies shipping documents (macro-F1 **__**), extracts fields via OCR (exact-match **__** on key fields), and scores shipment risk with **XGBoost** (PR-AUC **__**, calibrated; evaluated on unseen templates).
- Designed a risk-gated escrow flow using a payment gateway in **sandbox mode** with signed webhooks, an append-only ledger and idempotent release/refund handling.
- Deployed a Dockerized FastAPI + PostgreSQL service on AWS with CI (GitHub Actions) and documented experiments with MLflow.

Skills line to add: `XGBoost, scikit-learn, OCR (Tesseract), NLP, SHAP, MLflow, FastAPI, Docker, AWS`.

Keep wording truthful: say "synthetic data" and "sandbox payments" in the README, and avoid terms like "production" or "real fraud detection".

## 3. Application email checklist
Subject line required by the JD: `Application – Machine Learning Intern` to `ops@theimehub.com`.
- [ ] Resume tailored for ML (replace the current recruiter-oriented summary)
- [ ] GitHub link to the TradeGuard repo (pinned)
- [ ] 3 to 4 lines: what you built, one metric, one lesson from error analysis
- [ ] Link to demo video or live demo

## 4. README structure that impresses
1. One-paragraph problem and solution
2. Architecture diagram
3. Demo GIF/video
4. Results table with baselines and stress tests
5. Failure cases and limitations (shows maturity)
6. How to run in one command
7. Tech stack and design decisions
8. Links to the docs folder

## 5. Interview talking points
- **Why XGBoost here?** Tabular, mixed-type, missing values, strong with limited data, works with SHAP.
- **Why not let ML decide everything?** Hard rules for must-not-fail cases; reject option for low confidence.
- **Biggest risk?** Synthetic labels; how stress tests and honest reporting address it.
- **Why calibrate?** Thresholds trigger money movement; scores need to behave like probabilities.
- **What would change with real data?** Label noise, new templates, drift monitoring, human-in-the-loop retraining.
- **Payments design:** webhook as source of truth, idempotency, append-only ledger.
- **What you cut and why** (scope discipline).

## 6. Learning plan to fill resume gaps
| Gap | How the project fills it | Extra study |
|---|---|---|
| ML libraries | XGBoost, scikit-learn throughout | scikit-learn pipelines, cross-validation |
| OCR/NLP | OCR pipeline and extraction | Tesseract page segmentation modes, token classification basics |
| Evaluation | PR curves, calibration, ablations | Imbalanced-learning metrics |
| Cloud | AWS deployment | EC2, S3, IAM basics |
