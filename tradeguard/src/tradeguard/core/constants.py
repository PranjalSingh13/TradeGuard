from enum import Enum


class UserRole(str, Enum):
    BUYER = "buyer"
    SELLER = "seller"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class ShipmentStatus(str, Enum):
    CREATED = "created"
    PAYMENT_PENDING = "payment_pending"
    FUNDS_HELD = "funds_held"
    DOCS_UPLOADED = "docs_uploaded"
    PROCESSING = "processing"
    UNDER_REVIEW = "under_review"
    HELD_FOR_RISK = "held_for_risk"
    AUTO_RELEASE_APPROVED = "auto_release_approved"
    RELEASE_APPROVED = "release_approved"
    REFUND_APPROVED = "refund_approved"
    RELEASED = "released"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class DocumentType(str, Enum):
    BILL_OF_LADING = "bill_of_lading"
    COMMERCIAL_INVOICE = "commercial_invoice"
    PACKING_LIST = "packing_list"
    CERTIFICATE_OF_ORIGIN = "certificate_of_origin"
    OTHER = "other"


class DecisionType(str, Enum):
    AUTO_RELEASE = "auto_release"
    MANUAL_REVIEW = "manual_review"
    HOLD = "hold"


class LedgerType(str, Enum):
    HOLD = "hold"
    RELEASE = "release"
    REFUND = "refund"


class CheckSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DiscrepancyType(str, Enum):
    WEIGHT_MISMATCH = "weight_mismatch"
    PACKAGE_COUNT_MISMATCH = "package_count_mismatch"
    CONSIGNEE_NAME_ALTERED = "consignee_name_altered"
    INVALID_CONTAINER_CHECK_DIGIT = "invalid_container_check_digit"
    CONTAINER_MISMATCH = "container_mismatch"
    PORT_MISMATCH = "port_mismatch"
    DATE_ORDER_VIOLATION = "date_order_violation"
    VALUE_OUTLIER = "value_outlier"
    DUPLICATE_DOCUMENT = "duplicate_document"

