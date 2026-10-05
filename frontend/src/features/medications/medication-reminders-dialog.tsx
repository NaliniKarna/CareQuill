"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlarmClock, Loader2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { getApiErrorMessage } from "@/lib/api-client";
import { medicationService } from "@/services/medication-service";
import type { Medication, MedicationReminder } from "@/types/api";

const DAY_OPTIONS: { code: string; label: string }[] = [
  { code: "mon", label: "M" },
  { code: "tue", label: "T" },
  { code: "wed", label: "W" },
  { code: "thu", label: "T" },
  { code: "fri", label: "F" },
  { code: "sat", label: "S" },
  { code: "sun", label: "S" },
];

function formatDays(days: string): string {
  if (days === "daily") return "Daily";
  return days
    .split(",")
    .map((d) => d[0].toUpperCase() + d.slice(1))
    .join(", ");
}

function ReminderRow({
  medicationId,
  reminder,
  onDeleted,
}: {
  medicationId: string;
  reminder: MedicationReminder;
  onDeleted: () => void;
}) {
  const queryClient = useQueryClient();

  const toggleMutation = useMutation({
    mutationFn: (is_enabled: boolean) =>
      medicationService.updateReminder(medicationId, reminder.id, { is_enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["medication-reminders", medicationId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to update this reminder.")),
  });

  const deleteMutation = useMutation({
    mutationFn: () => medicationService.deleteReminder(medicationId, reminder.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["medication-reminders", medicationId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Reminder removed.");
      onDeleted();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to remove this reminder.")),
  });

  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2">
      <div className="flex items-center gap-3">
        <AlarmClock className="size-4 text-muted-foreground" />
        <div>
          <p className="text-sm font-medium">{reminder.reminder_time.slice(0, 5)}</p>
          <p className="text-xs text-muted-foreground">{formatDays(reminder.days_of_week)}</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Switch
          checked={reminder.is_enabled}
          disabled={toggleMutation.isPending}
          onCheckedChange={(checked) => toggleMutation.mutate(checked)}
          aria-label="Enabled"
        />
        <Button
          variant="ghost"
          size="icon"
          aria-label="Delete reminder"
          onClick={() => deleteMutation.mutate()}
          disabled={deleteMutation.isPending}
        >
          {deleteMutation.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Trash2 className="size-4 text-destructive" />
          )}
        </Button>
      </div>
    </div>
  );
}

function AddReminderForm({ medicationId }: { medicationId: string }) {
  const queryClient = useQueryClient();
  const [time, setTime] = useState("08:00");
  const [selectedDays, setSelectedDays] = useState<string[]>([]);
  const [daily, setDaily] = useState(true);
  const [notes, setNotes] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      medicationService.createReminder(medicationId, {
        reminder_time: `${time}:00`,
        days_of_week: daily
          ? "daily"
          : DAY_OPTIONS.map((d) => d.code).filter((code) => selectedDays.includes(code)).join(","),
        is_enabled: true,
        notes: notes || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["medication-reminders", medicationId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Reminder added.");
      setNotes("");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to add this reminder.")),
  });

  const toggleDay = (code: string) => {
    setSelectedDays((prev) => (prev.includes(code) ? prev.filter((d) => d !== code) : [...prev, code]));
  };

  const canSubmit = daily || selectedDays.length > 0;

  return (
    <div className="flex flex-col gap-3 rounded-md border border-dashed border-border p-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor="reminder-time">Time</Label>
          <Input id="reminder-time" type="time" value={time} onChange={(e) => setTime(e.target.value)} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="reminder-notes">Notes (optional)</Label>
          <Input id="reminder-notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <Label>Days</Label>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant={daily ? "default" : "outline"}
            onClick={() => {
              setDaily(true);
              setSelectedDays([]);
            }}
          >
            Daily
          </Button>
          {DAY_OPTIONS.map((day) => (
            <button
              key={day.code}
              type="button"
              onClick={() => {
                setDaily(false);
                toggleDay(day.code);
              }}
              className={cn(
                "flex size-8 items-center justify-center rounded-full border border-input text-xs font-medium transition-colors",
                !daily && selectedDays.includes(day.code)
                  ? "bg-primary text-primary-foreground"
                  : "bg-transparent text-foreground hover:bg-accent"
              )}
              aria-pressed={!daily && selectedDays.includes(day.code)}
            >
              {day.label}
            </button>
          ))}
        </div>
      </div>
      <Button
        type="button"
        size="sm"
        className="self-start"
        disabled={!canSubmit || mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? <Loader2 className="animate-spin" /> : <Plus />}
        Add reminder
      </Button>
    </div>
  );
}

export function MedicationRemindersDialog({
  open,
  onOpenChange,
  medication,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  medication: Medication | null;
}) {
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["medication-reminders", medication?.id],
    queryFn: () => medicationService.listReminders(medication!.id),
    enabled: open && Boolean(medication),
  });

  useEffect(() => {
    if (open) refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, refreshKey]);

  if (!medication) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reminders for {medication.name}</DialogTitle>
          <DialogDescription>
            These are records you keep for yourself -- no push notifications are sent.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          {isLoading && (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </div>
          )}
          {isError && <p className="text-sm text-destructive">Couldn&apos;t load reminders.</p>}
          {data && data.length === 0 && (
            <p className="text-sm text-muted-foreground">No reminders yet for this medication.</p>
          )}
          {data && data.length > 0 && (
            <div className="flex flex-col gap-2">
              {data.map((reminder) => (
                <ReminderRow
                  key={reminder.id}
                  medicationId={medication.id}
                  reminder={reminder}
                  onDeleted={() => setRefreshKey((k) => k + 1)}
                />
              ))}
            </div>
          )}
          <AddReminderForm medicationId={medication.id} />
        </div>
      </DialogContent>
    </Dialog>
  );
}
