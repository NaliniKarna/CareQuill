from functools import lru_cache

from app.core.config import settings
from app.email.console_email import ConsoleEmailSender
from app.email.http_providers import MailgunEmailSender, SendGridEmailSender
from app.email.interface import EmailSender
from app.email.smtp_email import SMTPEmailSender


@lru_cache
def get_email_sender() -> EmailSender:
    if settings.email_backend == "smtp":
        return SMTPEmailSender()
    if settings.email_backend == "sendgrid":
        return SendGridEmailSender()
    if settings.email_backend == "mailgun":
        return MailgunEmailSender()
    return ConsoleEmailSender()
