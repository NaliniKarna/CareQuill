"""
Tesseract-backed OCR engine (`pytesseract` + Pillow driving the local
`tesseract` binary). This is the default OCR implementation when
OCR_ENABLED=true.

Everything CPU-heavy (image decoding, preprocessing, Tesseract itself) runs
in a worker thread via `asyncio.to_thread`. Calling it inline from an
`async def` would freeze the whole API for the seconds a scan takes to OCR.

Sandbox/CI note: `pytesseract` requires the `tesseract-ocr` system package.
If that binary is missing, `app.ocr.factory.get_ocr_engine` logs a clear
warning and falls back to `NullOCREngine` instead of crashing.
"""
from __future__ import annotations

import asyncio
import io

from PIL import Image, ImageOps

from app.core.config import settings
from app.ocr.interface import OCREngine, OCRResult

_SUPPORTED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg"}
# Tesseract is most accurate when characters are roughly 30-40 px tall;
# phone photos are fine, small screenshots/thumbnails need enlarging.
_MIN_OCR_WIDTH = 1500
_MAX_OCR_WIDTH = 4000
_MAX_IMAGE_PIXELS = 60_000_000  # decompression-bomb guard


class TesseractOCREngine(OCREngine):
    """Extracts text from a single image. PDF-specific handling (rendering
    pages to images when the PDF has no text layer) lives in
    `app.services.document_processing_service`, which calls this engine
    once per rendered page."""

    def __init__(self) -> None:
        # Imported lazily so importing this module doesn't itself require
        # the tesseract binary -- only *using* it does.
        import pytesseract

        self._pytesseract = pytesseract

    # -- public API -------------------------------------------------------
    async def extract(self, *, file_bytes: bytes, mime_type: str) -> OCRResult:
        if mime_type not in _SUPPORTED_IMAGE_MIME_TYPES:
            return OCRResult(raw_text="", confidence=None, engine="tesseract")
        return await asyncio.to_thread(self._extract_sync, file_bytes, False)

    async def extract_annotations(self, *, file_bytes: bytes, mime_type: str) -> OCRResult:
        if mime_type not in _SUPPORTED_IMAGE_MIME_TYPES:
            return OCRResult(raw_text="", confidence=None, engine="tesseract")
        return await asyncio.to_thread(self._extract_sync, file_bytes, True)

    # -- internals (blocking; always called via to_thread) ------------------
    def _load(self, file_bytes: bytes) -> Image.Image:
        Image.MAX_IMAGE_PIXELS = _MAX_IMAGE_PIXELS
        opened = Image.open(io.BytesIO(file_bytes))
        opened.load()
        # Respect phone-camera rotation so text isn't read sideways.
        image: Image.Image = ImageOps.exif_transpose(opened) or opened
        return image

    @staticmethod
    def _preprocess(image: Image.Image, *, invert: bool = False) -> Image.Image:
        """Grayscale -> upscale small images -> stretch contrast. Cheap steps
        that measurably improve Tesseract on photos and low-res scans, and
        that never change the stored original."""
        gray = ImageOps.grayscale(image)
        width, height = gray.size
        if width < _MIN_OCR_WIDTH:
            scale = _MIN_OCR_WIDTH / width
            gray = gray.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
        elif width > _MAX_OCR_WIDTH:
            scale = _MAX_OCR_WIDTH / width
            gray = gray.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
        gray = ImageOps.autocontrast(gray, cutoff=1)
        return ImageOps.invert(gray) if invert else gray

    def _run(self, image: Image.Image) -> tuple[str, float | None]:
        timeout = settings.ocr_timeout_seconds
        data = self._pytesseract.image_to_data(
            image,
            lang=settings.ocr_languages,
            output_type=self._pytesseract.Output.DICT,
            timeout=timeout,
        )
        words: list[str] = []
        scores: list[int] = []
        last_line_key: tuple[int, int, int] | None = None
        line_words: list[str] = []
        lines: list[str] = []
        for i, text in enumerate(data.get("text", [])):
            conf_raw = str(data["conf"][i])
            if not text.strip() or not conf_raw.lstrip("-").isdigit() or int(conf_raw) < 0:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            if last_line_key is not None and key != last_line_key and line_words:
                lines.append(" ".join(line_words))
                line_words = []
            last_line_key = key
            line_words.append(text.strip())
            words.append(text.strip())
            scores.append(int(conf_raw))
        if line_words:
            lines.append(" ".join(line_words))
        confidence = round(sum(scores) / len(scores) / 100, 3) if scores else None
        return "\n".join(lines), confidence

    def _extract_sync(self, file_bytes: bytes, annotations_mode: bool) -> OCRResult:
        image = self._load(file_bytes)
        try:
            text, confidence = self._run(self._preprocess(image))
            if annotations_mode:
                # X-ray/CT annotations are typically LIGHT text on a DARK
                # field; Tesseract expects dark-on-light, so also try the
                # inverted image and keep whichever read more words.
                inv_text, inv_conf = self._run(self._preprocess(image, invert=True))
                if len(inv_text.split()) > len(text.split()):
                    text, confidence = inv_text, inv_conf
        finally:
            image.close()
        return OCRResult(raw_text=text, confidence=confidence, engine="tesseract")
