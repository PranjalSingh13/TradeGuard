"""Rules-based and regex field extractor for shipping documents.

Extracts structured key-value entities from OCR text for all 4 document types.
"""
import re
from typing import Any
from tradeguard.core.constants import DocumentType


class RulesExtractor:
    """Extracts shipping entities and values using domain anchors and regular expressions."""

    def extract_fields(self, text: str, doc_type: DocumentType) -> dict[str, Any]:
        """Extract fields according to the identified document type."""
        extracted: dict[str, Any] = {}

        # 1. Container number: Look for anchored container number first, then ISO 6346 pattern
        anchored_cont = re.search(
            r"(?:container\s*no\.?|container\s*number|equipment\s*id)\s*[:\-]?\s*([A-Z0-9\s]{11,13})",
            text,
            re.IGNORECASE,
        )
        if anchored_cont:
            raw = anchored_cont.group(1).replace(" ", "").upper()
            m = re.match(r"([A-Z]{3}[UJZ]\d{7})", raw)
            if m:
                extracted["container_number"] = m.group(1)
        
        if "container_number" not in extracted:
            cont_match = re.search(r"\b([A-Z]{3}[UJZ]\s*\d{7})\b", text)
            if cont_match:
                extracted["container_number"] = cont_match.group(1).replace(" ", "").upper()

        # 2. Weights (Gross & Net)
        gross_match = re.search(
            r"(?:gross\s*weight|gross\s*wt\.?|g\.w\.?)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*(?:kg|kgs)?",
            text,
            re.IGNORECASE,
        )
        if gross_match:
            extracted["gross_weight_kg"] = float(gross_match.group(1).replace(",", ""))

        net_match = re.search(
            r"(?:net\s*weight|net\s*wt\.?|n\.w\.?)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*(?:kg|kgs)?",
            text,
            re.IGNORECASE,
        )
        if net_match:
            extracted["net_weight_kg"] = float(net_match.group(1).replace(",", ""))

        # 3. Package Count
        pkg_match = re.search(
            r"(?:packages?|pkgs?|cartons?|total\s*pkgs?)\s*[:\-]?\s*(\d+)",
            text,
            re.IGNORECASE,
        )
        if pkg_match:
            extracted["package_count"] = int(pkg_match.group(1))

        # 4. Dates
        date_match = re.search(
            r"\b(\d{4}-\d{2}-\d{2})\b",
            text,
        )
        if date_match:
            extracted["date"] = date_match.group(1)

        # 5. Ports of Loading and Discharge
        pol_match = re.search(
            r"(?:port\s*of\s*loading|loading\s*port|pol)\s*[:\-]?\s*([A-Za-z0-9\s,\-]+?)(?:\n|port\s*of|$)",
            text,
            re.IGNORECASE,
        )
        if pol_match:
            extracted["port_of_loading"] = pol_match.group(1).strip()

        pod_match = re.search(
            r"(?:port\s*of\s*discharge|discharge\s*port|pod)\s*[:\-]?\s*([A-Za-z0-9\s,\-]+?)(?:\n|vessel|$)",
            text,
            re.IGNORECASE,
        )
        if pod_match:
            extracted["port_of_discharge"] = pod_match.group(1).strip()

        # 6. Shipper and Consignee
        shipper_match = re.search(
            r"(?:shipper|exporter|seller)\s*[:\-]?\s*([A-Za-z0-9\s,\.&'\-]+?)(?:\n\s*consignee|\n\s*buyer|\n\s*notify|$)",
            text,
            re.IGNORECASE,
        )
        if shipper_match:
            extracted["shipper"] = shipper_match.group(1).strip()

        consignee_match = re.search(
            r"(?:consignee|buyer|importer)\s*[:\-]?\s*([A-Za-z0-9\s,\.&'\-]+?)(?:\n\s*notify|\n\s*port|\n\s*vessel|$)",
            text,
            re.IGNORECASE,
        )
        if consignee_match:
            extracted["consignee"] = consignee_match.group(1).strip()

        # Type-specific extraction
        if doc_type == DocumentType.BILL_OF_LADING:
            bol_num = re.search(
                r"(?:bill\s*of\s*lading\s*no\.?|b/?l\s*no\.?|document\s*no\.?)\s*[:\-]?\s*([A-Z0-9\-]+)",
                text,
                re.IGNORECASE,
            )
            if bol_num:
                extracted["document_number"] = bol_num.group(1).strip()
            shipped_date = re.search(
                r"(?:shipped\s*on\s*board|on\s*board\s*date)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})",
                text,
                re.IGNORECASE,
            )
            if shipped_date:
                extracted["shipped_on_board_date"] = shipped_date.group(1)

        elif doc_type == DocumentType.COMMERCIAL_INVOICE:
            inv_num = re.search(
                r"(?:invoice\s*no\.?|inv\s*#?)\s*[:\-]?\s*([A-Z0-9\-]+)",
                text,
                re.IGNORECASE,
            )
            if inv_num:
                extracted["document_number"] = inv_num.group(1).strip()
            amt_match = re.search(
                r"(?:total\s*amount|total\s*value|grand\s*total)\s*[:\-]?\s*(?:[A-Z]{3}|\$)?\s*([\d,]+(?:\.\d{2})?)",
                text,
                re.IGNORECASE,
            )
            if amt_match:
                extracted["total_amount"] = float(amt_match.group(1).replace(",", ""))
                extracted["currency"] = "USD"

        elif doc_type == DocumentType.PACKING_LIST:
            pl_num = re.search(
                r"(?:packing\s*list\s*no\.?|pl\s*#?)\s*[:\-]?\s*([A-Z0-9\-]+)",
                text,
                re.IGNORECASE,
            )
            if pl_num:
                extracted["document_number"] = pl_num.group(1).strip()

        elif doc_type == DocumentType.CERTIFICATE_OF_ORIGIN:
            coo_num = re.search(
                r"(?:certificate\s*no\.?|coo\s*#?)\s*[:\-]?\s*([A-Z0-9\-]+)",
                text,
                re.IGNORECASE,
            )
            if coo_num:
                extracted["document_number"] = coo_num.group(1).strip()
            hs_match = re.search(r"(?:hs\s*code|tariff\s*no\.?)\s*[:\-]?\s*(\d{4}(?:\.\d{2})?)", text, re.IGNORECASE)
            if hs_match:
                extracted["hs_code"] = hs_match.group(1)

        return extracted
