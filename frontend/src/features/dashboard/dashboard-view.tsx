"use client";

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { useQueries, useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowRight, CheckCircle2, UserRound } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { appointmentService } from "@/services/appointment-service";
import { dashboardService } from "@/services/dashboard-service";
import { doctorService } from "@/services/doctor-service";
import { medicationService } from "@/services/medication-service";

import {
  ActiveMedicationsPanel,
  QuickActionsMenu,
  UpcomingAppointmentsPanel,
  UpcomingRemindersPanel,
} from "./dashboard-widgets";
import { buildUpcomingReminders } from "./upcoming-reminders";

// Reminders are stored per medication, so cap the fan-out on the dashboard.
const MAX_MEDICATIONS_FOR_REMINDERS = 8;

export function DashboardView() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: dashboardService.get,
  });

  const medicationsQuery = useQuery({
    queryKey: ["medications", "active-for-dashboard"],
    queryFn: () => medicationService.list({ active: true }),
  });
  const medications = medicationsQuery.data;
  const reminderMedications = useMemo(
    () => (medications ?? []).slice(0, MAX_MEDICATIONS_FOR_REMINDERS),
    [medications]
  );

  const reminderQueries = useQueries({
    queries: reminderMedications.map((m) => ({
      queryKey: ["medication-reminders", m.id],
      queryFn: () => medicationService.listReminders(m.id),
    })),
  });
  const remindersLoading =
    medicationsQuery.isLoading || reminderQueries.some((q) => q.isLoading);

  const now = new Date();
  const upcomingReminders = buildUpcomingReminders(
    reminderMedications,
    reminderQueries.map((q) => q.data),
    now
  );

  const appointmentsQuery = useQuery({
    queryKey: ["appointments", "upcoming"],
    queryFn: () => appointmentService.list("upcoming"),
  });
  const doctorsQuery = useQuery({
    queryKey: ["doctors"],
    queryFn: () => doctorService.list(),
  });
  const doctorNameById = useMemo(
    () => Object.fromEntries((doctorsQuery.data ?? []).map((d) => [d.id, d.name])),
    [doctorsQuery.data]
  );

  // The unverified-email reminder is a one-time pop-up per browser session
  // instead of a permanent banner on the page.
  const needsEmailVerification = Boolean(
    data?.notifications.some((n) => n.toLowerCase().includes("verify your email"))
  );
  useEffect(() => {
    if (!needsEmailVerification) return;
    try {
      if (window.sessionStorage.getItem("verify-email-toast") === "1") return;
      window.sessionStorage.setItem("verify-email-toast", "1");
    } catch {
      // Storage unavailable: show the pop-up anyway.
    }
    toast.warning("Please verify your email address", {
      description: "Open the verification link we sent to your inbox.",
      duration: 10000,
    });
  }, [needsEmailVerification]);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-36" />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-56" />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <Alert variant="destructive">
        <AlertCircle />
        <AlertTitle>Couldn&apos;t load your dashboard</AlertTitle>
        <AlertDescription>Please refresh the page or try again shortly.</AlertDescription>
      </Alert>
    );
  }

  const percent = data.profile_completion_percent;
  const complete = percent >= 100;

  return (
    <div className="flex flex-col gap-6">
      {/* Welcome + profile completion, in one calm banner */}
      <section className="rounded-xl border border-border bg-gradient-to-br from-accent to-card p-5 shadow-sm sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{data.welcome_message}</h1>
            <p className="text-muted-foreground">Here&apos;s an overview of your health record.</p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button asChild variant="outline" size="sm" className="bg-card/80">
              <Link href="/settings?tab=profile" aria-label="Health profile">
                <UserRound />
                <span className="hidden sm:inline">Health profile</span>
              </Link>
            </Button>
            <QuickActionsMenu />
          </div>
        </div>

        <div className="mt-5 rounded-lg border border-border/70 bg-card/80 p-4">
          <div className="flex items-start gap-3">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              {complete ? <CheckCircle2 className="size-5 text-success" /> : <UserRound className="size-5" />}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4">
                <p className="text-sm font-semibold">Profile completion</p>
                <p className="text-sm font-semibold text-primary">{percent}% complete</p>
              </div>
              <p className="text-sm text-muted-foreground">
                A complete profile helps make your Record Summary more accurate.
              </p>
              <Progress value={percent} className="mt-3" aria-label="Profile completion" />
              {!complete && (
                <Link
                  href="/settings?tab=profile"
                  className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                >
                  Finish your profile <ArrowRight className="size-3.5" />
                </Link>
              )}
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <ActiveMedicationsPanel
          medications={medications}
          totalCount={data.active_medications_count}
          isLoading={medicationsQuery.isLoading}
        />
        <UpcomingRemindersPanel
          reminders={upcomingReminders}
          isLoading={remindersLoading}
          now={now}
        />
        <UpcomingAppointmentsPanel
          appointments={appointmentsQuery.data}
          doctorNameById={doctorNameById}
          isLoading={appointmentsQuery.isLoading}
        />
      </div>
    </div>
  );
}
