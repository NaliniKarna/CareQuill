"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { doctorService } from "@/services/doctor-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { DoctorContact, DoctorContactInput } from "@/types/api";

const doctorSchema = z.object({
  name: z.string().min(1, "Name is required").max(200),
  email: z.string().email("Enter a valid email").optional().or(z.literal("")),
  phone: z.string().max(30).optional().or(z.literal("")),
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

export function DoctorFormDialog({
  open,
  onOpenChange,
  doctor,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  doctor: DoctorContact | null;
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
    defaultValues: toFormValues(null),
  });

  useEffect(() => {
    if (open) reset(toFormValues(doctor));
  }, [open, doctor, reset]);

  const mutation = useMutation({
    mutationFn: (values: DoctorContactInput) =>
      doctor ? doctorService.update(doctor.id, values) : doctorService.create(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["doctors"] });
      toast.success(isEditing ? "Doctor updated." : "Doctor added.");
      onOpenChange(false);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to save this contact.")),
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit doctor contact" : "Add doctor contact"}</DialogTitle>
          <DialogDescription>Doctors here can be selected when booking appointments or sharing summaries.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-2">
            <Label htmlFor="doctor-name">Name</Label>
            <Input
              id="doctor-name"
              placeholder="e.g. Dr. Asha Rao"
              aria-invalid={Boolean(errors.name)}
              {...register("name")}
            />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="doctor-email">Email</Label>
              <Input
                id="doctor-email"
                type="email"
                aria-invalid={Boolean(errors.email)}
                {...register("email")}
              />
              {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="doctor-phone">Phone</Label>
              <Input id="doctor-phone" type="tel" {...register("phone")} />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="doctor-specialization">Specialization</Label>
              <Input id="doctor-specialization" placeholder="e.g. Cardiology" {...register("specialization")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="doctor-clinic">Clinic / hospital</Label>
              <Input id="doctor-clinic" {...register("clinic_name")} />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <Loader2 className="animate-spin" />}
              {isEditing ? "Save changes" : "Add contact"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
