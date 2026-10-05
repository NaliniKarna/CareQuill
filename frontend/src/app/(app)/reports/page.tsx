import { Suspense } from "react";

import { ListSkeleton } from "@/components/shared/page-states";
import { ReportsView } from "@/features/reports/reports-view";

export default function ReportsPage() {
  return (
    <Suspense fallback={<ListSkeleton />}>
      <ReportsView />
    </Suspense>
  );
}
