"""SQLAlchemy models for TradeGuard.

Corresponds to docs/05-DATABASE-SCHEMA.md.
"""
from datetime import datetime
import uuid
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.types import JSON

Base = declarative_base()

# Use standard JSON compatible across Postgres and SQLite
JsonType = JSON().with_variant(JSONB, "postgresql")


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'buyer' | 'seller' | 'reviewer' | 'admin'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    reference = Column(String(100), unique=True, nullable=False, index=True)
    buyer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    seller_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    origin_port = Column(String(255))
    destination_port = Column(String(255))
    incoterm = Column(String(50))
    declared_amount_minor = Column(BigInteger, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(String(50), nullable=False, default="created")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    documents = relationship("Document", back_populates="shipment", cascade="all, delete-orphan")
    validation_checks = relationship("ValidationCheck", back_populates="shipment", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="shipment", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="shipment")
    review_cases = relationship("ReviewCase", back_populates="shipment")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    shipment_id = Column(String(36), ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    storage_key = Column(String(500), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    declared_type = Column(String(50))
    predicted_type = Column(String(50))
    type_confidence = Column(Float)
    ocr_mean_conf = Column(Float)
    page_count = Column(Integer, default=1)
    status = Column(String(50), nullable=False, default="uploaded")
    failure_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    shipment = relationship("Shipment", back_populates="documents")
    extractions = relationship("Extraction", back_populates="document", cascade="all, delete-orphan")


class Extraction(Base):
    __tablename__ = "extractions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    fields = Column(JsonType, nullable=False, default=dict)
    field_confidences = Column(JsonType, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="extractions")


class ValidationCheck(Base):
    __tablename__ = "validation_checks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    shipment_id = Column(String(36), ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    check_name = Column(String(100), nullable=False)
    passed = Column(Boolean, nullable=False)
    severity = Column(String(20), nullable=False)  # 'low' | 'medium' | 'high'
    detail = Column(JsonType, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    shipment = relationship("Shipment", back_populates="validation_checks")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    shipment_id = Column(String(36), ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    decision = Column(String(50), nullable=False)  # 'auto_release' | 'manual_review' | 'hold'
    features = Column(JsonType, nullable=False, default=dict)
    top_reasons = Column(JsonType, default=list)
    thresholds = Column(JsonType, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    shipment = relationship("Shipment", back_populates="risk_assessments")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    shipment_id = Column(String(36), ForeignKey("shipments.id"), nullable=False, index=True)
    gateway = Column(String(50), nullable=False)
    gateway_order_id = Column(String(100), unique=True)
    gateway_payment_id = Column(String(100), unique=True)
    amount_minor = Column(BigInteger, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(String(50), nullable=False)  # 'created' | 'captured' | 'released' | 'refunded'
    idempotency_key = Column(String(100), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    shipment = relationship("Shipment", back_populates="payments")
    ledger_entries = relationship("LedgerEntry", back_populates="payment")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(String(36), ForeignKey("shipments.id"), nullable=False, index=True)
    payment_id = Column(String(36), ForeignKey("payments.id"), nullable=True, index=True)
    entry_type = Column(String(20), nullable=False)  # 'hold' | 'release' | 'refund'
    amount_minor = Column(BigInteger, nullable=False)
    external_ref = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    payment = relationship("Payment", back_populates="ledger_entries")


class ReviewCase(Base):
    __tablename__ = "review_cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    shipment_id = Column(String(36), ForeignKey("shipments.id"), nullable=False, index=True)
    assigned_to = Column(String(36), ForeignKey("users.id"), nullable=True)
    status = Column(String(50), nullable=False, default="open")  # 'open' | 'decided'
    decision = Column(String(50))  # 'approve' | 'reject'
    reason = Column(Text)
    decided_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    shipment = relationship("Shipment", back_populates="review_cases")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gateway = Column(String(50), nullable=False)
    event_id = Column(String(100), nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JsonType, nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_gateway_event_id", "gateway", "event_id", unique=True),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=False)
    metadata_json = Column("metadata", JsonType, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

