"""Feature extraction for the TradeGuard ML Risk Model.

Transforms extraction bundles and validation check outcomes into numeric feature vectors.
"""
from typing import Any
import numpy as np
from tradeguard.core.constants import CheckSeverity
from tradeguard.validation.cross_doc import ShipmentExtractionBundle, ValidationResult


FEATURE_NAMES = [
    "weight_diff_pct",
    "pkg_diff_abs",
    "pkg_diff_pct",
    "consignee_similarity",
    "shipper_similarity",
    "container_mismatch_flag",
    "container_checkdigit_valid",
    "port_mismatch_flag",
    "date_gap_days",
    "date_order_violation",
    "missing_required_count",
    "failed_checks_count",
    "high_severity_failed_count",
    "ocr_conf_mean",
    "ocr_conf_min",
    "cls_conf_min",
]


def extract_features_dict(
    bundle: ShipmentExtractionBundle,
    validation_results: list[ValidationResult],
) -> dict[str, float]:
    """Build a dictionary of tabular features from a shipment extraction bundle and check results."""
    feat: dict[str, float] = {k: 0.0 for k in FEATURE_NAMES}

    # Defaults
    feat["consignee_similarity"] = 1.0
    feat["shipper_similarity"] = 1.0
    feat["container_checkdigit_valid"] = 1.0
    feat["ocr_conf_mean"] = 0.95
    feat["ocr_conf_min"] = 0.95
    feat["cls_conf_min"] = 0.95

    # Process validation checks
    failed_count = 0
    high_sev_failed_count = 0

    for res in validation_results:
        if not res.passed:
            failed_count += 1
            if res.severity == CheckSeverity.HIGH:
                high_sev_failed_count += 1

        if res.check_name == "weight_agreement":
            diff = res.detail.get("diff_pct", 0.0)
            feat["weight_diff_pct"] = float(diff)
        elif res.check_name == "package_count_agreement":
            diff_abs = res.detail.get("diff_abs", 0)
            feat["pkg_diff_abs"] = float(diff_abs)
            bp = res.detail.get("bol_package_count", 1)
            feat["pkg_diff_pct"] = float(diff_abs / max(bp, 1))
        elif res.check_name == "consignee_similarity":
            feat["consignee_similarity"] = float(res.detail.get("similarity", 1.0))
        elif res.check_name == "shipper_similarity":
            feat["shipper_similarity"] = float(res.detail.get("similarity", 1.0))
        elif res.check_name == "container_cross_match":
            feat["container_mismatch_flag"] = 0.0 if res.passed else 1.0
        elif res.check_name == "iso6346_check_digit":
            feat["container_checkdigit_valid"] = 1.0 if res.passed else 0.0
        elif res.check_name in ("port_of_loading_agreement", "port_of_discharge_agreement"):
            if not res.passed:
                feat["port_mismatch_flag"] = 1.0
        elif res.check_name == "date_order_validity":
            feat["date_gap_days"] = float(res.detail.get("gap_days", 0.0))
            feat["date_order_violation"] = 0.0 if res.passed else 1.0
        elif res.check_name == "required_fields_present":
            feat["missing_required_count"] = float(res.detail.get("missing_count", 0))

    feat["failed_checks_count"] = float(failed_count)
    feat["high_severity_failed_count"] = float(high_sev_failed_count)

    # Process OCR & Classifier confidence
    if bundle.ocr_mean_confs:
        feat["ocr_conf_mean"] = float(np.mean(bundle.ocr_mean_confs))
        feat["ocr_conf_min"] = float(np.min(bundle.ocr_mean_confs))
    if bundle.cls_confs:
        feat["cls_conf_min"] = float(np.min(bundle.cls_confs))

    return feat


def extract_features_vector(
    bundle: ShipmentExtractionBundle,
    validation_results: list[ValidationResult],
) -> np.ndarray:
    """Return a 1D numpy array matching FEATURE_NAMES order."""
    feat_dict = extract_features_dict(bundle, validation_results)
    return np.array([feat_dict[k] for k in FEATURE_NAMES], dtype=np.float32)

