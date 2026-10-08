"use client";

import Link from "next/link";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, CalendarClock, History, Plus, Send, type LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ListSkeleton, PageHeader } from "@/components/shared/page-states";
import { DoctorProfileView } from "@/features/doctors/doctor-profile-view";
import { DoctorsView } from "@/features/doctors/doctors-view";
import { appointmentService } from "@/services/appointment-service";
import { cn } from "@/lib/utils";

import { AppointmentFormDialog } from "./appointment-form-dialog";
import { AppointmentsView } from "./appointments-view";
import { NextAppointments } from "./next-appointments";

// The report builder and history are large; load them only when opened.
const ReportBuilderView = dynamic(
  () => import("@/features/reports/report-builder-view").then((m) => m.ReportBuilderView),
  { loading: () => <ListSkeleton /> },
);
const ShareHistoryView = dynamic(
  () => import("@/features/reports/share-history-view").then((m) => m.ShareHistoryView),
  { loading: () => <ListSkeleton /> },
);

type SectionId = "appointments" | "share" | "history";

const SECTIONS: { id: SectionId; label: string; hint: string; icon: LucideIcon }[] = [
  { id: "appointments", label: "Appointments", hint: "Doctors and visits", icon: CalendarClock },
  { id: "share", label: "Share report", hint: "Email or QR code", icon: Send },
  { id: "history", label: "History", hint: "What you shared", icon: History },
];

function parseTab(value: string | null): SectionId {
  // "doctors" is the old tab id; doctors now live on the appointments tab.
  return SECTIONS.some((s) => s.id === value) ? (value as SectionId) : "appointments";
}

function StepSection({
  id,
  step,
  title,
  description,
  children,
}: {
  id: string;
  step: number;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="flex scroll-mt-24 flex-col gap-5">
      <div className="flex items-start gap-3 border-b border-border pb-4">
        <span
          aria-hidden
          className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground shadow-sm"
        >
          {step}
        </span>
        <div>
          <h2 id={`${id}-title`} className="text-lg font-semibold">
            {title}
          </h2>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

export function AppointmentsHub() {
  const params = useSearchParams();
  const active = parseTab(params.get("tab"));
  const doctorId = params.get("doctor") ?? undefined;
  // A doctor's profile replaces the combined view: ?profile=<id> (old links used tab=doctors&doctor=<id>).
  const profileId = params.get("profile") ?? (params.get("tab") === "doctors" ? doctorId : undefined);
  const summaryId = params.get("summary") ?? undefined;
  const showAll = params.get("view") === "all";
  const [addOpen, setAddOpen] = useState(false);

  const upcoming = useQuery({
    queryKey: ["appointments", "upcoming"],
    queryFn: () => appointmentService.list("upcoming"),
  });
  const counts: Partial<Record<SectionId, number>> = { appointments: upcoming.data?.length };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Appointments"
        description="Save your doctors, add your appointments, and share health reports by email or QR code."
      />

      <nav aria-label="Appointment sections" className="grid grid-cols-1 gap-2 sm:grid-cols-3 sm:gap-3 lg:max-w-3xl lg:grid-cols-3">
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
        {active === "appointments" &&
          (profileId ? (
            <DoctorProfileView key={profileId} doctorId={profileId} />
          ) : showAll ? (
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <Button asChild variant="ghost" size="sm" className="-ml-2">
                  <Link href="/appointments" scroll={false}>
                    <ArrowLeft /> Back
                  </Link>
                </Button>
                <Button onClick={() => setAddOpen(true)}>
                  <Plus /> Add appointment
                </Button>
              </div>
              <AppointmentsView onAdd={() => setAddOpen(true)} />
            </div>
          ) : (
            <div className="flex flex-col gap-10">
              <NextAppointments onAdd={() => setAddOpen(true)} />
              <div id="doctors" className="scroll-mt-24">
                <DoctorsView />
              </div>
            </div>
          ))}
        {active === "share" && (
          <ReportBuilderView
            key={`${doctorId ?? ""}-${summaryId ?? ""}`}
            initialDoctorId={doctorId}
            initialAiSummaryId={summaryId}
          />
        )}
        {active === "history" && <ShareHistoryView />}
      </section>

      <AppointmentFormDialog open={addOpen} onOpenChange={setAddOpen} creating />
    </div>
  );
}
