"""Shapes for the family circle."""
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

FamilyRelation = Literal[
    "spouse", "parent", "child", "sibling", "grandparent", "grandchild", "other"
]
LinkStatus = Literal["unlinked", "pending", "active", "ended"]


class FamilyMemberBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    relation: FamilyRelation
    date_of_birth: date | None = None
    blood_group: str | None = Field(default=None, max_length=10)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required.")
        return value

    @field_validator("date_of_birth")
    @classmethod
    def _not_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return value


class FamilyMemberCreate(FamilyMemberBase):
    pass


class FamilyMemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    relation: FamilyRelation | None = None
    date_of_birth: date | None = None
    blood_group: str | None = Field(default=None, max_length=10)
    notes: str | None = Field(default=None, max_length=2000)


class FamilyMemberRead(BaseModel):
    """What the manager sees. While access is pending or ended, the person's
    own details are not exposed beyond the name and relation the manager typed."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    relation: str
    date_of_birth: date | None
    blood_group: str | None
    notes: str | None
    link_status: LinkStatus
    # unlinked: documents the manager stores; active: the person's documents.
    # None while the manager has no access.
    document_count: int | None = None
    invite_active: bool = False
    invite_expires_at: datetime | None = None
    claimed_at: datetime | None = None
    created_at: datetime


class FamilyInviteCreated(BaseModel):
    code: str
    expires_at: datetime


class FamilyClaimRequest(BaseModel):
    code: str = Field(min_length=6, max_length=40)


class FamilyLinkedToMe(BaseModel):
    """A profile another patient keeps for me (seen from my side)."""

    id: uuid.UUID
    manager_name: str
    relation: str  # how the manager described me, e.g. "parent"
    link_status: LinkStatus
    claimed_at: datetime | None


class FamilyAccessDecision(BaseModel):
    allow: bool


class FamilyDocumentRead(BaseModel):
    id: uuid.UUID
    title: str
    category: str | None
    original_filename: str
    mime_type: str
    file_size: int
    visit_date: date | None
    doctor_name: str | None
    hospital_name: str | None
    created_at: datetime
    # family: stored on the manager's side; account: from the person's own account
    source: Literal["family", "account"]
    can_delete: bool


class FamilyShareRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    doctor_contact_id: uuid.UUID | None = None
    recipient_email: EmailStr | None = None
    recipient_name: str | None = Field(default=None, max_length=200)
    message: str | None = Field(default=None, max_length=500)


class FamilyShareLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recipient_name: str | None
    recipient_email: str
    document_titles: list[str]
    status: str
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime
