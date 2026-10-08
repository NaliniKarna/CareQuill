"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CalendarClock, Clock, Plus, Stethoscope } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState, ErrorState, ListSkeleton } from "@/components/shared/page-states";
import { appointmentService } from "@/services/appointment-service";
import { doctorService } from "@/services/doctor-service";

import { DateTile } from "./appointments-view";

const SHOWN = 3;

/** The next few upcoming visits, with a link to the full list. */
export function NextAppointments({ onAdd }: { onAdd: () => void }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["appointments", "upcoming"],
    queryFn: () => appointmentService.list("upcoming"),
  });
  const { data: doctors } = useQuery({ queryKey: ["doctors"], queryFn: () => doctorService.list() });
  const doctorName = (id: string | null) => doctors?.find((d) => d.id === id)?.name ?? null;

  return (
    <section aria-labelledby="next-appointments" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="next-appointments" className="text-base font-semibold">
            Next appointments
          </h2>
          <p className="text-sm text-muted-foreground">
            Upcoming visits also appear on your dashboard and in notifications.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link href="/appointments?view=all" scroll={false}>
              View all appointments <ArrowRight />
            </Link>
          </Button>
          <Button onClick={onAdd}>
            <Plus /> Add appointment
          </Button>
        </div>
      </div>

      {isLoading && <ListSkeleton />}
      {isError && <ErrorState description="Couldn't load your appointments." onRetry={() => refetch()} />}

      {data && data.length === 0 && (
        <EmptyState
          icon={CalendarClock}
          title="No upcoming appointments"
          description="Add a visit you have coming up and it will show here."
        />
      )}

      {data && data.length > 0 && (
        <div className="grid grid-cols-[minmax(0,1fr)] gap-3 md:grid-cols-3">
          {data.slice(0, SHOWN).map((appt) => (
            <Card key={appt.id}>
              <CardContent className="flex items-start gap-4">
                <DateTile iso={appt.appointment_date} muted={false} />
                <div className="flex min-w-0 flex-col gap-1">
                  <p className="truncate font-medium">{appt.reason || "Appointment"}</p>
                  <p className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm text-muted-foreground">
                    {appt.appointment_time && (
                      <span className="inline-flex items-center gap-1">
                        <Clock className="size-3.5" /> {appt.appointment_time.slice(0, 5)}
                      </span>
                    )}
                    {doctorName(appt.doctor_contact_id) && (
                      <span className="inline-flex min-w-0 items-center gap-1">
                        <Stethoscope className="size-3.5 shrink-0" />
                        <span className="truncate">{doctorName(appt.doctor_contact_id)}</span>
                      </span>
                    )}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}
