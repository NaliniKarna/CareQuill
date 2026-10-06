"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { preferenceService } from "@/services/preference-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { NotificationPrefs } from "@/types/api";

const PREF_LABELS: Array<{ key: keyof NotificationPrefs; label: string; description: string }> = [
  {
    key: "appointment_reminders",
    label: "Appointment reminders",
    description: "Notify me when an appointment is approaching.",
  },
  {
    key: "medication_reminders",
    label: "Medication reminders",
    description: "Notify me about medication reminders due today.",
  },
  {
    key: "ai_summary_ready",
    label: "Record Summary ready",
    description: "Notify me when a new Record Summary has been generated.",
  },
  {
    key: "document_processed",
    label: "Document processed",
    description: "Notify me when an uploaded document finishes processing.",
  },
  {
    key: "report_shared",
    label: "Report shared",
    description: "Notify me when a health report is successfully shared.",
  },
  {
    key: "email_failures",
    label: "Email failures",
    description: "Notify me if a report or summary email fails to send.",
  },
];

export function NotificationPreferencesForm() {
  const queryClient = useQueryClient();
  const { data: preferences, isLoading } = useQuery({
    queryKey: ["preferences"],
    queryFn: () => preferenceService.get(),
  });

  // Unsaved local edits only -- the saved values always come straight from
  // the query, so there's nothing to sync into local state on load.
  const [pendingChanges, setPendingChanges] = useState<Partial<NotificationPrefs>>({});

  const effective: NotificationPrefs | null = preferences
    ? { ...preferences.notification_prefs, ...pendingChanges }
    : null;
  const isDirty = Object.keys(pendingChanges).length > 0;

  const mutation = useMutation({
    mutationFn: (notification_prefs: NotificationPrefs) =>
      preferenceService.update({ notification_prefs }),
    onSuccess: (data) => {
      queryClient.setQueryData(["preferences"], data);
      setPendingChanges({});
      toast.success("Notification preferences saved.");
    },
    onError: (error) =>
      toast.error(getApiErrorMessage(error, "Unable to save your notification preferences.")),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Notifications</CardTitle>
        <CardDescription>Choose which in-app notifications you want to receive.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {isLoading && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-10" />
            <Skeleton className="h-10" />
            <Skeleton className="h-10" />
          </div>
        )}
        {effective &&
          PREF_LABELS.map(({ key, label, description }) => (
            <div key={key} className="flex items-center justify-between gap-4">
              <div>
                <Label htmlFor={`pref-${key}`}>{label}</Label>
                <p className="text-xs text-muted-foreground">{description}</p>
              </div>
              <Switch
                id={`pref-${key}`}
                checked={effective[key]}
                onCheckedChange={(checked) =>
                  setPendingChanges((prev) => ({ ...prev, [key]: checked }))
                }
              />
            </div>
          ))}
        {effective && (
          <Button
            className="self-start"
            disabled={!isDirty || mutation.isPending}
            onClick={() => mutation.mutate(effective)}
          >
            {mutation.isPending ? <Loader2 className="animate-spin" /> : <Save />}
            Save preferences
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
