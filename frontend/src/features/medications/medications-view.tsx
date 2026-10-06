"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlarmClock, Pencil, Pill, Plus, Power, PowerOff, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState, ErrorState, ListSkeleton, PageHeader } from "@/components/shared/page-states";
import { medicationService } from "@/services/medication-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { Medication } from "@/types/api";

import { MedicationFormDialog } from "./medication-form-dialog";
import { MedicationRemindersDialog } from "./medication-reminders-dialog";

export function MedicationsView({ embedded = false }: { embedded?: boolean } = {}) {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"active" | "inactive">("active");
  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Medication | null>(null);
  const [remindersFor, setRemindersFor] = useState<Medication | null>(null);
  const [deleting, setDeleting] = useState<Medication | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["medications", tab, search],
    queryFn: () =>
      medicationService.list({
        active: tab === "active",
        q: search.trim() || undefined,
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => medicationService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["medications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      toast.success("Medication removed.");
      setDeleting(null);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to remove this medication.")),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: (med: Medication) =>
      med.is_active ? medicationService.deactivate(med.id) : medicationService.activate(med.id),
    onSuccess: (_, med) => {
      queryClient.invalidateQueries({ queryKey: ["medications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(med.is_active ? "Marked as inactive." : "Marked as active.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to update this medication.")),
  });

  const openAdd = () => {
    setEditing(null);
    setFormOpen(true);
  };
  const openEdit = (med: Medication) => {
    setEditing(med);
    setFormOpen(true);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        compact={embedded}
        title="Medications"
        description="Medications you're taking or have taken, with optional reminders."
        action={
          <Button onClick={openAdd}>
            <Plus /> Add medication
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs value={tab} onValueChange={(v) => setTab(v as "active" | "inactive")}>
          <TabsList>
            <TabsTrigger value="active">Active</TabsTrigger>
            <TabsTrigger value="inactive">Inactive</TabsTrigger>
          </TabsList>
        </Tabs>
        <div className="relative sm:w-72">
          <Search className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search medications..."
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {isLoading && <ListSkeleton />}
      {isError && <ErrorState description="Couldn't load your medications." onRetry={() => refetch()} />}

      {data && data.length === 0 && (
        <EmptyState
          icon={Pill}
          title={tab === "active" ? "No active medications" : "No inactive medications"}
          description={
            tab === "active"
              ? "Add a medication you're currently taking."
              : "Medications you deactivate will show up here."
          }
          action={
            tab === "active" ? (
              <Button onClick={openAdd}>
                <Plus /> Add medication
              </Button>
            ) : undefined
          }
        />
      )}

      {data && data.length > 0 && (
        <div className="flex flex-col gap-3">
          {data.map((med) => (
            <Card key={med.id}>
              <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{med.name}</p>
                    <Badge variant={med.is_active ? "success" : "secondary"}>
                      {med.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {[med.dosage, med.frequency].filter(Boolean).join(" · ") || "No dosage details"}
                  </p>
                  {med.instructions && (
                    <p className="text-sm text-muted-foreground">{med.instructions}</p>
                  )}
                  {(med.start_date || med.end_date) && (
                    <p className="text-xs text-muted-foreground">
                      {med.start_date ?? "—"} to {med.end_date ?? "ongoing"}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 flex-wrap gap-1">
                  <Button variant="outline" size="sm" onClick={() => setRemindersFor(med)}>
                    <AlarmClock className="size-4" /> Reminders
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={med.is_active ? "Deactivate" : "Activate"}
                    disabled={toggleActiveMutation.isPending}
                    onClick={() => toggleActiveMutation.mutate(med)}
                  >
                    {med.is_active ? (
                      <PowerOff className="size-4" />
                    ) : (
                      <Power className="size-4" />
                    )}
                  </Button>
                  <Button variant="ghost" size="icon" aria-label="Edit" onClick={() => openEdit(med)}>
                    <Pencil className="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Delete"
                    onClick={() => setDeleting(med)}
                  >
                    <Trash2 className="size-4 text-destructive" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <MedicationFormDialog open={formOpen} onOpenChange={setFormOpen} medication={editing} />
      <MedicationRemindersDialog
        open={Boolean(remindersFor)}
        onOpenChange={(open) => !open && setRemindersFor(null)}
        medication={remindersFor}
      />

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Remove this medication?"
        description={`This will permanently remove "${deleting?.name}" and any of its reminders. This cannot be undone.`}
        confirmLabel="Remove"
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
      />
    </div>
  );
}
