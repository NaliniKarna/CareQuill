import { Suspense } from "react";

import { ListSkeleton } from "@/components/shared/page-states";
import { SettingsView } from "@/features/settings/settings-view";

export default function SettingsPage() {
  return (
    <Suspense fallback={<ListSkeleton />}>
      <SettingsView />
    </Suspense>
  );
}
