# 06. API Specification

Base URL: `/api/v1`. JSON unless noted. Auth: `Authorization: Bearer <JWT>`. FastAPI will also serve live OpenAPI docs at `/docs`; treat this file as the design contract.

## 1. Conventions
- IDs are UUIDs. Timestamps are ISO 8601 UTC. Money is an integer in minor units (paise/cents) plus a currency code.
- Pagination: `?page=1&page_size=20`.
- State-changing payment calls accept an `Idempotency-Key` header.
- Error format:
```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Human readable", "details": [] } }
```
- Status codes: 200/201 success, 400/422 validation, 401 unauthenticated, 403 forbidden, 404 not found, 409 conflict (state), 429 rate limited.

## 2. Endpoints

### Auth
| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/auth/register` | public | Create user (role limited to buyer/seller; reviewer/admin seeded) |
| POST | `/auth/login` | public | Returns access and refresh tokens |
| POST | `/auth/refresh` | public | Rotate tokens |
| GET | `/me` | any | Current user |

### Shipments
| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/shipments` | buyer | Create shipment |
| GET | `/shipments` | any | List own shipments (reviewer/admin: all) |
| GET | `/shipments/{id}` | party/reviewer/admin | Detail with status timeline |
| GET | `/shipments/{id}/timeline` | party/reviewer/admin | Status and audit events |

### Documents and processing
| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/shipments/{id}/documents` | seller | Multipart upload (`file`, optional `declared_type`) |
| GET | `/shipments/{id}/documents` | party/reviewer | List documents with predicted type and status |
| GET | `/documents/{id}/extraction` | party/reviewer | Extracted fields and confidences |
| POST | `/shipments/{id}/process` | seller/admin | Start (or re-run) the pipeline |
| GET | `/shipments/{id}/checks` | party/reviewer | Validation check results |
| GET | `/shipments/{id}/risk` | party/reviewer | Latest risk assessment: score, decision, reasons |

### Payments
| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/shipments/{id}/payment/order` | buyer | Create gateway order for the server-computed amount |
| POST | `/payments/verify` | buyer | Verify client-side payment signature |
| POST | `/webhooks/razorpay` | gateway | Signed webhook receiver (raw body verified) |
| GET | `/shipments/{id}/ledger` | party/reviewer | Ledger entries (hold, release, refund) |

### Review
| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/review/cases` | reviewer | Open cases, newest/highest risk first |
| GET | `/review/cases/{id}` | reviewer | Case detail with fields, checks, reasons |
| POST | `/review/cases/{id}/decision` | reviewer | `{ "decision": "approve|reject", "reason": "..." }` |

### Stateless ML API (P1)
| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/ml/classify` | any (API key/JWT) | Single file in, document type and confidence out |
| POST | `/ml/extract` | any | Single file in, fields and confidences out |

### Admin and ops
| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/admin/models` | admin | Model versions and metrics |
| POST | `/admin/models/{id}/activate` | admin | Set active model for its task |
| GET | `/admin/thresholds` | admin | Current decision thresholds |
| GET | `/health` | public | Liveness/readiness |

## 3. Example payloads

**Create shipment**
```http
POST /api/v1/shipments
{
  "reference": "TG-2026-0001",
  "seller_id": "7a1c...",
  "origin_port": "INNSA",
  "destination_port": "NLRTM",
  "incoterm": "FOB",
  "declared_amount_minor": 125000000,
  "currency": "INR"
}
```

**Risk assessment response**
```json
{
  "shipment_id": "b3e0...",
  "model_version": "risk-xgb-0.3.1",
  "score": 0.1840,
  "decision": "manual_review",
  "thresholds": { "t_low": 0.10, "t_high": 0.60 },
  "top_reasons": [
    { "feature": "weight_diff_pct", "value": 0.034, "impact": 0.21, "text": "Gross weight differs by 3.4% between bill of lading and packing list" },
    { "feature": "consignee_name_similarity", "value": 0.88, "impact": 0.12, "text": "Consignee name is similar but not identical across documents" }
  ],
  "checks": [
    { "name": "container_iso6346_valid", "passed": true, "severity": "high" },
    { "name": "weight_match", "passed": false, "severity": "medium" }
  ]
}
```

**Stateless classify**
```http
POST /api/v1/ml/classify   (multipart/form-data: file)
-> { "doc_type": "commercial_invoice", "confidence": 0.973, "model_version": "doc-cls-0.2.0", "ocr_mean_conf": 0.91 }
```

**Review decision**
```http
POST /api/v1/review/cases/{id}/decision
{ "decision": "approve", "reason": "Weight variance within tolerance; consignee name is a legal-entity abbreviation." }
```

## 4. Webhook handling contract
1. Read the **raw** request body.
2. Verify the signature header against the webhook secret; reject with 400 on mismatch.
3. Insert into `webhook_events` (`gateway`, `event_id` unique); if duplicate, return 200 without reprocessing.
4. Process in a transaction; update payment, ledger and shipment status.
5. Return 200 quickly; do slow work asynchronously.

## 5. Rate limits (suggested)
Auth endpoints: 10/min per IP. Uploads: 30/min per user. ML endpoints: 60/min per key.
