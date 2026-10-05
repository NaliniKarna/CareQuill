"""
Tesseract-backed OCR engine (`pytesseract` + Pillow driving the local
`tesseract` binary). This is the default OCR implementation when
OCR_ENABLED=true.

Sandbox/CI note: `pytesseract` requires the `tesseract-ocr` system package
to be installed (e.g. `apt-get install -y tesseract-ocr`). If that binary is
missing -- for example in a locked-down build environment with no package
network access -- `app.ocr.factory.get_ocr_engine` catches the failure,
logs a clear warning, and falls back to `NullOCREngine` rather than
crashing the app at import time. This mirrors this repo's existing pattern
of substituting a safe default when an external asset can't be fetched at
build time (see the frontend's shadcn/Google-Fonts fallback notes).
"""
import io

from PIL import Image

from app.ocr.interface import OCREngine, OCRResult

_SUPPORTED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg"}


class TesseractOCREngine(OCREngine):
    """Extracts text from a single image. PDF-specific handling (rendering
    pages to images when the PDF has no text layer) lives in
    `app.services.document_processing_service`, which calls this engine
    once per rendered page."""

    def __init__(self) -> None:
        # Imported lazily (and only once, here) so that importing this
        # module doesn't itself require the tesseract binary to be present
        # -- only *using* it does. The factory probes availability at
        # startup by calling `pytesseract.get_tesseract_version()`.
        import pytesseract

        self._pytesseract = pytesseract

    async def extract(self, *, file_bytes: bytes, mime_type: str) -> OCRResult:
        if mime_type not in _SUPPORTED_IMAGE_MIME_TYPES:
            return OCRResult(raw_text="", confidence=None, engine="tesseract")

        image = Image.open(io.BytesIO(file_bytes))
        try:
            raw_text = self._pytesseract.image_to_string(image)
            confidence = self._mean_confidence(image)
        finally:
            image.close()

        return OCRResult(raw_text=raw_text, confidence=confidence, engine="tesseract")

    def _mean_confidence(self, image: Image.Image) -> float | None:
        """Mean confidence of recognized words, scaled from Tesseract's 0-100
        range down to 0-1 to match the `document_extractions.confidence`
        column (NUMERIC(4,3))."""
        data = self._pytesseract.image_to_data(
            image, output_type=self._pytesseract.Output.DICT
        )
        scores = [
            int(conf)
            for conf, text in zip(data.get("conf", []), data.get("text", []), strict=False)
            if str(conf).lstrip("-").isdigit() and int(conf) >= 0 and text.strip()
        ]
        if not scores:
            return None
        return round((sum(scores) / len(scores)) / 100, 3)
