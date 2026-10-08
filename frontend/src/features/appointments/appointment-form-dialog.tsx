"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Appointment } from "@/types/api";

import { AppointmentForm } from "./appointment-form";

/** Adds a new appointment, or edits one when `appointment` is given. */
export function AppointmentFormDialog({
  open,
  onOpenChange,
  appointment = null,
  creating = false,
  defaultDoctorId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  appointment?: Appointment | null;
  /** Open in "add" mode (no appointment to edit). */
  creating?: boolean;
  /** Pre-selects a doctor when adding. */
  defaultDoctorId?: string;
}) {
  const isEdit = Boolean(appointment);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit appointment" : "Add appointment"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Update the details of this appointment."
              : "Record a visit you have coming up. CareQuill reminds you 48 hours before."}
          </DialogDescription>
        </DialogHeader>
        {(appointment || creating) && (
          <AppointmentForm
            appointment={appointment}
            defaultDoctorId={defaultDoctorId}
            idPrefix={isEdit ? "appt-edit" : "appt-new"}
            onSaved={() => onOpenChange(false)}
            onCancel={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
