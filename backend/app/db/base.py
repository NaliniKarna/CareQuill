"""
Single import point that pulls in every model so that Alembic's
autogenerate can see the full schema, and so `Base.metadata` reflects all
tables in one place. Import `app.db.base` (not `app.db.base_class`)
whenever you need the fully-populated metadata (Alembic env.py, test
fixtures that create/drop all tables).
"""
from app.db.base_class import Base
from app.models.ai_summary import AISummary  # noqa: E402,F401
from app.models.allergy import Allergy  # noqa: E402,F401
from app.models.appointment import Appointment  # noqa: E402,F401
from app.models.audit_log import AuditLog  # noqa: E402,F401
from app.models.doctor_contact import DoctorContact  # noqa: E402,F401
from app.models.document_extraction import DocumentExtraction  # noqa: E402,F401
from app.models.email_log import EmailLog  # noqa: E402,F401
from app.models.family_member import (  # noqa: E402,F401
    FamilyDocument,
    FamilyMember,
    FamilyShareLog,
)
from app.models.health_profile import HealthProfile  # noqa: E402,F401
from app.models.health_snapshot import HealthSnapshot  # noqa: E402,F401
from app.models.journal_entry import JournalEntry  # noqa: E402,F401
from app.models.medical_condition import MedicalCondition  # noqa: E402,F401
from app.models.medical_document import MedicalDocument  # noqa: E402,F401
from app.models.medication import Medication  # noqa: E402,F401
from app.models.medication_reminder import MedicationReminder  # noqa: E402,F401
from app.models.notification import Notification  # noqa: E402,F401
from app.models.refresh_token import RefreshToken  # noqa: E402,F401
from app.models.report_share_link import ReportShareLink  # noqa: E402,F401
from app.models.timeline_note import TimelineNote  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401
from app.models.user_preference import UserPreference  # noqa: E402,F401
from app.models.verification_token import (  # noqa: E402,F401
    EmailVerificationToken,
    PasswordResetToken,
)

__all__ = ["Base"]
