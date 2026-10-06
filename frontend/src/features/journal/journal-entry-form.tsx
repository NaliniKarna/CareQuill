"use client";

import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { journalService } from "@/services/journal-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { JournalEntry } from "@/types/api";

import { localTodayIso, MOODS } from "./mood";

const schema = z.object({
  entry_date: z.string().min(1, "Choose a date"),
  mood: z.number().int().min(1).max(5).nullable(),
  title: z.string().max(200, "Keep the title under 200 characters").optional(),
  body: z
    .string()
    .trim()
    .min(1, "Write something before saving")
    .max(10_000, "That is too long - keep it under 10,000 characters"),
});
type FormValues = z.infer<typeof schema>;

function toValues(entry: JournalEntry | null): FormValues {
  return {
    entry_date: entry?.entry_date ?? localTodayIso(),
    mood: entry?.mood ?? null,
    title: entry?.title ?? "",
    body: entry?.body ?? "",
  };
}

export function JournalEntryForm({
  entry = null,
  onSaved,
  submitLabel = "Save entry",
}: {
  entry?: JournalEntry | null;
  onSaved?: () => void;
  submitLabel?: string;
}) {
  const queryClient = useQueryClient();
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: toValues(entry) });

  useEffect(() => reset(toValues(entry)), [entry, reset]);

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      const payload = {
        entry_date: values.entry_date,
        mood: values.mood,
        title: values.title?.trim() || null,
        body: values.body,
      };
      return entry ? journalService.update(entry.id, payload) : journalService.create(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journal"] });
      toast.success(entry ? "Entry updated." : "Saved to your journal.");
      if (!entry) reset(toValues(null));
      onSaved?.();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to save this entry.")),
  });

  return (
    <form
      onSubmit={handleSubmit((values) => mutation.mutate(values))}
      className="flex flex-col gap-5"
      noValidate
    >
      <div className="flex flex-col gap-2">
        <Label id="mood-label">How are you feeling?</Label>
        <Controller
          control={control}
          name="mood"
          render={({ field }) => (
            <div role="radiogroup" aria-labelledby="mood-label" className="grid grid-cols-5 gap-2">
              {MOODS.map((m) => {
                const selected = field.value === m.value;
                return (
                  <button
                    key={m.value}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    onClick={() => field.onChange(selected ? null : m.value)}
                    className={cn(
                      "flex flex-col items-center gap-1 rounded-xl border px-1 py-2.5 text-xs transition-colors",
                      "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                      selected
                        ? "border-primary bg-accent font-medium"
                        : "border-border bg-card text-muted-foreground hover:bg-muted",
                    )}
                  >
                    <m.icon className={cn("size-6", selected ? m.tone : "")} />
                    {m.label}
                  </button>
                );
              })}
            </div>
          )}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-[11rem_minmax(0,1fr)]">
        <div className="flex flex-col gap-2">
          <Label htmlFor="journal-date">Date</Label>
          <Input
            id="journal-date"
            type="date"
            max={localTodayIso()}
            aria-invalid={Boolean(errors.entry_date)}
            {...register("entry_date")}
          />
          {errors.entry_date && <p className="text-sm text-destructive">{errors.entry_date.message}</p>}
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="journal-title">Title (optional)</Label>
          <Input
            id="journal-title"
            placeholder="e.g. Morning walk, slept badly"
            aria-invalid={Boolean(errors.title)}
            {...register("title")}
          />
          {errors.title && <p className="text-sm text-destructive">{errors.title.message}</p>}
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="journal-body">What is on your mind today?</Label>
        <Textarea
          id="journal-body"
          rows={6}
          className="leading-relaxed"
          placeholder="Symptoms, sleep, meals, mood, questions for your doctor - write whatever helps."
          aria-invalid={Boolean(errors.body)}
          {...register("body")}
        />
        {errors.body && <p className="text-sm text-destructive">{errors.body.message}</p>}
      </div>

      <Button type="submit" className="self-start" disabled={mutation.isPending}>
        {mutation.isPending ? <Loader2 className="animate-spin" /> : <Save />}
        {submitLabel}
      </Button>
    </form>
  );
}
