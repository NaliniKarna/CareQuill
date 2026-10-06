"""
OCR abstraction. OCR output is always an *extraction aid*: raw text plus a
confidence score, never treated as source of truth. Consumers (document
processing services) must route results through patient review before
anything becomes verified data.

OCR reads PRINTED TEXT. It cannot "read" a radiograph, MRI or CT slice - those
are pictures of anatomy, not text. For them `extract_annotations` only
recovers the small amount of burned-in text (side markers, dates, labels).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OCRResult:
    raw_text: str
    confidence: float | None
    engine: str


class OCREngine(ABC):
    # False for the no-op engine, so callers can tell "OCR is switched off"
    # from "OCR ran and found nothing".
    is_real: bool = True

    @abstractmethod
    async def extract(self, *, file_bytes: bytes, mime_type: str) -> OCRResult:
        ...

    async def extract_annotations(self, *, file_bytes: bytes, mime_type: str) -> OCRResult:
        """Best-effort read of burned-in text on a medical IMAGE (X-ray, MRI,
        CT). Defaults to plain `extract`; engines may specialise (light text
        on a dark background, etc.)."""
        return await self.extract(file_bytes=file_bytes, mime_type=mime_type)
