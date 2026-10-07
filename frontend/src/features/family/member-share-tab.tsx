"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, Mail, Paperclip, Send, Stethoscope, XCircle } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { useAuth } from "@/hooks/use-auth";
import { familyService } from "@/services/family-service";
import { doctorService } from "@/services/doctor-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { cn, formatBytes } from "@/lib/utils";
import type { FamilyMember, FamilyShareInput } from "@/types/api";

const MAX_EMAIL_BYTES = 20 * 1024 * 1024; // mirrors the server's default limit
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type RecipientMode = "doctor" | "email";

function Step({
  number,
  title,
  description,
  children,
}: {
  number: number;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <fieldset className="flex flex-col gap-4">
      <legend className="mb-3 flex items-start gap-3">
        <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
          {number}
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

export function MemberShareTab({ member }: { member: FamilyMember }) {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [mode, setMode] = useState<RecipientMode>("doctor");
  const [doctorId, setDoctorId] = useState("");
  const [email, setEmail] = useState("");
  const [recipientName, setRecipientName] = useState("");
  const [documentIds, setDocumentIds] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [sent, setSent] = useState<string | null>(null);

  const { data: doctors } = useQuery({ queryKey: ["doctors"], queryFn: () => doctorService.list() });
  const { data: documents, isLoading: docsLoading } = useQuery({
    queryKey: ["family", "documents", member.id],
    queryFn: () => familyService.listDocuments(member.id),
  });
  const { data: history } = useQuery({
    queryKey: ["family", "shares", member.id],
    queryFn: () => familyService.listShares(member.id),
  });

  const doctorsWithEmail = (doctors ?? []).filter((d) => d.email);
  const selectedBytes = (documents ?? [])
    .filter((d) => documentIds.includes(d.id))
    .reduce((sum, d) => sum + d.file_size, 0);
  const tooLarge = selectedBytes > MAX_EMAIL_BYTES;
  const selectedDoctor = doctorsWithEmail.find((d) => d.id === doctorId);

  const mutation = useMutation({
    mutationFn: (payload: FamilyShareInput) => familyService.share(member.id, payload),
    onSuccess: (log) => {
      queryClient.invalidateQueries({ queryKey: ["family", "shares", member.id] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      setConfirmOpen(false);
      if (log.status === "sent") {
        setSent(log.recipient_name || log.recipient_email);
        setDocumentIds([]);
        setMessage("");
        toast.success("Documents sent.");
      } else {
        setError(log.error_message || "The email could not be delivered.");
      }
    },
    onError: (e) => {
      setConfirmOpen(false);
      setError(getApiErrorMessage(e, "Unable to send the documents."));
    },
  });

  const toggle = (id: string) => {
    setSent(null);
    setError(null);
    setDocumentIds((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]));
  };

  const payload = (): FamilyShareInput => ({
    document_ids: documentIds,
    doctor_contact_id: mode === "doctor" ? doctorId : null,
    recipient_email: mode === "email" ? email.trim() : null,
    recipient_name: mode === "email" ? recipientName.trim() || null : null,
    message: message.trim() || null,
  });

  const validate = (): string | null => {
    if (mode === "doctor" && !doctorId) return "Choose a doctor to send to.";
    if (mode === "email" && !EMAIL_PATTERN.test(email.trim())) return "Enter a valid email address.";
    if (documentIds.length === 0) return "Select at least one document to send.";
    if (tooLarge) return "The selected files are too large for email. Choose fewer documents.";
    return null;
  };

  const onReview = (event: React.FormEvent) => {
    event.preventDefault();
    const problem = validate();
    setError(problem);
    setSent(null);
    if (!problem) setConfirmOpen(true);
  };

  const recipientLabel = mode === "doctor" ? selectedDoctor?.name : recipientName.trim() || email.trim();

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <Card>
        <CardHeader>
          <CardTitle>Send documents for {member.full_name}</CardTitle>
          <CardDescription>
            Emails a one-page summary plus the original files you tick. Nothing is sent until you confirm.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onReview} className="flex flex-col gap-8" noValidate>
            <Step number={1} title="Who should receive it?" description="A doctor you saved, or any email address, including their own.">
              <div role="group" aria-label="Recipient type" className="grid grid-cols-2 gap-2 sm:max-w-md">
                {(
                  [
                    { id: "doctor", label: "A doctor", icon: Stethoscope },
                    { id: "email", label: "An email address", icon: Mail },
                  ] as const
                ).map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    type="button"
                    aria-pressed={mode === id}
                    onClick={() => {
                      setMode(id);
                      setError(null);
                    }}
                    className={cn(
                      "flex items-center justify-center gap-2 rounded-lg border p-2.5 text-sm font-medium transition-colors",
                      "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                      mode === id ? "border-primary bg-accent" : "hover:bg-accent/50",
                    )}
                  >
                    <Icon className="size-4" /> {label}
                  </button>
                ))}
              </div>

              {mode === "doctor" ? (
                <div className="flex flex-col gap-2 sm:max-w-md">
                  <Label htmlFor="fs-doctor">Doctor</Label>
                  <Select value={doctorId || undefined} onValueChange={(v) => { setDoctorId(v); setError(null); }}>
                    <SelectTrigger id="fs-doctor">
                      <SelectValue placeholder={doctorsWithEmail.length ? "Select a doctor" : "No doctors with an email"} />
                    </SelectTrigger>
                    <SelectContent>
                      {doctorsWithEmail.map((d) => (
                        <SelectItem key={d.id} value={d.id}>
                          {d.name}
                          {d.specialization ? ` · ${d.specialization}` : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {doctors && doctorsWithEmail.length === 0 && (
                    <p className="text-xs text-muted-foreground">
                      Add a doctor with an email in Appointments, or choose “An email address”.
                    </p>
                  )}
                </div>
              ) : (
                <div className="grid gap-4 sm:max-w-xl sm:grid-cols-2">
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="fs-email">Email address</Label>
                    <Input
                      id="fs-email"
                      type="email"
                      autoComplete="off"
                      value={email}
                      onChange={(e) => { setEmail(e.target.value); setError(null); }}
                    />
                    {user?.email && (
                      <button
                        type="button"
                        className="self-start text-xs text-primary underline-offset-2 hover:underline"
                        onClick={() => setEmail(user.email)}
                      >
                        Use my email
                      </button>
                    )}
                  </div>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="fs-name">Name (optional)</Label>
                    <Input id="fs-name" value={recipientName} onChange={(e) => setRecipientName(e.target.value)} />
                  </div>
                </div>
              )}
            </Step>

            <Step number={2} title="Which documents?" description="The original files are attached to the email.">
              {docsLoading && <p className="text-sm text-muted-foreground">Loading documents…</p>}
              {documents && documents.length === 0 && (
                <p className="text-sm text-muted-foreground">Add a document in the Documents tab first.</p>
              )}
              {documents && documents.length > 0 && (
                <div className="flex flex-col gap-2">
                  {documents.map((doc) => (
                    <label
                      key={doc.id}
                      className={cn(
                        "flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors",
                        documentIds.includes(doc.id) ? "border-primary bg-accent/40" : "hover:bg-accent/30",
                      )}
                    >
                      <Checkbox
                        className="mt-0.5"
                        checked={documentIds.includes(doc.id)}
                        onCheckedChange={() => toggle(doc.id)}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">{doc.title}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {doc.original_filename} · {formatBytes(doc.file_size)}
                        </span>
                      </span>
                    </label>
                  ))}
                  <p
                    className={cn("text-xs", tooLarge ? "text-destructive" : "text-muted-foreground")}
                    aria-live="polite"
                  >
                    <Paperclip className="mr-1 inline size-3" />
                    {formatBytes(selectedBytes)} of {formatBytes(MAX_EMAIL_BYTES)} email limit
                  </p>
                </div>
              )}
            </Step>

            <Step number={3} title="Add a message" description="Optional. It appears in the email and on the summary page.">
              <div className="flex flex-col gap-2">
                <Label htmlFor="fs-message" className="sr-only">
                  Message
                </Label>
                <Textarea
                  id="fs-message"
                  rows={3}
                  maxLength={500}
                  placeholder="e.g. These are the latest blood tests, please review before the visit."
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                />
                <p className="text-right text-xs text-muted-foreground">{message.length}/500</p>
              </div>
            </Step>

            {error && (
              <Alert variant="destructive" role="alert">
                <XCircle />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            {sent && (
              <Alert>
                <CheckCircle2 />
                <AlertTitle>Sent</AlertTitle>
                <AlertDescription>The documents were emailed to {sent}.</AlertDescription>
              </Alert>
            )}

            <div>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? <Loader2 className="animate-spin" /> : <Send />}
                Review and send
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card className="h-fit">
        <CardHeader>
          <CardTitle className="text-base">Sent for {member.full_name}</CardTitle>
        </CardHeader>
        <CardContent>
          {history && history.length === 0 && (
            <p className="text-sm text-muted-foreground">Nothing sent yet.</p>
          )}
          <ul className="flex flex-col gap-3">
            {(history ?? []).map((log) => (
              <li key={log.id} className="rounded-lg border p-3 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-medium">{log.recipient_name || log.recipient_email}</span>
                  <Badge variant={log.status === "sent" ? "success" : "destructive"}>{log.status}</Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {new Date(log.created_at).toLocaleString()} · {log.document_titles.length} file
                  {log.document_titles.length === 1 ? "" : "s"}
                </p>
                <p className="mt-1 truncate text-xs text-muted-foreground">{log.document_titles.join(", ")}</p>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Send these documents?"
        description={`${documentIds.length} file${documentIds.length === 1 ? "" : "s"} for ${member.full_name} will be emailed to ${recipientLabel ?? "the recipient"}.`}
        confirmLabel="Send email"
        isLoading={mutation.isPending}
        onConfirm={() => mutation.mutate(payload())}
      />
    </div>
  );
}
