class TradeGuardException(Exception):
    """Base domain exception for TradeGuard."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class DocumentProcessingError(TradeGuardException):
    """Raised when document ingestion, OCR, or parsing fails."""

    def __init__(self, message: str, document_id: str | None = None):
        super().__init__(message, code="DOC_PROCESSING_ERROR")
        self.document_id = document_id


class ValidationError(TradeGuardException):
    """Raised when domain or cross-document validation encounters an invalid state."""

    def __init__(self, message: str, check_name: str | None = None):
        super().__init__(message, code="VALIDATION_ERROR")
        self.check_name = check_name


class PaymentLedgerError(TradeGuardException):
    """Raised when a payment state transition violates escrow invariants (e.g. double spend)."""

    def __init__(self, message: str, payment_id: str | None = None):
        super().__init__(message, code="PAYMENT_LEDGER_ERROR")
        self.payment_id = payment_id


class UnauthorizedTransitionError(TradeGuardException):
    """Raised when an illegal shipment state machine transition is attempted."""

    def __init__(self, current_status: str, target_status: str):
        msg = f"Cannot transition shipment from '{current_status}' to '{target_status}'"
        super().__init__(msg, code="ILLEGAL_STATE_TRANSITION")

