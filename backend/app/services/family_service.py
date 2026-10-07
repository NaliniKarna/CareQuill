"""
Family circle: one patient (the "manager") keeps profiles for relatives,
stores their documents, shares them with a doctor, and can hand a profile to
the relative's own CareQuill account.

Ownership model
---------------
* ``unlinked``  The relative has no account. The manager owns the profile and
  its documents (``family_documents``).
* ``pending``   The relative claimed the profile with a one-time invite code.
  Their documents were moved into their own account. Until they decide, the
  manager has NO access (the safe default).
* ``active``    The relative chose to keep the manager as a helper. The
  manager can view, upload and share documents, but never edit or delete
  the relative's existing data. Uploads land in the relative's own account,
  so OCR/AI suggestions wait there for the relative's review.
* ``ended``     The relative removed the manager's access.

Every method re-checks ownership from the database; ids from the client are
never trusted, so one patient can't reach another's profile or documents.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationAppError,
)
from app.core.logging import logger
from app.email.factory import get_email_sender
from app.email.interface import EmailMessage
from app.email.templates import render_family_share_email
from app.models.family_member import (
    LINK_ACTIVE,
    LINK_ENDED,
    LINK_PENDING,
    LINK_UNLINKED,
    FamilyDocument,
    FamilyMember,
    FamilyShareLog,
)
from app.models.medical_document import MedicalDocument
from app.models.user import User
from app.pdf.factory import get_pdf_generator
from app.repositories.doctor_contact_repository import DoctorContactRepository
from app.repositories.family_repository import FamilyRepository
from app.repositories.health_profile_repository import HealthProfileRepository
from app.repositories.medical_document_repository import MedicalDocumentRepository
from app.schemas.family import (
    FamilyDocumentRead,
    FamilyLinkedToMe,
    FamilyMemberCreate,
    FamilyMemberRead,
    FamilyMemberUpdate,
    FamilyShareRequest,
)
from app.schemas.medical_document import MedicalDocumentUploadForm
from app.services.audit_service import AuditService
from app.services.document_service import DocumentService, mime_type_for_extension
from app.services.notification_service import NotificationService
from app.storage.factory import get_storage_backend
from app.utils.files import generate_stored_filename, sanitize_filename

# No 0/O/1/I/L: the code is read aloud or typed from a message.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_CODE_GROUP = 5
_MAX_DOCUMENTS_LISTED = 200
_NOT_FOUND = "Family member not found."


def hash_code(code: str) -> str:
    return hashlib.sha256(normalize_code(code).encode("utf-8")).hexdigest()


def normalize_code(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def _generate_code() -> str:
    groups = [
        "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_GROUP)) for _ in range(2)
    ]
    return "CQ-" + "-".join(groups)


@dataclass
class DocumentFile:
    content: bytes
    filename: str
    mime_type: str


@dataclass
class ClaimResult:
    member: FamilyMember
    new_document_ids: list[uuid.UUID]


class FamilyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FamilyRepository(session)
        self.documents = MedicalDocumentRepository(session)
        self.profiles = HealthProfileRepository(session)
        self.doctors = DoctorContactRepository(session)
        self.storage = get_storage_backend()
        self.audit = AuditService(session)
        self.notifications = NotificationService(session)

    # -- profiles -------------------------------------------------------------
    async def create_member(
        self, *, manager_id: uuid.UUID, data: FamilyMemberCreate
    ) -> FamilyMember:
        if await self.repo.count_for_manager(manager_id) >= settings.family_max_members:
            raise ValidationAppError(
                f"You can add up to {settings.family_max_members} family members."
            )
        member = await self.repo.create_member(manager_id=manager_id, **data.model_dump())
        await self.audit.record(
            user_id=manager_id,
            event_type="family_member_create",
            resource_type="family_member",
            resource_id=member.id,
        )
        return member

    async def list_members(self, *, manager_id: uuid.UUID) -> list[FamilyMemberRead]:
        members = await self.repo.list_for_manager(manager_id)
        return [await self._to_read(m) for m in members]

    async def get_member(
        self, *, manager_id: uuid.UUID, member_id: uuid.UUID
    ) -> FamilyMemberRead:
        return await self._to_read(await self._owned(manager_id, member_id))

    async def update_member(
        self, *, manager_id: uuid.UUID, member_id: uuid.UUID, data: FamilyMemberUpdate
    ) -> FamilyMember:
        member = await self._owned(manager_id, member_id)
        if member.link_status != LINK_UNLINKED:
            raise ForbiddenError(
                "This profile now belongs to the person's own account, so its details "
                "can't be edited here."
            )
        for key, value in data.model_dump(exclude_unset=True).items():
            if key in {"full_name", "relation"} and value is None:
                continue
            setattr(member, key, value)
        await self.session.flush()
        return member

    async def delete_member(self, *, manager_id: uuid.UUID, member_id: uuid.UUID) -> None:
        """Removes the profile from the manager's circle. A linked person's own
        account and documents are never touched."""
        member = await self._owned(manager_id, member_id)
        paths = [d.storage_path for d in await self.repo.list_documents(member.id)]
        await self.repo.delete_member(member)
        await self.audit.record(
            user_id=manager_id,
            event_type="family_member_delete",
            resource_type="family_member",
            resource_id=member_id,
        )
        await self.session.commit()
        await self._delete_files(paths)

    async def _to_read(self, member: FamilyMember) -> FamilyMemberRead:
        read = FamilyMemberRead.model_validate(member)
        now = datetime.now(UTC)
        read.invite_active = bool(
            member.link_status == LINK_UNLINKED
            and member.invite_code_hash
            and member.invite_expires_at
            and member.invite_expires_at > now
        )
        if not read.invite_active:
            read.invite_expires_at = None
        if member.link_status == LINK_UNLINKED:
            read.document_count = await self.repo.count_documents(member.id)
        elif member.link_status == LINK_ACTIVE and member.linked_user_id:
            _, total = await self.documents.list_for_patient(
                member.linked_user_id, limit=1, offset=0
            )
            read.document_count = total
        return read

    async def _owned(self, manager_id: uuid.UUID, member_id: uuid.UUID) -> FamilyMember:
        member = await self.repo.get_member_for_manager(member_id, manager_id)
        if member is None:
            raise NotFoundError(_NOT_FOUND)
        return member

    async def _accessible(self, manager_id: uuid.UUID, member_id: uuid.UUID) -> FamilyMember:
        """The profile, but only if the manager may touch its documents."""
        member = await self._owned(manager_id, member_id)
        if member.link_status == LINK_PENDING:
            raise ForbiddenError(
                "Waiting for this person to choose whether you keep access to their record."
            )
        if member.link_status == LINK_ENDED:
            raise ForbiddenError("This person has ended your access to their record.")
        return member

    # -- invite & claim ------------------------------------------------------------
    async def create_invite(
        self, *, manager_id: uuid.UUID, member_id: uuid.UUID
    ) -> tuple[str, datetime]:
        member = await self._owned(manager_id, member_id)
        if member.link_status != LINK_UNLINKED:
            raise ConflictError("This person already has an account linked to this profile.")
        code = _generate_code()
        expires_at = datetime.now(UTC) + timedelta(days=settings.family_invite_valid_days)
        member.invite_code_hash = hash_code(code)
        member.invite_expires_at = expires_at
        await self.session.flush()
        await self.audit.record(
            user_id=manager_id,
            event_type="family_invite_create",
            resource_type="family_member",
            resource_id=member.id,
        )
        return code, expires_at

    async def revoke_invite(self, *, manager_id: uuid.UUID, member_id: uuid.UUID) -> None:
        member = await self._owned(manager_id, member_id)
        member.invite_code_hash = None
        member.invite_expires_at = None
        await self.session.flush()

    async def claim(self, *, user: User, code: str) -> ClaimResult:
        member = await self.repo.get_by_invite_hash_for_update(hash_code(code))
        invalid = ValidationAppError("This invite code is not valid or has expired.")
        if (
            member is None
            or member.link_status != LINK_UNLINKED
            or member.invite_expires_at is None
            or member.invite_expires_at <= datetime.now(UTC)
        ):
            raise invalid
        if member.manager_id == user.id:
            raise ValidationAppError("You can't claim a profile you created yourself.")
        already = await self.repo.list_linked_to_user(user.id)
        if any(m.manager_id == member.manager_id for m in already):
            raise ValidationAppError(
                "You already linked a profile from this person. Ask them to remove it first."
            )

        # Move the documents into the person's own account. Each copy goes
        # through DocumentService so the same validation and audit rules apply.
        old_documents = await self.repo.list_documents(member.id)
        document_service = DocumentService(self.session)
        new_ids: list[uuid.UUID] = []
        old_paths: list[str] = []
        for old in old_documents:
            try:
                content = await self.storage.read(storage_path=old.storage_path)
            except FileNotFoundError:
                logger.warning("Family document file missing during claim; skipped.")
                continue
            created = await document_service.upload(
                patient_id=user.id,
                file_bytes=content,
                original_filename=old.original_filename,
                form=MedicalDocumentUploadForm(
                    title=old.title,
                    category=old.category,  # type: ignore[arg-type]
                    visit_date=old.visit_date,
                    doctor_name=old.doctor_name,
                    hospital_name=old.hospital_name,
                ),
            )
            new_ids.append(created.id)
            old_paths.append(old.storage_path)
            await self.repo.delete_document(old)

        member.linked_user_id = user.id
        member.link_status = LINK_PENDING
        member.claimed_at = datetime.now(UTC)
        member.invite_code_hash = None
        member.invite_expires_at = None
        await self.session.flush()

        await self.audit.record(
            user_id=user.id,
            event_type="family_claim",
            resource_type="family_member",
            resource_id=member.id,
        )
        await self.notifications.notify(
            patient_id=member.manager_id,
            type="family_update",
            title="Profile claimed",
            body=(
                f"{member.full_name} claimed their profile. Their documents moved to their "
                "own account. They will choose whether you keep access."
            ),
            related_resource_id=member.id,
        )
        await self.session.commit()
        await self._delete_files(old_paths)
        return ClaimResult(member=member, new_document_ids=new_ids)

    # -- the person's side ---------------------------------------------------------
    async def list_linked_to_me(self, *, user_id: uuid.UUID) -> list[FamilyLinkedToMe]:
        items = []
        for member in await self.repo.list_linked_to_user(user_id):
            items.append(
                FamilyLinkedToMe(
                    id=member.id,
                    manager_name=await self._display_name(member.manager_id),
                    relation=member.relation,
                    link_status=member.link_status,  # type: ignore[arg-type]
                    claimed_at=member.claimed_at,
                )
            )
        return items

    async def decide_access(
        self, *, user_id: uuid.UUID, member_id: uuid.UUID, allow: bool
    ) -> FamilyLinkedToMe:
        member = await self.repo.get_member_for_subject(member_id, user_id)
        if member is None:
            raise NotFoundError(_NOT_FOUND)
        member.link_status = LINK_ACTIVE if allow else LINK_ENDED
        await self.session.flush()
        await self.audit.record(
            user_id=user_id,
            event_type="family_access_allow" if allow else "family_access_end",
            resource_type="family_member",
            resource_id=member.id,
        )
        await self.notifications.notify(
            patient_id=member.manager_id,
            type="family_update",
            title="Access updated",
            body=(
                f"{member.full_name} chose to keep you as a helper on their record."
                if allow
                else f"{member.full_name} ended your access to their record."
            ),
            related_resource_id=member.id,
        )
        return FamilyLinkedToMe(
            id=member.id,
            manager_name=await self._display_name(member.manager_id),
            relation=member.relation,
            link_status=member.link_status,  # type: ignore[arg-type]
            claimed_at=member.claimed_at,
        )

    async def _display_name(self, user_id: uuid.UUID) -> str:
        profile = await self.profiles.get_by_user_id(user_id)
        if profile is not None:
            name = f"{profile.first_name} {profile.last_name}".strip()
            if name:
                return name
        return "A CareQuill user"

    # -- documents --------------------------------------------------------------------
    async def list_documents(
        self, *, manager_id: uuid.UUID, member_id: uuid.UUID
    ) -> list[FamilyDocumentRead]:
        member = await self._accessible(manager_id, member_id)
        if member.link_status == LINK_UNLINKED:
            docs = await self.repo.list_documents(member.id)
            return [_family_doc_read(d) for d in docs]
        assert member.linked_user_id is not None
        items, _ = await self.documents.list_for_patient(
            member.linked_user_id, limit=_MAX_DOCUMENTS_LISTED, offset=0
        )
        return [_account_doc_read(d) for d in items]

    async def upload_document(
        self,
        *,
        manager_id: uuid.UUID,
        member_id: uuid.UUID,
        file_bytes: bytes,
        original_filename: str,
        form: MedicalDocumentUploadForm,
    ) -> tuple[FamilyDocumentRead, uuid.UUID | None]:
        """Returns the stored document and, for a linked person, the id of the
        new account document that still needs OCR processing."""
        member = await self._accessible(manager_id, member_id)
        document_service = DocumentService(self.session)

        if member.link_status == LINK_ACTIVE:
            assert member.linked_user_id is not None
            created = await document_service.upload(
                patient_id=member.linked_user_id,
                file_bytes=file_bytes,
                original_filename=original_filename,
                form=form,
            )
            await self.audit.record(
                user_id=manager_id,
                event_type="family_helper_upload",
                resource_type="medical_document",
                resource_id=created.id,
            )
            await self.notifications.notify(
                patient_id=member.linked_user_id,
                type="family_update",
                title="A helper added a document",
                body=(
                    f"{await self._display_name(manager_id)} uploaded \"{created.title}\" to "
                    "your record. Review it in Medical Records."
                ),
                related_resource_id=created.id,
            )
            return _account_doc_read(created), created.id

        document_service.validate_file(file_bytes=file_bytes, original_filename=original_filename)
        stored_filename = generate_stored_filename(original_filename)
        storage_path = await self.storage.save(
            relative_path=f"family/{stored_filename}", content=file_bytes
        )
        try:
            document = await self.repo.create_document(
                family_member_id=member.id,
                title=form.title,
                category=form.category,
                original_filename=sanitize_filename(original_filename),
                stored_filename=stored_filename,
                storage_path=storage_path,
                mime_type=mime_type_for_extension(original_filename),
                file_size=len(file_bytes),
                visit_date=form.visit_date,
                doctor_name=form.doctor_name,
                hospital_name=form.hospital_name,
            )
            await self.audit.record(
                user_id=manager_id,
                event_type="family_document_upload",
                resource_type="family_document",
                resource_id=document.id,
            )
        except Exception:
            await self.storage.delete(storage_path=storage_path)
            raise
        return _family_doc_read(document), None

    async def read_document(
        self, *, manager_id: uuid.UUID, member_id: uuid.UUID, document_id: uuid.UUID
    ) -> DocumentFile:
        member = await self._accessible(manager_id, member_id)
        doc = await self._find_document(member, document_id)
        try:
            content = await self.storage.read(storage_path=doc.storage_path)
        except FileNotFoundError as exc:
            raise NotFoundError("The document's file could not be found.") from exc
        return DocumentFile(content, doc.original_filename, doc.mime_type)

    async def delete_document(
        self, *, manager_id: uuid.UUID, member_id: uuid.UUID, document_id: uuid.UUID
    ) -> None:
        member = await self._accessible(manager_id, member_id)
        if member.link_status != LINK_UNLINKED:
            raise ForbiddenError(
                "Documents in a person's own account can only be deleted by that person."
            )
        doc = await self.repo.get_document(document_id, member.id)
        if doc is None:
            raise NotFoundError("Document not found.")
        path = doc.storage_path
        await self.repo.delete_document(doc)
        await self.audit.record(
            user_id=manager_id,
            event_type="family_document_delete",
            resource_type="family_document",
            resource_id=document_id,
        )
        await self.session.commit()
        await self._delete_files([path])

    async def _find_document(
        self, member: FamilyMember, document_id: uuid.UUID
    ) -> FamilyDocument | MedicalDocument:
        found: FamilyDocument | MedicalDocument | None
        if member.link_status == LINK_UNLINKED:
            found = await self.repo.get_document(document_id, member.id)
        else:
            assert member.linked_user_id is not None
            found = await self.documents.get_by_id_for_patient(document_id, member.linked_user_id)
        if found is None:
            raise NotFoundError("Document not found.")
        return found

    # -- sharing ---------------------------------------------------------------------
    async def share(
        self, *, manager: User, member_id: uuid.UUID, request: FamilyShareRequest
    ) -> FamilyShareLog:
        member = await self._accessible(manager.id, member_id)

        recipient_email: str | None
        recipient_name: str | None
        if request.doctor_contact_id is not None:
            doctor = await self.doctors.get_by_id_for_patient(request.doctor_contact_id, manager.id)
            if doctor is None:
                raise NotFoundError("Doctor contact not found.")
            if not doctor.email:
                raise ValidationAppError("This doctor contact has no email address on file.")
            recipient_email, recipient_name = doctor.email, doctor.name
        elif request.recipient_email is not None:
            recipient_email, recipient_name = str(request.recipient_email), request.recipient_name
        else:
            raise ValidationAppError("Choose a doctor or enter an email address to send to.")

        documents = [
            await self._find_document(member, doc_id)
            for doc_id in dict.fromkeys(request.document_ids)
        ]
        limit_bytes = settings.max_email_attachments_mb * 1024 * 1024
        if sum(d.file_size for d in documents) > limit_bytes:
            raise ValidationAppError(
                f"The selected documents are larger than {settings.max_email_attachments_mb} MB, "
                "which email can't deliver. Choose fewer documents."
            )

        sender_name = await self._display_name(manager.id)
        pdf_bytes = await get_pdf_generator().generate_health_summary_pdf(
            structured_data={
                "patient_info": {
                    "name": member.full_name,
                    "date_of_birth": (
                        member.date_of_birth.isoformat() if member.date_of_birth else None
                    ),
                    "blood_group": member.blood_group,
                },
                "report_date": datetime.now(UTC).date().isoformat(),
                "documents": [{"title": d.title, "category": d.category} for d in documents],
                "patient_notes_text": request.message,
            }
        )
        report_date = datetime.now(UTC).date().isoformat()
        attachments: list[tuple[str, bytes, str]] = [
            (f"health-summary-{report_date}.pdf", pdf_bytes, "application/pdf")
        ]
        for doc in documents:
            try:
                content = await self.storage.read(storage_path=doc.storage_path)
            except FileNotFoundError as exc:
                raise NotFoundError(
                    f"A selected document ('{doc.title}') could not be found in storage."
                ) from exc
            attachments.append((doc.original_filename, content, doc.mime_type))

        titles = [d.title for d in documents]
        html_body, text_body = render_family_share_email(
            recipient_name=recipient_name,
            member_name=member.full_name,
            sender_name=sender_name,
            document_titles=titles,
            message=request.message,
        )
        result = await get_email_sender().send(
            EmailMessage(
                to=recipient_email,
                subject=f"CareQuill health documents for {member.full_name}",
                html_body=html_body,
                text_body=text_body,
                attachments=attachments,
                reply_to=manager.email,
            )
        )
        log = await self.repo.create_share_log(
            manager_id=manager.id,
            family_member_id=member.id,
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            document_titles=titles,
            status="sent" if result.success else "failed",
            error_message=None if result.success else (result.error_message or "")[:500],
            sent_at=datetime.now(UTC) if result.success else None,
        )
        await self.audit.record(
            user_id=manager.id,
            event_type="family_share",
            resource_type="family_share_log",
            resource_id=log.id,
        )
        if result.success and member.link_status == LINK_ACTIVE and member.linked_user_id:
            await self.notifications.notify(
                patient_id=member.linked_user_id,
                type="family_update",
                title="Your documents were shared",
                body=(
                    f"{sender_name} sent {len(documents)} of your documents to "
                    f"{recipient_name or recipient_email}."
                ),
                related_resource_id=log.id,
            )
        if not result.success:
            await self.notifications.notify(
                patient_id=manager.id,
                type="email_failure",
                title="Family documents were not delivered",
                body=f"We couldn't send documents for {member.full_name}.",
                related_resource_id=log.id,
            )
        return log

    async def list_shares(
        self, *, manager_id: uuid.UUID, member_id: uuid.UUID
    ) -> list[FamilyShareLog]:
        member = await self._owned(manager_id, member_id)
        return await self.repo.list_share_logs(manager_id=manager_id, family_member_id=member.id)

    # -- housekeeping ----------------------------------------------------------------
    async def _delete_files(self, paths: list[str]) -> None:
        for path in paths:
            try:
                await self.storage.delete(storage_path=path)
            except Exception:  # noqa: BLE001 - records are already gone; log and move on
                logger.exception("Could not remove a stored family document file.")


def _family_doc_read(doc: FamilyDocument) -> FamilyDocumentRead:
    return FamilyDocumentRead(
        id=doc.id,
        title=doc.title,
        category=doc.category,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        visit_date=doc.visit_date,
        doctor_name=doc.doctor_name,
        hospital_name=doc.hospital_name,
        created_at=doc.created_at,
        source="family",
        can_delete=True,
    )


def _account_doc_read(doc: MedicalDocument) -> FamilyDocumentRead:
    return FamilyDocumentRead(
        id=doc.id,
        title=doc.title,
        category=doc.category,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        visit_date=doc.visit_date,
        doctor_name=doc.doctor_name,
        hospital_name=doc.hospital_name,
        created_at=doc.created_at,
        source="account",
        can_delete=False,
    )
