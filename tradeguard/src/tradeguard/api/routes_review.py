"""Review queue and manual dispute resolution endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from tradeguard.api.deps import require_role
from tradeguard.api.schemas import ReviewDecisionRequest
from tradeguard.core.constants import ShipmentStatus
from tradeguard.db.models import Payment, ReviewCase, Shipment, User
from tradeguard.db.session import get_db
from tradeguard.payments.ledger import LedgerService

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue")
def list_review_queue(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("reviewer")),
):
    cases = (
        db.query(ReviewCase)
        .filter(ReviewCase.status == "open")
        .order_by(ReviewCase.created_at.desc())
        .all()
    )
    results = []
    for c in cases:
        shipment = db.query(Shipment).filter(Shipment.id == c.shipment_id).first()
        results.append({
            "case_id": c.id,
            "shipment_id": c.shipment_id,
            "shipment_reference": shipment.reference if shipment else "unknown",
            "reason": c.reason,
            "created_at": c.created_at,
        })
    return results


@router.post("/{case_id}/decision")
def submit_review_decision(
    case_id: str,
    req: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("reviewer")),
):
    case = db.query(ReviewCase).filter(ReviewCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Review case not found")
    if case.status != "open":
        raise HTTPException(status_code=400, detail="Review case is already decided")

    case.assigned_to = user.id
    case.status = "decided"
    case.decision = req.decision
    case.reason = req.reason
    case.decided_at = datetime.utcnow()

    shipment = db.query(Shipment).filter(Shipment.id == case.shipment_id).first()
    payment = (
        db.query(Payment)
        .filter(Payment.shipment_id == case.shipment_id, Payment.status == "captured")
        .first()
    )
    ledger = LedgerService(db)

    if req.decision == "approve":
        if shipment:
            shipment.status = ShipmentStatus.RELEASE_APPROVED.value
        if payment:
            ledger.record_release(
                shipment_id=shipment.id,
                payment_id=payment.id,
                amount_minor=payment.amount_minor,
                external_ref=f"MANUAL_APPROVAL_BY_{user.email}",
            )
    elif req.decision == "reject":
        if shipment:
            shipment.status = ShipmentStatus.REFUND_APPROVED.value
        if payment:
            ledger.record_refund(
                shipment_id=shipment.id,
                payment_id=payment.id,
                amount_minor=payment.amount_minor,
                external_ref=f"MANUAL_REJECTION_BY_{user.email}",
            )
    else:
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'reject'")

    db.commit()
    return {"case_id": case.id, "status": case.status, "decision": case.decision}

