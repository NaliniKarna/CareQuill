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

    attachments = ["CareQuill Health Summary", *document_titles]
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
        "CareQuill"
    )

    attachment_html = "".join(f"<li>{html.escape(title)}</li>" for title in attachments)
    html_body = (
        f"<p>Hello Dr. {html.escape(doctor_name)},</p>"
        f"<p>{html.escape(intro)}<br/>"
        "They have shared their health summary with you in advance.</p>"
        f"<p>Attached:</p><ul>{attachment_html}</ul>"
        "<p>Please note that the attached summary is AI-assisted and based on "
        "information provided by the patient.</p>"
        "<p>Regards,<br/>CareQuill</p>"
    )

    return html_body, text_body


def render_family_share_email(
    *,
    recipient_name: str | None,
    member_name: str,
    sender_name: str,
    document_titles: list[str],
    message: str | None,
) -> tuple[str, str]:
    """Returns (html_body, text_body) for documents a patient shares on
    behalf of a family member. No dates of birth or contact details in the
    body; those belong only in the attached summary."""
    greeting = f"Hello {recipient_name}," if recipient_name else "Hello,"
    intro = f"{sender_name} is sharing health documents for {member_name} with you."
    attachments = ["CareQuill Health Summary", *document_titles]
    attachment_lines = "\n".join(f"- {title}" for title in attachments)
    note = f"Message from {sender_name}:\n{message}\n\n" if message else ""

    text_body = (
        f"{greeting}\n\n{intro}\n\n{note}Attached:\n{attachment_lines}\n\n"
        "The attached documents are the original files provided by the patient's family.\n\n"
        "Regards,\nCareQuill"
    )
    attachment_html = "".join(f"<li>{html.escape(title)}</li>" for title in attachments)
    note_html = (
        f"<p><strong>Message from {html.escape(sender_name)}:</strong><br/>"
        f"{html.escape(message)}</p>"
        if message
        else ""
    )
    html_body = (
        f"<p>{html.escape(greeting)}</p><p>{html.escape(intro)}</p>{note_html}"
        f"<p>Attached:</p><ul>{attachment_html}</ul>"
        "<p>The attached documents are the original files provided by the patient's "
        "family.</p><p>Regards,<br/>CareQuill</p>"
    )
    return html_body, text_body


def render_contact_email(*, name: str, email: str, message: str) -> tuple[str, str]:
    """Returns (html_body, text_body) for a Contact Us submission sent to the
    CareQuill team. Every user-supplied value is escaped."""
    text_body = (
        "New message from the CareQuill contact form\n\n"
        f"Name: {name}\nEmail: {email}\n\n{message}\n"
    )
    html_body = (
        "<p><strong>New message from the CareQuill contact form</strong></p>"
        f"<p>Name: {html.escape(name)}<br/>Email: {html.escape(email)}</p>"
        f"<p style='white-space:pre-wrap'>{html.escape(message)}</p>"
        "<p style='color:#666;font-size:12px'>Reply to this email to answer the sender.</p>"
    )
    return html_body, text_body
