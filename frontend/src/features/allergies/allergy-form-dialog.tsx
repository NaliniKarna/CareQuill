"use client";

import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { allergyService } from "@/services/allergy-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { Allergy, AllergyInput } from "@/types/api";

const allergySchema = z.object({
  name: z.string().min(1, "Name is required").max(200),
  severity: z.enum(["mild", "moderate", "severe", ""]).optional(),
  reaction: z.string().max(500).optional().or(z.literal("")),
  notes: z.string().optional().or(z.literal("")),
});

type AllergyFormValues = z.infer<typeof allergySchema>;

function toFormValues(allergy: Allergy | null): AllergyFormValues {
  return {
    name: allergy?.name ?? "",
    severity: allergy?.severity ?? "",
    reaction: allergy?.reaction ?? "",
    notes: allergy?.notes ?? "",
  };
}

export function AllergyFormDialog({
  open,
  onOpenChange,
  allergy,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  allergy: Allergy | null;
}) {
  const queryClient = useQueryClient();
  const isEditing = Boolean(allergy);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AllergyFormValues>({
    resolver: zodResolver(allergySchema),
    defaultValues: toFormValues(null),
  });

  useEffect(() => {
    if (open) reset(toFormValues(allergy));
  }, [open, allergy, reset]);

  const mutation = useMutation({
    mutationFn: (values: AllergyInput) =>
      allergy ? allergyService.update(allergy.id, values) : allergyService.create(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["allergies"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      toast.success(isEditing ? "Allergy updated." : "Allergy added.");
      onOpenChange(false);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to save this allergy.")),
  });

  const onSubmit = (values: AllergyFormValues) => {
    mutation.mutate({
      name: values.name,
      severity: values.severity || null,
      reaction: values.reaction || null,
      notes: values.notes || null,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit allergy" : "Add allergy"}</DialogTitle>
          <DialogDescription>
            Record substances you react to so your care team can be aware.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-2">
            <Label htmlFor="allergy-name">Allergen</Label>
            <Input
              id="allergy-name"
              placeholder="e.g. Penicillin"
              aria-invalid={Boolean(errors.name)}
              {...register("name")}
            />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="allergy-severity">Severity</Label>
            <Controller
              control={control}
              name="severity"
              render={({ field }) => (
                <Select value={field.value || "none"} onValueChange={(v) => field.onChange(v === "none" ? "" : v)}>
                  <SelectTrigger id="allergy-severity">
                    <SelectValue placeholder="Select severity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Unspecified</SelectItem>
                    <SelectItem value="mild">Mild</SelectItem>
                    <SelectItem value="moderate">Moderate</SelectItem>
                    <SelectItem value="severe">Severe</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="allergy-reaction">Reaction</Label>
            <Input id="allergy-reaction" placeholder="e.g. Hives, swelling" {...register("reaction")} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="allergy-notes">Notes</Label>
            <Textarea id="allergy-notes" rows={3} {...register("notes")} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <Loader2 className="animate-spin" />}
              {isEditing ? "Save changes" : "Add allergy"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
