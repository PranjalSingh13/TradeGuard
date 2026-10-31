"""Cross-document reconciliation and validation engine.

Checks consistency across Bill of Lading, Commercial Invoice, Packing List, and Certificate of Origin.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from rapidfuzz import fuzz

from tradeguard.core.constants import CheckSeverity
from tradeguard.validation.iso6346 import is_valid_container


@dataclass
class ValidationResult:
    check_name: str
    passed: bool
    severity: CheckSeverity
    detail: dict[str, Any] = field(default_factory=dict)
    is_hard_rule: bool = False


@dataclass
class ShipmentExtractionBundle:
    """Aggregated extractions across all uploaded documents for a shipment."""
    bill_of_lading: dict[str, Any] | None = None
    commercial_invoice: dict[str, Any] | None = None
    packing_list: dict[str, Any] | None = None
    certificate_of_origin: dict[str, Any] | None = None
    declared_amount_minor: int | None = None
    category: str | None = None
    ocr_mean_confs: list[float] = field(default_factory=list)
    cls_confs: list[float] = field(default_factory=list)


def run_cross_document_validation(bundle: ShipmentExtractionBundle) -> list[ValidationResult]:
    """Execute all deterministic domain and cross-document validation checks."""
    results: list[ValidationResult] = []

    bol = bundle.bill_of_lading or {}
    inv = bundle.commercial_invoice or {}
    pl = bundle.packing_list or {}
    coo = bundle.certificate_of_origin or {}

    # 1. ISO 6346 Container Number Check
    containers = []
    for doc in [bol, pl]:
        c = doc.get("container_number")
        if c:
            containers.append(c)
    
    if containers:
        invalid_containers = [c for c in containers if not is_valid_container(str(c))]
        if invalid_containers:
            results.append(
                ValidationResult(
                    check_name="iso6346_check_digit",
                    passed=False,
                    severity=CheckSeverity.HIGH,
                    detail={"invalid_containers": invalid_containers},
                    is_hard_rule=True,  # Check digit failure is a hard rule
                )
            )
        else:
            results.append(
                ValidationResult(
                    check_name="iso6346_check_digit",
                    passed=True,
                    severity=CheckSeverity.HIGH,
                    detail={"validated_containers": containers},
                    is_hard_rule=True,
                )
            )

    # 2. Container Consistency Across Documents
    bol_cont = bol.get("container_number")
    pl_cont = pl.get("container_number")
    if bol_cont and pl_cont:
        cont_match = (
            str(bol_cont).replace(" ", "").upper() == str(pl_cont).replace(" ", "").upper()
        )
        results.append(
            ValidationResult(
                check_name="container_cross_match",
                passed=cont_match,
                severity=CheckSeverity.HIGH,
                detail={"bol_container": bol_cont, "pl_container": pl_cont},
                is_hard_rule=True,  # Different container numbers on BoL vs PL is a hard rule
            )
        )

    # 3. Gross Weight Agreement (BoL vs Packing List)
    bol_weight = bol.get("gross_weight_kg")
    pl_weight = pl.get("gross_weight_kg")
    if bol_weight is not None and pl_weight is not None:
        try:
            bw = float(bol_weight)
            pw = float(pl_weight)
            max_w = max(bw, pw)
            diff_pct = abs(bw - pw) / max_w if max_w > 0 else 0.0
            # > 2% mismatch is flagged
            passed = diff_pct <= 0.02
            severity = CheckSeverity.HIGH if diff_pct > 0.05 else (
                CheckSeverity.MEDIUM if not passed else CheckSeverity.LOW
            )
            results.append(
                ValidationResult(
                    check_name="weight_agreement",
                    passed=passed,
                    severity=severity,
                    detail={"bol_weight_kg": bw, "pl_weight_kg": pw, "diff_pct": round(diff_pct * 100, 2)},
                )
            )
        except (ValueError, TypeError):
            pass

    # 4. Package Count Agreement (BoL vs Packing List)
    bol_pkg = bol.get("package_count")
    pl_pkg = pl.get("package_count")
    if bol_pkg is not None and pl_pkg is not None:
        try:
            bp = int(bol_pkg)
            pp = int(pl_pkg)
            diff_abs = abs(bp - pp)
            passed = diff_abs == 0
            severity = CheckSeverity.HIGH if diff_abs > 5 else (
                CheckSeverity.MEDIUM if not passed else CheckSeverity.LOW
            )
            results.append(
                ValidationResult(
                    check_name="package_count_agreement",
                    passed=passed,
                    severity=severity,
                    detail={"bol_package_count": bp, "pl_package_count": pp, "diff_abs": diff_abs},
                )
            )
        except (ValueError, TypeError):
            pass

    # 5. Consignee Name Similarity (BoL vs Invoice vs CoO)
    consignees = [d.get("consignee") for d in [bol, inv, coo] if d.get("consignee")]
    if len(consignees) >= 2:
        c1, c2 = consignees[0], consignees[1]
        sim_ratio = fuzz.token_sort_ratio(str(c1).lower(), str(c2).lower()) / 100.0
        passed = sim_ratio >= 0.85
        results.append(
            ValidationResult(
                check_name="consignee_similarity",
                passed=passed,
                severity=CheckSeverity.HIGH if sim_ratio < 0.60 else (
                    CheckSeverity.MEDIUM if not passed else CheckSeverity.LOW
                ),
                detail={"consignee_1": c1, "consignee_2": c2, "similarity": round(sim_ratio, 3)},
            )
        )

    # 6. Shipper Name Similarity (BoL vs Invoice vs CoO)
    shippers = [d.get("shipper") for d in [bol, inv, coo] if d.get("shipper")]
    if len(shippers) >= 2:
        s1, s2 = shippers[0], shippers[1]
        sim_ratio = fuzz.token_sort_ratio(str(s1).lower(), str(s2).lower()) / 100.0
        passed = sim_ratio >= 0.85
        results.append(
            ValidationResult(
                check_name="shipper_similarity",
                passed=passed,
                severity=CheckSeverity.HIGH if sim_ratio < 0.60 else (
                    CheckSeverity.MEDIUM if not passed else CheckSeverity.LOW
                ),
                detail={"shipper_1": s1, "shipper_2": s2, "similarity": round(sim_ratio, 3)},
            )
        )

    # 7. Ports of Loading and Discharge Agreement (BoL vs Invoice / CoO)
    bol_pol = bol.get("port_of_loading")
    bol_pod = bol.get("port_of_discharge")
    coo_pol = coo.get("port_of_loading")
    coo_pod = coo.get("port_of_discharge")
    if bol_pol and coo_pol:
        pol_match = fuzz.ratio(str(bol_pol).lower(), str(coo_pol).lower()) >= 80
        results.append(
            ValidationResult(
                check_name="port_of_loading_agreement",
                passed=pol_match,
                severity=CheckSeverity.MEDIUM,
                detail={"bol_pol": bol_pol, "coo_pol": coo_pol},
            )
        )
    if bol_pod and coo_pod:
        pod_match = fuzz.ratio(str(bol_pod).lower(), str(coo_pod).lower()) >= 80
        results.append(
            ValidationResult(
                check_name="port_of_discharge_agreement",
                passed=pod_match,
                severity=CheckSeverity.MEDIUM,
                detail={"bol_pod": bol_pod, "coo_pod": coo_pod},
            )
        )

    # 8. Date Sequence Check (Invoice Date <= Shipped on Board Date)
    inv_date_str = inv.get("date")
    bol_date_str = bol.get("shipped_on_board_date") or bol.get("date")
    if inv_date_str and bol_date_str:
        try:
            inv_d = date.fromisoformat(str(inv_date_str))
            bol_d = date.fromisoformat(str(bol_date_str))
            passed = inv_d <= bol_d
            gap_days = (bol_d - inv_d).days
            results.append(
                ValidationResult(
                    check_name="date_order_validity",
                    passed=passed,
                    severity=CheckSeverity.MEDIUM if not passed else CheckSeverity.LOW,
                    detail={"invoice_date": str(inv_d), "shipped_date": str(bol_d), "gap_days": gap_days},
                )
            )
        except (ValueError, TypeError):
            pass

    # 9. Required Fields Presence Check
    missing_fields = []
    required_bol = ["document_number", "shipper", "consignee", "port_of_loading", "port_of_discharge", "gross_weight_kg"]
    for req in required_bol:
        if not bol.get(req):
            missing_fields.append(f"bol.{req}")
    required_inv = ["document_number", "date", "total_amount", "currency"]
    for req in required_inv:
        if not inv.get(req):
            missing_fields.append(f"invoice.{req}")

    results.append(
        ValidationResult(
            check_name="required_fields_present",
            passed=len(missing_fields) == 0,
            severity=CheckSeverity.HIGH if len(missing_fields) > 2 else (
                CheckSeverity.MEDIUM if missing_fields else CheckSeverity.LOW
            ),
            detail={"missing_fields": missing_fields, "missing_count": len(missing_fields)},
        )
    )

    return results

