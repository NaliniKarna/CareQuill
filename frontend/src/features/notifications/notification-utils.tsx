import {
  CalendarClock,
  FileText,
  Pill,
  Send,
  Sparkles,
  XCircle,
  type LucideIcon,
} from "lucide-react";

import type { NotificationType } from "@/types/api";

export const NOTIFICATION_ICON: Record<NotificationType, LucideIcon> = {
  appointment_approaching: CalendarClock,
  medication_reminder: Pill,
  ai_summary_ready: Sparkles,
  document_processed: FileText,
  report_shared: Send,
  email_failure: XCircle,
};

export const NOTIFICATION_LABEL: Record<NotificationType, string> = {
  appointment_approaching: "Appointment",
  medication_reminder: "Medication",
  ai_summary_ready: "AI summary",
  document_processed: "Document",
  report_shared: "Report shared",
  email_failure: "Email failed",
};
