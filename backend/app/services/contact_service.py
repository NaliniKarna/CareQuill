"""Public Contact Us form: forwards a visitor's message to the CareQuill team
by email. Nothing is stored in the database, and the message body is never
logged (visitors sometimes paste personal details despite the warning)."""
from __future__ import annotations

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import logger
from app.email.factory import get_email_sender
from app.email.interface import EmailMessage
from app.email.templates import render_contact_email
from app.schemas.contact import ContactRequest


class ContactDeliveryError(AppError):
    status_code = 502
    code = "contact_delivery_failed"


def _single_line(value: str) -> str:
    """Strips line breaks so a name can never inject extra email headers."""
    return " ".join(value.split())


class ContactService:
    async def submit(self, data: ContactRequest) -> None:
        if data.website:
            # Bot trap: pretend it worked, send nothing.
            logger.info("Contact form honeypot triggered; message dropped.")
            return

        name = _single_line(data.name)
        html_body, text_body = render_contact_email(
            name=name, email=str(data.email), message=data.message
        )
        result = await get_email_sender().send(
            EmailMessage(
                to=settings.contact_receiver_email,
                subject=f"CareQuill contact form: {name}"[:150],
                html_body=html_body,
                text_body=text_body,
                reply_to=str(data.email),
            )
        )
        if not result.success:
            logger.error("Contact form email could not be delivered.")
            raise ContactDeliveryError(
                "We couldn't send your message right now. Please email us directly instead."
            )
