"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarPlus, Loader2, Save } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { appointmentService } from "@/services/appointment-service";
import { doctorService } from "@/services/doctor-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { localTodayIso } from "@/lib/utils";
import type { Appointment, AppointmentCreateInput, AppointmentUpdateInput } from "@/types/api";

const appointmentSchema = z.object({
  doctor_contact_id: z.string().optional(),
  appointment_date: z.string().min(1, "Choose the date of the appointment."),
  appointment_time: z.string().optional().or(z.literal("")),
  reason: z.string().max(500, "Keep the reason under 500 characters.").optional().or(z.literal("")),
  notes: z.string().max(2000, "Keep notes under 2000 characters.").optional().or(z.literal("")),
});

type AppointmentFormValues = z.infer<typeof appointmentSchema>;

function toFormValues(appointment: Appointment | null, defaultDoctorId = ""): AppointmentFormValues {
  return {
    doctor_contact_id: appointment?.doctor_contact_id ?? defaultDoctorId,
    appointment_date: appointment?.appointment_date ?? "",
    appointment_time: appointment?.appointment_time?.slice(0, 5) ?? "",
    reason: appointment?.reason ?? "",
    notes: appointment?.notes ?? "",
  };
}

/**
 * Add or edit an appointment the patient already has (CareQuill does not
 * book with clinics; it records the visit so it shows on the dashboard and
 * in reminders). Used inline on the Appointments tab and inside the edit
 * dialog, so there is one form for both.
 */
export function AppointmentForm({
  appointment = null,
  defaultDoctorId,
  onSaved,
  onCancel,
  idPrefix = "appt",
}: {
  appointment?: Appointment | null;
  defaultDoctorId?: string;
  onSaved?: () => void;
  onCancel?: () => void;
  /** Keeps input ids unique when two forms are on screen. */
  idPrefix?: string;
}) {
  const queryClient = useQueryClient();
  const isEditing = Boolean(appointment);
  const { data: doctors, isLoading: doctorsLoading } = useQuery({
    queryKey: ["doctors"],
    queryFn: () => doctorService.list(),
  });

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AppointmentFormValues>({
    resolver: zodResolver(appointmentSchema),
    defaultValues: toFormValues(appointment, defaultDoctorId),
  });

  useEffect(() => {
    reset(toFormValues(appointment, defaultDoctorId));
  }, [appointment, defaultDoctorId, reset]);

  const mutation = useMutation({
    mutationFn: (values: AppointmentCreateInput | AppointmentUpdateInput) =>
      appointment
        ? appointmentService.update(appointment.id, values)
        : appointmentService.create(values as AppointmentCreateInput),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      toast.success(isEditing ? "Appointment updated." : "Appointment added.");
      if (!isEditing) reset(toFormValues(null, defaultDoctorId));
      onSaved?.();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to save this appointment.")),
  });

  const onSubmit = (values: AppointmentFormValues) => {
    mutation.mutate({
      doctor_contact_id: values.doctor_contact_id || null,
      appointment_date: values.appointment_date,
      appointment_time: values.appointment_time ? `${values.appointment_time}:00` : null,
      reason: values.reason?.trim() || null,
      notes: values.notes?.trim() || null,
    });
  };

  const id = (name: string) => `${idPrefix}-${name}`;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
      <div className="flex flex-col gap-2">
        <Label htmlFor={id("doctor")}>Doctor</Label>
        <Controller
          control={control}
          name="doctor_contact_id"
          render={({ field }) => (
            <Select
              value={field.value || "none"}
              onValueChange={(v) => field.onChange(v === "none" ? "" : v)}
            >
              <SelectTrigger id={id("doctor")} className="w-full">
                <SelectValue placeholder={doctorsLoading ? "Loading..." : "Choose a doctor"} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No doctor / not listed</SelectItem>
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
            No doctors saved yet.{" "}
            <Link href="/appointments?tab=doctors" className="font-medium text-primary hover:underline">
              Add a doctor
            </Link>{" "}
            to link them to visits.
          </p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor={id("date")}>
            Date <span className="text-destructive">*</span>
          </Label>
          <Input
            id={id("date")}
            type="date"
            min={isEditing ? undefined : localTodayIso()}
            aria-invalid={Boolean(errors.appointment_date)}
            aria-describedby={errors.appointment_date ? id("date-error") : undefined}
            {...register("appointment_date")}
          />
          {errors.appointment_date && (
            <p id={id("date-error")} className="text-xs text-destructive">
              {errors.appointment_date.message}
            </p>
          )}
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor={id("time")}>Time</Label>
          <Input id={id("time")} type="time" {...register("appointment_time")} />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor={id("reason")}>Reason for visit</Label>
        <Input
          id={id("reason")}
          placeholder="e.g. Quarterly diabetes review"
          aria-invalid={Boolean(errors.reason)}
          {...register("reason")}
        />
        {errors.reason && <p className="text-xs text-destructive">{errors.reason.message}</p>}
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor={id("notes")}>Notes</Label>
        <Textarea
          id={id("notes")}
          rows={3}
          placeholder="Things to bring or ask, e.g. fasting required, bring last blood test"
          aria-invalid={Boolean(errors.notes)}
          {...register("notes")}
        />
        {errors.notes && <p className="text-xs text-destructive">{errors.notes.message}</p>}
      </div>

      <div className="flex flex-col-reverse gap-2 pt-1 sm:flex-row sm:justify-end">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? <Loader2 className="animate-spin" /> : isEditing ? <Save /> : <CalendarPlus />}
          {isEditing ? "Save changes" : "Add appointment"}
        </Button>
      </div>
    </form>
  );
}
