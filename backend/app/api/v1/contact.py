from fastapi import APIRouter, Depends

from app.core.rate_limit import contact_rate_limit
from app.schemas.common import MessageResponse
from app.schemas.contact import ContactRequest
from app.services.contact_service import ContactService

router = APIRouter(prefix="/public/contact", tags=["contact"])


@router.post("", response_model=MessageResponse, dependencies=[Depends(contact_rate_limit)])
async def send_contact_message(payload: ContactRequest):
    """Public (no login). Emails the message to the CareQuill team; the
    visitor's address is set as Reply-To."""
    await ContactService().submit(payload)
    return MessageResponse(message="Thank you. Your message was sent.")
