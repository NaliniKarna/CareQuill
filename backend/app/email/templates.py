"""
Email body templates. Kept separate from `health_report_service` so the
template text itself is easy to find and edit without wading through the
sharing pipeline's business logic.
"""
from __future__ import annotations

import html


def render_health_report_email(
    *,
    doctor_name: str,
    patient_name: str,
    appointment_date_display: str | None,
    document_titles: list[str],
) -> tuple[str, str]:
    """Returns (html_body, text_body) for the health-report share email.
    Deliberately minimal -- no patient DOB/address/phone here, that
    information belongs only in the attached PDF, never the email body."""
    if appointment_date_display:
        intro = (
            f"The patient {patient_name} has an upcoming appointment on "
            f"{appointment_date_display}."
        )
    else:
        intro = f"The patient {patient_name} has shared their health summary with you."

    attachments = ["MedQueue AI Health Summary", *document_titles]
    attachment_lines = "\n".join(f"- {title}" for title in attachments)

    text_body = (
        f"Hello Dr. {doctor_name},\n\n"
        f"{intro}\n"
        "They have shared their health summary with you in advance.\n\n"
        "Attached:\n"
        f"{attachment_lines}\n\n"
        "Please note that the attached summary is AI-assisted and based on "
        "information provided by the patient.\n\n"
        "Regards,\n"
        "MedQueue AI"
    )

    attachment_html = "".join(f"<li>{html.escape(title)}</li>" for title in attachments)
    html_body = (
        f"<p>Hello Dr. {html.escape(doctor_name)},</p>"
        f"<p>{html.escape(intro)}<br/>"
        "They have shared their health summary with you in advance.</p>"
        f"<p>Attached:</p><ul>{attachment_html}</ul>"
        "<p>Please note that the attached summary is AI-assisted and based on "
        "information provided by the patient.</p>"
        "<p>Regards,<br/>MedQueue AI</p>"
    )

    return html_body, text_body
