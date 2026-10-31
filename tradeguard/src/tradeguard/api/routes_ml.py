"""Stateless ML classification and extraction endpoints."""
from fastapi import APIRouter, HTTPException
from tradeguard.api.schemas import ClassifyRequest, ClassifyResponse, ExtractRequest, ExtractResponse
from tradeguard.core.constants import DocumentType
from tradeguard.extraction.rules_extractor import RulesExtractor
from tradeguard.ml.models.doc_classifier import DocumentClassifier

router = APIRouter(prefix="/ml", tags=["ml"])
classifier = DocumentClassifier()
extractor = RulesExtractor()


@router.post("/classify", response_model=ClassifyResponse)
def classify_document(req: ClassifyRequest):
    doc_type, confidence = classifier.predict(req.text)
    return ClassifyResponse(predicted_type=doc_type.value, confidence=confidence)


@router.post("/extract", response_model=ExtractResponse)
def extract_document_fields(req: ExtractRequest):
    try:
        dtype = DocumentType(req.document_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type '{req.document_type}'. Expected one of: {[e.value for e in DocumentType]}",
        )

    fields = extractor.extract_fields(req.text, dtype)
    return ExtractResponse(document_type=dtype.value, fields=fields)

