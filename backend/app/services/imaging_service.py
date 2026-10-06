"""
Handling of medical IMAGES (X-ray, MRI, CT slices).

What OCR can and cannot do
--------------------------
OCR turns pictures of *printed text* into text. An X-ray, MRI or CT slice is a
picture of anatomy, so there is no text to read in the part that matters. Run
through OCR such a file yields nothing, or garbage, and used to be reported as
"OCR: completed". This module is the honest path for those uploads:

 * The original image is stored untouched (as for every document) and the UI
   offers an in-app viewer.
 * Only the small burned-in annotations are read - side markers (L/R), dates,
   patient/hospital labels - as an aid for filing the record.
 * An OPTIONAL vision model may add purely descriptive metadata (what kind of
   image, which body region, image quality). It has no field for findings.
 * The app NEVER interprets the image, never looks for abnormalities and never
   offers a diagnosis. For the clinical content the patient should upload the
   radiologist's written report, which is text and goes through the normal
   OCR/extraction pipeline.
"""
from __future__ import annotations

import asyncio
import io
import re

from PIL import Image, ImageOps

from app.ai.document_prompts import build_image_description_prompt
from app.ai.document_schemas import ImageDescription
from app.ai.interface import AIProvider
from app.ai.json_utils import extract_json_object
from app.core.logging import logger
from app.ocr.interface import OCREngine
from app.services.entity_extraction_service import clean_text, empty_entities, extract_dates

IMAGING_CATEGORIES = frozenset({"xray", "mri", "ct_scan"})

IMAGING_NOTICE = (
    "This is a medical image (for example an X-ray, MRI or CT scan). MedQueue AI "
    "keeps it exactly as uploaded and does not interpret images or look for "
    "findings - OCR can only read printed text, not anatomy. To get the clinical "
    "content into your record, upload the radiologist's written report as well "
    "(its text can be read automatically), and share both with your doctor."
)

NO_TEXT_IMAGE_NOTICE = (
    "No readable text was found in this image. If it is a scan, X-ray or photo, "
    "it is stored unchanged and can be viewed or downloaded, but nothing could be "
    "extracted automatically."
)

_MARKER_RE = re.compile(r"\b(LEFT|RIGHT|L|R)\b")
_MAX_VISION_EDGE = 1024


def is_imaging_category(category: str | None) -> bool:
    return category in IMAGING_CATEGORIES


def _image_info(file_bytes: bytes) -> dict:
    with Image.open(io.BytesIO(file_bytes)) as image:
        return {"width": image.width, "height": image.height, "mode": image.mode}


async def read_image_info(file_bytes: bytes) -> dict | None:
    try:
        return await asyncio.to_thread(_image_info, file_bytes)
    except Exception:  # noqa: BLE001 - corrupt image: caller degrades gracefully
        logger.warning("Could not read image dimensions.", exc_info=True)
        return None


async def build_imaging_extraction(
    *, file_bytes: bytes, mime_type: str, ocr_engine: OCREngine
) -> tuple[str, float | None, dict]:
    """Phase 1 (always runs, no AI needed). Returns (annotation_text,
    confidence, extracted_data) with the same top-level entity keys the
    frontend already understands, plus an `imaging` block."""
    annotation_text = ""
    confidence: float | None = None
    if ocr_engine.is_real:
        result = await ocr_engine.extract_annotations(file_bytes=file_bytes, mime_type=mime_type)
        annotation_text = clean_text(result.raw_text)
        confidence = result.confidence

    info = await read_image_info(file_bytes)
    markers = sorted({m.group(1) for m in _MARKER_RE.finditer(annotation_text)})
    data = empty_entities()
    data["dates"] = extract_dates(annotation_text)
    data["document_kind"] = "medical_image"
    data["imaging"] = {
        "interpretation": "not_performed",
        "notice": IMAGING_NOTICE,
        "image_info": info,
        "annotations": {
            "text_lines": [line for line in annotation_text.splitlines() if line.strip()][:20],
            "side_markers_seen": markers,
        },
        "ai_description": None,
    }
    return annotation_text, confidence, data


def _downscale_for_vision(file_bytes: bytes) -> bytes:
    with Image.open(io.BytesIO(file_bytes)) as image:
        gray_or_rgb = image.convert("RGB")
        gray_or_rgb = ImageOps.exif_transpose(gray_or_rgb) or gray_or_rgb
        gray_or_rgb.thumbnail((_MAX_VISION_EDGE, _MAX_VISION_EDGE))
        out = io.BytesIO()
        gray_or_rgb.save(out, format="JPEG", quality=85)
        return out.getvalue()


async def describe_image_with_ai(
    *, provider: AIProvider, file_bytes: bytes, model_name: str
) -> dict | None:
    """Phase 2 (optional). Descriptive metadata only; returns None on any
    failure so it can never block or fail the document pipeline."""
    try:
        small = await asyncio.to_thread(_downscale_for_vision, file_bytes)
        raw = await provider.generate_json(
            prompt=build_image_description_prompt(), images=[small], use_vision_model=True
        )
        payload = extract_json_object(raw)
        if payload is None:
            return None
        description = ImageDescription.model_validate(payload)
    except Exception as exc:  # noqa: BLE001 - never block the pipeline
        logger.warning("Image description unavailable: %s", type(exc).__name__)
        return None
    return {**description.model_dump(), "model": model_name, "source": "ai"}
