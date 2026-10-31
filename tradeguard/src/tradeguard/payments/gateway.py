"""Payment Gateway Interface and Simulated Sandbox Provider.

Follows docs/08-PAYMENT-ESCROW.md.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import hmac
import uuid


@dataclass
class GatewayOrder:
    order_id: str
    amount_minor: int
    currency: str
    status: str  # 'created' | 'attempted' | 'paid'


@dataclass
class GatewayPayment:
    payment_id: str
    order_id: str
    amount_minor: int
    currency: str
    status: str  # 'captured' | 'failed' | 'refunded'


class PaymentGateway(ABC):
    """Abstract interface for payment gateway providers (Razorpay, Stripe, Simulated)."""

    @abstractmethod
    def create_order(self, amount_minor: int, currency: str, reference: str) -> GatewayOrder:
        pass

    @abstractmethod
    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        pass

    @abstractmethod
    def release_funds(self, payment_id: str, amount_minor: int, recipient_ref: str) -> str:
        """Disburse held funds to seller. Returns transfer transaction reference."""
        pass

    @abstractmethod
    def refund_funds(self, payment_id: str, amount_minor: int) -> str:
        """Refund held funds to buyer. Returns refund transaction reference."""
        pass


class SimulatedGateway(PaymentGateway):
    """In-memory sandbox gateway for reproducible testing and development without live credentials."""

    def __init__(self, secret: str = "simulated_secret"):
        self.secret = secret
        self.orders: dict[str, GatewayOrder] = {}
        self.payments: dict[str, GatewayPayment] = {}

    def create_order(self, amount_minor: int, currency: str, reference: str) -> GatewayOrder:
        order_id = f"order_sim_{uuid.uuid4().hex[:12]}"
        order = GatewayOrder(order_id=order_id, amount_minor=amount_minor, currency=currency, status="created")
        self.orders[order_id] = order
        return order

    def simulate_capture(self, order_id: str) -> tuple[str, str]:
        """Simulate buyer completing checkout. Returns (payment_id, signature)."""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError("Order not found")
        payment_id = f"pay_sim_{uuid.uuid4().hex[:12]}"
        order.status = "paid"
        self.payments[payment_id] = GatewayPayment(
            payment_id=payment_id,
            order_id=order_id,
            amount_minor=order.amount_minor,
            currency=order.currency,
            status="captured",
        )
        # Compute valid HMAC signature
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        sig = hmac.new(self.secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return payment_id, sig

    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        expected_sig = hmac.new(self.secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, signature)

    def release_funds(self, payment_id: str, amount_minor: int, recipient_ref: str) -> str:
        payment = self.payments.get(payment_id)
        if not payment:
            raise ValueError("Payment not found in gateway")
        transfer_id = f"xfer_sim_{uuid.uuid4().hex[:12]}"
        return transfer_id

    def refund_funds(self, payment_id: str, amount_minor: int) -> str:
        payment = self.payments.get(payment_id)
        if not payment:
            raise ValueError("Payment not found in gateway")
        payment.status = "refunded"
        refund_id = f"rfnd_sim_{uuid.uuid4().hex[:12]}"
        return refund_id

