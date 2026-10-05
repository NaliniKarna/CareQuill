"use client";

import { useSearchParams } from "next/navigation";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/shared/page-states";

import { EmailHistoryView } from "./email-history-view";
import { ReportBuilderView } from "./report-builder-view";

export function ReportsView() {
  const searchParams = useSearchParams();
  const summaryId = searchParams.get("summary") ?? undefined;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Health reports"
        description="Build a report from your records and share it with a doctor by email."
      />

      <Tabs defaultValue="build">
        <TabsList>
          <TabsTrigger value="build">Share report</TabsTrigger>
          <TabsTrigger value="history">Email history</TabsTrigger>
        </TabsList>
        <TabsContent value="build" className="pt-4">
          <ReportBuilderView initialAiSummaryId={summaryId} />
        </TabsContent>
        <TabsContent value="history" className="pt-4">
          <EmailHistoryView />
        </TabsContent>
      </Tabs>
    </div>
  );
}
