"""Shipments management and document processing endpoints."""
import hashlib
from typing import List
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from tradeguard.api.deps import get_current_user
from tradeguard.api.schemas import DocumentUploadResponse, ShipmentCreateRequest, ShipmentResponse
from tradeguard.core.constants import ShipmentStatus
from tradeguard.db.models import Document, Shipment, User
from tradeguard.db.session import get_db
from tradeguard.services.orchestrator import ShipmentOrchestrator

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.post("", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
def create_shipment(
    req: ShipmentCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = db.query(Shipment).filter(Shipment.reference == req.reference).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Shipment with reference '{req.reference}' already exists",
        )
    shipment = Shipment(
        reference=req.reference,
        buyer_id=user.id,
        seller_id=req.seller_id,
        origin_port=req.origin_port,
        destination_port=req.destination_port,
        incoterm=req.incoterm,
        declared_amount_minor=req.declared_amount_minor,
        currency=req.currency,
        status=ShipmentStatus.CREATED.value,
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    return shipment


@router.get("", response_model=List[ShipmentResponse])
def list_shipments(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role in ("reviewer", "admin"):
        return db.query(Shipment).order_by(Shipment.created_at.desc()).all()
    # Buyers and sellers see shipments they are parties to
    return (
        db.query(Shipment)
        .filter((Shipment.buyer_id == user.id) | (Shipment.seller_id == user.id))
        .order_by(Shipment.created_at.desc())
        .all()
    )


@router.get("/{shipment_id}")
def get_shipment_details(
    shipment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    docs = db.query(Document).filter(Document.shipment_id == shipment.id).all()
    return {
        "shipment": {
            "id": shipment.id,
            "reference": shipment.reference,
            "status": shipment.status,
            "declared_amount_minor": shipment.declared_amount_minor,
            "currency": shipment.currency,
            "origin_port": shipment.origin_port,
            "destination_port": shipment.destination_port,
            "incoterm": shipment.incoterm,
            "created_at": shipment.created_at,
        },
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "declared_type": d.declared_type,
                "predicted_type": d.predicted_type,
                "status": d.status,
                "ocr_mean_conf": d.ocr_mean_conf,
            }
            for d in docs
        ],
        "validation_checks": [
            {
                "check_name": v.check_name,
                "passed": v.passed,
                "severity": v.severity,
                "detail": v.detail,
            }
            for v in shipment.validation_checks
        ],
        "risk_assessments": [
            {
                "score": r.score,
                "decision": r.decision,
                "top_reasons": r.top_reasons,
                "created_at": r.created_at,
            }
            for r in shipment.risk_assessments
        ],
    }


@router.post("/{shipment_id}/documents", response_model=DocumentUploadResponse)
def upload_shipment_document(
    shipment_id: str,
    filename: str = Form(...),
    declared_type: str = Form(...),
    document_text: str = Form(""),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Read content either from uploaded file or form text
    if file:
        content = file.file.read()
        sha256 = hashlib.sha256(content).hexdigest()
        text_content = content.decode("utf-8", errors="ignore")
    else:
        content = document_text.encode("utf-8")
        sha256 = hashlib.sha256(content).hexdigest()
        text_content = document_text

    doc = Document(
        shipment_id=shipment.id,
        uploaded_by=user.id,
        filename=filename,
        storage_key=text_content,
        sha256=sha256,
        declared_type=declared_type,
        status="uploaded",
    )
    db.add(doc)

    # Update shipment status
    if shipment.status == ShipmentStatus.FUNDS_HELD.value or shipment.status == ShipmentStatus.CREATED.value:
        shipment.status = ShipmentStatus.DOCS_UPLOADED.value

    db.commit()
    db.refresh(doc)
    return DocumentUploadResponse(
        id=doc.id,
        shipment_id=shipment.id,
        filename=doc.filename,
        sha256=doc.sha256,
        status=doc.status,
        declared_type=doc.declared_type,
    )


@router.post("/{shipment_id}/process")
def process_shipment_pipeline(
    shipment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    orchestrator = ShipmentOrchestrator(db)
    outcome = orchestrator.process_shipment(shipment_id)
    return {
        "shipment_id": shipment_id,
        "decision": outcome.decision.value,
        "risk_score": outcome.risk_score,
        "reasons": outcome.reasons,
        "failed_checks": outcome.failed_checks,
        "hard_rule_triggered": outcome.hard_rule_triggered,
    }

