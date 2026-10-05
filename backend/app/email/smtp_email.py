"""SMTP email backend using Python's standard library, run in a worker
thread so it never blocks the async event loop."""
import asyncio
import logging
import smtplib
from email.message import EmailMessage as StdEmailMessage

from app.core.config import settings
from app.email.interface import EmailMessage, EmailSender, EmailSendResult

logger = logging.getLogger("medqueue.email")


class SMTPEmailSender(EmailSender):
    def _send_sync(self, message: EmailMessage) -> EmailSendResult:
        msg = StdEmailMessage()
        msg["Subject"] = message.subject
        msg["From"] = f"{settings.email_from_name} <{settings.email_from_address}>"
        msg["To"] = message.to
        msg.set_content(message.text_body or "This email requires an HTML-capable client.")
        msg.add_alternative(message.html_body, subtype="html")

        for filename, content, mime_type in message.attachments or []:
            maintype, _, subtype = mime_type.partition("/")
            msg.add_attachment(
                content, maintype=maintype or "application", subtype=subtype or "octet-stream",
                filename=filename,
            )

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
            return EmailSendResult(success=True)
        except Exception as exc:  # pragma: no cover - network dependent
            logger.error("smtp-email failed to=%s error=%s", message.to, str(exc))
            return EmailSendResult(success=False, error_message=str(exc))

    async def send(self, message: EmailMessage) -> EmailSendResult:
        return await asyncio.to_thread(self._send_sync, message)
