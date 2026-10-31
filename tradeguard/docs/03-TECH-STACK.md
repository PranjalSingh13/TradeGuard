# 03. Tech Stack

Principle: use boring, well-known tools for the platform so the time goes into the ML. Pin versions in `pyproject.toml` and `package.json`; the versions below are choices, not a promise about the latest release.

## 1. Stack at a glance

| Layer | Choice | Why | Alternatives |
|---|---|---|---|
| Language | Python 3.11 | JD requires Python; ML ecosystem | none |
| API framework | FastAPI + Uvicorn | Typed, async, auto OpenAPI docs | Flask (you know it), Django |
| Validation | Pydantic v2 | Request/response schemas | marshmallow |
| ORM / migrations | SQLAlchemy 2.x + Alembic | Standard, testable | SQLModel, Django ORM |
| Database | PostgreSQL | Relational integrity for money; JSONB for features | MySQL |
| Object storage | S3 (MinIO locally) | Document files kept out of DB | local disk (dev only) |
| Background work | FastAPI BackgroundTasks (MVP); Celery + Redis (P2) | Keep MVP simple | RQ, Dramatiq |
| Auth | JWT (access + refresh), bcrypt/argon2, RBAC | You already know this stack | OAuth provider |
| OCR | Tesseract (pytesseract) baseline; PaddleOCR comparison | JD names Tesseract; compare engines | EasyOCR, AWS Textract |
| PDF/image handling | PyMuPDF or pdf2image, OpenCV, Pillow | Rasterize PDFs, deskew, denoise | none |
| Text features | scikit-learn TF-IDF (word + char n-grams) | Strong, fast baseline | sentence embeddings |
| Fuzzy matching | rapidfuzz | Name/address similarity features | difflib |
| Classical ML | scikit-learn, **XGBoost** | JD: ML library; XGBoost is a project requirement | LightGBM |
| Document AI (P2) | PyTorch + Hugging Face Transformers, LayoutLMv3 | JD names LayoutLM | Donut, Textract |
| Explainability | SHAP | Per-decision reasons | LIME |
| Calibration | scikit-learn CalibratedClassifierCV | Thresholds need real probabilities | manual Platt |
| Experiment tracking | MLflow (local) | Runs, params, metrics, artifacts | Weights & Biases, CSV logs |
| Data generation | Faker, Jinja2 + WeasyPrint (or ReportLab), OpenCV/Albumentations noise | Varied templates plus scan noise | manual PDFs |
| Payments | Razorpay (test mode), behind a `PaymentGateway` interface | INR, India-friendly; sandbox | Stripe (manual capture / separate transfers) |
| Frontend | React + Vite + Tailwind, TanStack Query | Already in your skill set | Next.js |
| Testing | pytest, httpx TestClient, Playwright (optional) | Standard | unittest |
| Quality | ruff, black, mypy (light), pre-commit | Clean repo signal | flake8 |
| Containers | Docker, docker-compose | One-command run | Podman |
| CI/CD | GitHub Actions | Free for public repos | GitLab CI |
| Cloud | AWS: EC2 + S3 (+ RDS optional), CloudWatch logs | JD names AWS/GCP/Azure | GCP Cloud Run |

## 2. Why these ML choices
- **Document classifier:** TF-IDF + logistic regression as the baseline, then XGBoost on the same features. Reporting both shows you compare rather than assume.
- **Extraction:** a rules/regex + keyword-anchor baseline first, because it is explainable and fast. LayoutLMv3 is a P2 comparison, not a dependency.
- **Risk model:** XGBoost on tabular cross-document features. This is the right tool for mixed numeric/boolean features, handles missing values, and works well with SHAP.

## 3. Hardware and cost notes
- Training XGBoost and scikit-learn models runs fine on a laptop CPU.
- LayoutLMv3 fine-tuning: use a free GPU notebook (Colab/Kaggle). Export the model and test CPU inference separately.
- Serving: classical models plus Tesseract run comfortably on a small VM. LayoutLM inference wants more memory; plan an instance with at least 2 GB RAM, or keep LayoutLM as an offline experiment.
- Check current AWS free-tier terms and instance pricing before deploying; they change.

## 4. Dependencies summary (starting point)
```
fastapi, uvicorn[standard], pydantic, sqlalchemy, alembic, psycopg[binary]
python-jose or pyjwt, passlib[bcrypt], python-multipart, boto3
pytesseract, opencv-python-headless, pymupdf, pillow
scikit-learn, xgboost, shap, pandas, numpy, rapidfuzz, mlflow
faker, jinja2, weasyprint, albumentations
razorpay
pytest, httpx, ruff, black, pre-commit
# P2: torch, transformers, datasets, seqeval, celery, redis
```

## 5. Public datasets for practice and sanity checks
- **RVL-CDIP**: document-image classification (includes an invoice class).
- **FUNSD**: form understanding (token classification, LayoutLM-style).
- **SROIE / CORD**: receipt/key-information extraction.

No public dataset of labeled bills of lading with fraud labels is assumed; that is why the project generates synthetic shipments. Check each dataset's license before use.
