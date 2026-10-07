"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  Eye,
  FileDown,
  FileText,
  Loader2,
  Mail,
  Paperclip,
  Pencil,
  QrCode,
  Send,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { aiSummaryService } from "@/services/ai-summary-service";
import { appointmentService } from "@/services/appointment-service";
import { doctorService } from "@/services/doctor-service";
import { documentService } from "@/services/document-service";
import { reportService } from "@/services/report-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { cn, formatBytes } from "@/lib/utils";
import type { EmailLogRead, HealthReportPreview, HealthReportRequest } from "@/types/api";

import { QrShareDialog } from "./qr-share-dialog";
import { SECTION_LABEL } from "./section-labels";


interface SectionFlags {
  conditions: boolean;
  allergies: boolean;
  medications: boolean;
  timeline: boolean;
  patientNotes: boolean;
  aiSummary: boolean;
}

// Nothing is included until the patient ticks it (explicit opt-in).
const INITIAL_SECTIONS: SectionFlags = {
  conditions: false,
  allergies: false,
  medications: false,
  timeline: false,
  patientNotes: false,
  aiSummary: false,
};

const SECTION_OPTIONS: { key: "conditions" | "allergies" | "medications" | "timeline"; label: string; hint: string }[] = [
  { key: "conditions", label: "Conditions", hint: "Diagnosed and managed conditions" },
  { key: "allergies", label: "Allergies", hint: "Allergies, severity and reactions" },
  { key: "medications", label: "Current medications", hint: "Active medicines and doses" },
  { key: "timeline", label: "Timeline", hint: "Recent health events" },
];

function FormSection({
  step,
  title,
  description,
  children,
}: {
  step: number;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <fieldset className="flex flex-col gap-4">
      <legend className="mb-3 flex items-start gap-3">
        <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
          {step}
        </span>
        <span>
          <span className="block font-semibold">{title}</span>
          <span className="block text-sm text-muted-foreground">{description}</span>
        </span>
      </legend>
      <div className="flex flex-col gap-4 sm:pl-10">{children}</div>
    </fieldset>
  );
}

export function ReportBuilderView({
  initialAiSummaryId,
  initialDoctorId,
}: {
  initialAiSummaryId?: string;
  /** Pre-selects a doctor (e.g. "Share report" on a doctor's profile). */
  initialDoctorId?: string;
}) {
  const queryClient = useQueryClient();

  const [doctorId, setDoctorId] = useState(initialDoctorId ?? "");
  const [appointmentId, setAppointmentId] = useState("");
  const [sections, setSections] = useState<SectionFlags>(
    initialAiSummaryId ? { ...INITIAL_SECTIONS, aiSummary: true } : INITIAL_SECTIONS,
  );
  const [aiSummaryId, setAiSummaryId] = useState(initialAiSummaryId ?? "");
  const [patientNotesText, setPatientNotesText] = useState("");
  const [documentIds, setDocumentIds] = useState<string[]>([]);

  const [preview, setPreview] = useState<HealthReportPreview | null>(null);
  const [shareResult, setShareResult] = useState<EmailLogRead | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [qrOpen, setQrOpen] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const { data: doctors, isLoading: doctorsLoading } = useQuery({
    queryKey: ["doctors"],
    queryFn: () => doctorService.list(),
  });
  const { data: appointments } = useQuery({
    queryKey: ["appointments", "upcoming"],
    queryFn: () => appointmentService.list("upcoming"),
  });
  const { data: summaries } = useQuery({
    queryKey: ["ai-summaries"],
    queryFn: () => aiSummaryService.list(),
  });
  const { data: documents, isLoading: documentsLoading } = useQuery({
    queryKey: ["documents", "for-report"],
    queryFn: () => documentService.list({ limit: 100 }),
  });

  const eligibleSummaries = (summaries ?? []).filter((s) => s.status !== "pending_review");
  const pendingSummaryCount = (summaries ?? []).filter((s) => s.status === "pending_review").length;
  const selectedSummary = summaries?.find((s) => s.id === aiSummaryId) ?? null;
  const selectedDoctor = doctors?.find((d) => d.id === doctorId) ?? null;
  const doctorAppointments = (appointments ?? []).filter(
    (a) => !doctorId || a.doctor_contact_id === doctorId,
  );
  const selectedDocsBytes = (documents?.items ?? [])
    .filter((d) => documentIds.includes(d.id))
    .reduce((sum, d) => sum + d.file_size, 0);

  const clearResults = () => {
    setPreview(null);
    setShareResult(null);
    setValidationError(null);
  };

  const toggleSection = (key: keyof SectionFlags, value: boolean) => {
    clearResults();
    setSections((prev) => ({ ...prev, [key]: value }));
  };

  const toggleDocument = (id: string) => {
    clearResults();
    setDocumentIds((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]));
  };

  function buildPayload(): HealthReportRequest {
    return {
      doctor_contact_id: doctorId || null,
      appointment_id: appointmentId || null,
      ai_summary_id: sections.aiSummary ? aiSummaryId || null : null,
      document_ids: documentIds,
      include_conditions: sections.conditions,
      include_allergies: sections.allergies,
      include_medications: sections.medications,
      include_timeline: sections.timeline,
      include_patient_notes: sections.patientNotes,
      include_ai_summary: sections.aiSummary,
      patient_notes_text: sections.patientNotes ? patientNotesText.trim() || null : null,
    };
  }

  function validate(): string | null {
    if (sections.aiSummary && !aiSummaryId) return "Choose which Record Summary to include.";
    if (sections.patientNotes && !patientNotesText.trim()) return "Write your note, or untick “Your notes”.";
    const anySection = Object.values(sections).some(Boolean);
    if (!anySection && documentIds.length === 0) {
      return "Select at least one section or document to include in the report.";
    }
    return null;
  }

  const previewMutation = useMutation({
    mutationFn: (payload: HealthReportRequest) => reportService.preview(payload),
    onSuccess: (data) => setPreview(data),
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to build a preview.")),
  });

  const generateMutation = useMutation({
    mutationFn: (payload: HealthReportRequest) => reportService.generateAndOpen(payload),
    onSuccess: () => toast.success("The PDF opened in a new tab."),
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to generate the PDF.")),
  });

  const shareMutation = useMutation({
    mutationFn: (payload: HealthReportRequest) => reportService.share(payload),
    onSuccess: (log) => {
      setShareResult(log);
      setConfirmOpen(false);
      queryClient.invalidateQueries({ queryKey: ["email-logs"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      if (log.status === "sent") {
        toast.success(`Report shared with ${log.doctor_email}.`);
      } else {
        toast.error("The email could not be sent.");
      }
    },
    onError: (error) => {
      setConfirmOpen(false);
      toast.error(getApiErrorMessage(error, "Unable to share this report."));
    },
  });

  const handlePreview = () => {
    const error = validate();
    if (error) {
      setValidationError(error);
      return;
    }
    setValidationError(null);
    previewMutation.mutate(buildPayload());
  };

  const tooBigForEmail =
    preview !== null && preview.attachments_total_bytes > preview.max_email_attachments_bytes;
  const canEmail = Boolean(preview) && Boolean(selectedDoctor?.email) && !tooBigForEmail;
  const summaryAlreadyShared = selectedSummary?.status === "shared";
  const emailSent = shareResult?.status === "sent";

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
      {/* ---------------- Form ---------------- */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="size-5 text-primary" /> Create a health report
          </CardTitle>
          <CardDescription>
            Choose what to include, preview it, then email it to a doctor or share it with a QR code.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            noValidate
            onSubmit={(e) => {
              e.preventDefault();
              handlePreview();
            }}
            className="flex flex-col gap-6"
          >
            <FormSection step={1} title="Recipient" description="Who is this report for?">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="report-doctor">Doctor</Label>
                  <Select
                    value={doctorId || "none"}
                    onValueChange={(v) => {
                      clearResults();
                      setDoctorId(v === "none" ? "" : v);
                      setAppointmentId("");
                    }}
                  >
                    <SelectTrigger id="report-doctor" className="w-full">
                      <SelectValue placeholder={doctorsLoading ? "Loading..." : "Choose a doctor"} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Anyone (QR code only)</SelectItem>
                      {doctors?.map((doctor) => (
                        <SelectItem key={doctor.id} value={doctor.id}>
                          {doctor.name}
                          {doctor.email ? "" : " — no email"}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    {selectedDoctor
                      ? selectedDoctor.email
                        ? `Email goes to ${selectedDoctor.email}.`
                        : "No email on file: you can still use a QR code."
                      : "Needed only for sending by email."}
                  </p>
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="report-appointment">Appointment (optional)</Label>
                  <Select
                    value={appointmentId || "none"}
                    onValueChange={(v) => {
                      clearResults();
                      setAppointmentId(v === "none" ? "" : v);
                    }}
                  >
                    <SelectTrigger id="report-appointment" className="w-full">
                      <SelectValue placeholder="No appointment" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No appointment</SelectItem>
                      {doctorAppointments.map((appt) => (
                        <SelectItem key={appt.id} value={appt.id}>
                          {appt.appointment_date}
                          {appt.reason ? ` — ${appt.reason}` : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    {doctorAppointments.length === 0
                      ? "No upcoming appointments to link."
                      : "Adds the visit date and reason to the report."}
                  </p>
                </div>
              </div>
            </FormSection>

            <Separator />

            <FormSection step={2} title="What to include" description="Pick the parts of your record to share.">
              <div className="grid gap-2 sm:grid-cols-2">
                {SECTION_OPTIONS.map(({ key, label, hint }) => (
                  <label
                    key={key}
                    className={cn(
                      "flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors",
                      sections[key] ? "border-primary/50 bg-accent/50" : "hover:bg-muted/50",
                    )}
                  >
                    <Checkbox
                      className="mt-0.5"
                      checked={sections[key]}
                      onCheckedChange={(checked) => toggleSection(key, checked === true)}
                    />
                    <span>
                      <span className="block text-sm font-medium">{label}</span>
                      <span className="block text-xs text-muted-foreground">{hint}</span>
                    </span>
                  </label>
                ))}
              </div>

              <div className="flex flex-col gap-2 rounded-lg border p-3">
                <label className="flex cursor-pointer items-center gap-3 text-sm font-medium">
                  <Checkbox
                    checked={sections.aiSummary}
                    onCheckedChange={(checked) => toggleSection("aiSummary", checked === true)}
                  />
                  Record Summary
                </label>
                {sections.aiSummary && (
                  <div className="flex flex-col gap-2 pl-7">
                    <Label htmlFor="report-summary" className="sr-only">
                      Which Record Summary?
                    </Label>
                    <Select
                      value={aiSummaryId || undefined}
                      onValueChange={(v) => {
                        clearResults();
                        setAiSummaryId(v);
                      }}
                    >
                      <SelectTrigger id="report-summary" className="w-full">
                        <SelectValue placeholder="Choose a reviewed Record Summary" />
                      </SelectTrigger>
                      <SelectContent>
                        {eligibleSummaries.map((s) => (
                          <SelectItem key={s.id} value={s.id}>
                            {new Date(s.created_at).toLocaleDateString()} ({s.status.replace("_", " ")})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {eligibleSummaries.length === 0 && (
                      <p className="text-xs text-muted-foreground">
                        No reviewed summaries yet.{" "}
                        <Link href="/record-summary" className="font-medium text-primary hover:underline">
                          Create and approve one
                        </Link>{" "}
                        first.
                      </p>
                    )}
                    {pendingSummaryCount > 0 && (
                      <p className="text-xs text-muted-foreground">
                        {pendingSummaryCount} summary{pendingSummaryCount > 1 ? "ies" : ""} still need
                        {pendingSummaryCount > 1 ? "" : "s"} your review before they can be shared.
                      </p>
                    )}
                  </div>
                )}
              </div>

              <div className="flex flex-col gap-2 rounded-lg border p-3">
                <label className="flex cursor-pointer items-center gap-3 text-sm font-medium">
                  <Checkbox
                    checked={sections.patientNotes}
                    onCheckedChange={(checked) => toggleSection("patientNotes", checked === true)}
                  />
                  Your notes
                </label>
                {sections.patientNotes && (
                  <div className="flex flex-col gap-1.5 pl-7">
                    <Label htmlFor="report-patient-notes" className="sr-only">
                      Your notes for the doctor
                    </Label>
                    <Textarea
                      id="report-patient-notes"
                      rows={3}
                      maxLength={4000}
                      placeholder="e.g. I've noticed more frequent headaches this month."
                      value={patientNotesText}
                      onChange={(e) => {
                        clearResults();
                        setPatientNotesText(e.target.value);
                      }}
                    />
                    <p className="text-right text-xs text-muted-foreground tabular-nums">
                      {patientNotesText.length}/4000
                    </p>
                  </div>
                )}
              </div>
            </FormSection>

            <Separator />

            <FormSection
              step={3}
              title="Attach documents"
              description="Selected files are sent as the original files, not just their names."
            >
              {documentsLoading && <p className="text-sm text-muted-foreground">Loading documents...</p>}
              {documents && documents.items.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  You haven&apos;t uploaded any documents yet.{" "}
                  <Link href="/medical-records?tab=documents" className="font-medium text-primary hover:underline">
                    Upload one
                  </Link>
                  .
                </p>
              )}
              {documents && documents.items.length > 0 && (
                <div className="flex max-h-72 flex-col divide-y overflow-y-auto rounded-lg border">
                  {documents.items.map((doc) => (
                    <label
                      key={doc.id}
                      className={cn(
                        "flex cursor-pointer items-center gap-3 px-3 py-2.5 text-sm transition-colors",
                        documentIds.includes(doc.id) ? "bg-accent/50" : "hover:bg-muted/50",
                      )}
                    >
                      <Checkbox
                        checked={documentIds.includes(doc.id)}
                        onCheckedChange={() => toggleDocument(doc.id)}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium">{doc.title}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {doc.original_filename}
                          {doc.category ? ` · ${doc.category.replace("_", " ")}` : ""}
                        </span>
                      </span>
                      <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                        {formatBytes(doc.file_size)}
                      </span>
                    </label>
                  ))}
                </div>
              )}
              {documentIds.length > 0 && (
                <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Paperclip className="size-3.5" />
                  {documentIds.length} selected · {formatBytes(selectedDocsBytes)}
                </p>
              )}
            </FormSection>

            {validationError && (
              <Alert variant="destructive">
                <XCircle />
                <AlertTitle>Can&apos;t build this report yet</AlertTitle>
                <AlertDescription>{validationError}</AlertDescription>
              </Alert>
            )}

            <div className="flex justify-end border-t pt-4">
              <Button type="submit" disabled={previewMutation.isPending}>
                {previewMutation.isPending ? <Loader2 className="animate-spin" /> : <Eye />}
                Preview report
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* ---------------- Preview & share ---------------- */}
      <Card className="lg:sticky lg:top-6">
        <CardHeader>
          <CardTitle>Preview &amp; share</CardTitle>
          <CardDescription>Nothing is sent or shared until you choose an option below.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {!preview && (
            <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed px-4 py-10 text-center">
              <Eye className="size-8 text-muted-foreground" />
              <p className="text-sm font-medium">No preview yet</p>
              <p className="max-w-xs text-xs text-muted-foreground">
                Fill in the form and press “Preview report” to check exactly what will be shared.
              </p>
            </div>
          )}

          {preview && (
            <dl className="flex flex-col gap-3 rounded-lg bg-muted/50 p-4 text-sm">
              <div>
                <dt className="text-xs font-medium text-muted-foreground uppercase">For</dt>
                <dd>
                  {preview.doctor_name ?? "Anyone with the QR code"}
                  {preview.doctor_email ? (
                    <span className="text-muted-foreground"> · {preview.doctor_email}</span>
                  ) : null}
                </dd>
              </div>
              {(preview.appointment_date || preview.appointment_reason) && (
                <div>
                  <dt className="text-xs font-medium text-muted-foreground uppercase">Appointment</dt>
                  <dd>
                    {preview.appointment_date ?? "—"}
                    {preview.appointment_reason ? ` — ${preview.appointment_reason}` : ""}
                  </dd>
                </div>
              )}
              <div>
                <dt className="text-xs font-medium text-muted-foreground uppercase">Includes</dt>
                <dd className="mt-1 flex flex-wrap gap-1">
                  {preview.included_sections
                    .filter((s) => s !== "documents" && s !== "appointment")
                    .map((s) => (
                      <Badge key={s} variant="secondary">
                        {SECTION_LABEL[s] ?? s}
                      </Badge>
                    ))}
                </dd>
              </div>
              {preview.documents.length > 0 && (
                <div>
                  <dt className="text-xs font-medium text-muted-foreground uppercase">
                    Attached files ({formatBytes(preview.attachments_total_bytes)})
                  </dt>
                  <dd>
                    <ul className="mt-1 flex flex-col gap-1">
                      {preview.documents.map((d) => (
                        <li key={d.original_filename + d.title} className="flex items-center gap-2">
                          <Paperclip className="size-3.5 shrink-0 text-muted-foreground" />
                          <span className="truncate">{d.original_filename}</span>
                          <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                            {formatBytes(d.file_size)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </dd>
                </div>
              )}
              {preview.patient_notes_text && (
                <div>
                  <dt className="text-xs font-medium text-muted-foreground uppercase">Your notes</dt>
                  <dd className="whitespace-pre-wrap">{preview.patient_notes_text}</dd>
                </div>
              )}
              {preview.ai_summary_text && (
                <div>
                  <dt className="text-xs font-medium text-muted-foreground uppercase">Record Summary</dt>
                  <dd className="line-clamp-6 whitespace-pre-wrap">{preview.ai_summary_text}</dd>
                </div>
              )}
            </dl>
          )}

          {preview && tooBigForEmail && (
            <Alert variant="warning">
              <AlertTitle>Too large for email</AlertTitle>
              <AlertDescription>
                Attachments are {formatBytes(preview.attachments_total_bytes)}; email allows up to{" "}
                {formatBytes(preview.max_email_attachments_bytes)}. Remove some documents, or share with
                a QR code instead.
              </AlertDescription>
            </Alert>
          )}

          {preview && (
            <div className="flex flex-col gap-2">
              <Button
                variant="outline"
                disabled={generateMutation.isPending}
                onClick={() => generateMutation.mutate(buildPayload())}
              >
                {generateMutation.isPending ? <Loader2 className="animate-spin" /> : <FileDown />}
                Open PDF
              </Button>
              <div className="grid grid-cols-2 gap-2">
                <Button disabled={!canEmail || emailSent} onClick={() => setConfirmOpen(true)}>
                  <Send /> Share PDF by email
                </Button>
                <Button variant="secondary" onClick={() => setQrOpen(true)}>
                  <QrCode /> Create QR code
                </Button>
              </div>
              {!selectedDoctor && (
                <p className="text-xs text-muted-foreground">
                  <Mail className="mr-1 inline size-3.5" />
                  Choose a doctor with an email to send by email.
                </p>
              )}
              {selectedDoctor && !selectedDoctor.email && (
                <p className="text-xs text-muted-foreground">
                  Add an email to {selectedDoctor.name}&apos;s profile to send by email.
                </p>
              )}
              {sections.aiSummary && aiSummaryId && !summaryAlreadyShared && (
                <Button variant="ghost" size="sm" asChild className="self-start">
                  <Link href={`/record-summary?id=${aiSummaryId}`}>
                    <Pencil /> Edit Record Summary
                  </Link>
                </Button>
              )}
            </div>
          )}

          {shareResult && (
            <Alert variant={shareResult.status === "sent" ? "success" : "destructive"}>
              {shareResult.status === "sent" ? <CheckCircle2 /> : <XCircle />}
              <AlertTitle>{shareResult.status === "sent" ? "Sent" : "Failed to send"}</AlertTitle>
              <AlertDescription>
                {shareResult.status === "sent"
                  ? `The report${preview?.documents.length ? " and attached files were" : " was"} emailed to ${shareResult.doctor_email}.`
                  : (shareResult.error_message ?? "The email could not be delivered. Please try again.")}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Email this report to your doctor?"
        description={`The PDF${
          documentIds.length ? ` and ${documentIds.length} attached file${documentIds.length > 1 ? "s" : ""}` : ""
        } will be sent to ${selectedDoctor?.email ?? "the selected doctor"}. This can't be undone.`}
        confirmLabel="Send email"
        destructive={false}
        isLoading={shareMutation.isPending}
        onConfirm={() => shareMutation.mutate(buildPayload())}
      />

      <QrShareDialog
        open={qrOpen}
        onOpenChange={setQrOpen}
        payload={buildPayload()}
        documentCount={documentIds.length}
      />
    </div>
  );
}
