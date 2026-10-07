"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, History, Send, Stethoscope, type LucideIcon } from "lucide-react";

import { ListSkeleton, PageHeader } from "@/components/shared/page-states";
import { DoctorProfileView } from "@/features/doctors/doctor-profile-view";
import { DoctorsView } from "@/features/doctors/doctors-view";
import { appointmentService } from "@/services/appointment-service";
import { doctorService } from "@/services/doctor-service";
import { cn } from "@/lib/utils";

import { AppointmentsView } from "./appointments-view";

// The report builder and history are large; load them only when opened.
const ReportBuilderView = dynamic(
  () => import("@/features/reports/report-builder-view").then((m) => m.ReportBuilderView),
  { loading: () => <ListSkeleton /> },
);
const ShareHistoryView = dynamic(
  () => import("@/features/reports/share-history-view").then((m) => m.ShareHistoryView),
  { loading: () => <ListSkeleton /> },
);

type SectionId = "appointments" | "doctors" | "share" | "history";

const SECTIONS: { id: SectionId; label: string; hint: string; icon: LucideIcon }[] = [
  { id: "appointments", label: "Appointments", hint: "Your visits", icon: CalendarClock },
  { id: "doctors", label: "Doctors", hint: "Your contacts", icon: Stethoscope },
  { id: "share", label: "Share report", hint: "Email or QR code", icon: Send },
  { id: "history", label: "History", hint: "What you shared", icon: History },
];

function parseTab(value: string | null): SectionId {
  return SECTIONS.some((s) => s.id === value) ? (value as SectionId) : "appointments";
}

export function AppointmentsHub() {
  const params = useSearchParams();
  const active = parseTab(params.get("tab"));
  const doctorId = params.get("doctor") ?? undefined;
  const summaryId = params.get("summary") ?? undefined;

  const upcoming = useQuery({
    queryKey: ["appointments", "upcoming"],
    queryFn: () => appointmentService.list("upcoming"),
  });
  const doctors = useQuery({ queryKey: ["doctors"], queryFn: () => doctorService.list() });
  const counts: Partial<Record<SectionId, number>> = {
    appointments: upcoming.data?.length,
    doctors: doctors.data?.length,
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Appointments"
        description="Keep track of visits and doctors, and share health reports by email or QR code."
      />

      <nav aria-label="Appointment sections" className="grid grid-cols-2 gap-2 sm:gap-3 lg:max-w-4xl lg:grid-cols-4">
        {SECTIONS.map(({ id, label, hint, icon: Icon }) => {
          const selected = id === active;
          const count = counts[id];
          return (
            <Link
              key={id}
              href={`/appointments?tab=${id}`}
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

      <section aria-label={SECTIONS.find((s) => s.id === active)?.label}>
        {active === "appointments" && <AppointmentsView key={doctorId} defaultDoctorId={doctorId} />}
        {active === "doctors" &&
          (doctorId ? <DoctorProfileView key={doctorId} doctorId={doctorId} /> : <DoctorsView />)}
        {active === "share" && (
          <ReportBuilderView
            key={`${doctorId ?? ""}-${summaryId ?? ""}`}
            initialDoctorId={doctorId}
            initialAiSummaryId={summaryId}
          />
        )}
        {active === "history" && <ShareHistoryView />}
      </section>
    </div>
  );
}
