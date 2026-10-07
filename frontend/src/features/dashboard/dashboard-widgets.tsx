"use client";

import Link from "next/link";
import {
  AlarmClock,
  ArrowRight,
  CalendarClock,
  FileStack,
  LayoutGrid,
  Pill,
  Share2,
  Sparkles,
  UserRound,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";
import type { Appointment, Medication } from "@/types/api";

import { formatReminderWhen, type UpcomingReminder } from "./upcoming-reminders";

// ---------------------------------------------------------------------------
// Quick actions: hidden behind one icon so the page stays calm.
// ---------------------------------------------------------------------------
const QUICK_ACTIONS = [
  { label: "Complete your profile", href: "/settings?tab=profile", icon: UserRound },
  { label: "Add medication", href: "/medical-records?tab=medications", icon: Pill },
  { label: "Upload report", href: "/medical-records", icon: FileStack },
  { label: "Book appointment", href: "/appointments", icon: CalendarClock },
  { label: "Create Record Summary", href: "/record-summary", icon: Sparkles },
  { label: "Share with doctor", href: "/appointments?tab=share", icon: Share2 },
];

export function QuickActionsMenu() {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="icon" aria-label="Quick actions" title="Quick actions">
          <LayoutGrid className="size-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-64 p-2">
        <p className="px-2 pb-1 pt-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Quick actions
        </p>
        <ul className="flex flex-col">
          {QUICK_ACTIONS.map((action) => (
            <li key={action.label}>
              <Link
                href={action.href}
                className="flex items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                <action.icon className="size-4 text-primary" />
                {action.label}
              </Link>
            </li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  );
}

// ---------------------------------------------------------------------------
// Panel shell shared by the three overview cards.
// ---------------------------------------------------------------------------
function Panel({
  icon: Icon,
  title,
  count,
  href,
  linkLabel,
  children,
}: {
  icon: React.ElementType;
  title: string;
  count?: number;
  href: string;
  linkLabel: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <Icon className="size-5" />
          </div>
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
        {count !== undefined && <Badge variant="secondary">{count}</Badge>}
      </CardHeader>
      <CardContent className="flex flex-1 flex-col justify-between gap-4">
        {children}
        <Link
          href={href}
          className="flex items-center gap-1 self-start text-sm text-primary hover:underline"
        >
          {linkLabel} <ArrowRight className="size-3.5" />
        </Link>
      </CardContent>
    </Card>
  );
}

function EmptyLine({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded-md border border-dashed border-border px-3 py-4 text-center text-sm text-muted-foreground">
      {children}
    </p>
  );
}

function RowSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      <Skeleton className="h-10" />
      <Skeleton className="h-10" />
    </div>
  );
}

const MAX_ROWS = 3;

export function ActiveMedicationsPanel({
  medications,
  totalCount,
  isLoading,
}: {
  medications: Medication[] | undefined;
  totalCount: number;
  isLoading: boolean;
}) {
  return (
    <Panel
      icon={Pill}
      title="Active medications"
      count={totalCount}
      href="/medical-records?tab=medications"
      linkLabel="Manage medications"
    >
      {isLoading ? (
        <RowSkeleton />
      ) : medications && medications.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {medications.slice(0, MAX_ROWS).map((m) => (
            <li
              key={m.id}
              className="flex items-center justify-between gap-2 rounded-md bg-secondary/60 px-3 py-2"
            >
              <span className="truncate text-sm font-medium">{m.name}</span>
              <span className="shrink-0 text-xs text-muted-foreground">
                {[m.dosage, m.frequency].filter(Boolean).join(" · ") || "No dosage set"}
              </span>
            </li>
          ))}
          {totalCount > MAX_ROWS && (
            <li className="px-1 text-xs text-muted-foreground">+{totalCount - MAX_ROWS} more</li>
          )}
        </ul>
      ) : (
        <EmptyLine>No active medications yet.</EmptyLine>
      )}
    </Panel>
  );
}

export function UpcomingRemindersPanel({
  reminders,
  isLoading,
  now,
}: {
  reminders: UpcomingReminder[];
  isLoading: boolean;
  now: Date;
}) {
  return (
    <Panel
      icon={AlarmClock}
      title="Upcoming reminders"
      href="/medical-records?tab=medications"
      linkLabel="Edit reminders"
    >
      {isLoading ? (
        <RowSkeleton />
      ) : reminders.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {reminders.slice(0, MAX_ROWS).map((r) => (
            <li
              key={`${r.id}-${r.at.getTime()}`}
              className="flex items-center justify-between gap-2 rounded-md bg-secondary/60 px-3 py-2"
            >
              <span className="truncate text-sm font-medium">
                {r.medicationName}
                {r.dosage ? <span className="font-normal text-muted-foreground"> · {r.dosage}</span> : null}
              </span>
              <span className="shrink-0 text-xs text-primary">{formatReminderWhen(r.at, now)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyLine>No reminders set. Add one from a medication.</EmptyLine>
      )}
    </Panel>
  );
}

function formatAppointmentDate(date: string, time: string | null): string {
  const [y, m, d] = date.split("-").map(Number);
  const when = new Date(y, m - 1, d);
  const day = when.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
  if (!time) return day;
  const [h, min] = time.split(":").map(Number);
  const t = new Date(2000, 0, 1, h, min).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
  return `${day}, ${t}`;
}

export function UpcomingAppointmentsPanel({
  appointments,
  doctorNameById,
  isLoading,
}: {
  appointments: Appointment[] | undefined;
  doctorNameById: Record<string, string>;
  isLoading: boolean;
}) {
  const scheduled = (appointments ?? []).filter((a) => a.status === "scheduled");
  return (
    <Panel
      icon={CalendarClock}
      title="Upcoming appointments"
      href="/appointments"
      linkLabel="All appointments"
    >
      {isLoading ? (
        <RowSkeleton />
      ) : scheduled.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {scheduled.slice(0, MAX_ROWS).map((a) => (
            <li key={a.id} className="rounded-md bg-secondary/60 px-3 py-2">
              <p className="text-sm font-medium">
                {formatAppointmentDate(a.appointment_date, a.appointment_time)}
              </p>
              <p className="truncate text-xs text-muted-foreground">
                {[
                  a.doctor_contact_id ? doctorNameById[a.doctor_contact_id] : null,
                  a.reason,
                ]
                  .filter(Boolean)
                  .join(" · ") || "No details"}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyLine>None scheduled.</EmptyLine>
      )}
    </Panel>
  );
}
