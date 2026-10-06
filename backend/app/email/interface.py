"""
Email abstraction. Services depend only on `EmailSender`, never on smtplib
or a specific provider's SDK, so SMTP can be swapped for SendGrid/Mailgun
via configuration alone (see `app.email.factory`).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmailMessage:
    to: str
    subject: str
    html_body: str
    text_body: str | None = None
    attachments: list[tuple[str, bytes, str]] | None = None
    # attachments: list of (filename, content, mime_type)
    # Replies go here instead of the system sender (e.g. the patient who
    # shared a report). The visible From stays the configured sender.
    reply_to: str | None = None


@dataclass
class EmailSendResult:
    success: bool
    provider_message_id: str | None = None
    error_message: str | None = None


class EmailSender(ABC):
    @abstractmethod
    async def send(self, message: EmailMessage) -> EmailSendResult:
        ...
