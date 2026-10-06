"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, Stethoscope, type LucideIcon } from "lucide-react";

import { PageHeader } from "@/components/shared/page-states";
import { DoctorProfileView } from "@/features/doctors/doctor-profile-view";
import { DoctorsView } from "@/features/doctors/doctors-view";
import { appointmentService } from "@/services/appointment-service";
import { doctorService } from "@/services/doctor-service";
import { cn } from "@/lib/utils";

import { AppointmentsView } from "./appointments-view";

const SECTIONS: { id: "appointments" | "doctors"; label: string; hint: string; icon: LucideIcon }[] = [
  { id: "appointments", label: "Appointments", hint: "Your visits", icon: CalendarClock },
  { id: "doctors", label: "Doctors", hint: "Contacts & reports", icon: Stethoscope },
];

export function AppointmentsHub() {
  const params = useSearchParams();
  const active = params.get("tab") === "doctors" ? "doctors" : "appointments";
  const doctorId = params.get("doctor") ?? undefined;
  const summaryId = params.get("summary") ?? undefined;

  const upcoming = useQuery({
    queryKey: ["appointments", "upcoming"],
    queryFn: () => appointmentService.list("upcoming"),
  });
  const doctors = useQuery({ queryKey: ["doctors"], queryFn: () => doctorService.list() });
  const counts = { appointments: upcoming.data?.length, doctors: doctors.data?.length };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Appointments"
        description="Book visits, keep your doctors' details, and share health reports with them."
      />

      <nav aria-label="Appointment sections" className="grid grid-cols-2 gap-2 sm:max-w-lg sm:gap-3">
        {SECTIONS.map(({ id, label, hint, icon: Icon }) => {
          const selected = id === active;
          const count = counts[id];
          return (
            <Link
              key={id}
              href={`/appointments?tab=${id}${id === "doctors" && summaryId ? `&summary=${summaryId}` : ""}`}
              scroll={false}
              aria-current={selected ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-xl border bg-card p-3 transition-colors",
                "hover:border-primary/40 hover:bg-accent/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                selected && "border-primary bg-accent shadow-sm",
              )}
            >
              <span
                className={cn(
                  "hidden size-9 shrink-0 items-center justify-center rounded-lg sm:flex",
                  selected ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
                )}
              >
                <Icon className="size-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium">{label}</span>
                  {count !== undefined && (
                    <span className="rounded-full bg-muted px-2 text-xs font-medium text-muted-foreground tabular-nums">
                      {count}
                    </span>
                  )}
                </span>
                <span className="hidden truncate text-xs text-muted-foreground sm:block">{hint}</span>
              </span>
            </Link>
          );
        })}
      </nav>

      <section aria-label={active === "doctors" ? "Doctors" : "Appointments"}>
        {active === "appointments" && <AppointmentsView embedded />}
        {active === "doctors" &&
          (doctorId ? (
            <DoctorProfileView key={doctorId} doctorId={doctorId} summaryId={summaryId} />
          ) : (
            <DoctorsView summaryId={summaryId} />
          ))}
      </section>
    </div>
  );
}
