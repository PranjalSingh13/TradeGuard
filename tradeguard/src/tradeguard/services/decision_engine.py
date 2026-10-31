"""TradeGuard Decision Engine.

Combines ML risk probability, deterministic validation rules, and confidence gates into tri-state escrow decisions.
"""
from dataclasses import dataclass, field
from typing import Any

from tradeguard.core.config import settings
from tradeguard.core.constants import CheckSeverity, DecisionType
from tradeguard.validation.cross_doc import ValidationResult


@dataclass
class DecisionOutcome:
    decision: DecisionType
    risk_score: float
    reasons: list[str]
    top_features: list[dict[str, Any]] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    hard_rule_triggered: bool = False
    confidence_gate_failed: bool = False


class DecisionEngine:
    """Evaluates risk score, hard-rules, and quality gates to govern escrow release."""

    def __init__(
        self,
        t_low: float = settings.RISK_THRESHOLD_LOW,
        t_high: float = settings.RISK_THRESHOLD_HIGH,
        ocr_gate: float = settings.OCR_CONFIDENCE_GATE,
        cls_gate: float = settings.CLASSIFIER_CONFIDENCE_GATE,
    ):
        self.t_low = t_low
        self.t_high = t_high
        self.ocr_gate = ocr_gate
        self.cls_gate = cls_gate

    def evaluate(
        self,
        risk_score: float,
        validation_results: list[ValidationResult],
        ocr_conf_min: float = 1.0,
        cls_conf_min: float = 1.0,
        pipeline_error: bool = False,
        top_features: list[dict[str, Any]] | None = None,
    ) -> DecisionOutcome:
        """Apply deterministic gates and score thresholds."""
        reasons = []
        failed_checks = []
        hard_rule_failed = False
        conf_gate_failed = False

        # 1. Pipeline or OCR/Classifier confidence gate checks
        if pipeline_error:
            return DecisionOutcome(
                decision=DecisionType.MANUAL_REVIEW,
                risk_score=risk_score,
                reasons=["Pipeline execution failure occurred during processing"],
                confidence_gate_failed=True,
            )

        if ocr_conf_min < self.ocr_gate:
            conf_gate_failed = True
            reasons.append(
                f"Minimum OCR confidence {ocr_conf_min:.2f} is below gate {self.ocr_gate:.2f}"
            )

        if cls_conf_min < self.cls_gate:
            conf_gate_failed = True
            reasons.append(
                f"Document classification confidence {cls_conf_min:.2f} is below gate {self.cls_gate:.2f}"
            )

        # 2. Check hard rules and validation checks
        for check in validation_results:
            if not check.passed:
                failed_checks.append(check.check_name)
                if check.is_hard_rule and check.severity == CheckSeverity.HIGH:
                    hard_rule_failed = True
                    reasons.append(
                        f"Hard rule violation: {check.check_name} failed ({check.detail})"
                    )

        # 3. Decision Logic
        if conf_gate_failed:
            decision = DecisionType.MANUAL_REVIEW
        elif hard_rule_failed:
            decision = DecisionType.HOLD
            reasons.append("High-severity deterministic check failed: immediate hold")
        elif risk_score >= self.t_high:
            decision = DecisionType.HOLD
            reasons.append(
                f"ML Risk score ({risk_score:.2f}) exceeds high risk threshold ({self.t_high:.2f})"
            )
        elif risk_score >= self.t_low:
            decision = DecisionType.MANUAL_REVIEW
            reasons.append(
                f"Borderline risk score ({risk_score:.2f}) between {self.t_low:.2f} and {self.t_high:.2f}"
            )
        else:
            decision = DecisionType.AUTO_RELEASE
            reasons.append(
                f"Shipment passed all hard rules and risk score ({risk_score:.2f}) is below threshold ({self.t_low:.2f})"
            )

        return DecisionOutcome(
            decision=decision,
            risk_score=round(risk_score, 4),
            reasons=reasons,
            top_features=top_features or [],
            failed_checks=failed_checks,
            hard_rule_triggered=hard_rule_failed,
            confidence_gate_failed=conf_gate_failed,
        )

