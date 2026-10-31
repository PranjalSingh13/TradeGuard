"""Pydantic schemas for request/response serialization."""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr, Field


# Auth
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = Field(default="buyer")


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str


# Shipments
class ShipmentCreateRequest(BaseModel):
    reference: str
    seller_id: str
    origin_port: str = "INNSA - Nhava Sheva"
    destination_port: str = "NLRTM - Rotterdam"
    incoterm: str = "FOB"
    declared_amount_minor: int = Field(gt=0)
    currency: str = "USD"


class ShipmentResponse(BaseModel):
    id: str
    reference: str
    buyer_id: str
    seller_id: str
    origin_port: str | None
    destination_port: str | None
    incoterm: str | None
    declared_amount_minor: int
    currency: str
    status: str
    created_at: datetime


# Documents
class DocumentUploadResponse(BaseModel):
    id: str
    shipment_id: str
    filename: str
    sha256: str
    status: str
    declared_type: str | None


# Payments
class CreateOrderRequest(BaseModel):
    shipment_id: str


class CapturePaymentRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str


# Review
class ReviewDecisionRequest(BaseModel):
    decision: str  # 'approve' | 'reject'
    reason: str


# Stateless ML
class ClassifyRequest(BaseModel):
    text: str


class ClassifyResponse(BaseModel):
    predicted_type: str
    confidence: float


class ExtractRequest(BaseModel):
    text: str
    document_type: str


class ExtractResponse(BaseModel):
    document_type: str
    fields: dict[str, Any]

