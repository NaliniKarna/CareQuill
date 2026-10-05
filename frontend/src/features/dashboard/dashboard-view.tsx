"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  UserRound,
  Pill,
  FileStack,
  CalendarClock,
  Sparkles,
  Share2,
  AlertCircle,
  ArrowRight,
  AlarmClock,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { dashboardService } from "@/services/dashboard-service";

const QUICK_ACTIONS = [
  { label: "Complete your profile", href: "/profile", icon: UserRound, enabled: true },
  { label: "Add medication", href: "/medications", icon: Pill, enabled: true },
  { label: "Upload report", href: "/medical-records", icon: FileStack, enabled: true },
  { label: "Book appointment", href: "/appointments", icon: CalendarClock, enabled: true },
  { label: "Generate health summary", href: "/ai-summary", icon: Sparkles, enabled: true },
  { label: "Share with doctor", href: "/ai-summary", icon: Share2, enabled: true },
];

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
          <Icon className="size-5" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-lg font-semibold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export function DashboardView() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: dashboardService.get,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-40" />
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

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{data.welcome_message}</h1>
        <p className="text-muted-foreground">Here&apos;s an overview of your health record.</p>
      </div>

      {data.notifications.length > 0 && (
        <div className="flex flex-col gap-2">
          {data.notifications.map((notification) => (
            <Alert key={notification}>
              <AlertCircle />
              <AlertDescription>{notification}</AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <StatCard
          icon={Pill}
          label="Active medications"
          value={data.active_medications_count}
        />
        <StatCard
          icon={FileStack}
          label="Medical documents"
          value={data.recent_documents_count}
        />
        <StatCard
          icon={CalendarClock}
          label="Next appointment"
          value={
            data.next_appointment
              ? `${data.next_appointment.appointment_date}${
                  data.next_appointment.doctor_name ? ` · ${data.next_appointment.doctor_name}` : ""
                }`
              : "None scheduled"
          }
        />
        <StatCard
          icon={AlarmClock}
          label="Reminders due today"
          value={data.reminders_due_today_count}
        />
        <StatCard
          icon={Sparkles}
          label="AI summary"
          value={
            data.latest_ai_summary_status
              ? data.latest_ai_summary_status.replace("_", " ")
              : "Not generated"
          }
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile completion</CardTitle>
          <CardDescription>
            A complete profile helps generate more accurate AI summaries later.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center justify-between text-sm">
            <span>{data.profile_completion_percent}% complete</span>
            {data.profile_completion_percent < 100 && (
              <Link href="/profile" className="flex items-center gap-1 text-primary hover:underline">
                Finish your profile <ArrowRight className="size-3.5" />
              </Link>
            )}
          </div>
          <Progress value={data.profile_completion_percent} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Quick actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {QUICK_ACTIONS.map((action) =>
              action.enabled ? (
                <Button key={action.label} asChild variant="outline" className="justify-start">
                  <Link href={action.href}>
                    <action.icon />
                    {action.label}
                  </Link>
                </Button>
              ) : (
                <Button
                  key={action.label}
                  variant="outline"
                  className="justify-start"
                  disabled
                >
                  <action.icon />
                  {action.label}
                  <Badge variant="secondary" className="ml-auto text-[10px]">
                    Soon
                  </Badge>
                </Button>
              )
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
