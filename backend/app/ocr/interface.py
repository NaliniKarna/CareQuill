"""
OCR abstraction. OCR output is always an *extraction aid*: raw text plus a
confidence score, never treated as source of truth. Consumers (document
processing services, a later checkpoint) must route results through patient
review before anything becomes verified data.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OCRResult:
    raw_text: str
    confidence: float | None
    engine: str


class OCREngine(ABC):
    @abstractmethod
    async def extract(self, *, file_bytes: bytes, mime_type: str) -> OCRResult:
        ...
