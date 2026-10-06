"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Eye,
  Info,
  Loader2,
  MessageCircleQuestion,
  Plus,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { AllergyFormDialog, type AllergyPrefill } from "@/features/allergies/allergy-form-dialog";
import {
  ConditionFormDialog,
  type ConditionPrefill,
} from "@/features/conditions/condition-form-dialog";
import {
  MedicationFormDialog,
  type MedicationPrefill,
} from "@/features/medications/medication-form-dialog";
import { documentService } from "@/services/document-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { DocumentExplanation, ExtractedData, MedicalDocument } from "@/types/api";

import { DocumentViewer } from "./document-viewer";

type Adding =
  | { kind: "medication"; prefill: MedicationPrefill }
  | { kind: "allergy"; prefill: AllergyPrefill }
  | { kind: "condition"; prefill: ConditionPrefill };

const SECTION_LABEL = "text-xs font-medium text-muted-foreground uppercase tracking-wide";

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className="ml-2 h-6 px-2 text-xs"
      aria-label={label}
      onClick={onClick}
    >
      <Plus className="size-3" />
      Review &amp; add
    </Button>
  );
}

function EntityList({
  label,
  items,
  onAdd,
}: {
  label: string;
  items: string[] | undefined;
  onAdd?: (item: string) => void;
}) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <p className={SECTION_LABEL}>{label}</p>
      <ul className="mt-1 list-disc pl-5 text-sm">
        {items.map((item, i) => (
          <li key={i}>
            {item}
            {onAdd && <AddButton label={`Review and add ${item}`} onClick={() => onAdd(item)} />}
          </li>
        ))}
      </ul>
    </div>
  );
}

function hasStructuredData(e: ExtractedData | null | undefined): boolean {
  return Boolean(
    e &&
      (e.medications?.length ||
        e.conditions?.length ||
        e.allergies?.length ||
        e.procedures?.length ||
        e.dates?.length ||
        e.lab_values?.length ||
        e.recommendations?.length)
  );
}

function ExplanationCard({ explanation }: { explanation: DocumentExplanation }) {
  return (
    <div className="flex flex-col gap-3 rounded-md border border-border p-3">
      <p className="text-sm">{explanation.explanation}</p>
      {explanation.terms.length > 0 && (
        <div>
          <p className={SECTION_LABEL}>Terms</p>
          <ul className="mt-1 list-disc pl-5 text-sm">
            {explanation.terms.map((t, i) => (
              <li key={i}>
                <span className="font-medium">{t.term}</span>: {t.meaning}
              </li>
            ))}
          </ul>
        </div>
      )}
      {explanation.questions_for_doctor.length > 0 && (
        <div>
          <p className={SECTION_LABEL}>Questions you could ask your doctor</p>
          <ul className="mt-1 list-disc pl-5 text-sm">
            {explanation.questions_for_doctor.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-xs text-muted-foreground">
        AI-generated plain-language explanation of the wording ({explanation.model}). It is not a
        diagnosis or medical advice.
      </p>
    </div>
  );
}

export function DocumentExtractionPanel({ document }: { document: MedicalDocument }) {
  const queryClient = useQueryClient();
  const [showRawText, setShowRawText] = useState(false);
  const [showViewer, setShowViewer] = useState(false);
  const [adding, setAdding] = useState<Adding | null>(null);
  const [explanation, setExplanation] = useState<DocumentExplanation | null>(null);

  const ready = document.processing_status === "processed" || document.processing_status === "failed";

  const { data, isLoading, isError } = useQuery({
    queryKey: ["document-extraction", document.id],
    queryFn: () => documentService.getExtraction(document.id),
    enabled: ready,
    retry: false,
    // The AI step runs after the quick OCR step; keep checking until it settles.
    refetchInterval: (query) =>
      query.state.data?.extracted_data?.ai_status === "pending" ? 3000 : false,
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

  const reprocessMutation = useMutation({
    mutationFn: () => documentService.reprocess(document.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["document-extraction", document.id] });
      toast.success("Reading this document again...");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to re-read this document.")),
  });

  const explainMutation = useMutation({
    mutationFn: () => documentService.explain(document.id),
    onSuccess: (result) => setExplanation(result),
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to explain this document.")),
  });

  const viewer = (
    <div className="flex flex-col gap-2">
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="self-start"
        onClick={() => setShowViewer((v) => !v)}
      >
        <Eye className="size-4" />
        {showViewer ? "Hide original" : "View original"}
      </Button>
      {showViewer && <DocumentViewer document={document} />}
    </div>
  );

  if (document.processing_status === "uploaded" || document.processing_status === "processing") {
    return (
      <div className="flex flex-col gap-3">
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          This document is still being read. You can already view the original.
        </p>
        {viewer}
      </div>
    );
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
      <div className="flex flex-col gap-3">
        <p className="text-sm text-muted-foreground">
          Nothing could be extracted from this document automatically. The original is kept safe.
        </p>
        {viewer}
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="self-start"
          disabled={reprocessMutation.isPending}
          onClick={() => reprocessMutation.mutate()}
        >
          {reprocessMutation.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw className="size-4" />}
          Try reading again
        </Button>
      </div>
    );
  }

  const extracted = data.extracted_data;
  const isImage = extracted?.document_kind === "medical_image";
  const structured = hasStructuredData(extracted);
  const aiStatus = extracted?.ai_status;
  const canExplain = Boolean(data.raw_text) && !isImage;

  return (
    <div className="flex flex-col gap-4">
      <Alert variant="warning">
        <AlertTriangle />
        <AlertTitle>Automatic reading -- review before treating as fact</AlertTitle>
        <AlertDescription>
          This was pulled from your document by OCR{aiStatus === "done" ? " and AI" : ""} and may
          contain errors. Nothing is added to your Medications, Conditions or Allergies unless you
          choose &quot;Review &amp; add&quot; and save it yourself.
        </AlertDescription>
      </Alert>

      {isImage && extracted?.imaging && (
        <Alert>
          <Info />
          <AlertTitle>Medical image</AlertTitle>
          <AlertDescription>
            <p>{extracted.imaging.notice}</p>
            {extracted.imaging.ai_description && (
              <p className="mt-2">
                Description (AI, not a finding):{" "}
                {[
                  extracted.imaging.ai_description.modality,
                  extracted.imaging.ai_description.body_region,
                  extracted.imaging.ai_description.view,
                ]
                  .filter(Boolean)
                  .join(" · ") || "n/a"}
                {extracted.imaging.ai_description.quality_notes
                  ? ` -- ${extracted.imaging.ai_description.quality_notes}`
                  : ""}
              </p>
            )}
            {(extracted.imaging.annotations?.text_lines?.length ?? 0) > 0 && (
              <p className="mt-2">
                Text printed on the image: {extracted.imaging.annotations?.text_lines?.join(" | ")}
              </p>
            )}
          </AlertDescription>
        </Alert>
      )}

      {!isImage && extracted?.notice && (
        <Alert>
          <Info />
          <AlertDescription>{extracted.notice}</AlertDescription>
        </Alert>
      )}

      {viewer}

      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={data.status === "reviewed" ? "success" : data.status === "dismissed" ? "secondary" : "warning"}>
          {data.status.replace("_", " ")}
        </Badge>
        {data.confidence !== null && (
          <span className="text-xs text-muted-foreground">
            OCR confidence: {Math.round(data.confidence * 100)}%
          </span>
        )}
        {aiStatus === "pending" && (
          <Badge variant="secondary">
            <Loader2 className="mr-1 size-3 animate-spin" />
            AI is reading...
          </Badge>
        )}
        {aiStatus === "done" && (
          <Badge variant="secondary">
            <Sparkles className="mr-1 size-3" />
            AI-assisted
          </Badge>
        )}
        {aiStatus === "failed" && <Badge variant="secondary">AI step failed -- OCR result shown</Badge>}
      </div>

      {extracted?.ai_summary && <p className="text-sm">{extracted.ai_summary}</p>}

      {structured ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {extracted?.medications && extracted.medications.length > 0 && (
            <div>
              <p className={SECTION_LABEL}>Medications</p>
              <ul className="mt-1 list-disc pl-5 text-sm">
                {extracted.medications.map((med, i) => (
                  <li key={i}>
                    {med.name}
                    {med.dosage ? ` — ${med.dosage}` : ""}
                    {med.frequency ? ` (${med.frequency})` : ""}
                    <AddButton
                      label={`Review and add ${med.name ?? "medication"}`}
                      onClick={() =>
                        setAdding({
                          kind: "medication",
                          prefill: {
                            name: med.name,
                            dosage: med.dosage,
                            frequency: med.frequency,
                          },
                        })
                      }
                    />
                  </li>
                ))}
              </ul>
            </div>
          )}
          <EntityList
            label="Conditions"
            items={extracted?.conditions}
            onAdd={(name) => setAdding({ kind: "condition", prefill: { name } })}
          />
          <EntityList
            label="Allergies"
            items={extracted?.allergies}
            onAdd={(name) => setAdding({ kind: "allergy", prefill: { name } })}
          />
          <EntityList label="Procedures" items={extracted?.procedures} />
          <EntityList label="Dates mentioned" items={extracted?.dates} />
          <EntityList label="Recommendations" items={extracted?.recommendations} />
          {extracted?.lab_values && extracted.lab_values.length > 0 && (
            <div>
              <p className={SECTION_LABEL}>Lab values</p>
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
        !isImage && (
          <p className="text-sm text-muted-foreground">No structured entities were detected in this document.</p>
        )
      )}

      {canExplain && (
        <div className="flex flex-col gap-2">
          {!explanation && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="self-start"
              disabled={explainMutation.isPending}
              onClick={() => explainMutation.mutate()}
            >
              {explainMutation.isPending ? (
                <Loader2 className="animate-spin" />
              ) : (
                <MessageCircleQuestion className="size-4" />
              )}
              Explain in plain language
            </Button>
          )}
          {explanation && <ExplanationCard explanation={explanation} />}
        </div>
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
        <Button
          type="button"
          size="sm"
          variant="ghost"
          disabled={reprocessMutation.isPending}
          onClick={() => reprocessMutation.mutate()}
        >
          {reprocessMutation.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw className="size-4" />}
          Re-read
        </Button>
      </div>

      <MedicationFormDialog
        open={adding?.kind === "medication"}
        onOpenChange={(o) => !o && setAdding(null)}
        medication={null}
        prefill={adding?.kind === "medication" ? adding.prefill : undefined}
        sourceDocumentId={document.id}
      />
      <AllergyFormDialog
        open={adding?.kind === "allergy"}
        onOpenChange={(o) => !o && setAdding(null)}
        allergy={null}
        prefill={adding?.kind === "allergy" ? adding.prefill : undefined}
        sourceDocumentId={document.id}
      />
      <ConditionFormDialog
        open={adding?.kind === "condition"}
        onOpenChange={(o) => !o && setAdding(null)}
        condition={null}
        prefill={adding?.kind === "condition" ? adding.prefill : undefined}
        sourceDocumentId={document.id}
      />
    </div>
  );
}
