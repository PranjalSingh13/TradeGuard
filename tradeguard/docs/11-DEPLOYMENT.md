# 11. Deployment and DevOps

## 1. Local development
```
git clone <repo> && cd tradeguard
cp .env.example .env
docker compose up --build        # api, postgres, minio, (redis optional), frontend
make data                        # generate synthetic dataset
make train                       # train classifier + risk model, log to MLflow
make test
```
`docker-compose.yml` services: `api`, `db` (Postgres), `minio` (S3-compatible), `frontend`, optional `redis` and `worker`, optional `mlflow`.

## 2. Environment variables
| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection |
| `JWT_SECRET`, `JWT_EXPIRES_MIN` | Auth |
| `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | Object storage |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | Gateway (test keys) |
| `PAYMENT_GATEWAY` | `razorpay` or `simulated` |
| `OCR_ENGINE` | `tesseract` or `paddle` |
| `T_LOW`, `T_HIGH`, `OCR_GATE`, `CLS_GATE` | Decision thresholds (defaults come from the active model's metadata) |
| `MODEL_DIR` | Where model artifacts are loaded from |

Commit only `.env.example`.

## 3. Docker image notes
- Base on a slim Python image; install Tesseract and WeasyPrint system libraries in the image.
- Multi-stage build to keep the image small; pin dependency versions.
- Keep heavy P2 dependencies (PyTorch/Transformers) in a separate optional image or extra so the core API stays light.
- Run as a non-root user; add a `HEALTHCHECK`.

## 4. CI pipeline (GitHub Actions)
1. Checkout, set up Python, cache dependencies
2. `ruff` and format check
3. `pytest` with a Postgres service container
4. Build the Docker image
5. (Optional) Push to a registry and deploy on tag

## 5. AWS deployment (simple path)
| Piece | Choice |
|---|---|
| Compute | One EC2 instance running docker-compose (size it for Tesseract plus models; at least 2 GB RAM if LayoutLM is served) |
| Storage | S3 bucket for documents (private, server-side encryption) |
| Database | Postgres container on the instance, or RDS if budget allows |
| Networking | Security group allowing 80/443 only (plus SSH from your IP); Nginx or Caddy as reverse proxy with HTTPS |
| Secrets | Environment variables via SSM Parameter Store or a protected `.env` on the host |
| Logs | Container logs to CloudWatch (optional) |
| Domain/HTTPS | Free certificate via Let's Encrypt (Caddy handles this automatically) |

Alternatives: a single container on a PaaS (Render, as in your other projects) for the API, with S3 for storage. Check free-tier terms and pricing before choosing; they change.

## 6. Release checklist
- [ ] All tests green, model gates passed
- [ ] Migrations applied
- [ ] Sandbox keys only; webhook URL registered in the gateway dashboard
- [ ] HTTPS working; CORS restricted to the frontend origin
- [ ] Backups: database dump script documented
- [ ] README demo link and video updated

## 7. Operations notes
- Version every model; roll back by activating the previous version.
- Log model version, thresholds and timings with every decision.
- Stop the instance when not demoing to save cost.
