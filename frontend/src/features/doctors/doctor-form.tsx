"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Save, UserPlus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { doctorService } from "@/services/doctor-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { isValidPhone, PHONE_ERROR, PHONE_MAX_LENGTH } from "@/lib/phone";
import type { DoctorContact, DoctorContactInput } from "@/types/api";

const doctorSchema = z.object({
  name: z.string().trim().min(1, "Enter the doctor's name.").max(200),
  email: z.string().email("Enter a valid email address.").optional().or(z.literal("")),
  phone: z.string().refine(isValidPhone, PHONE_ERROR).optional(),
  specialization: z.string().max(150).optional().or(z.literal("")),
  clinic_name: z.string().max(200).optional().or(z.literal("")),
});

type DoctorFormValues = z.infer<typeof doctorSchema>;

function toFormValues(doctor: DoctorContact | null): DoctorFormValues {
  return {
    name: doctor?.name ?? "",
    email: doctor?.email ?? "",
    phone: doctor?.phone ?? "",
    specialization: doctor?.specialization ?? "",
    clinic_name: doctor?.clinic_name ?? "",
  };
}

/**
 * Add or edit a doctor contact. Used inline on the Appointments tab (step 1)
 * and inside the edit dialog, so there is one form for both.
 */
export function DoctorForm({
  doctor = null,
  onSaved,
  onCancel,
  idPrefix = "doctor",
}: {
  doctor?: DoctorContact | null;
  onSaved?: () => void;
  onCancel?: () => void;
  /** Keeps input ids unique when two forms are on screen. */
  idPrefix?: string;
}) {
  const queryClient = useQueryClient();
  const isEditing = Boolean(doctor);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<DoctorFormValues>({
    resolver: zodResolver(doctorSchema),
    defaultValues: toFormValues(doctor),
  });

  useEffect(() => {
    reset(toFormValues(doctor));
  }, [doctor, reset]);

  const mutation = useMutation({
    mutationFn: (values: DoctorContactInput) =>
      doctor ? doctorService.update(doctor.id, values) : doctorService.create(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["doctors"] });
      toast.success(isEditing ? "Doctor updated." : "Doctor added. You can now add an appointment.");
      if (!isEditing) reset(toFormValues(null));
      onSaved?.();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to save this doctor.")),
  });

  const onSubmit = (values: DoctorFormValues) => {
    mutation.mutate({
      name: values.name,
      email: values.email || null,
      phone: values.phone || null,
      specialization: values.specialization || null,
      clinic_name: values.clinic_name || null,
    });
  };

  const id = (name: string) => `${idPrefix}-${name}`;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
      <div className="flex flex-col gap-2">
        <Label htmlFor={id("name")}>
          Name <span className="text-destructive">*</span>
        </Label>
        <Input
          id={id("name")}
          placeholder="e.g. Dr. Asha Rao"
          autoComplete="off"
          aria-invalid={Boolean(errors.name)}
          {...register("name")}
        />
        {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor={id("specialization")}>Specialization</Label>
          <Input id={id("specialization")} placeholder="e.g. Cardiology" {...register("specialization")} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor={id("clinic")}>Clinic / hospital</Label>
          <Input id={id("clinic")} {...register("clinic_name")} />
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor={id("email")}>Email</Label>
          <Input id={id("email")} type="email" aria-invalid={Boolean(errors.email)} {...register("email")} />
          {errors.email ? (
            <p className="text-xs text-destructive">{errors.email.message}</p>
          ) : (
            <p className="text-xs text-muted-foreground">Needed to email reports to this doctor.</p>
          )}
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor={id("phone")}>Phone</Label>
          <Input
            id={id("phone")}
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            maxLength={PHONE_MAX_LENGTH}
            placeholder="+977 9812345678"
            aria-invalid={Boolean(errors.phone)}
            {...register("phone")}
          />
          {errors.phone && <p className="text-xs text-destructive">{errors.phone.message}</p>}
        </div>
      </div>
      <div className="flex flex-col-reverse gap-2 pt-1 sm:flex-row sm:justify-end">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? <Loader2 className="animate-spin" /> : isEditing ? <Save /> : <UserPlus />}
          {isEditing ? "Save changes" : "Add doctor"}
        </Button>
      </div>
    </form>
  );
}
