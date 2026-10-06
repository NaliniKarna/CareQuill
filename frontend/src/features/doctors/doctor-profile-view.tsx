"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CalendarClock, Mail, Pencil, Phone, Send, Trash2, History } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { ErrorState, ListSkeleton } from "@/components/shared/page-states";
import { AppointmentsView } from "@/features/appointments/appointments-view";
import { EmailHistoryView } from "@/features/reports/email-history-view";
import { doctorService } from "@/services/doctor-service";
import { getApiErrorMessage } from "@/lib/api-client";

import { DoctorAvatar } from "./doctors-view";
import { DoctorFormDialog } from "./doctor-form-dialog";

// The report builder is large; load it only when a profile is opened.
const ReportBuilderView = dynamic(
  () => import("@/features/reports/report-builder-view").then((m) => m.ReportBuilderView),
  { loading: () => <ListSkeleton /> },
);

export function DoctorProfileView({ doctorId, summaryId }: { doctorId: string; summaryId?: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [section, setSection] = useState(summaryId ? "share" : "appointments");

  const { data: doctors, isLoading, isError, refetch } = useQuery({
    queryKey: ["doctors"],
    queryFn: () => doctorService.list(),
  });
  const doctor = doctors?.find((d) => d.id === doctorId) ?? null;

  const deleteMutation = useMutation({
    mutationFn: (id: string) => doctorService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["doctors"] });
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      toast.success("Doctor contact removed.");
      router.replace("/appointments?tab=doctors");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to remove this contact.")),
  });

  const back = (
    <Button asChild variant="ghost" size="sm" className="-ml-2 self-start">
      <Link href="/appointments?tab=doctors">
        <ArrowLeft className="size-4" /> All doctors
      </Link>
    </Button>
  );

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        {back}
        <Skeleton className="h-32" />
        <ListSkeleton rows={2} />
      </div>
    );
  }
  if (isError) {
    return <ErrorState description="Couldn't load this doctor." onRetry={() => refetch()} />;
  }
  if (!doctor) {
    return (
      <div className="flex flex-col gap-4">
        {back}
        <ErrorState description="This doctor could not be found. They may have been removed." />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {back}

      <Card>
        <CardContent className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-4">
            <DoctorAvatar name={doctor.name} className="size-16 text-xl" />
            <div className="min-w-0">
              <h2 className="truncate text-xl font-semibold tracking-tight">{doctor.name}</h2>
              <p className="truncate text-sm text-muted-foreground">
                {doctor.specialization || "General"}
                {doctor.clinic_name ? ` · ${doctor.clinic_name}` : ""}
              </p>
              <div className="mt-2 flex flex-col gap-1 text-sm text-muted-foreground sm:flex-row sm:flex-wrap sm:gap-x-5">
                <span className="flex items-center gap-1.5 truncate">
                  <Mail className="size-3.5 shrink-0" /> {doctor.email || "No email on file"}
                </span>
                <span className="flex items-center gap-1.5">
                  <Phone className="size-3.5 shrink-0" /> {doctor.phone || "No phone on file"}
                </span>
              </div>
            </div>
          </div>
          <div className="flex shrink-0 gap-2">
            <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
              <Pencil className="size-4" /> Edit
            </Button>
            <Button variant="outline" size="sm" onClick={() => setDeleteOpen(true)}>
              <Trash2 className="size-4 text-destructive" /> Remove
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs value={section} onValueChange={setSection}>
        <TabsList>
          <TabsTrigger value="appointments">
            <CalendarClock className="size-4" /> Appointments
          </TabsTrigger>
          <TabsTrigger value="share">
            <Send className="size-4" /> Share report
          </TabsTrigger>
          <TabsTrigger value="history">
            <History className="size-4" /> History
          </TabsTrigger>
        </TabsList>
        <TabsContent value="appointments" className="pt-4">
          <AppointmentsView embedded doctorId={doctor.id} />
        </TabsContent>
        <TabsContent value="share" className="pt-4">
          <ReportBuilderView fixedDoctorId={doctor.id} initialAiSummaryId={summaryId} />
        </TabsContent>
        <TabsContent value="history" className="pt-4">
          <EmailHistoryView doctorEmail={doctor.email} />
        </TabsContent>
      </Tabs>

      <DoctorFormDialog open={editOpen} onOpenChange={setEditOpen} doctor={doctor} />

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Remove this doctor?"
        description={`This will permanently remove "${doctor.name}" from your contacts. Existing appointments keep their date but lose the doctor link. This cannot be undone.`}
        confirmLabel="Remove"
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate(doctor.id)}
      />
    </div>
  );
}
