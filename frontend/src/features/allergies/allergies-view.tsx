"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, ShieldAlert, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState, ErrorState, ListSkeleton, PageHeader } from "@/components/shared/page-states";
import { allergyService } from "@/services/allergy-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { Allergy, AllergySeverity } from "@/types/api";

import { AllergyFormDialog } from "./allergy-form-dialog";

const SEVERITY_VARIANT: Record<AllergySeverity, "warning" | "destructive" | "secondary"> = {
  mild: "secondary",
  moderate: "warning",
  severe: "destructive",
};

export function AllergiesView() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Allergy | null>(null);
  const [deleting, setDeleting] = useState<Allergy | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["allergies"],
    queryFn: () => allergyService.list(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => allergyService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["allergies"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      toast.success("Allergy removed.");
      setDeleting(null);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to remove this allergy.")),
  });

  const openAdd = () => {
    setEditing(null);
    setFormOpen(true);
  };
  const openEdit = (allergy: Allergy) => {
    setEditing(allergy);
    setFormOpen(true);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Allergies"
        description="Substances you're allergic to, so anyone treating you can plan around them."
        action={
          <Button onClick={openAdd}>
            <Plus /> Add allergy
          </Button>
        }
      />

      {isLoading && <ListSkeleton />}
      {isError && <ErrorState description="Couldn't load your allergies." onRetry={() => refetch()} />}

      {data && data.length === 0 && (
        <EmptyState
          icon={ShieldAlert}
          title="No allergies recorded"
          description="Add an allergy to keep it visible on your health summary."
          action={
            <Button onClick={openAdd}>
              <Plus /> Add allergy
            </Button>
          }
        />
      )}

      {data && data.length > 0 && (
        <div className="flex flex-col gap-3">
          {data.map((allergy) => (
            <Card key={allergy.id}>
              <CardContent className="flex items-start justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{allergy.name}</p>
                    {allergy.severity && (
                      <Badge variant={SEVERITY_VARIANT[allergy.severity]}>{allergy.severity}</Badge>
                    )}
                  </div>
                  {allergy.reaction && (
                    <p className="text-sm text-muted-foreground">Reaction: {allergy.reaction}</p>
                  )}
                  {allergy.notes && <p className="text-sm text-muted-foreground">{allergy.notes}</p>}
                </div>
                <div className="flex shrink-0 gap-1">
                  <Button variant="ghost" size="icon" aria-label="Edit" onClick={() => openEdit(allergy)}>
                    <Pencil className="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Delete"
                    onClick={() => setDeleting(allergy)}
                  >
                    <Trash2 className="size-4 text-destructive" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <AllergyFormDialog open={formOpen} onOpenChange={setFormOpen} allergy={editing} />

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Remove this allergy?"
        description={`This will permanently remove "${deleting?.name}" from your records. This cannot be undone.`}
        confirmLabel="Remove"
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
      />
    </div>
  );
}
