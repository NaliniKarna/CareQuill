"use client";

import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { familyService } from "@/services/family-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { localTodayIso } from "@/lib/utils";
import type { FamilyMember, FamilyRelation } from "@/types/api";

import { BLOOD_GROUPS, RELATIONS } from "./family-constants";

const schema = z.object({
  full_name: z.string().trim().min(1, "Name is required").max(150),
  relation: z.string().min(1, "Choose how they are related to you"),
  date_of_birth: z
    .string()
    .optional()
    .refine((v) => !v || v <= localTodayIso(), "Date of birth can't be in the future"),
  blood_group: z.string().optional(),
  notes: z.string().max(2000, "Keep notes under 2000 characters").optional(),
});

type Values = z.infer<typeof schema>;

/** Add a family member, or edit one the patient still manages. The form is
 * mounted only while open, so each opening starts from fresh values. */
export function MemberFormDialog({
  open,
  onOpenChange,
  member,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  member?: FamilyMember | null;
  onSaved?: (member: FamilyMember) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {open && <MemberForm member={member ?? null} onClose={() => onOpenChange(false)} onSaved={onSaved} />}
      </DialogContent>
    </Dialog>
  );
}

function MemberForm({
  member,
  onClose,
  onSaved,
}: {
  member: FamilyMember | null;
  onClose: () => void;
  onSaved?: (member: FamilyMember) => void;
}) {
  const queryClient = useQueryClient();
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      full_name: member?.full_name ?? "",
      relation: member?.relation ?? "",
      date_of_birth: member?.date_of_birth ?? "",
      blood_group: member?.blood_group ?? "",
      notes: member?.notes ?? "",
    },
  });

  const mutation = useMutation({
    mutationFn: (values: Values) => {
      const payload = {
        full_name: values.full_name.trim(),
        relation: values.relation as FamilyRelation,
        date_of_birth: values.date_of_birth || null,
        blood_group: values.blood_group || null,
        notes: values.notes?.trim() || null,
      };
      return member ? familyService.updateMember(member.id, payload) : familyService.createMember(payload);
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["family"] });
      toast.success(member ? "Profile updated." : "Family member added.");
      onSaved?.(saved);
      onClose();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to save this profile.")),
  });

  return (
    <>
      <DialogHeader>
        <DialogTitle>{member ? "Edit profile" : "Add family member"}</DialogTitle>
        <DialogDescription>
          Basic details help doctors identify the right person. You can add their documents next.
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="flex flex-col gap-4" noValidate>
        <div className="flex flex-col gap-2">
          <Label htmlFor="fm-name">Full name</Label>
          <Input id="fm-name" autoComplete="off" aria-invalid={Boolean(errors.full_name)} {...register("full_name")} />
          {errors.full_name && <p className="text-sm text-destructive">{errors.full_name.message}</p>}
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-2">
            <Label htmlFor="fm-relation">Relation to you</Label>
            <Controller
              control={control}
              name="relation"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="fm-relation" aria-invalid={Boolean(errors.relation)}>
                    <SelectValue placeholder="Select relation" />
                  </SelectTrigger>
                  <SelectContent>
                    {RELATIONS.map((r) => (
                      <SelectItem key={r.value} value={r.value}>
                        {r.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.relation && <p className="text-sm text-destructive">{errors.relation.message}</p>}
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="fm-dob">Date of birth</Label>
            <Input id="fm-dob" type="date" max={localTodayIso()} {...register("date_of_birth")} />
            {errors.date_of_birth && <p className="text-sm text-destructive">{errors.date_of_birth.message}</p>}
          </div>
        </div>
        <div className="flex flex-col gap-2 sm:max-w-[50%]">
          <Label htmlFor="fm-blood">Blood group</Label>
          <Controller
            control={control}
            name="blood_group"
            render={({ field }) => (
              <Select value={field.value || "none"} onValueChange={(v) => field.onChange(v === "none" ? "" : v)}>
                <SelectTrigger id="fm-blood">
                  <SelectValue placeholder="Not set" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Not set</SelectItem>
                  {BLOOD_GROUPS.map((g) => (
                    <SelectItem key={g} value={g}>
                      {g}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="fm-notes">Notes (optional)</Label>
          <Textarea id="fm-notes" rows={3} placeholder="Anything useful to remember" {...register("notes")} />
          {errors.notes && <p className="text-sm text-destructive">{errors.notes.message}</p>}
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            {member ? "Save changes" : "Add family member"}
          </Button>
        </DialogFooter>
      </form>
    </>
  );
}
