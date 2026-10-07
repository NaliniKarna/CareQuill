"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CalendarPlus, History, Mail, Pencil, Phone, Send, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { ErrorState, ListSkeleton } from "@/components/shared/page-states";
import { AppointmentsView } from "@/features/appointments/appointments-view";
import { EmailHistoryView } from "@/features/reports/email-history-view";
import { doctorService } from "@/services/doctor-service";
import { getApiErrorMessage } from "@/lib/api-client";

import { DoctorAvatar } from "./doctors-view";
import { DoctorFormDialog } from "./doctor-form-dialog";

/**
 * One doctor: contact details, visits with them and what was shared with
 * them. Adding visits and sharing happen on their own tabs (pre-filled with
 * this doctor), so there is a single form for each.
 */
export function DoctorProfileView({ doctorId }: { doctorId: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

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
          <div className="flex shrink-0 flex-wrap gap-2">
            <Button size="sm" asChild>
              <Link href={`/appointments?tab=appointments&doctor=${doctor.id}`}>
                <CalendarPlus className="size-4" /> Add appointment
              </Link>
            </Button>
            <Button size="sm" variant="secondary" asChild>
              <Link href={`/appointments?tab=share&doctor=${doctor.id}`}>
                <Send className="size-4" /> Share report
              </Link>
            </Button>
            <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
              <Pencil className="size-4" /> Edit
            </Button>
            <Button variant="outline" size="sm" onClick={() => setDeleteOpen(true)}>
              <Trash2 className="size-4 text-destructive" /> Remove
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid items-start gap-6 xl:grid-cols-2">
        <AppointmentsView doctorId={doctor.id} showForm={false} />
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <History className="size-4 text-primary" /> Reports emailed to this doctor
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmailHistoryView doctorEmail={doctor.email} />
          </CardContent>
        </Card>
      </div>

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
