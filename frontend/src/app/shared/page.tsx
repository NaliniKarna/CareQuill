import type { Metadata } from "next";

import { SharedReportView } from "@/features/shared-report/shared-report-view";

export const metadata: Metadata = {
  title: "Shared health report · CareQuill",
  // Private, patient-shared content: keep it out of search engines and
  // never leak the page address to other sites.
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default function SharedReportPage() {
  return <SharedReportView />;
}
