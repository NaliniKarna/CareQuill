// Types mirror the backend's Pydantic schemas 1:1 (see backend/app/schemas).
// Keeping this file in sync with the backend is a manual step for now; a
// generated client (e.g. from the OpenAPI schema at /api/v1/openapi.json)
// is a natural follow-up but out of scope for this checkpoint.

export interface User {
  id: string;
  email: string;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface HealthProfile {
  id: string;
  user_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string | null;
  gender: string | null;
  blood_group: string | null;
  phone: string | null;
  address: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  height: number | null;
  weight: number | null;
  created_at: string;
  updated_at: string;
}

export type HealthProfileInput = Omit<
  HealthProfile,
  "id" | "user_id" | "created_at" | "updated_at"
>;

export interface NextAppointmentSummary {
  id: string;
  appointment_date: string;
  reason: string | null;
  doctor_name: string | null;
}

export interface DashboardResponse {
  welcome_message: string;
  profile_completion_percent: number;
  has_health_profile: boolean;
  next_appointment: NextAppointmentSummary | null;
  active_medications_count: number;
  recent_documents_count: number;
  reminders_due_today_count: number;
  health_snapshot_status: "not_generated" | "up_to_date" | "stale";
  latest_ai_summary_status: string | null;
  notifications: string[];
}

// --- Medications -----------------------------------------------------------

/** Where a record came from: typed by the patient, or added by the patient
 * after reviewing an AI/OCR suggestion from one of their documents. */
export type RecordSource = "manual" | "document_suggestion";

export interface Medication {
  id: string;
  patient_id: string;
  name: string;
  dosage: string | null;
  frequency: string | null;
  instructions: string | null;
  start_date: string | null;
  end_date: string | null;
  notes: string | null;
  is_active: boolean;
  source?: RecordSource;
  source_document_id?: string | null;
  created_at: string;
  updated_at: string;
}

export type MedicationInput = {
  name: string;
  dosage: string | null;
  frequency: string | null;
  instructions: string | null;
  start_date: string | null;
  end_date: string | null;
  notes: string | null;
  is_active?: boolean;
  /** Set only when the patient adds a record after reviewing an AI/OCR suggestion. */
  source_document_id?: string;
};

export interface MedicationReminder {
  id: string;
  medication_id: string;
  patient_id: string;
  reminder_time: string;
  days_of_week: string;
  is_enabled: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface MedicationReminderInput {
  reminder_time: string;
  days_of_week: string;
  is_enabled: boolean;
  notes: string | null;
}

export type MedicationReminderUpdateInput = Partial<MedicationReminderInput>;

// --- Allergies ---------------------------------------------------------

export type AllergySeverity = "mild" | "moderate" | "severe";

export interface Allergy {
  id: string;
  patient_id: string;
  name: string;
  severity: AllergySeverity | null;
  reaction: string | null;
  notes: string | null;
  source?: RecordSource;
  source_document_id?: string | null;
  created_at: string;
  updated_at: string;
}

export type AllergyInput = {
  name: string;
  severity: AllergySeverity | null;
  reaction: string | null;
  notes: string | null;
  source_document_id?: string;
};

// --- Conditions ----------------------------------------------------------

export type ConditionStatus = "active" | "managed" | "resolved";

export interface MedicalCondition {
  id: string;
  patient_id: string;
  name: string;
  diagnosed_date: string | null;
  status: ConditionStatus | null;
  notes: string | null;
  source?: RecordSource;
  source_document_id?: string | null;
  created_at: string;
  updated_at: string;
}

export type MedicalConditionInput = {
  name: string;
  diagnosed_date: string | null;
  status: ConditionStatus | null;
  notes: string | null;
  source_document_id?: string;
};

// --- Doctor contacts -------------------------------------------------------

export interface DoctorContact {
  id: string;
  patient_id: string;
  name: string;
  email: string | null;
  phone: string | null;
  specialization: string | null;
  clinic_name: string | null;
  created_at: string;
  updated_at: string;
}

export type DoctorContactInput = {
  name: string;
  email: string | null;
  phone: string | null;
  specialization: string | null;
  clinic_name: string | null;
};

// --- Appointments ----------------------------------------------------------

export type AppointmentStatus = "scheduled" | "completed" | "cancelled" | "missed";

export interface Appointment {
  id: string;
  patient_id: string;
  doctor_contact_id: string | null;
  appointment_date: string;
  appointment_time: string | null;
  reason: string | null;
  notes: string | null;
  status: AppointmentStatus;
  created_at: string;
  updated_at: string;
}

export type AppointmentCreateInput = {
  doctor_contact_id: string | null;
  appointment_date: string;
  appointment_time: string | null;
  reason: string | null;
  notes: string | null;
};

export type AppointmentUpdateInput = Partial<AppointmentCreateInput>;

// --- Medical documents -------------------------------------------------

export type DocumentCategory =
  | "prescription"
  | "blood_test"
  | "lab_report"
  | "xray"
  | "mri"
  | "ct_scan"
  | "discharge_summary"
  | "vaccination"
  | "referral"
  | "other";

export type DocumentProcessingStatus = "uploaded" | "processing" | "processed" | "failed";
export type DocumentOcrStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "not_applicable"
  | "skipped"
  | "no_text";

export interface MedicalDocument {
  id: string;
  patient_id: string;
  title: string;
  category: DocumentCategory | null;
  original_filename: string;
  mime_type: string;
  file_size: number;
  visit_date: string | null;
  doctor_name: string | null;
  hospital_name: string | null;
  ocr_status: string;
  processing_status: string;
  created_at: string;
  updated_at: string;
}

export interface MedicalDocumentListResponse {
  items: MedicalDocument[];
  total: number;
  limit: number;
  offset: number;
}

export interface MedicalDocumentUploadInput {
  file: File;
  title: string;
  category?: DocumentCategory | "";
  visit_date?: string;
  doctor_name?: string;
  hospital_name?: string;
}

export interface ExtractedMedication {
  name?: string;
  dosage?: string;
  frequency?: string;
  [key: string]: unknown;
}

export interface ExtractedData {
  medications?: ExtractedMedication[];
  conditions?: string[];
  allergies?: string[];
  procedures?: string[];
  dates?: string[];
  lab_values?: Array<{
    label?: string;
    value?: string;
    unit?: string;
    range?: string;
    flag?: string;
    [key: string]: unknown;
  }>;
  recommendations?: string[];
  /** "medical_image" for X-ray / MRI / CT uploads. */
  document_kind?: string;
  /** Present when OCR could not run or found nothing; shown to the patient. */
  notice?: string;
  /** Background AI step: pending -> done | failed | unavailable | disabled. */
  ai_status?: "pending" | "done" | "failed" | "unavailable" | "disabled";
  extraction_method?: string;
  ai_summary?: string | null;
  imaging?: ImagingInfo;
}

export interface ImagingInfo {
  interpretation: "not_performed";
  notice: string;
  image_info?: { width: number; height: number; mode: string } | null;
  annotations?: { text_lines?: string[]; side_markers_seen?: string[] };
  ai_description?: {
    modality?: string | null;
    body_region?: string | null;
    view?: string | null;
    quality_notes?: string | null;
    [key: string]: unknown;
  } | null;
}

export interface DocumentExplanation {
  explanation: string;
  terms: Array<{ term: string; meaning: string }>;
  questions_for_doctor: string[];
  model: string;
}

export interface AIStatus {
  enabled: boolean;
  provider: string;
  available: boolean;
  model: string | null;
  model_ready: boolean | null;
  detail: string | null;
  document_ai_enabled: boolean;
  vision_enabled: boolean;
}

export type ExtractionStatus = "pending_review" | "processing" | "reviewed" | "dismissed" | "failed";

export interface DocumentExtraction {
  id: string;
  document_id: string;
  raw_text: string | null;
  confidence: number | null;
  extracted_data: ExtractedData | null;
  status: string;
  created_at: string;
  updated_at: string;
}

// --- Health snapshots ------------------------------------------------------

export interface HealthSnapshotVersion {
  id: string;
  version: number;
  created_at: string;
}

export interface HealthSnapshot {
  id: string;
  patient_id: string;
  version: number;
  snapshot_data: Record<string, unknown>;
  created_at: string;
}

// --- AI summaries ----------------------------------------------------------

export type AISummaryStatus = "pending_review" | "reviewed" | "shared" | "outdated";

export interface AISummary {
  id: string;
  patient_id: string;
  health_snapshot_id: string | null;
  summary_text: string;
  edited_summary_text: string | null;
  structured_summary: Record<string, unknown> | null;
  model_name: string;
  prompt_version: string;
  status: string;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AISummaryGenerateInput {
  patient_concerns?: string | null;
  include_document_ids?: string[] | null;
}

export type EmailLogStatus = "sent" | "failed" | "pending";

export interface EmailLog {
  id: string;
  patient_id: string;
  appointment_id: string | null;
  doctor_email: string;
  subject: string;
  status: string;
  error_message: string | null;
  sent_at: string | null;
  created_at: string;
}

// --- Health reports (preview / generate PDF / share with doctor) ----------

export interface HealthReportRequest {
  doctor_contact_id?: string | null;
  appointment_id?: string | null;
  ai_summary_id?: string | null;
  document_ids: string[];
  include_conditions: boolean;
  include_allergies: boolean;
  include_medications: boolean;
  include_timeline: boolean;
  include_patient_notes: boolean;
  include_ai_summary: boolean;
  patient_notes_text?: string | null;
}

export interface ReportDocumentInfo {
  title: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
}

export interface HealthReportPreview {
  doctor_name: string | null;
  doctor_email: string | null;
  appointment_date: string | null;
  appointment_reason: string | null;
  included_sections: string[];
  document_titles: string[];
  /** Selected documents; they are attached as the original files when shared. */
  documents: ReportDocumentInfo[];
  attachments_total_bytes: number;
  max_email_attachments_bytes: number;
  ai_summary_text: string | null;
  patient_notes_text: string | null;
}

// Full detail returned directly from /reports/share (the patient's own
// action, in the same response).
export interface EmailLogRead {
  id: string;
  patient_id: string;
  appointment_id: string | null;
  doctor_email: string;
  doctor_name: string | null;
  subject: string;
  report_name: string | null;
  status: string;
  error_message: string | null;
  sent_at: string | null;
  created_at: string;
}

// Narrower shape used by GET /email-logs (metadata-only sharing history,
// never the attached document/summary content).
export interface EmailLogListItem {
  id: string;
  doctor_name: string | null;
  doctor_email: string;
  appointment_date: string | null;
  appointment_reason: string | null;
  report_name: string | null;
  status: string;
  sent_at: string | null;
  created_at: string;
}

// --- Notifications -----------------------------------------------------

export type NotificationType =
  | "appointment_approaching"
  | "medication_reminder"
  | "ai_summary_ready"
  | "document_processed"
  | "report_shared"
  | "email_failure"
  | "family_update";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  is_read: boolean;
  related_resource_id: string | null;
  created_at: string;
  // True for a real, stored row (can be marked read); false for a
  // computed-on-read notification, which is always informational/unread.
  persisted: boolean;
}

// --- Preferences ---------------------------------------------------------

export interface NotificationPrefs {
  appointment_reminders: boolean;
  medication_reminders: boolean;
  ai_summary_ready: boolean;
  document_processed: boolean;
  report_shared: boolean;
  email_failures: boolean;
}

export interface UserPreference {
  notification_prefs: NotificationPrefs;
  data_sharing_consent: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserPreferenceUpdateInput {
  notification_prefs?: NotificationPrefs;
  data_sharing_consent?: boolean;
}

// --- Auth: change password -------------------------------------------------

export interface ChangePasswordInput {
  current_password: string;
  new_password: string;
}

// --- Journal -------------------------------------------------------------

export interface JournalEntry {
  id: string;
  patient_id: string;
  entry_date: string;
  mood: number | null;
  title: string | null;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface JournalEntryInput {
  entry_date: string;
  mood: number | null;
  title: string | null;
  body: string;
}

export interface JournalListResponse {
  items: JournalEntry[];
  total: number;
}

// --- QR-code / link sharing ------------------------------------------------
export type ReportShareLinkStatus = "active" | "expired" | "revoked";

export interface ReportShareLink {
  id: string;
  recipient_label: string | null;
  report_name: string;
  included_sections: string[];
  document_count: number;
  expires_at: string;
  revoked_at: string | null;
  view_count: number;
  last_viewed_at: string | null;
  created_at: string;
  status: ReportShareLinkStatus;
}

/** Returned once on creation; the URL can't be fetched again later. */
export interface ReportShareLinkCreated extends ReportShareLink {
  url: string;
}

export interface SharedDocumentInfo {
  id: string;
  title: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
}

export interface SharedReportInfo {
  patient_name: string;
  report_name: string;
  recipient_label: string | null;
  included_sections: string[];
  created_at: string;
  expires_at: string;
  documents: SharedDocumentInfo[];
}

// --- Family circle ------------------------------------------------------

export type FamilyRelation =
  | "spouse"
  | "parent"
  | "child"
  | "sibling"
  | "grandparent"
  | "grandchild"
  | "other";

/** unlinked: no account, you keep their documents. pending: they claimed it
 * and have not chosen yet. active: they keep you as a helper. ended: they
 * removed your access. */
export type FamilyLinkStatus = "unlinked" | "pending" | "active" | "ended";

export interface FamilyMember {
  id: string;
  full_name: string;
  relation: FamilyRelation;
  date_of_birth: string | null;
  blood_group: string | null;
  notes: string | null;
  link_status: FamilyLinkStatus;
  document_count: number | null;
  invite_active: boolean;
  invite_expires_at: string | null;
  claimed_at: string | null;
  created_at: string;
}

export interface FamilyMemberInput {
  full_name: string;
  relation: FamilyRelation;
  date_of_birth: string | null;
  blood_group: string | null;
  notes: string | null;
}

export interface FamilyInviteCreated {
  code: string;
  expires_at: string;
}

export interface FamilyLinkedToMe {
  id: string;
  manager_name: string;
  relation: FamilyRelation;
  link_status: FamilyLinkStatus;
  claimed_at: string | null;
}

export interface FamilyDocument {
  id: string;
  title: string;
  category: DocumentCategory | null;
  original_filename: string;
  mime_type: string;
  file_size: number;
  visit_date: string | null;
  doctor_name: string | null;
  hospital_name: string | null;
  created_at: string;
  source: "family" | "account";
  can_delete: boolean;
}

export interface FamilyShareInput {
  document_ids: string[];
  doctor_contact_id: string | null;
  recipient_email: string | null;
  recipient_name: string | null;
  message: string | null;
}

export interface FamilyShareLog {
  id: string;
  recipient_name: string | null;
  recipient_email: string;
  document_titles: string[];
  status: "sent" | "failed";
  error_message: string | null;
  sent_at: string | null;
  created_at: string;
}
