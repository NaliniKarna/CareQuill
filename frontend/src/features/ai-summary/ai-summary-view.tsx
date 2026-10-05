"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, FileText, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";

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
import type { AISummary } from "@/types/api";

import { ShareSummaryDialog } from "./share-summary-dialog";
import { SummaryReviewPanel } from "./summary-review-panel";

const STATUS_VARIANT: Record<string, "warning" | "secondary" | "success" | "default"> = {
  pending_review: "warning",
  reviewed: "secondary",
  shared: "success",
  outdated: "default",
};

function SnapshotSection() {
  const queryClient = useQueryClient();
  const { data: snapshot, isLoading } = useQuery({
    queryKey: ["health-snapshot-latest"],
    queryFn: () => healthSnapshotService.getLatest(),
  });

  const generateMutation = useMutation({
    mutationFn: () => healthSnapshotService.generate(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["health-snapshot-latest"] });
      toast.success("A new health snapshot was generated.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to generate a health snapshot.")),
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Health snapshot</CardTitle>
          <CardDescription>
            A point-in-time capture of your verified health data, used as the basis for AI
            summaries.
          </CardDescription>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={generateMutation.isPending}
          onClick={() => generateMutation.mutate()}
        >
          {generateMutation.isPending ? <Loader2 className="animate-spin" /> : <Camera />}
          Generate new snapshot
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading && <p className="text-sm text-muted-foreground">Loading...</p>}
        {!isLoading && !snapshot && (
          <p className="text-sm text-muted-foreground">
            No snapshot has been generated yet. Generate one before creating an AI summary.
          </p>
        )}
        {snapshot && (
          <p className="text-sm text-muted-foreground">
            Version {snapshot.version}, generated {new Date(snapshot.created_at).toLocaleString()}.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function GenerateSummaryCard({ onGenerated }: { onGenerated: (summary: AISummary) => void }) {
  const queryClient = useQueryClient();
  const [concerns, setConcerns] = useState("");
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);

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
      toast.success("A new AI summary was generated. Review it below.");
      onGenerated(summary);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to generate an AI summary.")),
  });

  const toggleDoc = (id: string) => {
    setSelectedDocIds((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generate AI summary</CardTitle>
        <CardDescription>
          Optionally add anything you&apos;d like your doctor to know, and flag recent documents
          as extra context.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="patient-concerns">Concerns to mention (optional)</Label>
          <Textarea
            id="patient-concerns"
            rows={3}
            placeholder="e.g. I've been having headaches in the mornings"
            value={concerns}
            onChange={(e) => setConcerns(e.target.value)}
          />
        </div>
        {recentDocs && recentDocs.items.length > 0 && (
          <div className="flex flex-col gap-2">
            <Label>Include recent documents as context (optional)</Label>
            <div className="flex flex-col gap-2">
              {recentDocs.items.map((doc) => (
                <label key={doc.id} className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={selectedDocIds.includes(doc.id)}
                    onCheckedChange={() => toggleDoc(doc.id)}
                  />
                  {doc.title}
                </label>
              ))}
            </div>
          </div>
        )}
        <Button
          className="self-start"
          disabled={generateMutation.isPending}
          onClick={() => generateMutation.mutate()}
        >
          {generateMutation.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
          Generate AI summary
        </Button>
      </CardContent>
    </Card>
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

  // Default to the most recent summary until the person picks one
  // explicitly -- derived during render rather than via an effect, since
  // it's purely a function of `summaries` and `selectedId`.
  const effectiveSelectedId = selectedId ?? summaries?.[0]?.id ?? null;
  const selected = summaries?.find((s) => s.id === effectiveSelectedId) ?? null;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="AI health summary"
        description="Generate, review, and share an AI-assisted summary of your health record with a doctor."
        action={
          <Button asChild variant="outline">
            <Link href={selected ? `/reports?summary=${selected.id}` : "/reports"}>
              <FileText /> Build a health report
            </Link>
          </Button>
        }
      />

      <SnapshotSection />

      <GenerateSummaryCard onGenerated={(summary) => setSelectedId(summary.id)} />

      {isLoading && <ListSkeleton rows={1} />}
      {isError && <ErrorState description="Couldn't load your AI summaries." onRetry={() => refetch()} />}

      {selected && (
        <SummaryReviewPanel summary={selected} onShare={() => setShareOpen(true)} />
      )}

      <Card>
        <CardHeader>
          <CardTitle>Past summaries</CardTitle>
        </CardHeader>
        <CardContent>
          {summaries && summaries.length === 0 && (
            <EmptyState
              icon={Sparkles}
              title="No summaries yet"
              description="Generate your first AI summary above."
            />
          )}
          {summaries && summaries.length > 0 && (
            <div className="flex flex-col gap-2">
              {summaries.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setSelectedId(s.id)}
                  className={`flex items-center justify-between rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                    s.id === effectiveSelectedId
                      ? "border-primary bg-accent"
                      : "border-border hover:bg-accent"
                  }`}
                >
                  <span>{new Date(s.created_at).toLocaleString()}</span>
                  <Badge variant={STATUS_VARIANT[s.status] ?? "secondary"}>
                    {s.status.replace("_", " ")}
                  </Badge>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <ShareSummaryDialog open={shareOpen} onOpenChange={setShareOpen} summary={selected} />
    </div>
  );
}
