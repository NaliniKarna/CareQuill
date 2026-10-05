"""No-op OCR engine used when OCR_ENABLED=false, so document upload still
works (files are stored, just not auto-extracted) without EasyOCR/PaddleOCR
installed."""
from app.ocr.interface import OCREngine, OCRResult


class NullOCREngine(OCREngine):
    async def extract(self, *, file_bytes: bytes, mime_type: str) -> OCRResult:
        return OCRResult(raw_text="", confidence=None, engine="none")
