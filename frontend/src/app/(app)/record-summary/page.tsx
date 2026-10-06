import { Suspense } from "react";

import { ListSkeleton } from "@/components/shared/page-states";
import { AISummaryView } from "@/features/ai-summary/ai-summary-view";

export default function AISummaryPage() {
  return (
    <Suspense fallback={<ListSkeleton />}>
      <AISummaryView />
    </Suspense>
  );
}
