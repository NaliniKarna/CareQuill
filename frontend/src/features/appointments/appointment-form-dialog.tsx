"use client";

import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { appointmentService } from "@/services/appointment-service";
import { doctorService } from "@/services/doctor-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { Appointment, AppointmentCreateInput, AppointmentUpdateInput } from "@/types/api";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

const appointmentSchema = z.object({
  doctor_contact_id: z.string().optional(),
  appointment_date: z.string().min(1, "Date is required"),
  appointment_time: z.string().optional().or(z.literal("")),
  reason: z.string().max(500).optional().or(z.literal("")),
  notes: z.string().optional().or(z.literal("")),
});

type AppointmentFormValues = z.infer<typeof appointmentSchema>;

function toFormValues(appointment: Appointment | null): AppointmentFormValues {
  return {
    doctor_contact_id: appointment?.doctor_contact_id ?? "",
    appointment_date: appointment?.appointment_date ?? todayIso(),
    appointment_time: appointment?.appointment_time?.slice(0, 5) ?? "",
    reason: appointment?.reason ?? "",
    notes: appointment?.notes ?? "",
  };
}

export function AppointmentFormDialog({
  open,
  onOpenChange,
  appointment,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  appointment: Appointment | null;
}) {
  const queryClient = useQueryClient();
  const isEditing = Boolean(appointment);

  const { data: doctors } = useQuery({
    queryKey: ["doctors"],
    queryFn: () => doctorService.list(),
    enabled: open,
  });

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AppointmentFormValues>({
    resolver: zodResolver(appointmentSchema),
    defaultValues: toFormValues(null),
  });

  useEffect(() => {
    if (open) reset(toFormValues(appointment));
  }, [open, appointment, reset]);

  const mutation = useMutation({
    mutationFn: (values: AppointmentCreateInput | AppointmentUpdateInput) =>
      appointment
        ? appointmentService.update(appointment.id, values)
        : appointmentService.create(values as AppointmentCreateInput),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      toast.success(isEditing ? "Appointment updated." : "Appointment booked.");
      onOpenChange(false);
    },
    onError: (error) =>
      toast.error(getApiErrorMessage(error, "Unable to save this appointment.")),
  });

  const onSubmit = (values: AppointmentFormValues) => {
    mutation.mutate({
      doctor_contact_id: values.doctor_contact_id || null,
      appointment_date: values.appointment_date,
      appointment_time: values.appointment_time ? `${values.appointment_time}:00` : null,
      reason: values.reason || null,
      notes: values.notes || null,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit appointment" : "Book appointment"}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? "Update the details of this appointment."
              : "New appointments must be scheduled today or in the future."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-2">
            <Label htmlFor="appt-doctor">Doctor</Label>
            <Controller
              control={control}
              name="doctor_contact_id"
              render={({ field }) => (
                <Select value={field.value || "none"} onValueChange={(v) => field.onChange(v === "none" ? "" : v)}>
                  <SelectTrigger id="appt-doctor">
                    <SelectValue placeholder="Select a doctor (optional)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No doctor selected</SelectItem>
                    {doctors?.map((doctor) => (
                      <SelectItem key={doctor.id} value={doctor.id}>
                        {doctor.name}
                        {doctor.specialization ? ` — ${doctor.specialization}` : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {doctors?.length === 0 && (
              <p className="text-xs text-muted-foreground">
                No doctor contacts yet -- you can add one from the Doctor Contacts page.
              </p>
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="appt-date">Date</Label>
              <Input
                id="appt-date"
                type="date"
                min={isEditing ? undefined : todayIso()}
                aria-invalid={Boolean(errors.appointment_date)}
                {...register("appointment_date")}
              />
              {errors.appointment_date && (
                <p className="text-sm text-destructive">{errors.appointment_date.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="appt-time">Time</Label>
              <Input id="appt-time" type="time" {...register("appointment_time")} />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="appt-reason">Reason</Label>
            <Input id="appt-reason" placeholder="e.g. Annual checkup" {...register("reason")} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="appt-notes">Notes</Label>
            <Textarea id="appt-notes" rows={2} {...register("notes")} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <Loader2 className="animate-spin" />}
              {isEditing ? "Save changes" : "Book appointment"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
