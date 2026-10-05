"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarClock,
  FileStack,
  HeartPulse,
  History,
  NotebookPen,
  Pill,
  Sparkles,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState, ErrorState, ListSkeleton, PageHeader } from "@/components/shared/page-states";
import { timelineService } from "@/services/timeline-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { TimelineEntry, TimelineEntryType, TimelineTag } from "@/types/api";

import { AddNoteForm } from "./add-note-form";

const TYPE_ICON: Record<TimelineEntryType, React.ElementType> = {
  condition: HeartPulse,
  medication: Pill,
  document: FileStack,
  appointment: CalendarClock,
  note: NotebookPen,
  ai_extracted: Sparkles,
};

const TAG_VARIANT: Record<TimelineTag, "success" | "info" | "warning" | "secondary"> = {
  VERIFIED: "success",
  PATIENT_PROVIDED: "info",
  AI_EXTRACTED: "warning",
  UNVERIFIED: "secondary",
};

const TAG_LABEL: Record<TimelineTag, string> = {
  VERIFIED: "Verified",
  PATIENT_PROVIDED: "Patient-provided",
  AI_EXTRACTED: "AI-extracted",
  UNVERIFIED: "Unverified",
};

const TYPE_OPTIONS: { value: TimelineEntryType; label: string }[] = [
  { value: "condition", label: "Conditions" },
  { value: "medication", label: "Medications" },
  { value: "document", label: "Documents" },
  { value: "appointment", label: "Appointments" },
  { value: "note", label: "Notes" },
  { value: "ai_extracted", label: "AI-extracted" },
];

export function TimelineView() {
  const queryClient = useQueryClient();
  const [type, setType] = useState<string>("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [deletingNote, setDeletingNote] = useState<TimelineEntry | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["timeline", type, dateFrom, dateTo],
    queryFn: () =>
      timelineService.get({
        type: type === "all" ? undefined : type,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }),
  });

  const deleteNoteMutation = useMutation({
    mutationFn: (id: string) => timelineService.deleteNote(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      toast.success("Note removed.");
      setDeletingNote(null);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to remove this note.")),
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Health timeline"
        description="A chronological view of everything in your health record."
      />

      <AddNoteForm />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Select value={type} onValueChange={setType}>
          <SelectTrigger className="sm:w-56">
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {TYPE_OPTIONS.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex items-center gap-2">
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="sm:w-44" />
          <span className="text-sm text-muted-foreground">to</span>
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="sm:w-44" />
        </div>
        {(dateFrom || dateTo || type !== "all") && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setType("all");
              setDateFrom("");
              setDateTo("");
            }}
          >
            Clear filters
          </Button>
        )}
      </div>

      {isLoading && <ListSkeleton />}
      {isError && <ErrorState description="Couldn't load your timeline." onRetry={() => refetch()} />}

      {data && data.length === 0 && (
        <EmptyState
          icon={History}
          title="Nothing here yet"
          description="Entries from your conditions, medications, documents, appointments, and notes will appear here as you add them."
        />
      )}

      {data && data.length > 0 && (
        <div className="flex flex-col gap-3">
          {data.map((entry, i) => {
            const Icon = TYPE_ICON[entry.type];
            return (
              <Card key={`${entry.type}-${entry.source_id}-${i}`}>
                <CardContent className="flex items-start gap-4">
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-accent text-accent-foreground">
                    <Icon className="size-4" />
                  </div>
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium">{entry.title}</p>
                      <Badge variant={TAG_VARIANT[entry.tag]}>{TAG_LABEL[entry.tag]}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{entry.date}</p>
                    {entry.detail && <p className="text-sm text-muted-foreground">{entry.detail}</p>}
                  </div>
                  {entry.type === "note" && (
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Delete note"
                      onClick={() => setDeletingNote(entry)}
                    >
                      <Trash2 className="size-4 text-destructive" />
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <ConfirmDialog
        open={Boolean(deletingNote)}
        onOpenChange={(open) => !open && setDeletingNote(null)}
        title="Remove this note?"
        description="This will permanently remove this note from your timeline. This cannot be undone."
        confirmLabel="Remove"
        isLoading={deleteNoteMutation.isPending}
        onConfirm={() => deletingNote && deleteNoteMutation.mutate(deletingNote.source_id)}
      />
    </div>
  );
}
