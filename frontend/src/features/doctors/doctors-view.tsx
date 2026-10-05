"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Contact, Mail, Pencil, Phone, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState, ErrorState, ListSkeleton, PageHeader } from "@/components/shared/page-states";
import { doctorService } from "@/services/doctor-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { DoctorContact } from "@/types/api";

import { DoctorFormDialog } from "./doctor-form-dialog";

export function DoctorsView() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<DoctorContact | null>(null);
  const [deleting, setDeleting] = useState<DoctorContact | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["doctors"],
    queryFn: () => doctorService.list(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => doctorService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["doctors"] });
      toast.success("Doctor contact removed.");
      setDeleting(null);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to remove this contact.")),
  });

  const openAdd = () => {
    setEditing(null);
    setFormOpen(true);
  };
  const openEdit = (doctor: DoctorContact) => {
    setEditing(doctor);
    setFormOpen(true);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Doctor contacts"
        description="Doctors you can book appointments with, or share your health summary with."
        action={
          <Button onClick={openAdd}>
            <Plus /> Add doctor
          </Button>
        }
      />

      {isLoading && <ListSkeleton />}
      {isError && <ErrorState description="Couldn't load your doctor contacts." onRetry={() => refetch()} />}

      {data && data.length === 0 && (
        <EmptyState
          icon={Contact}
          title="No doctor contacts yet"
          description="Add a doctor to book appointments and share summaries with them."
          action={
            <Button onClick={openAdd}>
              <Plus /> Add doctor
            </Button>
          }
        />
      )}

      {data && data.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {data.map((doctor) => (
            <Card key={doctor.id}>
              <CardContent className="flex items-start justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <p className="font-medium">{doctor.name}</p>
                  {doctor.specialization && (
                    <p className="text-sm text-muted-foreground">{doctor.specialization}</p>
                  )}
                  {doctor.clinic_name && (
                    <p className="text-sm text-muted-foreground">{doctor.clinic_name}</p>
                  )}
                  {doctor.email && (
                    <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
                      <Mail className="size-3.5" /> {doctor.email}
                    </p>
                  )}
                  {doctor.phone && (
                    <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
                      <Phone className="size-3.5" /> {doctor.phone}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 gap-1">
                  <Button variant="ghost" size="icon" aria-label="Edit" onClick={() => openEdit(doctor)}>
                    <Pencil className="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Delete"
                    onClick={() => setDeleting(doctor)}
                  >
                    <Trash2 className="size-4 text-destructive" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <DoctorFormDialog open={formOpen} onOpenChange={setFormOpen} doctor={editing} />

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Remove this doctor contact?"
        description={`This will permanently remove "${deleting?.name}" from your contacts. Any existing appointments will keep their date, but lose the doctor link. This cannot be undone.`}
        confirmLabel="Remove"
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
      />
    </div>
  );
}
