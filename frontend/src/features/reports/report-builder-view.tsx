"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  FileDown,
  Loader2,
  Pencil,
  Send,
  Sparkles,
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
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { aiSummaryService } from "@/services/ai-summary-service";
import { appointmentService } from "@/services/appointment-service";
import { doctorService } from "@/services/doctor-service";
import { documentService } from "@/services/document-service";
import { reportService } from "@/services/report-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { EmailLogRead, HealthReportPreview, HealthReportRequest } from "@/types/api";

const SECTION_LABEL: Record<string, string> = {
  conditions: "Conditions",
  allergies: "Allergies",
  medications: "Medications",
  timeline: "Timeline",
  patient_notes: "Patient notes",
  ai_summary: "Record Summary",
};

interface SectionFlags {
  conditions: boolean;
  allergies: boolean;
  medications: boolean;
  timeline: boolean;
  patientNotes: boolean;
  aiSummary: boolean;
}

const INITIAL_SECTIONS: SectionFlags = {
  conditions: false,
  allergies: false,
  medications: false,
  timeline: false,
  patientNotes: false,
  aiSummary: false,
};

export function ReportBuilderView({
  initialAiSummaryId,
  fixedDoctorId,
}: {
  initialAiSummaryId?: string;
  /** When set, the report is for this doctor and the doctor picker is hidden. */
  fixedDoctorId?: string;
}) {
  const queryClient = useQueryClient();

  const [doctorId, setDoctorId] = useState(fixedDoctorId ?? "");
  const [appointmentId, setAppointmentId] = useState("");
  const [sections, setSections] = useState<SectionFlags>(
    initialAiSummaryId ? { ...INITIAL_SECTIONS, aiSummary: true } : INITIAL_SECTIONS
  );
  const [aiSummaryId, setAiSummaryId] = useState(initialAiSummaryId ?? "");
  const [patientNotesText, setPatientNotesText] = useState("");
  const [documentIds, setDocumentIds] = useState<string[]>([]);

  const [preview, setPreview] = useState<HealthReportPreview | null>(null);
  const [shareResult, setShareResult] = useState<EmailLogRead | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
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
  const { data: documents } = useQuery({
    queryKey: ["documents", "for-report"],
    queryFn: () => documentService.list({ limit: 100 }),
  });

  const eligibleSummaries = (summaries ?? []).filter((s) => s.status !== "pending_review");
  const pendingSummaryCount = (summaries ?? []).filter((s) => s.status === "pending_review").length;
  const selectedSummary = summaries?.find((s) => s.id === aiSummaryId) ?? null;

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
    if (!doctorId) return "Choose a doctor to build a report for.";
    if (sections.aiSummary && !aiSummaryId) return "Choose which Record Summary to include.";
    const anySection =
      sections.conditions ||
      sections.allergies ||
      sections.medications ||
      sections.timeline ||
      sections.patientNotes ||
      sections.aiSummary;
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
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to share this report.")),
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

  const selectedDoctor = doctors?.find((d) => d.id === doctorId) ?? null;
  const canShare = Boolean(preview) && Boolean(selectedDoctor?.email);
  const summaryAlreadyShared = selectedSummary?.status === "shared";

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>1. Doctor</CardTitle>
          <CardDescription>Who is this report for?</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {fixedDoctorId ? (
            <p className="text-sm font-medium">
              {selectedDoctor?.name ?? "Loading..."}
              {selectedDoctor?.email && (
                <span className="font-normal text-muted-foreground"> ({selectedDoctor.email})</span>
              )}
            </p>
          ) : (
            <>
          <Label htmlFor="report-doctor">Doctor</Label>
          <Select
            value={doctorId || undefined}
            onValueChange={(v) => {
              clearResults();
              setDoctorId(v);
            }}
          >
            <SelectTrigger id="report-doctor">
              <SelectValue placeholder={doctorsLoading ? "Loading..." : "Choose a doctor"} />
            </SelectTrigger>
            <SelectContent>
              {doctors?.map((doctor) => (
                <SelectItem key={doctor.id} value={doctor.id}>
                  {doctor.name}
                  {doctor.email ? ` (${doctor.email})` : " — no email on file"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
            </>
          )}
          {doctors?.length === 0 && (
            <p className="text-xs text-muted-foreground">
              You don&apos;t have any doctor contacts yet. Add one from the Doctors tab on the Appointments page.
            </p>
          )}
          {selectedDoctor && !selectedDoctor.email && (
            <p className="text-xs text-warning-foreground">
              This doctor has no email on file, so a report can be previewed and generated but not
              shared. Add an email to this doctor&apos;s profile to enable sharing.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>2. Appointment (optional)</CardTitle>
          <CardDescription>Link this report to an upcoming appointment.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <Label htmlFor="report-appointment">Appointment</Label>
          <Select
            value={appointmentId || "none"}
            onValueChange={(v) => {
              clearResults();
              setAppointmentId(v === "none" ? "" : v);
            }}
          >
            <SelectTrigger id="report-appointment">
              <SelectValue placeholder="No appointment" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No appointment</SelectItem>
              {appointments?.map((appt) => (
                <SelectItem key={appt.id} value={appt.id}>
                  {appt.appointment_date}
                  {appt.reason ? ` — ${appt.reason}` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {appointments?.length === 0 && (
            <p className="text-xs text-muted-foreground">No upcoming appointments to link.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>3. Sections to include</CardTitle>
          <CardDescription>Choose what this report covers.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid gap-3 sm:grid-cols-2">
            {(
              [
                ["conditions", "Conditions"],
                ["allergies", "Allergies"],
                ["medications", "Medications"],
                ["timeline", "Timeline"],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={sections[key]}
                  onCheckedChange={(checked) => toggleSection(key, checked === true)}
                />
                {label}
              </label>
            ))}
          </div>

          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={sections.patientNotes}
                onCheckedChange={(checked) => toggleSection("patientNotes", checked === true)}
              />
              Patient notes
            </label>
            {sections.patientNotes && (
              <div className="flex flex-col gap-2 pl-6">
                <Label htmlFor="report-patient-notes">Anything you&apos;d like to add</Label>
                <Textarea
                  id="report-patient-notes"
                  rows={3}
                  placeholder="e.g. I've noticed more frequent headaches this month."
                  value={patientNotesText}
                  onChange={(e) => {
                    clearResults();
                    setPatientNotesText(e.target.value);
                  }}
                />
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={sections.aiSummary}
                onCheckedChange={(checked) => toggleSection("aiSummary", checked === true)}
              />
              AI summary
            </label>
            {sections.aiSummary && (
              <div className="flex flex-col gap-2 pl-6">
                <Label htmlFor="report-summary">Which Record Summary?</Label>
                <Select
                  value={aiSummaryId || undefined}
                  onValueChange={(v) => {
                    clearResults();
                    setAiSummaryId(v);
                  }}
                >
                  <SelectTrigger id="report-summary">
                    <SelectValue placeholder="Choose a reviewed Record Summary" />
                  </SelectTrigger>
                  <SelectContent>
                    {eligibleSummaries.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {new Date(s.created_at).toLocaleString()} ({s.status.replace("_", " ")})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {eligibleSummaries.length === 0 && (
                  <p className="text-xs text-muted-foreground">
                    You don&apos;t have any reviewed Record Summaries yet. Generate and confirm one from
                    the Record Summary page first.
                  </p>
                )}
                {pendingSummaryCount > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {pendingSummaryCount} summary{pendingSummaryCount > 1 ? "ies" : ""} still{" "}
                    {pendingSummaryCount > 1 ? "await" : "awaits"} your review and{" "}
                    {pendingSummaryCount > 1 ? "aren't" : "isn't"} shown here — pending summaries
                    can&apos;t be shared until you review and confirm them.
                  </p>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>4. Documents to attach (optional)</CardTitle>
          <CardDescription>Nothing is attached by default.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {documents && documents.items.length === 0 && (
            <p className="text-sm text-muted-foreground">You haven&apos;t uploaded any documents yet.</p>
          )}
          {documents?.items.map((doc) => (
            <label key={doc.id} className="flex items-start gap-2 text-sm">
              <Checkbox
                className="mt-0.5"
                checked={documentIds.includes(doc.id)}
                onCheckedChange={() => toggleDocument(doc.id)}
              />
              <span>
                {doc.title}
                {doc.category && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    {doc.category.replace("_", " ")}
                  </span>
                )}
              </span>
            </label>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>5. Preview &amp; share</CardTitle>
          <CardDescription>
            Nothing is sent until you confirm &quot;Share with doctor&quot; below.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {validationError && (
            <Alert variant="destructive">
              <AlertTitle>Can&apos;t build this report yet</AlertTitle>
              <AlertDescription>{validationError}</AlertDescription>
            </Alert>
          )}

          <Button
            className="self-start"
            variant="outline"
            disabled={previewMutation.isPending}
            onClick={handlePreview}
          >
            {previewMutation.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
            Preview
          </Button>

          {preview && (
            <div className="flex flex-col gap-3 rounded-md border border-border p-4 text-sm">
              <div>
                <p className="font-medium">Doctor</p>
                <p className="text-muted-foreground">
                  {preview.doctor_name ?? "—"}
                  {preview.doctor_email ? ` (${preview.doctor_email})` : ""}
                </p>
              </div>
              {(preview.appointment_date || preview.appointment_reason) && (
                <div>
                  <p className="font-medium">Appointment</p>
                  <p className="text-muted-foreground">
                    {preview.appointment_date ?? "—"}
                    {preview.appointment_reason ? ` — ${preview.appointment_reason}` : ""}
                  </p>
                </div>
              )}
              <div>
                <p className="font-medium">Included sections</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {preview.included_sections.length === 0 && (
                    <span className="text-muted-foreground">None</span>
                  )}
                  {preview.included_sections.map((s) => (
                    <Badge key={s} variant="secondary">
                      {SECTION_LABEL[s] ?? s}
                    </Badge>
                  ))}
                </div>
              </div>
              {preview.document_titles.length > 0 && (
                <div>
                  <p className="font-medium">Attached documents</p>
                  <ul className="list-inside list-disc text-muted-foreground">
                    {preview.document_titles.map((title) => (
                      <li key={title}>{title}</li>
                    ))}
                  </ul>
                </div>
              )}
              {preview.patient_notes_text && (
                <div>
                  <p className="font-medium">Patient notes</p>
                  <p className="whitespace-pre-wrap text-muted-foreground">
                    {preview.patient_notes_text}
                  </p>
                </div>
              )}
              {preview.ai_summary_text && (
                <div>
                  <p className="font-medium">Record Summary</p>
                  <p className="whitespace-pre-wrap text-muted-foreground">
                    {preview.ai_summary_text}
                  </p>
                </div>
              )}

              <div className="flex flex-wrap gap-2 pt-2">
                {sections.aiSummary && aiSummaryId && !summaryAlreadyShared && (
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/record-summary?id=${aiSummaryId}`}>
                      <Pencil /> Edit Record Summary
                    </Link>
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  disabled={generateMutation.isPending}
                  onClick={() => generateMutation.mutate(buildPayload())}
                >
                  {generateMutation.isPending ? <Loader2 className="animate-spin" /> : <FileDown />}
                  Generate PDF
                </Button>
                <Button
                  size="sm"
                  disabled={!canShare || Boolean(shareResult && shareResult.status === "sent")}
                  onClick={() => setConfirmOpen(true)}
                >
                  <Send /> Share with doctor
                </Button>
              </div>
              {!selectedDoctor?.email && (
                <p className="text-xs text-muted-foreground">
                  Add an email address for this doctor to enable sharing.
                </p>
              )}
            </div>
          )}

          {shareResult && (
            <Alert variant={shareResult.status === "sent" ? "success" : "destructive"}>
              {shareResult.status === "sent" ? <CheckCircle2 /> : <XCircle />}
              <AlertTitle>{shareResult.status === "sent" ? "Sent" : "Failed to send"}</AlertTitle>
              <AlertDescription>
                {shareResult.status === "sent"
                  ? `The report was emailed to ${shareResult.doctor_email}.`
                  : shareResult.error_message ?? "The email could not be delivered. Please try again."}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Share this report with your doctor?"
        description={`This will email the report to ${selectedDoctor?.email ?? "the selected doctor"}. This can't be undone.`}
        confirmLabel="Share with doctor"
        destructive={false}
        isLoading={shareMutation.isPending}
        onConfirm={() => shareMutation.mutate(buildPayload())}
      />
    </div>
  );
}
