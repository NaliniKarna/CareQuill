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
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { medicationService } from "@/services/medication-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { Medication, MedicationInput } from "@/types/api";

const medicationSchema = z
  .object({
    name: z.string().min(1, "Name is required").max(200),
    dosage: z.string().max(100).optional().or(z.literal("")),
    frequency: z.string().max(100).optional().or(z.literal("")),
    instructions: z.string().optional().or(z.literal("")),
    start_date: z.string().optional().or(z.literal("")),
    end_date: z.string().optional().or(z.literal("")),
    notes: z.string().optional().or(z.literal("")),
  })
  .refine((v) => !v.start_date || !v.end_date || v.end_date >= v.start_date, {
    message: "End date must be on or after the start date.",
    path: ["end_date"],
  });

type MedicationFormValues = z.infer<typeof medicationSchema>;

/** Values pre-filled from an AI/OCR suggestion. The patient still reviews and
 * saves the form themselves -- nothing is created automatically. */
export type MedicationPrefill = { name?: string; dosage?: string; frequency?: string };

function toFormValues(
  medication: Medication | null,
  prefill?: MedicationPrefill
): MedicationFormValues {
  return {
    name: medication?.name ?? prefill?.name ?? "",
    dosage: medication?.dosage ?? prefill?.dosage ?? "",
    frequency: medication?.frequency ?? prefill?.frequency ?? "",
    instructions: medication?.instructions ?? "",
    start_date: medication?.start_date ?? "",
    end_date: medication?.end_date ?? "",
    notes: medication?.notes ?? "",
  };
}

export function MedicationFormDialog({
  open,
  onOpenChange,
  medication,
  prefill,
  sourceDocumentId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  medication: Medication | null;
  prefill?: MedicationPrefill;
  sourceDocumentId?: string;
}) {
  const queryClient = useQueryClient();
  const isEditing = Boolean(medication);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<MedicationFormValues>({
    resolver: zodResolver(medicationSchema),
    defaultValues: toFormValues(null),
  });

  useEffect(() => {
    if (open) reset(toFormValues(medication, prefill));
  }, [open, medication, prefill, reset]);

  const mutation = useMutation({
    mutationFn: (values: MedicationInput) =>
      medication
        ? medicationService.update(medication.id, values)
        : medicationService.create({
            ...values,
            ...(sourceDocumentId ? { source_document_id: sourceDocumentId } : {}),
          }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["medications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      toast.success(isEditing ? "Medication updated." : "Medication added.");
      onOpenChange(false);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to save this medication.")),
  });

  const onSubmit = (values: MedicationFormValues) => {
    mutation.mutate({
      name: values.name,
      dosage: values.dosage || null,
      frequency: values.frequency || null,
      instructions: values.instructions || null,
      start_date: values.start_date || null,
      end_date: values.end_date || null,
      notes: values.notes || null,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit medication" : "Add medication"}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? "Update the details of this medication."
              : "New medications are added as active. You can add reminders once it's saved."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-2">
            <Label htmlFor="med-name">Name</Label>
            <Input
              id="med-name"
              placeholder="e.g. Metformin"
              aria-invalid={Boolean(errors.name)}
              {...register("name")}
            />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="med-dosage">Dosage</Label>
              <Input id="med-dosage" placeholder="e.g. 500mg" {...register("dosage")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="med-frequency">Frequency</Label>
              <Input id="med-frequency" placeholder="e.g. Twice daily" {...register("frequency")} />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="med-instructions">Instructions</Label>
            <Textarea id="med-instructions" rows={2} placeholder="e.g. Take with food" {...register("instructions")} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="med-start">Start date</Label>
              <Input id="med-start" type="date" {...register("start_date")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="med-end">End date</Label>
              <Input id="med-end" type="date" aria-invalid={Boolean(errors.end_date)} {...register("end_date")} />
              {errors.end_date && <p className="text-sm text-destructive">{errors.end_date.message}</p>}
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="med-notes">Notes</Label>
            <Textarea id="med-notes" rows={2} {...register("notes")} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <Loader2 className="animate-spin" />}
              {isEditing ? "Save changes" : "Add medication"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
