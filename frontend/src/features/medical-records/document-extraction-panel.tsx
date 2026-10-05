"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { documentService } from "@/services/document-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { MedicalDocument } from "@/types/api";

function EntityList({ label, items }: { label: string; items: string[] | undefined }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
      <ul className="mt-1 list-disc pl-5 text-sm">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function DocumentExtractionPanel({ document }: { document: MedicalDocument }) {
  const queryClient = useQueryClient();
  const [showRawText, setShowRawText] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["document-extraction", document.id],
    queryFn: () => documentService.getExtraction(document.id),
    enabled: document.processing_status === "processed" || document.processing_status === "failed",
    retry: false,
  });

  const statusMutation = useMutation({
    mutationFn: (status: "reviewed" | "dismissed") =>
      documentService.updateExtractionStatus(document.id, status),
    onSuccess: (_, status) => {
      queryClient.invalidateQueries({ queryKey: ["document-extraction", document.id] });
      toast.success(status === "reviewed" ? "Marked as reviewed." : "Extraction dismissed.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to update the extraction status.")),
  });

  if (document.processing_status === "uploaded" || document.processing_status === "processing") {
    return <p className="text-sm text-muted-foreground">OCR processing is still running for this document.</p>;
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-16" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-muted-foreground">
        No AI extraction is available for this document (processing may have found no readable text).
      </p>
    );
  }

  const extracted = data.extracted_data;
  const hasStructuredData =
    extracted &&
    (extracted.medications?.length ||
      extracted.conditions?.length ||
      extracted.allergies?.length ||
      extracted.procedures?.length ||
      extracted.dates?.length ||
      extracted.lab_values?.length ||
      extracted.recommendations?.length);

  return (
    <div className="flex flex-col gap-4">
      <Alert variant="warning">
        <AlertTriangle />
        <AlertTitle>AI-extracted -- review before treating as fact</AlertTitle>
        <AlertDescription>
          This information was pulled automatically from your document with OCR. It may contain
          errors and is never written into your Medications, Conditions, or Allergies
          automatically -- add anything you confirm yourself through those pages.
        </AlertDescription>
      </Alert>

      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={data.status === "reviewed" ? "success" : data.status === "dismissed" ? "secondary" : "warning"}>
          {data.status.replace("_", " ")}
        </Badge>
        {data.confidence !== null && (
          <span className="text-xs text-muted-foreground">
            Confidence: {Math.round(data.confidence * 100)}%
          </span>
        )}
      </div>

      {hasStructuredData ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {extracted?.medications && extracted.medications.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Medications
              </p>
              <ul className="mt-1 list-disc pl-5 text-sm">
                {extracted.medications.map((med, i) => (
                  <li key={i}>
                    {med.name}
                    {med.dosage ? ` — ${med.dosage}` : ""}
                    {med.frequency ? ` (${med.frequency})` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <EntityList label="Conditions" items={extracted?.conditions} />
          <EntityList label="Allergies" items={extracted?.allergies} />
          <EntityList label="Procedures" items={extracted?.procedures} />
          <EntityList label="Dates mentioned" items={extracted?.dates} />
          <EntityList label="Recommendations" items={extracted?.recommendations} />
          {extracted?.lab_values && extracted.lab_values.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Lab values</p>
              <ul className="mt-1 list-disc pl-5 text-sm">
                {extracted.lab_values.map((lv, i) => (
                  <li key={i}>
                    {lv.label}: {lv.value} {lv.unit ?? ""}
                    {lv.range ? ` (ref ${lv.range})` : ""}
                    {lv.flag ? (
                      <Badge variant="warning" className="ml-1 align-middle text-[10px]">
                        {lv.flag}
                      </Badge>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No structured entities were detected in this document.</p>
      )}

      {data.raw_text && (
        <div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setShowRawText((s) => !s)}
            className="px-0"
          >
            {showRawText ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
            {showRawText ? "Hide raw OCR text" : "Show raw OCR text"}
          </Button>
          {showRawText && (
            <pre className="mt-2 max-h-64 overflow-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap">
              {data.raw_text}
            </pre>
          )}
        </div>
      )}

      <Separator />

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={data.status === "reviewed" || statusMutation.isPending}
          onClick={() => statusMutation.mutate("reviewed")}
        >
          {statusMutation.isPending && statusMutation.variables === "reviewed" && (
            <Loader2 className="animate-spin" />
          )}
          Mark reviewed
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={data.status === "dismissed" || statusMutation.isPending}
          onClick={() => statusMutation.mutate("dismissed")}
        >
          {statusMutation.isPending && statusMutation.variables === "dismissed" && (
            <Loader2 className="animate-spin" />
          )}
          Dismiss
        </Button>
      </div>
    </div>
  );
}