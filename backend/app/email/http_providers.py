"""
HTTP-API email senders (SendGrid, Mailgun) behind the same `EmailSender`
interface as SMTP/console. They use `httpx` (already a dependency) rather
than vendor SDKs so there is nothing extra to install.

Both providers report failure through `EmailSendResult(success=False)`
instead of raising, matching the SMTP sender: a mail outage must be
recorded in the email log (so the patient sees "failed" and can retry), not
crash the request. Error text is logged WITHOUT the message body - these
emails can contain patient health summaries.
"""
from __future__ import annotations

import base64

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.email.interface import EmailMessage, EmailSender, EmailSendResult

_TIMEOUT = 20.0


class SendGridEmailSender(EmailSender):
    API_URL = "https://api.sendgrid.com/v3/mail/send"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not settings.sendgrid_api_key:
            raise ValueError("EMAIL_BACKEND=sendgrid requires SENDGRID_API_KEY.")
        self._transport = transport

    async def send(self, message: EmailMessage) -> EmailSendResult:
        content = []
        if message.text_body:
            content.append({"type": "text/plain", "value": message.text_body})
        content.append({"type": "text/html", "value": message.html_body})
        payload: dict = {
            "personalizations": [{"to": [{"email": message.to}]}],
            "from": {"email": settings.email_from_address, "name": settings.email_from_name},
            "subject": message.subject,
            "content": content,
        }
        if message.reply_to:
            payload["reply_to"] = {"email": message.reply_to}
        if message.attachments:
            payload["attachments"] = [
                {
                    "content": base64.b64encode(data).decode("ascii"),
                    "filename": filename,
                    "type": mime_type,
                    "disposition": "attachment",
                }
                for filename, data, mime_type in message.attachments
            ]
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, transport=self._transport) as client:
                resp = await client.post(
                    self.API_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
                )
        except httpx.HTTPError as exc:
            logger.error("sendgrid request failed: %s", type(exc).__name__)
            return EmailSendResult(success=False, error_message="Could not reach SendGrid.")
        if resp.status_code in (200, 201, 202):
            return EmailSendResult(
                success=True, provider_message_id=resp.headers.get("x-message-id")
            )
        logger.error("sendgrid rejected the message: HTTP %s", resp.status_code)
        return EmailSendResult(
            success=False, error_message=f"SendGrid rejected the message (HTTP {resp.status_code})."
        )


class MailgunEmailSender(EmailSender):
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not settings.mailgun_api_key or not settings.mailgun_domain:
            raise ValueError("EMAIL_BACKEND=mailgun requires MAILGUN_API_KEY and MAILGUN_DOMAIN.")
        self._transport = transport
        self._url = f"https://api.mailgun.net/v3/{settings.mailgun_domain}/messages"

    async def send(self, message: EmailMessage) -> EmailSendResult:
        data = {
            "from": f"{settings.email_from_name} <{settings.email_from_address}>",
            "to": message.to,
            "subject": message.subject,
            "html": message.html_body,
        }
        if message.text_body:
            data["text"] = message.text_body
        if message.reply_to:
            data["h:Reply-To"] = message.reply_to
        files = [
            ("attachment", (filename, content, mime_type))
            for filename, content, mime_type in (message.attachments or [])
        ]
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, transport=self._transport) as client:
                resp = await client.post(
                    self._url,
                    data=data,
                    files=files or None,
                    auth=("api", settings.mailgun_api_key or ""),
                )
        except httpx.HTTPError as exc:
            logger.error("mailgun request failed: %s", type(exc).__name__)
            return EmailSendResult(success=False, error_message="Could not reach Mailgun.")
        if resp.status_code == 200:
            try:
                message_id = resp.json().get("id")
            except ValueError:
                message_id = None
            return EmailSendResult(success=True, provider_message_id=message_id)
        logger.error("mailgun rejected the message: HTTP %s", resp.status_code)
        return EmailSendResult(
            success=False, error_message=f"Mailgun rejected the message (HTTP {resp.status_code})."
        )
