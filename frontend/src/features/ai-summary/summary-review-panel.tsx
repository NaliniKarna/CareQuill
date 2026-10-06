"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Loader2, Save, Send } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { aiSummaryService } from "@/services/ai-summary-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { AISummary } from "@/types/api";

const editSchema = z.object({ text: z.string().min(1, "Summary text can't be empty") });
type EditFormValues = z.infer<typeof editSchema>;

export function SummaryReviewPanel({
  summary,
  onShare,
}: {
  summary: AISummary;
  onShare: () => void;
}) {
  const queryClient = useQueryClient();
  const currentText = summary.edited_summary_text ?? summary.summary_text;

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<EditFormValues>({
    resolver: zodResolver(editSchema),
    defaultValues: { text: currentText },
  });

  useEffect(() => {
    reset({ text: currentText });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [summary.id, currentText]);

  const isEditable = summary.status === "pending_review" || summary.status === "reviewed";
  const isConfirmable = summary.status === "pending_review" || summary.status === "reviewed";
  const isShareable = summary.status === "reviewed" || summary.status === "shared";

  const saveEditMutation = useMutation({
    mutationFn: (text: string) => aiSummaryService.saveEdit(summary.id, text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-summaries"] });
      toast.success("Edit saved.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to save your edit.")),
  });

  const confirmMutation = useMutation({
    mutationFn: () => aiSummaryService.confirm(summary.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-summaries"] });
      toast.success("Summary approved. You can now share it with a doctor.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to confirm this Record Summary.")),
  });

  const stepIndex = summary.status === "shared" ? 2 : summary.status === "reviewed" ? 1 : 0;

  return (
    <Card>
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>Your summary</CardTitle>
          <span className="text-xs text-muted-foreground">
            Created {new Date(summary.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
          </span>
        </div>
        <ol className="flex items-center gap-2 text-xs font-medium" aria-label="Progress">
          {["Draft", "Reviewed", "Shared"].map((label, i) => (
            <li key={label} className="flex items-center gap-2">
              <span
                className={cn(
                  "flex items-center gap-1.5 rounded-full px-2.5 py-1",
                  i <= stepIndex ? "bg-accent text-accent-foreground" : "bg-muted text-muted-foreground",
                )}
              >
                {i < stepIndex ? <CheckCircle2 className="size-3.5" /> : <span className="tabular-nums">{i + 1}</span>}
                {label}
              </span>
              {i < 2 && <span className="h-px w-4 bg-border" aria-hidden />}
            </li>
          ))}
        </ol>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <p className="flex items-start gap-2 rounded-lg bg-warning/10 px-3 py-2 text-xs text-warning-foreground">
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
          Written by AI from your records. Read it, fix anything that is wrong, then approve it.
        </p>

        <form
          onSubmit={handleSubmit((values) => saveEditMutation.mutate(values.text))}
          className="flex flex-col gap-3"
          noValidate
        >
          <Textarea
            rows={14}
            disabled={!isEditable}
            aria-label="Summary text"
            aria-invalid={Boolean(errors.text)}
            className="min-h-64 text-sm leading-relaxed"
            {...register("text")}
          />
          {errors.text && <p className="text-sm text-destructive">{errors.text.message}</p>}
          {isEditable && (
            <Button
              type="submit"
              variant="ghost"
              size="sm"
              className="self-start"
              disabled={!isDirty || saveEditMutation.isPending}
            >
              {saveEditMutation.isPending ? <Loader2 className="animate-spin" /> : <Save />}
              Save changes
            </Button>
          )}
        </form>

        <div className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-muted-foreground">
            {summary.status === "shared"
              ? "This summary has already been shared."
              : summary.status === "reviewed"
                ? "Approved. You can share it with a doctor."
                : "Approve it to unlock sharing."}
          </p>
          <div className="flex gap-2">
            {isConfirmable && summary.status === "pending_review" && (
              <Button disabled={confirmMutation.isPending} onClick={() => confirmMutation.mutate()}>
                {confirmMutation.isPending ? <Loader2 className="animate-spin" /> : <CheckCircle2 />}
                Approve summary
              </Button>
            )}
            <Button variant={summary.status === "pending_review" ? "outline" : "default"} disabled={!isShareable} onClick={onShare}>
              <Send /> Share
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
