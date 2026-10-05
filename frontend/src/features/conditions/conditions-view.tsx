"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HeartPulse, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState, ErrorState, ListSkeleton, PageHeader } from "@/components/shared/page-states";
import { conditionService } from "@/services/condition-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { ConditionStatus, MedicalCondition } from "@/types/api";

import { ConditionFormDialog } from "./condition-form-dialog";

const STATUS_VARIANT: Record<ConditionStatus, "warning" | "secondary" | "success"> = {
  active: "warning",
  managed: "secondary",
  resolved: "success",
};

export function ConditionsView() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<MedicalCondition | null>(null);
  const [deleting, setDeleting] = useState<MedicalCondition | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["conditions"],
    queryFn: () => conditionService.list(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => conditionService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conditions"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      toast.success("Condition removed.");
      setDeleting(null);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to remove this condition.")),
  });

  const openAdd = () => {
    setEditing(null);
    setFormOpen(true);
  };
  const openEdit = (condition: MedicalCondition) => {
    setEditing(condition);
    setFormOpen(true);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Medical conditions"
        description="Conditions you've been diagnosed with or are managing."
        action={
          <Button onClick={openAdd}>
            <Plus /> Add condition
          </Button>
        }
      />

      {isLoading && <ListSkeleton />}
      {isError && <ErrorState description="Couldn't load your conditions." onRetry={() => refetch()} />}

      {data && data.length === 0 && (
        <EmptyState
          icon={HeartPulse}
          title="No conditions recorded"
          description="Add a condition to keep your health record complete."
          action={
            <Button onClick={openAdd}>
              <Plus /> Add condition
            </Button>
          }
        />
      )}

      {data && data.length > 0 && (
        <div className="flex flex-col gap-3">
          {data.map((condition) => (
            <Card key={condition.id}>
              <CardContent className="flex items-start justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{condition.name}</p>
                    {condition.status && (
                      <Badge variant={STATUS_VARIANT[condition.status]}>{condition.status}</Badge>
                    )}
                  </div>
                  {condition.diagnosed_date && (
                    <p className="text-sm text-muted-foreground">
                      Diagnosed {condition.diagnosed_date}
                    </p>
                  )}
                  {condition.notes && <p className="text-sm text-muted-foreground">{condition.notes}</p>}
                </div>
                <div className="flex shrink-0 gap-1">
                  <Button variant="ghost" size="icon" aria-label="Edit" onClick={() => openEdit(condition)}>
                    <Pencil className="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Delete"
                    onClick={() => setDeleting(condition)}
                  >
                    <Trash2 className="size-4 text-destructive" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <ConditionFormDialog open={formOpen} onOpenChange={setFormOpen} condition={editing} />

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Remove this condition?"
        description={`This will permanently remove "${deleting?.name}" from your records. This cannot be undone.`}
        confirmLabel="Remove"
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
      />
    </div>
  );
}
