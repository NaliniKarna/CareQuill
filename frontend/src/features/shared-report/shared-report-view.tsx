"use client";

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Clock, Download, Eye, FileText, Loader2, Paperclip, ShieldCheck, TriangleAlert } from "lucide-react";
import { toast } from "sonner";

import { BrandLogo } from "@/components/shared/brand";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SECTION_LABEL } from "@/features/reports/section-labels";
import { sharedReportService } from "@/services/shared-report-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { openBlob } from "@/lib/blob";
import { formatBytes } from "@/lib/utils";

function subscribeToHash(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

/** Reads the secret token from the URL fragment (`/shared#<token>`).
 * `undefined` while rendering on the server (no fragment there). */
function useFragmentToken(): string | null | undefined {
  return useSyncExternalStore(
    subscribeToHash,
    () => window.location.hash.slice(1) || null,
    () => undefined,
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-accent/50 to-background">
      <header className="border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-3xl items-center px-4">
          <BrandLogo markClassName="h-8" />
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-8">{children}</main>
      <footer className="border-t px-4 py-5 text-center text-xs text-muted-foreground">
        Shared by a patient using CareQuill. CareQuill organises patient-provided information and does
        not diagnose or recommend treatment.
      </footer>
    </div>
  );
}

function Unavailable({ title, text }: { title: string; text: string }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
        <TriangleAlert className="size-10 text-warning" />
        <h1 className="text-lg font-semibold">{title}</h1>
        <p className="max-w-sm text-sm text-muted-foreground">{text}</p>
        <Button asChild variant="outline" className="mt-2">
          <Link href="/">Go to CareQuill</Link>
        </Button>
      </CardContent>
    </Card>
  );
}

export function SharedReportView() {
  const token = useFragmentToken();

  const info = useQuery({
    queryKey: ["shared-report", token],
    queryFn: () => sharedReportService.info(token as string),
    enabled: Boolean(token),
    retry: false,
    staleTime: Infinity,
  });

  const report = useMutation({
    mutationFn: async (mode: "view" | "download") => {
      const blob = await sharedReportService.report(token as string);
      openBlob(blob, mode === "download" ? { download: "health-summary.pdf" } : {});
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "The report could not be opened.")),
  });

  const documentDownload = useMutation({
    mutationFn: async (doc: { id: string; original_filename: string }) => {
      const blob = await sharedReportService.document(token as string, doc.id);
      openBlob(blob, { download: doc.original_filename });
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "The document could not be downloaded.")),
  });

  if (token === undefined || (token && info.isLoading)) {
    return (
      <Shell>
        <Skeleton className="h-40" />
        <Skeleton className="h-28" />
      </Shell>
    );
  }
  if (!token) {
    return (
      <Shell>
        <Unavailable
          title="This link is incomplete"
          text="Scan the QR code again, or ask the patient to send you the full link."
        />
      </Shell>
    );
  }
  if (info.isError || !info.data) {
    return (
      <Shell>
        <Unavailable
          title="This link is not available"
          text="It may have expired or been stopped by the patient. Ask them to share a new QR code."
        />
      </Shell>
    );
  }

  const data = info.data;
  const expires = new Date(data.expires_at).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
  const sections = data.included_sections.filter((s) => s !== "documents" && s !== "appointment");

  return (
    <Shell>
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2 text-sm text-success">
            <ShieldCheck className="size-4" /> Shared privately by the patient
          </div>
          <CardTitle className="text-2xl">{data.patient_name}</CardTitle>
          <CardDescription>
            {data.report_name}
            {data.recipient_label ? ` · for ${data.recipient_label}` : ""}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          {sections.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {sections.map((s) => (
                <Badge key={s} variant="secondary">
                  {SECTION_LABEL[s] ?? s}
                </Badge>
              ))}
            </div>
          )}
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button size="lg" disabled={report.isPending} onClick={() => report.mutate("view")}>
              {report.isPending ? <Loader2 className="animate-spin" /> : <Eye />}
              View report
            </Button>
            <Button size="lg" variant="outline" disabled={report.isPending} onClick={() => report.mutate("download")}>
              <Download /> Download PDF
            </Button>
          </div>
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="size-3.5" /> Available until {expires}
          </p>
        </CardContent>
      </Card>

      {data.documents.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Paperclip className="size-4 text-primary" /> Attached documents
            </CardTitle>
            <CardDescription>Original files uploaded by the patient.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col divide-y rounded-lg border">
              {data.documents.map((doc) => (
                <li key={doc.id} className="flex items-center gap-3 px-3 py-3">
                  <FileText className="size-5 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{doc.title}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {doc.original_filename} · {formatBytes(doc.file_size)}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={documentDownload.isPending}
                    onClick={() => documentDownload.mutate(doc)}
                  >
                    <Download className="size-4" /> Download
                  </Button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </Shell>
  );
}
