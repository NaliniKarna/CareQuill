"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, Contact, Mail, Pencil, Phone, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState, ErrorState, PageHeader } from "@/components/shared/page-states";
import { Skeleton } from "@/components/ui/skeleton";
import { doctorService } from "@/services/doctor-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { DoctorContact } from "@/types/api";

import { DoctorFormDialog } from "./doctor-form-dialog";

export function doctorInitials(name: string): string {
  const parts = name
    .replace(/^(dr\.?|prof\.?)\s+/i, "")
    .split(/\s+/)
    .filter(Boolean);
  return ((parts[0]?.[0] ?? "?") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

export function DoctorAvatar({ name, className = "size-12 text-base" }: { name: string; className?: string }) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-full bg-accent font-semibold text-accent-foreground ${className}`}
    >
      {doctorInitials(name)}
    </div>
  );
}

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
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
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

  const profileHref = (id: string) => `/appointments?profile=${id}`;

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        compact
        title="Doctors"
        description="Doctors you see. Open a profile to see their visits and what you shared."
        action={
          <Button onClick={openAdd}>
            <Plus /> Add doctor
          </Button>
        }
      />

      {isLoading && (
        <div className="grid grid-cols-[minmax(0,1fr)] gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-36" />
          ))}
        </div>
      )}
      {isError && <ErrorState description="Couldn't load your doctors." onRetry={() => refetch()} />}

      {data && data.length === 0 && (
        <EmptyState
          icon={Contact}
          title="No doctors added yet"
          description="Add a doctor to book appointments and share health reports with them."
          action={
            <Button onClick={openAdd}>
              <Plus /> Add doctor
            </Button>
          }
        />
      )}

      {data && data.length > 0 && (
        <div className="grid grid-cols-[minmax(0,1fr)] gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {data.map((doctor) => (
            <Card key={doctor.id} className="group transition-colors hover:border-primary/40">
              <CardContent className="flex h-full flex-col gap-4">
                <div className="flex items-start gap-3">
                  <DoctorAvatar name={doctor.name} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{doctor.name}</p>
                    <p className="truncate text-sm text-muted-foreground">
                      {doctor.specialization || "General"}
                      {doctor.clinic_name ? ` · ${doctor.clinic_name}` : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-0.5">
                    <Button variant="ghost" size="icon" className="size-8" aria-label={`Edit ${doctor.name}`} onClick={() => openEdit(doctor)}>
                      <Pencil className="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon" className="size-8"
                      aria-label={`Remove ${doctor.name}`}
                      onClick={() => setDeleting(doctor)}
                    >
                      <Trash2 className="size-4 text-destructive" />
                    </Button>
                  </div>
                </div>

                <div className="flex flex-col gap-1 text-sm text-muted-foreground">
                  <p className="flex items-center gap-2 truncate">
                    <Mail className="size-3.5 shrink-0" />
                    <span className="truncate">{doctor.email || "No email on file"}</span>
                  </p>
                  <p className="flex items-center gap-2 truncate">
                    <Phone className="size-3.5 shrink-0" />
                    <span className="truncate">{doctor.phone || "No phone on file"}</span>
                  </p>
                </div>

                <Button asChild variant="outline" size="sm" className="mt-auto justify-between">
                  <Link href={profileHref(doctor.id)}>
                    View profile <ChevronRight className="size-4" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <DoctorFormDialog open={formOpen} onOpenChange={setFormOpen} doctor={editing} />

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Remove this doctor?"
        description={`This will permanently remove "${deleting?.name}" from your contacts. Existing appointments keep their date but lose the doctor link. This cannot be undone.`}
        confirmLabel="Remove"
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
      />
    </div>
  );
}
