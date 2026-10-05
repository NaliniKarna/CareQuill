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
import { conditionService } from "@/services/condition-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { MedicalCondition, MedicalConditionInput } from "@/types/api";

const conditionSchema = z.object({
  name: z.string().min(1, "Name is required").max(200),
  diagnosed_date: z.string().optional().or(z.literal("")),
  status: z.enum(["active", "managed", "resolved", ""]).optional(),
  notes: z.string().optional().or(z.literal("")),
});

type ConditionFormValues = z.infer<typeof conditionSchema>;

function toFormValues(condition: MedicalCondition | null): ConditionFormValues {
  return {
    name: condition?.name ?? "",
    diagnosed_date: condition?.diagnosed_date ?? "",
    status: condition?.status ?? "",
    notes: condition?.notes ?? "",
  };
}

export function ConditionFormDialog({
  open,
  onOpenChange,
  condition,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  condition: MedicalCondition | null;
}) {
  const queryClient = useQueryClient();
  const isEditing = Boolean(condition);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ConditionFormValues>({
    resolver: zodResolver(conditionSchema),
    defaultValues: toFormValues(null),
  });

  useEffect(() => {
    if (open) reset(toFormValues(condition));
  }, [open, condition, reset]);

  const mutation = useMutation({
    mutationFn: (values: MedicalConditionInput) =>
      condition
        ? conditionService.update(condition.id, values)
        : conditionService.create(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conditions"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      toast.success(isEditing ? "Condition updated." : "Condition added.");
      onOpenChange(false);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to save this condition.")),
  });

  const onSubmit = (values: ConditionFormValues) => {
    mutation.mutate({
      name: values.name,
      diagnosed_date: values.diagnosed_date || null,
      status: values.status || null,
      notes: values.notes || null,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit condition" : "Add condition"}</DialogTitle>
          <DialogDescription>Track a diagnosed or ongoing medical condition.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-2">
            <Label htmlFor="condition-name">Condition</Label>
            <Input
              id="condition-name"
              placeholder="e.g. Type 2 diabetes"
              aria-invalid={Boolean(errors.name)}
              {...register("name")}
            />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="condition-date">Diagnosed date</Label>
              <Input id="condition-date" type="date" {...register("diagnosed_date")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="condition-status">Status</Label>
              <Controller
                control={control}
                name="status"
                render={({ field }) => (
                  <Select value={field.value || "none"} onValueChange={(v) => field.onChange(v === "none" ? "" : v)}>
                    <SelectTrigger id="condition-status">
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Unspecified</SelectItem>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="managed">Managed</SelectItem>
                      <SelectItem value="resolved">Resolved</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="condition-notes">Notes</Label>
            <Textarea id="condition-notes" rows={3} {...register("notes")} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <Loader2 className="animate-spin" />}
              {isEditing ? "Save changes" : "Add condition"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
