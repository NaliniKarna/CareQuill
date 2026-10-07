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

/** Edits an existing appointment. Adding happens in the inline form. */
export function AppointmentFormDialog({
  open,
  onOpenChange,
  appointment,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  appointment: Appointment | null;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit appointment</DialogTitle>
          <DialogDescription>Update the details of this appointment.</DialogDescription>
        </DialogHeader>
        {appointment && (
          <AppointmentForm
            appointment={appointment}
            idPrefix="appt-edit"
            onSaved={() => onOpenChange(false)}
            onCancel={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
