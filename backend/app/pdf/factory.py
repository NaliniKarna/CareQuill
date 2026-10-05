from functools import lru_cache

from app.pdf.interface import PDFReportGenerator
from app.pdf.reportlab_generator import ReportLabPDFGenerator


@lru_cache
def get_pdf_generator() -> PDFReportGenerator:
    """Only one implementation exists so far, but kept behind a factory for
    consistency with app.ai/app.ocr/app.email/app.storage -- a future
    implementation (e.g. a different rendering engine) can be swapped in
    via configuration without touching `HealthReportService`."""
    return ReportLabPDFGenerator()
