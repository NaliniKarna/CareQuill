from functools import lru_cache

from app.core.config import settings
from app.email.console_email import ConsoleEmailSender
from app.email.interface import EmailSender
from app.email.smtp_email import SMTPEmailSender


@lru_cache
def get_email_sender() -> EmailSender:
    if settings.email_backend == "smtp":
        return SMTPEmailSender()
    if settings.email_backend in ("sendgrid", "mailgun"):
        # Placeholder: swap in a provider-specific implementation behind the
        # same EmailSender interface when a checkpoint requires it.
        raise NotImplementedError(
            f"Email backend '{settings.email_backend}' is not implemented yet. "
            "Use EMAIL_BACKEND=smtp or EMAIL_BACKEND=console."
        )
    return ConsoleEmailSender()
