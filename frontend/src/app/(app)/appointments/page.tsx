import { Suspense } from "react";

import { AppointmentsHub } from "@/features/appointments/appointments-hub";

export default function AppointmentsPage() {
  return (
    <Suspense fallback={null}>
      <AppointmentsHub />
    </Suspense>
  );
}
