# 08. Payment and Escrow Flow

> **Sandbox only.** Real escrow is a regulated activity. TradeGuard simulates the *behavior* of escrow using gateway test mode plus an internal ledger. Gateway feature names and availability below should be **verified against the current gateway documentation** before building, since they vary by account type and region.

## 1. Design goals
- The ML/validation decision controls when funds move.
- Funds can leave the HELD state **exactly once** (release or refund).
- Safe under retries, duplicate webhooks and partial failures.
- Gateway is swappable (`PaymentGateway` interface).

## 2. Gateway interface
```python
class PaymentGateway(Protocol):
    def create_order(self, amount_minor: int, currency: str, receipt: str) -> GatewayOrder: ...
    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool: ...
    def verify_webhook(self, raw_body: bytes, signature: str) -> bool: ...
    def release(self, payment_id: str, amount_minor: int, seller_ref: str) -> GatewayResult: ...
    def refund(self, payment_id: str, amount_minor: int) -> GatewayResult: ...
```
Implementations: `RazorpayGateway` (test mode), `StripeGateway` (optional), `SimulatedGateway` (ledger-only, for tests and as fallback).

## 3. Primary flow (Razorpay test mode)
1. **Create order:** buyer calls `POST /shipments/{id}/payment/order`. Server computes the amount from the shipment (never from the client), creates a gateway order with the shipment reference as receipt, stores a `payments` row (`created`).
2. **Checkout:** frontend opens the gateway checkout with the order ID (test cards/UPI per gateway docs).
3. **Client confirmation:** frontend posts the payment ID, order ID and signature to `POST /payments/verify`. Server verifies the signature (HMAC-SHA256 over `order_id|payment_id` with the key secret, per gateway docs). This is a convenience; it is **not** the source of truth.
4. **Webhook (source of truth):** `payment.captured` (or equivalent) arrives; server verifies the webhook signature over the raw body, dedupes by event ID, marks payment `captured`, appends a `hold` ledger entry, and moves the shipment to `funds_held`.
5. **Decision:** after document processing, the decision engine returns `auto_release`, `manual_review` or `hold`.
6. **Release path:** write the release intent, call `gateway.release(...)`, and append the `release` ledger entry only when the gateway confirms (or immediately in simulated mode). Shipment becomes `released`.
7. **Refund path:** reviewer rejects (or a hold expires) so server calls `gateway.refund(...)`, waits for the refund confirmation event, appends a `refund` ledger entry, shipment becomes `refunded`.

## 4. How "release to seller" can be implemented
| Option | Description | Notes |
|---|---|---|
| A. Gateway marketplace transfer | Razorpay Route-style transfer to a seller linked account in test mode (transfers can be created on hold and released later, per gateway docs) | Closest to real escrow; check account eligibility |
| B. Authorize now, capture later | Stripe-style manual capture; capture on release, cancel/refund on reject | Authorization windows are limited; check current rules |
| C. Ledger-only simulation | Platform account holds funds; release is a ledger entry plus a mock payout record | Always available; clearly label as simulation |

Recommended order: build **C first** (works everywhere), then add **A or B** behind the same interface.

## 5. Ledger rules
- Append-only `ledger_entries`; corrections are new entries, never edits.
- Entry types: `hold`, `release`, `refund`.
- Database constraint: at most one `release` or `refund` per payment (partial unique index in [05-DATABASE-SCHEMA.md](05-DATABASE-SCHEMA.md)).
- Invariant checked by tests: `sum(hold) - sum(release) - sum(refund) >= 0` and equals zero after a terminal state.

## 6. Idempotency and concurrency
- Clients send `Idempotency-Key` on order creation and verification; server stores and replays results.
- Webhooks deduped on `(gateway, event_id)`.
- Release/refund executed inside a transaction with a row lock on the shipment (`SELECT ... FOR UPDATE`) and a state check.
- Gateway calls use a stored external reference so a retry cannot double-pay.

## 7. Failure handling
| Scenario | Behavior |
|---|---|
| Payment fails or is abandoned | Shipment stays `payment_pending`, then `cancelled` after expiry |
| Duplicate webhook | Ignored (already in `webhook_events`) |
| Webhook arrives before client verify | Webhook wins; verify endpoint becomes a no-op |
| Invalid webhook signature | 400, logged, no state change |
| Release call times out | Mark `release_pending`; reconcile job queries gateway state before retrying |
| Pipeline error or low OCR confidence | Decision = `manual_review`; funds stay held |
| Reviewer never acts | Configurable SLA; escalate and eventually refund per policy (documented, simulated) |
| Amount tampering in client | Ignored; server-computed amount only |

## 8. Security checklist
- [ ] Keys in environment variables, never committed
- [ ] Webhook signature verified on raw body
- [ ] Amounts server-side, integers in minor units
- [ ] HTTPS only on deployment
- [ ] No card data touches your servers (gateway-hosted checkout)
- [ ] Audit log entry for every money-related transition

## 9. Test scenarios (sandbox)
1. Happy path: pay, hold, auto-release.
2. Pay, manual review, reviewer approves, release.
3. Pay, manual review, reviewer rejects, refund.
4. High-risk hold, reviewer rejects, refund.
5. Duplicate webhook delivery.
6. Out-of-order events.
7. Concurrent release attempts (expect exactly one success).
8. Gateway timeout then reconciliation.
