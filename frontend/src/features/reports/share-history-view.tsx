"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, Eye, Mail, Paperclip, QrCode } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState, ErrorState, ListSkeleton } from "@/components/shared/page-states";
import { reportService } from "@/services/report-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { ReportShareLink, ReportShareLinkStatus } from "@/types/api";

import { EmailHistoryView } from "./email-history-view";

const LINK_STATUS: Record<ReportShareLinkStatus, { label: string; variant: "success" | "secondary" | "destructive" }> = {
  active: { label: "Active", variant: "success" },
  expired: { label: "Expired", variant: "secondary" },
  revoked: { label: "Stopped", variant: "destructive" },
};

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function ShareLinksList() {
  const queryClient = useQueryClient();
  const [revoking, setRevoking] = useState<ReportShareLink | null>(null);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["share-links"],
    queryFn: () => reportService.listShareLinks(),
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => reportService.revokeShareLink(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["share-links"] });
      toast.success("The link no longer works.");
      setRevoking(null);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to stop this link.")),
  });

  if (isLoading) return <ListSkeleton rows={2} />;
  if (isError) {
    return <ErrorState description="Couldn't load your QR code links." onRetry={() => refetch()} />;
  }
  if (!data || data.length === 0) {
    return (
      <EmptyState
        icon={QrCode}
        title="No QR codes yet"
        description="QR codes you create from Share report will show up here."
      />
    );
  }

  return (
    <>
      <ul className="flex flex-col divide-y rounded-lg border">
        {data.map((link) => {
          const status = LINK_STATUS[link.status];
          return (
            <li key={link.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium">{link.recipient_label ?? "Anyone with the code"}</p>
                  <Badge variant={status.variant}>{status.label}</Badge>
                </div>
                <p className="flex flex-wrap gap-x-4 gap-y-0.5 text-sm text-muted-foreground">
                  <span>Created {formatDateTime(link.created_at)}</span>
                  <span>
                    {link.status === "revoked" && link.revoked_at
                      ? `Stopped ${formatDateTime(link.revoked_at)}`
                      : `${link.status === "expired" ? "Expired" : "Expires"} ${formatDateTime(link.expires_at)}`}
                  </span>
                </p>
                <p className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <Eye className="size-3.5" /> Opened {link.view_count} time{link.view_count === 1 ? "" : "s"}
                    {link.last_viewed_at ? ` · last ${formatDateTime(link.last_viewed_at)}` : ""}
                  </span>
                  {link.document_count > 0 && (
                    <span className="inline-flex items-center gap-1">
                      <Paperclip className="size-3.5" /> {link.document_count} document
                      {link.document_count === 1 ? "" : "s"}
                    </span>
                  )}
                </p>
              </div>
              {link.status === "active" && (
                <Button variant="outline" size="sm" onClick={() => setRevoking(link)}>
                  <Ban className="size-4 text-destructive" /> Stop link
                </Button>
              )}
            </li>
          );
        })}
      </ul>
      <ConfirmDialog
        open={Boolean(revoking)}
        onOpenChange={(open) => !open && setRevoking(null)}
        title="Stop this link?"
        description="The QR code and link stop working immediately, for everyone. This cannot be undone."
        confirmLabel="Stop link"
        isLoading={revokeMutation.isPending}
        onConfirm={() => revoking && revokeMutation.mutate(revoking.id)}
      />
    </>
  );
}

/** Everything the patient has shared: emailed reports and QR code links. */
export function ShareHistoryView() {
  return (
    <div className="grid items-start gap-6 xl:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <QrCode className="size-5 text-primary" /> QR code links
          </CardTitle>
          <CardDescription>See how often each link was opened, and stop any link at any time.</CardDescription>
        </CardHeader>
        <CardContent>
          <ShareLinksList />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="size-5 text-primary" /> Emailed reports
          </CardTitle>
          <CardDescription>Reports you sent to doctors by email.</CardDescription>
        </CardHeader>
        <CardContent>
          <EmailHistoryView />
        </CardContent>
      </Card>
    </div>
  );
}
