"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { timelineService } from "@/services/timeline-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { TimelineNoteInput } from "@/types/api";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

const noteSchema = z.object({
  note_text: z.string().min(1, "Please enter a note"),
  event_date: z.string().min(1, "Date is required"),
});

type NoteFormValues = z.infer<typeof noteSchema>;

export function AddNoteForm() {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<NoteFormValues>({
    resolver: zodResolver(noteSchema),
    defaultValues: { note_text: "", event_date: todayIso() },
  });

  const mutation = useMutation({
    mutationFn: (values: TimelineNoteInput) => timelineService.createNote(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      toast.success("Note added to your timeline.");
      reset({ note_text: "", event_date: todayIso() });
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to add this note.")),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Add a note</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
          noValidate
        >
          <div className="flex flex-1 flex-col gap-2">
            <Label htmlFor="note-text">What happened?</Label>
            <Textarea
              id="note-text"
              rows={2}
              placeholder="e.g. Felt dizzy after morning walk"
              aria-invalid={Boolean(errors.note_text)}
              {...register("note_text")}
            />
            {errors.note_text && <p className="text-sm text-destructive">{errors.note_text.message}</p>}
          </div>
          <div className="flex flex-col gap-2 sm:w-44">
            <Label htmlFor="note-date">Date</Label>
            <Input id="note-date" type="date" {...register("event_date")} />
          </div>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? <Loader2 className="animate-spin" /> : <Plus />}
            Add note
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
