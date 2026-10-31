"""Shipment Pipeline Orchestrator.

Coordinates OCR, document classification, field extraction, validation, ML risk scoring, and escrow release.
"""
from typing import Any
import numpy as np
from sqlalchemy.orm import Session

from tradeguard.core.constants import DecisionType, DocumentType, ShipmentStatus
from tradeguard.db.models import (
    AuditLog,
    Document,
    Extraction,
    Payment,
    ReviewCase,
    RiskAssessment,
    Shipment,
    ValidationCheck,
)
from tradeguard.extraction.rules_extractor import RulesExtractor
from tradeguard.ml.features import extract_features_dict, extract_features_vector
from tradeguard.ml.models.doc_classifier import DocumentClassifier
from tradeguard.ml.models.risk_model import RiskModel
from tradeguard.ocr.engine import OCREngine
from tradeguard.payments.ledger import LedgerService
from tradeguard.services.decision_engine import DecisionEngine, DecisionOutcome
from tradeguard.validation.cross_doc import (
    ShipmentExtractionBundle,
    run_cross_document_validation,
)


class ShipmentOrchestrator:
    """End-to-end execution pipeline for cargo shipments."""

    def __init__(
        self,
        db: Session,
        risk_model: RiskModel | None = None,
        doc_classifier: DocumentClassifier | None = None,
        decision_engine: DecisionEngine | None = None,
    ):
        self.db = db
        self.ocr_engine = OCREngine()
        self.doc_classifier = doc_classifier or DocumentClassifier()
        self.rules_extractor = RulesExtractor()
        self.risk_model = risk_model
        self.decision_engine = decision_engine or DecisionEngine()
        self.ledger_service = LedgerService(db)

    def process_shipment(self, shipment_id: str) -> DecisionOutcome:
        """Run full document intelligence and risk assessment pipeline for a shipment."""
        shipment = self.db.query(Shipment).filter(Shipment.id == shipment_id).first()
        if not shipment:
            raise ValueError(f"Shipment {shipment_id} not found")

        shipment.status = ShipmentStatus.PROCESSING.value
        self.db.commit()

        documents = self.db.query(Document).filter(Document.shipment_id == shipment_id).all()
        if not documents:
            raise ValueError(f"No documents uploaded for shipment {shipment_id}")

        bundle = ShipmentExtractionBundle(declared_amount_minor=shipment.declared_amount_minor)

        # 1. Process each document
        for doc in documents:
            doc.status = "processing"
            self.db.commit()

            # Read text from storage / fallback
            doc_text = doc.storage_key or ""
            # If doc_text is not raw text, simulate OCR extraction
            ocr_res = self.ocr_engine.extract_from_text(doc_text, doc_id=doc.id)
            doc.ocr_mean_conf = ocr_res.mean_confidence
            bundle.ocr_mean_confs.append(ocr_res.mean_confidence)

            # Classify document
            pred_type, cls_conf = self.doc_classifier.predict(ocr_res.full_text)
            doc.predicted_type = pred_type.value
            doc.type_confidence = cls_conf
            bundle.cls_confs.append(cls_conf)

            # Extract fields
            extracted_fields = self.rules_extractor.extract_fields(ocr_res.full_text, pred_type)

            # Save extraction
            extraction_record = Extraction(
                document_id=doc.id,
                fields=extracted_fields,
                field_confidences={"mean_conf": ocr_res.mean_confidence},
            )
            self.db.add(extraction_record)

            # Map into shipment bundle
            if pred_type == DocumentType.BILL_OF_LADING:
                bundle.bill_of_lading = extracted_fields
            elif pred_type == DocumentType.COMMERCIAL_INVOICE:
                bundle.commercial_invoice = extracted_fields
            elif pred_type == DocumentType.PACKING_LIST:
                bundle.packing_list = extracted_fields
            elif pred_type == DocumentType.CERTIFICATE_OF_ORIGIN:
                bundle.certificate_of_origin = extracted_fields

            doc.status = "done"
            self.db.commit()

        # 2. Cross-document validation checks
        validation_results = run_cross_document_validation(bundle)
        for val in validation_results:
            chk = ValidationCheck(
                shipment_id=shipment.id,
                check_name=val.check_name,
                passed=val.passed,
                severity=val.severity.value,
                detail=val.detail,
            )
            self.db.add(chk)
        self.db.commit()

        # 3. Feature building
        features_dict = extract_features_dict(bundle, validation_results)
        feature_vector = extract_features_vector(bundle, validation_results)

        # 4. ML Risk Scoring
        risk_score = 0.05
        top_reasons = []
        if self.risk_model and self.risk_model.is_fitted:
            risk_score = self.risk_model.predict_risk_score(feature_vector)
            top_reasons = self.risk_model.explain(feature_vector)
        else:
            # Deterministic heuristic risk approximation if ML weights are not pre-loaded
            failed_hard = any(v.is_hard_rule and not v.passed for v in validation_results)
            failed_count = sum(1 for v in validation_results if not v.passed)
            if failed_hard:
                risk_score = 0.85
            elif failed_count > 0:
                risk_score = 0.45
            else:
                risk_score = 0.05

        # 5. Tri-State Decision Engine
        min_ocr = min(bundle.ocr_mean_confs) if bundle.ocr_mean_confs else 1.0
        min_cls = min(bundle.cls_confs) if bundle.cls_confs else 1.0
        outcome = self.decision_engine.evaluate(
            risk_score=risk_score,
            validation_results=validation_results,
            ocr_conf_min=min_ocr,
            cls_conf_min=min_cls,
            top_features=top_reasons,
        )

        # Record assessment in database
        assessment = RiskAssessment(
            shipment_id=shipment.id,
            score=outcome.risk_score,
            decision=outcome.decision.value,
            features=features_dict,
            top_reasons=outcome.top_features,
            thresholds={
                "t_low": self.decision_engine.t_low,
                "t_high": self.decision_engine.t_high,
                "ocr_gate": self.decision_engine.ocr_gate,
            },
        )
        self.db.add(assessment)

        # 6. Act on decision & update state machine
        if outcome.decision == DecisionType.AUTO_RELEASE:
            shipment.status = ShipmentStatus.AUTO_RELEASE_APPROVED.value
            # Find associated held payment and auto-release
            payment = (
                self.db.query(Payment)
                .filter(Payment.shipment_id == shipment.id, Payment.status == "captured")
                .first()
            )
            if payment:
                self.ledger_service.record_release(
                    shipment_id=shipment.id,
                    payment_id=payment.id,
                    amount_minor=payment.amount_minor,
                    external_ref="AUTO_RELEASE_ZERO_RISK",
                )

        elif outcome.decision == DecisionType.MANUAL_REVIEW:
            shipment.status = ShipmentStatus.UNDER_REVIEW.value
            case = ReviewCase(
                shipment_id=shipment.id,
                status="open",
                reason="; ".join(outcome.reasons),
            )
            self.db.add(case)

        elif outcome.decision == DecisionType.HOLD:
            shipment.status = ShipmentStatus.HELD_FOR_RISK.value

        # Log audit entry
        audit = AuditLog(
            action="SHIPMENT_PROCESSED",
            entity="shipment",
            entity_id=shipment.id,
            metadata_json={
                "decision": outcome.decision.value,
                "risk_score": outcome.risk_score,
                "reasons": outcome.reasons,
            },
        )
        self.db.add(audit)
        self.db.commit()

        return outcome

