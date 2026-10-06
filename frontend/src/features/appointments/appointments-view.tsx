"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarClock,
  CalendarX,
  Check,
  Clock,
  Pencil,
  Plus,
  Stethoscope,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState, ErrorState, ListSkeleton, PageHeader } from "@/components/shared/page-states";
import { appointmentService, type AppointmentFilter } from "@/services/appointment-service";
import { doctorService } from "@/services/doctor-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { Appointment, AppointmentStatus } from "@/types/api";

import { AppointmentFormDialog } from "./appointment-form-dialog";

const STATUS_VARIANT: Record<AppointmentStatus, "default" | "success" | "secondary" | "destructive"> = {
  scheduled: "default",
  completed: "success",
  cancelled: "secondary",
  missed: "destructive",
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function DateTile({ iso, muted }: { iso: string; muted: boolean }) {
  const [, month, day] = iso.split("-");
  return (
    <div
      className={`flex size-14 shrink-0 flex-col items-center justify-center rounded-xl ${
        muted ? "bg-muted text-muted-foreground" : "bg-accent text-accent-foreground"
      }`}
    >
      <span className="text-[0.65rem] font-semibold tracking-wide uppercase">
        {MONTHS[Number(month) - 1] ?? ""}
      </span>
      <span className="text-xl leading-none font-semibold">{Number(day)}</span>
    </div>
  );
}

export function AppointmentsView({
  embedded = false,
  doctorId,
}: {
  embedded?: boolean;
  /** Show only appointments with this doctor (used on a doctor's profile). */
  doctorId?: string;
} = {}) {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<AppointmentFilter>("upcoming");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Appointment | null>(null);
  const [deleting, setDeleting] = useState<Appointment | null>(null);
  const [cancelling, setCancelling] = useState<Appointment | null>(null);
  const [missing, setMissing] = useState<Appointment | null>(null);

  const { data: allData, isLoading, isError, refetch } = useQuery({
    queryKey: ["appointments", filter],
    queryFn: () => appointmentService.list(filter),
  });
  const data = doctorId ? allData?.filter((a) => a.doctor_contact_id === doctorId) : allData;

  const { data: doctors } = useQuery({ queryKey: ["doctors"], queryFn: () => doctorService.list() });
  const doctorName = (id: string | null) => doctors?.find((d) => d.id === id)?.name ?? null;

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["appointments"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    queryClient.invalidateQueries({ queryKey: ["timeline"] });
  };

  const deleteMutation = useMutation({
    mutationFn: (id: string) => appointmentService.remove(id),
    onSuccess: () => {
      invalidate();
      toast.success("Appointment removed.");
      setDeleting(null);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to remove this appointment.")),
  });

  const completeMutation = useMutation({
    mutationFn: (id: string) => appointmentService.complete(id),
    onSuccess: () => {
      invalidate();
      toast.success("Marked as completed.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to update this appointment.")),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => appointmentService.cancel(id),
    onSuccess: () => {
      invalidate();
      toast.success("Appointment cancelled.");
      setCancelling(null);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to cancel this appointment.")),
  });

  const missMutation = useMutation({
    mutationFn: (id: string) => appointmentService.miss(id),
    onSuccess: () => {
      invalidate();
      toast.success("Marked as missed.");
      setMissing(null);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to update this appointment.")),
  });

  const openAdd = () => {
    setEditing(null);
    setFormOpen(true);
  };
  const openEdit = (appt: Appointment) => {
    setEditing(appt);
    setFormOpen(true);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        compact={embedded}
        title="Appointments"
        description="Upcoming and past visits with your doctors."
        action={
          <Button onClick={openAdd}>
            <Plus /> Book appointment
          </Button>
        }
      />

      <Tabs value={filter} onValueChange={(v) => setFilter(v as AppointmentFilter)}>
        <TabsList>
          <TabsTrigger value="upcoming">Upcoming</TabsTrigger>
          <TabsTrigger value="past">Past</TabsTrigger>
        </TabsList>
      </Tabs>

      {isLoading && <ListSkeleton />}
      {isError && <ErrorState description="Couldn't load your appointments." onRetry={() => refetch()} />}

      {data && data.length === 0 && (
        <EmptyState
          icon={CalendarClock}
          title={filter === "upcoming" ? "No upcoming appointments" : "No past appointments"}
          description={
            filter === "upcoming" ? "Book an appointment to see it here." : "Completed or past visits will show up here."
          }
          action={
            filter === "upcoming" ? (
              <Button onClick={openAdd}>
                <Plus /> Book appointment
              </Button>
            ) : undefined
          }
        />
      )}

      {data && data.length > 0 && (
        <div className="flex flex-col gap-3">
          {data.map((appt) => (
            <Card key={appt.id}>
              <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center">
                <div className="flex min-w-0 flex-1 items-start gap-4">
                  <DateTile iso={appt.appointment_date} muted={appt.status !== "scheduled"} />
                  <div className="flex min-w-0 flex-col gap-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium">
                        {appt.reason || "Appointment"}
                      </p>
                      <Badge variant={STATUS_VARIANT[appt.status]} className="capitalize">
                        {appt.status}
                      </Badge>
                    </div>
                    <p className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm text-muted-foreground">
                      {appt.appointment_time && (
                        <span className="inline-flex items-center gap-1">
                          <Clock className="size-3.5" /> {appt.appointment_time.slice(0, 5)}
                        </span>
                      )}
                      {!doctorId && doctorName(appt.doctor_contact_id) && (
                        <span className="inline-flex items-center gap-1">
                          <Stethoscope className="size-3.5" /> {doctorName(appt.doctor_contact_id)}
                        </span>
                      )}
                    </p>
                    {appt.notes && <p className="text-sm text-muted-foreground">{appt.notes}</p>}
                  </div>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-1">
                  {appt.status === "scheduled" && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={completeMutation.isPending}
                        onClick={() => completeMutation.mutate(appt.id)}
                      >
                        <Check className="size-4" /> Complete
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Mark as missed"
                        title="Mark as missed"
                        onClick={() => setMissing(appt)}
                      >
                        <CalendarX className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Cancel appointment"
                        title="Cancel appointment"
                        onClick={() => setCancelling(appt)}
                      >
                        <X className="size-4" />
                      </Button>
                      <Button variant="ghost" size="icon" aria-label="Edit" onClick={() => openEdit(appt)}>
                        <Pencil className="size-4" />
                      </Button>
                    </>
                  )}
                  <Button variant="ghost" size="icon" aria-label="Delete" onClick={() => setDeleting(appt)}>
                    <Trash2 className="size-4 text-destructive" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <AppointmentFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        appointment={editing}
        defaultDoctorId={doctorId}
      />

      <ConfirmDialog
        open={Boolean(cancelling)}
        onOpenChange={(open) => !open && setCancelling(null)}
        title="Cancel this appointment?"
        description="This marks the appointment as cancelled. You can still see it under Past appointments."
        confirmLabel="Cancel appointment"
        isLoading={cancelMutation.isPending}
        onConfirm={() => cancelling && cancelMutation.mutate(cancelling.id)}
      />

      <ConfirmDialog
        open={Boolean(missing)}
        onOpenChange={(open) => !open && setMissing(null)}
        title="Mark this appointment as missed?"
        description="This marks the appointment as missed rather than completed."
        confirmLabel="Mark as missed"
        isLoading={missMutation.isPending}
        onConfirm={() => missing && missMutation.mutate(missing.id)}
      />

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Delete this appointment?"
        description="This will permanently remove this appointment from your records. This cannot be undone."
        confirmLabel="Delete"
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
      />
    </div>
  );
}
