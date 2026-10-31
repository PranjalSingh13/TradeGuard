import numpy as np
import pytest

from tradeguard.core.constants import DecisionType
from tradeguard.ml.features import extract_features_vector
from tradeguard.ml.models.risk_model import RiskModel
from tradeguard.ml.synthetic.generator import SyntheticDataGenerator
from tradeguard.services.decision_engine import DecisionEngine
from tradeguard.validation.cross_doc import (
    ShipmentExtractionBundle,
    run_cross_document_validation,
)
from tradeguard.validation.iso6346 import (
    generate_container_number,
    is_valid_container,
)


def test_container_generator_generates_valid_iso6346():
    for _ in range(25):
        num = generate_container_number()
        assert len(num) == 11
        assert is_valid_container(num)


def test_clean_shipment_validation_passes():
    gen = SyntheticDataGenerator(seed=101)
    record = gen.generate_single_shipment(1, inject_risk=False)
    results = run_cross_document_validation(record.bundle)

    # In clean shipment, check digit and cross matching pass
    for r in results:
        if r.check_name in ("iso6346_check_digit", "container_cross_match"):
            assert r.passed


def test_discrepancy_injection_triggers_checks():
    gen = SyntheticDataGenerator(seed=202)
    record = gen.generate_single_shipment(1, inject_risk=True)
    results = run_cross_document_validation(record.bundle)

    # Should have at least one failed check
    failed = [r for r in results if not r.passed]
    assert len(failed) > 0


def test_decision_engine_auto_release_and_hold():
    engine = DecisionEngine(t_low=0.20, t_high=0.60, ocr_gate=0.70)

    # 1. Low risk + clean validation -> AUTO_RELEASE
    bundle = ShipmentExtractionBundle(
        bill_of_lading={"document_number": "B1", "shipper": "S1", "consignee": "C1", "port_of_loading": "P1", "port_of_discharge": "P2", "gross_weight_kg": 1000},
        commercial_invoice={"document_number": "I1", "date": "2026-05-01", "total_amount": 5000, "currency": "USD"},
    )
    clean_results = run_cross_document_validation(bundle)
    outcome_clean = engine.evaluate(risk_score=0.08, validation_results=clean_results)
    assert outcome_clean.decision == DecisionType.AUTO_RELEASE

    # 2. High score -> HOLD
    outcome_high = engine.evaluate(risk_score=0.85, validation_results=clean_results)
    assert outcome_high.decision == DecisionType.HOLD

    # 3. Low OCR confidence -> MANUAL_REVIEW
    outcome_ocr = engine.evaluate(risk_score=0.05, validation_results=clean_results, ocr_conf_min=0.55)
    assert outcome_ocr.decision == DecisionType.MANUAL_REVIEW


def test_end_to_end_ml_train_and_inference():
    gen = SyntheticDataGenerator(seed=42)
    records = gen.generate_dataset(total_count=120, risk_ratio=0.25)

    X_list = []
    y_list = []
    for rec in records:
        checks = run_cross_document_validation(rec.bundle)
        vec = extract_features_vector(rec.bundle, checks)
        X_list.append(vec)
        y_list.append(1 if rec.is_risky else 0)

    X = np.array(X_list)
    y = np.array(y_list)

    model = RiskModel()
    model.fit(X, y)
    assert model.is_fitted

    # Prediction
    sample_vec = X[0]
    score = model.predict_risk_score(sample_vec)
    assert 0.0 <= score <= 1.0

    explanations = model.explain(sample_vec, top_k=3)
    assert len(explanations) <= 3

