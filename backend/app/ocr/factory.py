from functools import lru_cache

from app.core.config import settings
from app.core.logging import logger
from app.ocr.interface import OCREngine
from app.ocr.null_engine import NullOCREngine


@lru_cache
def get_ocr_engine() -> OCREngine:
    if not settings.ocr_enabled:
        return NullOCREngine()

    if settings.ocr_engine == "tesseract":
        return _build_tesseract_engine()

    # EasyOCR / PaddleOCR engines are not implemented yet. Declaring the
    # interface now keeps the architecture stable; failing loudly here beats
    # silently doing nothing when someone flips OCR_ENABLED=true with an
    # unimplemented engine selected.
    raise NotImplementedError(
        f"OCR engine '{settings.ocr_engine}' is not implemented yet. "
        "Set OCR_ENGINE=tesseract or OCR_ENABLED=false."
    )


def _build_tesseract_engine() -> OCREngine:
    """Falls back to NullOCREngine (with a warning log) rather than crashing
    the app when the `tesseract-ocr` system binary isn't installed -- this
    can happen in a sandbox/CI environment without package-manager network
    access. Document upload still works either way; only automatic text
    extraction is skipped."""
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
    except Exception:  # noqa: BLE001 -- deliberately broad: any failure to
        # probe the tesseract binary (missing binary, missing pytesseract,
        # broken PATH, ...) should degrade gracefully, not crash startup.
        logger.warning(
            "OCR_ENGINE=tesseract but the tesseract-ocr binary/pytesseract "
            "could not be initialized; falling back to NullOCREngine. "
            "Document uploads will still work, just without automatic OCR. "
            "Install tesseract-ocr (apt-get install -y tesseract-ocr) to "
            "enable it."
        )
        return NullOCREngine()

    from app.ocr.tesseract_engine import TesseractOCREngine

    return TesseractOCREngine()
