"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ChevronDown,
  FileText,
  Loader2,
  RefreshCw,
  Send,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState, ErrorState, ListSkeleton, PageHeader } from "@/components/shared/page-states";
import { aiSummaryService } from "@/services/ai-summary-service";
import { documentService } from "@/services/document-service";
import { healthSnapshotService } from "@/services/health-snapshot-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { AISummary } from "@/types/api";

import { ShareSummaryDialog } from "./share-summary-dialog";
import { SummaryReviewPanel } from "./summary-review-panel";

export const STATUS_LABEL: Record<string, string> = {
  pending_review: "Needs review",
  reviewed: "Reviewed",
  shared: "Shared",
  outdated: "Outdated",
};

export const STATUS_VARIANT: Record<string, "warning" | "secondary" | "success" | "default"> = {
  pending_review: "warning",
  reviewed: "secondary",
  shared: "success",
  outdated: "default",
};

/** Step 1: the verified data the summary is written from. */
function SnapshotLine() {
  const queryClient = useQueryClient();
  const { data: snapshot, isLoading } = useQuery({
    queryKey: ["health-snapshot-latest"],
    queryFn: () => healthSnapshotService.getLatest(),
  });

  const refreshMutation = useMutation({
    mutationFn: () => healthSnapshotService.generate(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["health-snapshot-latest"] });
      toast.success("Your records were refreshed.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to refresh your records.")),
  });

  return (
    <div className="flex items-center justify-between gap-3 rounded-lg bg-muted/60 px-3 py-2.5">
      <div className="min-w-0 text-sm">
        <p className="font-medium">Based on your confirmed records</p>
        <p className="truncate text-xs text-muted-foreground">
          {isLoading
            ? "Checking..."
            : snapshot
              ? `Last refreshed ${new Date(snapshot.created_at).toLocaleDateString()}`
              : "Not refreshed yet - refresh before generating."}
        </p>
      </div>
      <Button
        variant="outline"
        size="sm"
        disabled={refreshMutation.isPending}
        onClick={() => refreshMutation.mutate()}
      >
        {refreshMutation.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />}
        Refresh
      </Button>
    </div>
  );
}

function CreateSummaryCard({ onGenerated }: { onGenerated: (summary: AISummary) => void }) {
  const queryClient = useQueryClient();
  const [concerns, setConcerns] = useState("");
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [docsOpen, setDocsOpen] = useState(false);

  const { data: recentDocs } = useQuery({
    queryKey: ["documents", "recent-for-summary"],
    queryFn: () => documentService.list({ limit: 10 }),
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      aiSummaryService.generate({
        patient_concerns: concerns.trim() || undefined,
        include_document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
      }),
    onSuccess: (summary) => {
      queryClient.invalidateQueries({ queryKey: ["ai-summaries"] });
      toast.success("Your summary is ready. Review it before sharing.");
      setConcerns("");
      setSelectedDocIds([]);
      onGenerated(summary);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to create a summary.")),
  });

  const toggleDoc = (id: string) =>
    setSelectedDocIds((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]));

  const docs = recentDocs?.items ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <Sparkles className="size-4" />
          </span>
          New summary
        </CardTitle>
        <CardDescription>AI writes a draft from your records. You approve it.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <SnapshotLine />

        <div className="flex flex-col gap-2">
          <Label htmlFor="patient-concerns">Anything to mention? (optional)</Label>
          <Textarea
            id="patient-concerns"
            rows={3}
            placeholder="e.g. Headaches in the mornings this week"
            value={concerns}
            onChange={(e) => setConcerns(e.target.value)}
          />
        </div>

        {docs.length > 0 && (
          <div className="flex flex-col gap-2">
            <button
              type="button"
              onClick={() => setDocsOpen((o) => !o)}
              aria-expanded={docsOpen}
              className="flex items-center justify-between text-sm font-medium"
            >
              <span>
                Add documents as context
                {selectedDocIds.length > 0 && (
                  <span className="ml-2 text-xs font-normal text-primary">
                    {selectedDocIds.length} selected
                  </span>
                )}
              </span>
              <ChevronDown
                className={cn("size-4 text-muted-foreground transition-transform", docsOpen && "rotate-180")}
              />
            </button>
            {docsOpen && (
              <div className="flex max-h-44 flex-col gap-2 overflow-y-auto rounded-lg border p-3">
                {docs.map((doc) => (
                  <label key={doc.id} className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={selectedDocIds.includes(doc.id)}
                      onCheckedChange={() => toggleDoc(doc.id)}
                    />
                    <span className="truncate">{doc.title}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        )}

        <Button disabled={generateMutation.isPending} onClick={() => generateMutation.mutate()}>
          {generateMutation.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
          {generateMutation.isPending ? "Writing your summary..." : "Create summary"}
        </Button>
      </CardContent>
    </Card>
  );
}

function HistoryCard({
  summaries,
  selectedId,
  onSelect,
}: {
  summaries: AISummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  if (summaries.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Previous summaries</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-1.5">
        {summaries.slice(0, 6).map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => onSelect(s.id)}
            aria-current={s.id === selectedId ? "true" : undefined}
            className={cn(
              "flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors",
              s.id === selectedId ? "border-primary bg-accent" : "border-transparent hover:bg-muted",
            )}
          >
            <span>{new Date(s.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}</span>
            <Badge variant={STATUS_VARIANT[s.status] ?? "secondary"}>
              {STATUS_LABEL[s.status] ?? s.status}
            </Badge>
          </button>
        ))}
      </CardContent>
    </Card>
  );
}

/** Tells the patient up front whether AI is usable, instead of letting them
 * click Create and hit an opaque server error. */
function AIStatusBanner() {
  const { data } = useQuery({
    queryKey: ["ai-status"],
    queryFn: () => aiSummaryService.status(),
    staleTime: 60_000,
    retry: false,
  });
  if (!data || (data.enabled && data.available && data.model_ready !== false)) return null;
  return (
    <Alert variant="warning">
      <AlertTriangle />
      <AlertTitle>Summaries are not available right now</AlertTitle>
      <AlertDescription>
        {data.detail ??
          "The AI service is not configured. Your records, documents and reports still work normally."}
      </AlertDescription>
    </Alert>
  );
}

export function AISummaryView() {
  const searchParams = useSearchParams();
  const preselectedId = searchParams.get("id");
  const [selectedId, setSelectedId] = useState<string | null>(preselectedId);
  const [shareOpen, setShareOpen] = useState(false);

  const { data: summaries, isLoading, isError, refetch } = useQuery({
    queryKey: ["ai-summaries"],
    queryFn: () => aiSummaryService.list(),
  });

  // Default to the most recent summary until the person picks one.
  const effectiveSelectedId = selectedId ?? summaries?.[0]?.id ?? null;
  const selected = summaries?.find((s) => s.id === effectiveSelectedId) ?? null;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Record Summary"
        description="A clear summary of your health record. AI writes the draft, you review and approve it, then share it with a doctor if you wish."
        action={
          selected && (selected.status === "reviewed" || selected.status === "shared") ? (
            <Button asChild>
              <Link href={`/appointments?tab=share&summary=${selected.id}`}>
                <Send /> Share with a doctor
              </Link>
            </Button>
          ) : undefined
        }
      />

      <AIStatusBanner />

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[22rem_minmax(0,1fr)] lg:items-start">
        <div className="flex min-w-0 flex-col gap-6">
          <CreateSummaryCard onGenerated={(summary) => setSelectedId(summary.id)} />
          {summaries && (
            <HistoryCard
              summaries={summaries}
              selectedId={effectiveSelectedId}
              onSelect={setSelectedId}
            />
          )}
        </div>

        <div className="min-w-0">
          {isLoading && <ListSkeleton rows={2} />}
          {isError && (
            <ErrorState description="Couldn't load your summaries." onRetry={() => refetch()} />
          )}
          {selected && <SummaryReviewPanel summary={selected} onShare={() => setShareOpen(true)} />}
          {summaries && summaries.length === 0 && (
            <Card>
              <CardContent>
                <EmptyState
                  icon={FileText}
                  title="No summaries yet"
                  description="Create your first summary on the left. It stays a draft until you approve it."
                />
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <ShareSummaryDialog open={shareOpen} onOpenChange={setShareOpen} summary={selected} />
    </div>
  );
}
