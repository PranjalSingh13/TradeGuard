"""Stress tests and edge case evaluation on unexpected and adversarial data."""
import math
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tradeguard.api.app import app
from tradeguard.core.constants import CheckSeverity, DecisionType, DocumentType, ShipmentStatus
from tradeguard.core.exceptions import PaymentLedgerError
from tradeguard.db.models import Base, Shipment
from tradeguard.db.session import get_db
from tradeguard.extraction.rules_extractor import RulesExtractor
from tradeguard.ml.features import extract_features_dict, extract_features_vector
from tradeguard.ml.models.doc_classifier import DocumentClassifier
from tradeguard.ml.models.risk_model import RiskModel
from tradeguard.ocr.engine import OCREngine
from tradeguard.payments.gateway import SimulatedGateway
from tradeguard.payments.ledger import LedgerService
from tradeguard.services.decision_engine import DecisionEngine
from tradeguard.validation.cross_doc import ShipmentExtractionBundle, run_cross_document_validation
from tradeguard.validation.iso6346 import is_valid_container


# ---------------------------------------------------------------------------
# 1. OCR & Extraction on Garbage, Adversarial, and Empty Inputs
# ---------------------------------------------------------------------------

def test_ocr_on_empty_and_garbage_input():
    engine = OCREngine()

    # Empty string
    res_empty = engine.extract_from_text("")
    assert res_empty.mean_confidence <= 0.20
    assert res_empty.total_pages == 1

    # Whitespace only
    res_ws = engine.extract_from_text("    \n\t   \n  ")
    assert res_ws.mean_confidence <= 0.20

    # Non-printable / corrupted binary noise
    garbage = "".join(chr(i) for i in range(1, 25)) + "\x00\xff\xfe\x00\x00"
    res_garbage = engine.extract_from_text(garbage)
    assert res_garbage.mean_confidence < 0.65


def test_extractor_on_adversarial_text():
    extractor = RulesExtractor()

    # Highly corrupted text with emojis, symbols, and SQL injection strings
    corrupted_text = """
    @@@###$$$%%% DROP TABLE shipments; -- 
    BILL OF LADING NO: ' OR '1'='1
    CONTAINER NUMBER: INVALID_12345
    GROSS WEIGHT: not_a_number KG
    PACKAGES: -9999
    DATE: 9999-99-99
    """
    fields = extractor.extract_fields(corrupted_text, DocumentType.BILL_OF_LADING)

    # Should gracefully parse without throwing exceptions
    assert isinstance(fields, dict)
    # Should not crash on invalid numbers
    assert fields.get("gross_weight_kg") is None


def test_classifier_on_random_garbage():
    classifier = DocumentClassifier()

    # Pure gibberish
    gibberish = "qwertyuiop asdfghjkl zxcvbnm 1234567890 !@#$%^&*()_+~`"
    doc_type, conf = classifier.predict(gibberish)
    assert isinstance(doc_type, DocumentType)
    assert 0.0 <= conf <= 1.0


# ---------------------------------------------------------------------------
# 2. Validation Engine on Outliers, Missing Bundles, and Absurd Quantities
# ---------------------------------------------------------------------------

def test_validation_on_empty_bundle():
    bundle = ShipmentExtractionBundle()
    results = run_cross_document_validation(bundle)

    # Missing required fields check must trigger high severity
    missing_check = next((r for r in results if r.check_name == "required_fields_present"), None)
    assert missing_check is not None
    assert not missing_check.passed
    assert missing_check.severity == CheckSeverity.HIGH


def test_validation_on_absurd_weight_discrepancy():
    # BoL says 100,000 kg, Packing list says 5 kg (extreme fraud attempt)
    bundle = ShipmentExtractionBundle(
        bill_of_lading={
            "document_number": "MEDU9999999",
            "shipper": "Alpha Corp",
            "consignee": "Beta Corp",
            "gross_weight_kg": 100000.0,
            "port_of_loading": "INNSA",
            "port_of_discharge": "NLRTM",
        },
        packing_list={
            "document_number": "PL-1",
            "gross_weight_kg": 5.0,
        },
        commercial_invoice={
            "document_number": "INV-1",
            "total_amount": 50000,
            "currency": "USD",
            "date": "2026-01-01",
        },
    )
    results = run_cross_document_validation(bundle)
    weight_check = next((r for r in results if r.check_name == "weight_agreement"), None)
    assert weight_check is not None
    assert not weight_check.passed
    assert weight_check.severity == CheckSeverity.HIGH
    assert weight_check.detail["diff_pct"] > 90.0


def test_iso6346_adversarial_container_strings():
    # Test boundary and malformed values
    assert not is_valid_container("")
    assert not is_valid_container("       ")
    assert not is_valid_container("12345678901")
    assert not is_valid_container("CSQU305438")       # 10 chars (too short)
    assert not is_valid_container("CSQU30543833")     # 12 chars (too long)
    assert not is_valid_container("CSQA3054383")      # Category letter 'A' is illegal (must be U, J, Z)
    assert not is_valid_container("CSQU305438A")      # Last char not digit
    assert not is_valid_container("DROP TABLE --")


# ---------------------------------------------------------------------------
# 3. Decision Engine Hard-Rule & Low-OCR Overrides Under Stress
# ---------------------------------------------------------------------------

def test_decision_engine_hard_rule_override_even_with_zero_ml_score():
    engine = DecisionEngine(t_low=0.20, t_high=0.60, ocr_gate=0.70)

    # Even if ML model outputs 0.0000 (ultra-clean score),
    # a container check digit failure MUST force HOLD!
    corrupted_container_bundle = ShipmentExtractionBundle(
        bill_of_lading={
            "document_number": "B1",
            "shipper": "S1",
            "consignee": "C1",
            "container_number": "CSQU3054384",  # BAD check digit
            "port_of_loading": "INNSA",
            "port_of_discharge": "NLRTM",
            "gross_weight_kg": 5000,
        },
        commercial_invoice={"document_number": "I1", "date": "2026-05-01", "total_amount": 1000, "currency": "USD"},
    )
    results = run_cross_document_validation(corrupted_container_bundle)
    outcome = engine.evaluate(risk_score=0.0001, validation_results=results)

    assert outcome.decision == DecisionType.HOLD
    assert outcome.hard_rule_triggered
    assert "Hard rule violation" in outcome.reasons[0]


def test_decision_engine_low_ocr_forces_manual_review_never_auto_release():
    engine = DecisionEngine(t_low=0.20, t_high=0.60, ocr_gate=0.70)

    # Perfect clean validation, risk score = 0.01, BUT degraded scan OCR confidence 0.45
    bundle = ShipmentExtractionBundle(
        bill_of_lading={"document_number": "B1", "shipper": "S1", "consignee": "C1", "port_of_loading": "P1", "port_of_discharge": "P2", "gross_weight_kg": 1000},
        commercial_invoice={"document_number": "I1", "date": "2026-05-01", "total_amount": 5000, "currency": "USD"},
    )
    results = run_cross_document_validation(bundle)
    outcome = engine.evaluate(
        risk_score=0.01,
        validation_results=results,
        ocr_conf_min=0.45,  # Below 0.70 gate
    )

    assert outcome.decision == DecisionType.MANUAL_REVIEW
    assert outcome.confidence_gate_failed


# ---------------------------------------------------------------------------
# 4. Feature Extraction & Risk Model Resilience
# ---------------------------------------------------------------------------

def test_feature_vector_with_nan_and_infinite_values():
    bundle = ShipmentExtractionBundle(
        ocr_mean_confs=[0.95],
        cls_confs=[0.95],
    )
    # Empty validation
    vec = extract_features_vector(bundle, [])
    assert len(vec) == 16
    assert not np.isnan(vec).any()
    assert not np.isinf(vec).any()


def test_payment_gateway_tampered_signature():
    gateway = SimulatedGateway(secret="secret_123")
    order = gateway.create_order(50000, "USD", "REF-001")
    payment_id, sig = gateway.simulate_capture(order.order_id)

    # Tampered signature
    tampered_sig = sig[:-4] + "ffff"
    assert not gateway.verify_payment_signature(order.order_id, payment_id, tampered_sig)

    # Tampered payment_id
    assert not gateway.verify_payment_signature(order.order_id, "pay_fake_999", sig)

