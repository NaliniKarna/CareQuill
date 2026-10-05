"""
ReportLab-backed implementation of `PDFReportGenerator`. Produces a clean,
single-column PDF: patient info header, report date, appointment info (if
selected), then whichever sections the caller included.

Rendering is synchronous (ReportLab has no async API) but wrapped in
`asyncio.to_thread` so it never blocks the event loop, the same pattern
`SMTPEmailSender` uses for its blocking `smtplib` call.

Security note: every value rendered here comes from `structured_data`,
which `HealthReportService` builds using only human-readable fields (names,
dates, free text) -- never a raw database UUID. `html.escape` is applied to
every piece of patient-provided free text before it reaches a
ReportLab `Paragraph` (which interprets a minimal HTML-like markup), so a
condition/medication/note name containing `<`, `&`, etc. can't corrupt the
document layout.
"""
from __future__ import annotations

import asyncio
import html
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.pdf.interface import PDFReportGenerator

AI_SUMMARY_DISCLAIMER = (
    "AI-assisted summary generated from information provided by the patient "
    "and selected medical records. This summary is not a medical diagnosis "
    "or prescription."
)


def _esc(value: object | None) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


class ReportLabPDFGenerator(PDFReportGenerator):
    async def generate_health_summary_pdf(self, *, structured_data: dict) -> bytes:
        return await asyncio.to_thread(self._render, structured_data)

    def _render(self, data: dict) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=LETTER,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            title="Health Summary Report",
        )
        styles = _build_styles()
        story: list = []

        story.append(Paragraph("Health Summary Report", styles["Title"]))
        story.append(Paragraph(f"Report date: {_esc(data.get('report_date'))}", styles["Meta"]))
        story.append(Spacer(1, 0.15 * inch))

        story.extend(_patient_info_section(data.get("patient_info") or {}, styles))

        appointment = data.get("appointment")
        if appointment:
            story.extend(_appointment_section(appointment, styles))

        conditions = data.get("conditions")
        if conditions:
            story.extend(_simple_table_section(
                "Medical Conditions", styles,
                header=["Condition", "Status", "Diagnosed"],
                rows=[
                    [c.get("name"), c.get("status"), c.get("diagnosed_date")]
                    for c in conditions
                ],
            ))

        allergies = data.get("allergies")
        if allergies:
            story.extend(_simple_table_section(
                "Allergies", styles,
                header=["Allergy", "Severity", "Reaction"],
                rows=[
                    [a.get("name"), a.get("severity"), a.get("reaction")]
                    for a in allergies
                ],
            ))

        medications = data.get("medications")
        if medications:
            story.extend(_simple_table_section(
                "Medications", styles,
                header=["Medication", "Dosage", "Frequency", "Instructions"],
                rows=[
                    [m.get("name"), m.get("dosage"), m.get("frequency"), m.get("instructions")]
                    for m in medications
                ],
            ))

        timeline = data.get("timeline")
        if timeline:
            story.extend(_simple_table_section(
                "Timeline Excerpt", styles,
                header=["Date", "Type", "Title", "Detail"],
                rows=[
                    [t.get("date"), t.get("type"), t.get("title"), t.get("detail")]
                    for t in timeline
                ],
            ))

        documents = data.get("documents")
        if documents:
            story.extend(_simple_table_section(
                "Supporting Documents", styles,
                header=["Title", "Category"],
                rows=[[d.get("title"), d.get("category")] for d in documents],
            ))

        ai_summary_text = data.get("ai_summary_text")
        if ai_summary_text:
            story.extend(_ai_summary_section(ai_summary_text, styles))

        patient_notes_text = data.get("patient_notes_text")
        if patient_notes_text:
            story.append(Paragraph("Patient Notes", styles["SectionHeading"]))
            story.append(Paragraph(_esc(patient_notes_text).replace("\n", "<br/>"), styles["Body"]))
            story.append(Spacer(1, 0.15 * inch))

        doc.build(story)
        return buffer.getvalue()


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="Meta", parent=styles["Normal"], textColor=colors.HexColor("#555555"), fontSize=9,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6,
        textColor=colors.HexColor("#1a3d5c"),
    ))
    styles.add(ParagraphStyle(
        name="Body", parent=styles["Normal"], fontSize=10, leading=14,
    ))
    styles.add(ParagraphStyle(
        name="Disclaimer", parent=styles["Normal"], fontSize=8, leading=11,
        textColor=colors.HexColor("#666666"), spaceBefore=6,
    ))
    return styles


def _patient_info_section(patient_info: dict, styles) -> list:
    lines = [f"<b>Patient:</b> {_esc(patient_info.get('name') or 'Unknown')}"]
    if patient_info.get("date_of_birth"):
        lines.append(f"<b>Date of birth:</b> {_esc(patient_info['date_of_birth'])}")
    if patient_info.get("gender"):
        lines.append(f"<b>Gender:</b> {_esc(patient_info['gender'])}")
    if patient_info.get("blood_group"):
        lines.append(f"<b>Blood group:</b> {_esc(patient_info['blood_group'])}")
    return [
        Paragraph("<br/>".join(lines), styles["Body"]),
        Spacer(1, 0.2 * inch),
    ]


def _appointment_section(appointment: dict, styles) -> list:
    lines = [f"<b>Date:</b> {_esc(appointment.get('date'))}"]
    if appointment.get("time"):
        lines.append(f"<b>Time:</b> {_esc(appointment['time'])}")
    if appointment.get("doctor_name"):
        lines.append(f"<b>Doctor:</b> {_esc(appointment['doctor_name'])}")
    if appointment.get("reason"):
        lines.append(f"<b>Reason:</b> {_esc(appointment['reason'])}")
    return [
        Paragraph("Appointment", styles["SectionHeading"]),
        Paragraph("<br/>".join(lines), styles["Body"]),
        Spacer(1, 0.1 * inch),
    ]


def _simple_table_section(title: str, styles, *, header: list[str], rows: list[list]) -> list:
    table_data = [[Paragraph(f"<b>{_esc(h)}</b>", styles["Body"]) for h in header]]
    for row in rows:
        table_data.append([Paragraph(_esc(cell) or "—", styles["Body"]) for cell in row])

    table = Table(table_data, hAlign="LEFT", repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3f7")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [
        Paragraph(title, styles["SectionHeading"]),
        table,
        Spacer(1, 0.15 * inch),
    ]


def _ai_summary_section(summary_text: str, styles) -> list:
    return [
        Paragraph("AI-Assisted Summary", styles["SectionHeading"]),
        Paragraph(_esc(summary_text).replace("\n", "<br/>"), styles["Body"]),
        Paragraph(_esc(AI_SUMMARY_DISCLAIMER), styles["Disclaimer"]),
        Spacer(1, 0.15 * inch),
    ]
