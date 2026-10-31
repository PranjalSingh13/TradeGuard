"""Synthetic Cargo Shipment and Discrepancy Generator.

Generates ground-truth shipment records with realistic maritime entities and injects controlled discrepancies.
"""
from dataclasses import dataclass, field
import datetime
import random
from typing import Any
from faker import Faker

from tradeguard.core.constants import DiscrepancyType
from tradeguard.validation.cross_doc import ShipmentExtractionBundle
from tradeguard.validation.iso6346 import generate_container_number


MAJOR_PORTS = [
    "INNSA - Nhava Sheva, India",
    "INMAA - Chennai, India",
    "SGSIN - Singapore",
    "CNSHA - Shanghai, China",
    "NLRTM - Rotterdam, Netherlands",
    "USNYC - New York, USA",
    "USLAX - Los Angeles, USA",
    "AEJEA - Jebel Ali, UAE",
    "DEHAM - Hamburg, Germany",
    "GRPIR - Piraeus, Greece",
]

CARGO_CATEGORIES = [
    {"name": "Organic Arabica Coffee Beans", "hs": "0901.11", "price_per_kg": 4.5},
    {"name": "Basmati Rice Grade A", "hs": "1006.30", "price_per_kg": 1.2},
    {"name": "Cotton Yarn 30s Combed", "hs": "5205.23", "price_per_kg": 3.8},
    {"name": "Industrial Ceramic Tiles", "hs": "6907.21", "price_per_kg": 0.9},
    {"name": "Stainless Steel Fasteners", "hs": "7318.15", "price_per_kg": 5.2},
    {"name": "Solar Photovoltaic Modules", "hs": "8541.43", "price_per_kg": 18.0},
    {"name": "Auto Components - Brake Discs", "hs": "8708.30", "price_per_kg": 8.5},
]


@dataclass
class SyntheticShipmentRecord:
    shipment_id: str
    is_risky: bool
    injected_discrepancies: list[str] = field(default_factory=list)
    bundle: ShipmentExtractionBundle = field(default_factory=ShipmentExtractionBundle)
    metadata: dict[str, Any] = field(default_factory=dict)


class SyntheticDataGenerator:
    """Generates synthetic cargo document data with controlled discrepancies."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.fake = Faker()
        Faker.seed(seed)

    def generate_single_shipment(
        self,
        shipment_idx: int,
        inject_risk: bool = False,
    ) -> SyntheticShipmentRecord:
        r = self.rng
        fake = self.fake

        # Base ground truth
        shipper = f"{fake.company()} {fake.company_suffix()}"
        consignee = f"{fake.company()} Logistics & Trade"
        pol = r.choice(MAJOR_PORTS)
        pod = r.choice([p for p in MAJOR_PORTS if p != pol])
        category = r.choice(CARGO_CATEGORIES)

        container_no = generate_container_number(rng=r)
        package_count = r.randint(150, 900)
        net_weight = package_count * r.uniform(20.0, 45.0)
        gross_weight = round(net_weight * r.uniform(1.05, 1.12), 2)
        net_weight = round(net_weight, 2)

        total_value = round(gross_weight * category["price_per_kg"] * r.uniform(0.95, 1.05), 2)

        base_date = datetime.date(2026, r.randint(1, 10), r.randint(1, 20))
        invoice_date = base_date
        shipped_date = invoice_date + datetime.timedelta(days=r.randint(1, 7))

        doc_ref = f"TG-2026-{shipment_idx:05d}"
        bol_num = f"MEDU{r.randint(1000000, 9999999)}"
        inv_num = f"INV-{r.randint(10000, 99999)}"
        pl_num = f"PL-{r.randint(10000, 99999)}"
        coo_num = f"COO-{r.randint(10000, 99999)}"

        # Prepare per-document data
        bol_data = {
            "document_number": bol_num,
            "shipper": shipper,
            "consignee": consignee,
            "port_of_loading": pol,
            "port_of_discharge": pod,
            "container_number": container_no,
            "package_count": package_count,
            "gross_weight_kg": gross_weight,
            "goods_description": category["name"],
            "shipped_on_board_date": shipped_date.isoformat(),
        }

        inv_data = {
            "document_number": inv_num,
            "date": invoice_date.isoformat(),
            "shipper": shipper,
            "consignee": consignee,
            "total_amount": total_value,
            "currency": "USD",
            "incoterm": "FOB",
            "goods_description": category["name"],
        }

        pl_data = {
            "document_number": pl_num,
            "date": invoice_date.isoformat(),
            "shipper": shipper,
            "consignee": consignee,
            "container_number": container_no,
            "package_count": package_count,
            "gross_weight_kg": gross_weight,
            "net_weight_kg": net_weight,
        }

        coo_data = {
            "document_number": coo_num,
            "shipper": shipper,
            "consignee": consignee,
            "port_of_loading": pol,
            "port_of_discharge": pod,
            "goods_description": category["name"],
            "hs_code": category["hs"],
        }

        injected_types = []

        # Discrepancy Injection
        if inject_risk:
            # Pick 1 or 2 discrepancies
            possible_discrepancies = [
                DiscrepancyType.WEIGHT_MISMATCH,
                DiscrepancyType.PACKAGE_COUNT_MISMATCH,
                DiscrepancyType.CONSIGNEE_NAME_ALTERED,
                DiscrepancyType.INVALID_CONTAINER_CHECK_DIGIT,
                DiscrepancyType.CONTAINER_MISMATCH,
                DiscrepancyType.PORT_MISMATCH,
                DiscrepancyType.DATE_ORDER_VIOLATION,
            ]
            k = r.choices([1, 2, 3], weights=[0.70, 0.25, 0.05])[0]
            chosen = r.sample(possible_discrepancies, k)

            for d in chosen:
                injected_types.append(d.value)
                if d == DiscrepancyType.WEIGHT_MISMATCH:
                    # Alter PL weight by 8% to 25%
                    factor = r.choice([0.85, 1.18, 0.75])
                    pl_data["gross_weight_kg"] = round(gross_weight * factor, 2)
                elif d == DiscrepancyType.PACKAGE_COUNT_MISMATCH:
                    # Alter PL package count
                    diff = r.choice([-35, 42, -18, 80])
                    pl_data["package_count"] = max(10, package_count + diff)
                elif d == DiscrepancyType.CONSIGNEE_NAME_ALTERED:
                    # Alter consignee name on PL
                    pl_data["consignee"] = f"Global {fake.last_name()} Imp/Exp Corp"
                elif d == DiscrepancyType.INVALID_CONTAINER_CHECK_DIGIT:
                    # Corrupt the last check digit of container_no
                    last_digit = int(container_no[-1])
                    bad_digit = (last_digit + r.randint(1, 9)) % 10
                    corrupt_container = container_no[:-1] + str(bad_digit)
                    bol_data["container_number"] = corrupt_container
                elif d == DiscrepancyType.CONTAINER_MISMATCH:
                    # Different container on packing list
                    pl_data["container_number"] = generate_container_number(rng=r)
                elif d == DiscrepancyType.PORT_MISMATCH:
                    # Alter POD on CoO
                    other_pod = r.choice([p for p in MAJOR_PORTS if p != pod and p != pol])
                    coo_data["port_of_discharge"] = other_pod
                elif d == DiscrepancyType.DATE_ORDER_VIOLATION:
                    # Invoice date after shipped date
                    bad_inv_date = shipped_date + datetime.timedelta(days=r.randint(5, 20))
                    inv_data["date"] = bad_inv_date.isoformat()

        # Simulated OCR and Classifier confidence scores
        if inject_risk and r.random() < 0.15:
            # Degraded OCR quality in some problematic docs
            ocr_confs = [r.uniform(0.62, 0.78) for _ in range(4)]
            cls_confs = [r.uniform(0.72, 0.85) for _ in range(4)]
        else:
            ocr_confs = [r.uniform(0.88, 0.99) for _ in range(4)]
            cls_confs = [r.uniform(0.92, 0.99) for _ in range(4)]

        bundle = ShipmentExtractionBundle(
            bill_of_lading=bol_data,
            commercial_invoice=inv_data,
            packing_list=pl_data,
            certificate_of_origin=coo_data,
            declared_amount_minor=int(total_value * 100),
            category=category["name"],
            ocr_mean_confs=ocr_confs,
            cls_confs=cls_confs,
        )

        return SyntheticShipmentRecord(
            shipment_id=doc_ref,
            is_risky=inject_risk,
            injected_discrepancies=injected_types,
            bundle=bundle,
            metadata={
                "category": category["name"],
                "pol": pol,
                "pod": pod,
                "declared_value_usd": total_value,
            },
        )

    def generate_dataset(
        self,
        total_count: int = 1000,
        risk_ratio: float = 0.12,
    ) -> list[SyntheticShipmentRecord]:
        """Generate a complete dataset of shipments with a specified fraction of injected discrepancies."""
        records: list[SyntheticShipmentRecord] = []
        for i in range(1, total_count + 1):
            is_risky = self.rng.random() < risk_ratio
            records.append(self.generate_single_shipment(i, inject_risk=is_risky))
        return records

