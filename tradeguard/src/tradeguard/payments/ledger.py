"""Append-Only Escrow Ledger Service.

Enforces financial integrity: funds can move to terminal states ('release' or 'refund') exactly once.
"""
from sqlalchemy.orm import Session
from tradeguard.core.constants import LedgerType, ShipmentStatus
from tradeguard.core.exceptions import PaymentLedgerError
from tradeguard.db.models import LedgerEntry, Payment, Shipment


class LedgerService:
    """Manages escrow ledger transactions with database-level double-spend prevention."""

    def __init__(self, db: Session):
        self.db = db

    def record_hold(self, shipment_id: str, payment_id: str, amount_minor: int, external_ref: str | None = None) -> LedgerEntry:
        """Record funds held into escrow."""
        entry = LedgerEntry(
            shipment_id=shipment_id,
            payment_id=payment_id,
            entry_type=LedgerType.HOLD.value,
            amount_minor=amount_minor,
            external_ref=external_ref,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def record_release(self, shipment_id: str, payment_id: str, amount_minor: int, external_ref: str | None = None) -> LedgerEntry:
        """Disburse funds from escrow to seller. Guaranteed to execute at most once."""
        self._check_no_prior_terminal_entry(payment_id)

        entry = LedgerEntry(
            shipment_id=shipment_id,
            payment_id=payment_id,
            entry_type=LedgerType.RELEASE.value,
            amount_minor=amount_minor,
            external_ref=external_ref,
        )
        self.db.add(entry)

        # Update payment and shipment statuses
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if payment:
            payment.status = "released"

        shipment = self.db.query(Shipment).filter(Shipment.id == shipment_id).first()
        if shipment:
            shipment.status = ShipmentStatus.RELEASED.value

        self.db.commit()
        self.db.refresh(entry)
        return entry

    def record_refund(self, shipment_id: str, payment_id: str, amount_minor: int, external_ref: str | None = None) -> LedgerEntry:
        """Refund funds from escrow to buyer. Guaranteed to execute at most once."""
        self._check_no_prior_terminal_entry(payment_id)

        entry = LedgerEntry(
            shipment_id=shipment_id,
            payment_id=payment_id,
            entry_type=LedgerType.REFUND.value,
            amount_minor=amount_minor,
            external_ref=external_ref,
        )
        self.db.add(entry)

        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if payment:
            payment.status = "refunded"

        shipment = self.db.query(Shipment).filter(Shipment.id == shipment_id).first()
        if shipment:
            shipment.status = ShipmentStatus.REFUNDED.value

        self.db.commit()
        self.db.refresh(entry)
        return entry

    def _check_no_prior_terminal_entry(self, payment_id: str) -> None:
        """Verify that payment has not already been released or refunded."""
        existing = (
            self.db.query(LedgerEntry)
            .filter(
                LedgerEntry.payment_id == payment_id,
                LedgerEntry.entry_type.in_([LedgerType.RELEASE.value, LedgerType.REFUND.value]),
            )
            .first()
        )
        if existing:
            raise PaymentLedgerError(
                f"Double terminal transaction detected: payment {payment_id} already has a {existing.entry_type} entry",
                payment_id=payment_id,
            )

