"""Development-only email backend: logs the message instead of sending it.
Handy for local dev without an SMTP server, and used by the test suite."""
import logging

from app.email.interface import EmailMessage, EmailSender, EmailSendResult

logger = logging.getLogger("medqueue.email")


class ConsoleEmailSender(EmailSender):
    async def send(self, message: EmailMessage) -> EmailSendResult:
        logger.info(
            "console-email | to=%s subject=%s body_len=%d",
            message.to,
            message.subject,
            len(message.html_body),
        )
        return EmailSendResult(success=True, provider_message_id="console-local")
