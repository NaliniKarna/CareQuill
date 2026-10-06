"use client";

import { useQuery } from "@tanstack/react-query";
import { Mail } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState, ErrorState, ListSkeleton } from "@/components/shared/page-states";
import { emailLogService } from "@/services/email-log-service";
import type { EmailLogListItem } from "@/types/api";

const STATUS_VARIANT: Record<string, "success" | "destructive" | "secondary"> = {
  sent: "success",
  failed: "destructive",
  pending: "secondary",
};

export function EmailHistoryView({ doctorEmail }: { doctorEmail?: string | null } = {}) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["email-logs"],
    queryFn: () => emailLogService.list(),
  });

  if (isLoading) return <ListSkeleton />;
  if (isError) {
    return <ErrorState description="Couldn't load your sharing history." onRetry={() => refetch()} />;
  }
  // undefined = every log; null/empty = a doctor with no email, so nothing can match.
  const logs =
    doctorEmail === undefined
      ? data
      : data?.filter((l) => l.doctor_email.toLowerCase() === (doctorEmail ?? "").toLowerCase());
  if (!logs || logs.length === 0) {
    return (
      <EmptyState
        icon={Mail}
        title="No reports shared yet"
        description={
          doctorEmail !== undefined
            ? "Reports you share with this doctor will show up here."
            : "Reports you share with a doctor will show up here."
        }
      />
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {logs.map((log: EmailLogListItem) => (
        <Card key={log.id}>
          <CardContent className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex flex-col gap-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-medium">{log.doctor_name ?? log.doctor_email}</p>
                <Badge variant={STATUS_VARIANT[log.status] ?? "secondary"}>{log.status}</Badge>
              </div>
              <p className="text-sm text-muted-foreground">{log.doctor_email}</p>
              {log.report_name && (
                <p className="text-sm text-muted-foreground">Report: {log.report_name}</p>
              )}
              {log.appointment_date && (
                <p className="text-sm text-muted-foreground">
                  Appointment: {log.appointment_date}
                  {log.appointment_reason ? ` — ${log.appointment_reason}` : ""}
                </p>
              )}
            </div>
            <p className="shrink-0 text-xs text-muted-foreground">
              {log.sent_at
                ? new Date(log.sent_at).toLocaleString()
                : new Date(log.created_at).toLocaleString()}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
