"""Escrow payment routes: order creation, capture, webhooks, and ledger queries."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from tradeguard.api.deps import get_current_user
from tradeguard.api.schemas import CapturePaymentRequest, CreateOrderRequest
from tradeguard.core.constants import ShipmentStatus
from tradeguard.db.models import LedgerEntry, Payment, Shipment, User
from tradeguard.db.session import get_db
from tradeguard.payments.gateway import SimulatedGateway
from tradeguard.payments.ledger import LedgerService

router = APIRouter(prefix="/payments", tags=["payments"])
gateway = SimulatedGateway()


@router.post("/create-order")
def create_payment_order(
    req: CreateOrderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    shipment = db.query(Shipment).filter(Shipment.id == req.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    order = gateway.create_order(
        amount_minor=shipment.declared_amount_minor,
        currency=shipment.currency,
        reference=shipment.reference,
    )
    # Record payment entity
    payment = Payment(
        shipment_id=shipment.id,
        gateway="simulated",
        gateway_order_id=order.order_id,
        amount_minor=shipment.declared_amount_minor,
        currency=shipment.currency,
        status="created",
    )
    db.add(payment)
    shipment.status = ShipmentStatus.PAYMENT_PENDING.value
    db.commit()
    db.refresh(payment)

    return {
        "payment_id": payment.id,
        "gateway_order_id": order.order_id,
        "amount_minor": order.amount_minor,
        "currency": order.currency,
    }


@router.post("/simulate-checkout/{order_id}")
def simulate_checkout(order_id: str):
    """Utility endpoint to simulate successful buyer card authorization in sandbox mode."""
    try:
        payment_id, signature = gateway.simulate_capture(order_id)
        return {"payment_id": payment_id, "signature": signature, "order_id": order_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/capture")
def capture_payment(
    req: CapturePaymentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify HMAC signature
    is_valid = gateway.verify_payment_signature(req.order_id, req.payment_id, req.signature)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid payment verification signature")

    payment = db.query(Payment).filter(Payment.gateway_order_id == req.order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record for order not found")

    payment.gateway_payment_id = req.payment_id
    payment.status = "captured"

    shipment = db.query(Shipment).filter(Shipment.id == payment.shipment_id).first()
    if shipment:
        shipment.status = ShipmentStatus.FUNDS_HELD.value

    # Record hold in append-only ledger
    ledger = LedgerService(db)
    ledger.record_hold(
        shipment_id=payment.shipment_id,
        payment_id=payment.id,
        amount_minor=payment.amount_minor,
        external_ref=req.payment_id,
    )
    db.commit()

    return {"status": "funds_held", "payment_id": payment.id, "shipment_id": payment.shipment_id}


@router.get("/ledger/{shipment_id}")
def get_shipment_ledger(
    shipment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entries = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.shipment_id == shipment_id)
        .order_by(LedgerEntry.created_at.asc())
        .all()
    )
    return [
        {
            "id": e.id,
            "entry_type": e.entry_type,
            "amount_minor": e.amount_minor,
            "external_ref": e.external_ref,
            "created_at": e.created_at,
        }
        for e in entries
    ]

