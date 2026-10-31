"""Image preprocessing for shipping document OCR.

Applies deskewing, grayscale conversion, Otsu binarization, and denoising.
"""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image


def load_image(image_input: str | Path | bytes | np.ndarray) -> np.ndarray:
    """Load image from path, raw bytes, or existing numpy array into BGR format."""
    if isinstance(image_input, (str, Path)):
        img = cv2.imread(str(image_input))
        if img is None:
            raise ValueError(f"Could not read image from {image_input}")
        return img
    elif isinstance(image_input, bytes):
        nparr = np.frombuffer(image_input, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image from bytes")
        return img
    elif isinstance(image_input, np.ndarray):
        return image_input
    raise TypeError(f"Unsupported image input type: {type(image_input)}")


def deskew_image(image: np.ndarray) -> np.ndarray:
    """Detect text orientation angle and deskew image."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    # Invert and threshold to find text contours
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 50:
        return image  # Insufficient text pixels to estimate skew

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    elif angle > 45:
        angle = 90 - angle
    else:
        angle = -angle

    # Only deskew if skew is modest (e.g. between 0.5 and 20 degrees)
    if abs(angle) < 0.5 or abs(angle) > 25.0:
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


def preprocess_for_ocr(image_input: str | Path | bytes | np.ndarray) -> np.ndarray:
    """Full preprocessing pipeline: deskew, grayscale, median blur, and binarization."""
    img = load_image(image_input)
    deskewed = deskew_image(img)
    gray = cv2.cvtColor(deskewed, cv2.COLOR_BGR2GRAY) if len(deskewed.shape) == 3 else deskewed
    denoised = cv2.medianBlur(gray, 3)
    binarized = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
    )
    return binarized

