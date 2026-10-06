"use client";

import { useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookHeart, Lock, NotebookPen, Pencil, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState, ErrorState, ListSkeleton, PageHeader } from "@/components/shared/page-states";
import { journalService } from "@/services/journal-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { JournalEntry } from "@/types/api";

import { JournalEntryForm } from "./journal-entry-form";
import { moodFor } from "./mood";

const PAGE_SIZE = 20;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const RANGES = [
  { value: "all", label: "All time", days: null },
  { value: "7", label: "Last 7 days", days: 7 },
  { value: "30", label: "Last 30 days", days: 30 },
  { value: "90", label: "Last 3 months", days: 90 },
] as const;

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

function monthKey(iso: string): string {
  const [y, m] = iso.split("-");
  return `${["January","February","March","April","May","June","July","August","September","October","November","December"][Number(m) - 1]} ${y}`;
}

function EntryCard({
  entry,
  onEdit,
  onDelete,
}: {
  entry: JournalEntry;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const mood = moodFor(entry.mood);
  const [, month, day] = entry.entry_date.split("-");
  const long = entry.body.length > 280 || entry.body.split("\n").length > 4;

  return (
    <Card>
      <CardContent className="flex gap-4">
        <div className="flex size-14 shrink-0 flex-col items-center justify-center rounded-xl bg-accent text-accent-foreground">
          <span className="text-[0.65rem] font-semibold tracking-wide uppercase">
            {MONTHS[Number(month) - 1]}
          </span>
          <span className="text-xl leading-none font-semibold">{Number(day)}</span>
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="flex min-w-0 items-center gap-2">
              {mood && (
                <span title={`Mood: ${mood.label}`} className="shrink-0">
                  <mood.icon className={cn("size-5", mood.tone)} aria-label={`Mood: ${mood.label}`} />
                </span>
              )}
              <p className="truncate font-medium">{entry.title || "Journal entry"}</p>
            </div>
            <div className="flex shrink-0 gap-0.5">
              <Button variant="ghost" size="icon" className="size-8" aria-label="Edit entry" onClick={onEdit}>
                <Pencil className="size-4" />
              </Button>
              <Button variant="ghost" size="icon" className="size-8" aria-label="Delete entry" onClick={onDelete}>
                <Trash2 className="size-4 text-destructive" />
              </Button>
            </div>
          </div>
          <p
            className={cn(
              "mt-1 text-sm leading-relaxed whitespace-pre-wrap text-muted-foreground",
              !expanded && "line-clamp-4",
            )}
          >
            {entry.body}
          </p>
          {long && (
            <button
              type="button"
              onClick={() => setExpanded((e) => !e)}
              className="mt-1 text-xs font-medium text-primary hover:underline"
            >
              {expanded ? "Show less" : "Read more"}
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function JournalView() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [range, setRange] = useState<string>("all");
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [editing, setEditing] = useState<JournalEntry | null>(null);
  const [deleting, setDeleting] = useState<JournalEntry | null>(null);

  const days = RANGES.find((r) => r.value === range)?.days ?? null;
  const filtered = Boolean(search.trim()) || days !== null;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["journal", search.trim(), range, limit],
    queryFn: () =>
      journalService.list({
        q: search.trim() || undefined,
        date_from: days !== null ? isoDaysAgo(days) : undefined,
        limit,
      }),
    placeholderData: keepPreviousData,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => journalService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journal"] });
      toast.success("Entry deleted.");
      setDeleting(null);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to delete this entry.")),
  });

  const items = data?.items ?? [];
  const groups: { month: string; entries: JournalEntry[] }[] = [];
  for (const entry of items) {
    const key = monthKey(entry.entry_date);
    const last = groups[groups.length - 1];
    if (last && last.month === key) last.entries.push(entry);
    else groups.push({ month: key, entries: [entry] });
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Journal"
        description="A private place to note how you feel each day. Helpful to look back on before a doctor's visit."
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <NotebookPen className="size-4" />
            </span>
            New entry
          </CardTitle>
          <CardDescription className="flex items-center gap-1.5">
            <Lock className="size-3.5" /> Only you can see your journal. It is never shared with
            doctors or used by AI.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <JournalEntryForm />
        </CardContent>
      </Card>

      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-lg font-semibold tracking-tight">
            Your entries
            {data && <span className="ml-2 text-sm font-normal text-muted-foreground">{data.total}</span>}
          </h2>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative sm:w-64">
              <Search className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                aria-label="Search journal"
                placeholder="Search entries..."
                className="pl-8"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setLimit(PAGE_SIZE);
                }}
              />
            </div>
            <Select
              value={range}
              onValueChange={(v) => {
                setRange(v);
                setLimit(PAGE_SIZE);
              }}
            >
              <SelectTrigger aria-label="Date range" className="sm:w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RANGES.map((r) => (
                  <SelectItem key={r.value} value={r.value}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {isLoading && <ListSkeleton />}
        {isError && <ErrorState description="Couldn't load your journal." onRetry={() => refetch()} />}

        {data && items.length === 0 && (
          <EmptyState
            icon={BookHeart}
            title={filtered ? "No matching entries" : "Your journal is empty"}
            description={
              filtered
                ? "Try a different search or date range."
                : "Write your first entry above. Even a line a day builds a useful picture."
            }
          />
        )}

        {groups.map((group) => (
          <section key={group.month} className="flex flex-col gap-3" aria-label={group.month}>
            <h3 className="text-sm font-medium text-muted-foreground">{group.month}</h3>
            {group.entries.map((entry) => (
              <EntryCard
                key={entry.id}
                entry={entry}
                onEdit={() => setEditing(entry)}
                onDelete={() => setDeleting(entry)}
              />
            ))}
          </section>
        ))}

        {data && data.total > items.length && (
          <Button variant="outline" className="self-center" onClick={() => setLimit((l) => l + PAGE_SIZE)}>
            Show older entries
          </Button>
        )}
      </div>

      <Dialog open={Boolean(editing)} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Edit entry</DialogTitle>
          </DialogHeader>
          <JournalEntryForm entry={editing} submitLabel="Save changes" onSaved={() => setEditing(null)} />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Delete this entry?"
        description="This permanently removes the journal entry. This cannot be undone."
        confirmLabel="Delete"
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
      />
    </div>
  );
}
