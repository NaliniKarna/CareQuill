"""
PDF generation abstraction. Services depend only on `PDFReportGenerator`,
never on ReportLab directly, so the rendering library can be swapped
without touching `app.services.health_report_service` (see
`app.pdf.factory`).

`structured_data` contract (built by `HealthReportService`, consumed by the
generator implementation) -- a plain dict so the interface stays decoupled
from any specific domain model:

    {
        "patient_info": {"name": str, "date_of_birth": str | None,
                          "gender": str | None, "blood_group": str | None},
        "report_date": str (ISO date),
        "appointment": {"date": str, "time": str | None, "reason": str | None,
                         "doctor_name": str | None} | None,
        "conditions": [{"name", "status", "diagnosed_date"}] | None,
        "allergies": [{"name", "severity", "reaction"}] | None,
        "medications": [{"name", "dosage", "frequency", "instructions"}] | None,
        "timeline": [{"date", "type", "title", "detail"}] | None,
        "documents": [{"title", "category"}] | None,
        "ai_summary_text": str | None,
        "patient_notes_text": str | None,
    }

Every key that would correspond to a section the patient did not select is
omitted or None -- the generator must render only what it is given. Never
put an internal database UUID anywhere in the rendered PDF; only
human-readable labels and dates.
"""
from abc import ABC, abstractmethod


class PDFReportGenerator(ABC):
    @abstractmethod
    async def generate_health_summary_pdf(self, *, structured_data: dict) -> bytes:
        ...
