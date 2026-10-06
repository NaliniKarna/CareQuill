"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronUp,
  Download,
  FileStack,
  Loader2,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { Badge, badgeVariants } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState, ErrorState, ListSkeleton, PageHeader } from "@/components/shared/page-states";
import { documentService } from "@/services/document-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { MedicalDocument } from "@/types/api";
import type { VariantProps } from "class-variance-authority";

import { DOCUMENT_CATEGORIES, UploadDocumentDialog } from "./upload-document-dialog";
import { DocumentExtractionPanel } from "./document-extraction-panel";

type BadgeVariant = VariantProps<typeof badgeVariants>["variant"];

const PROCESSING_VARIANT: Record<string, BadgeVariant> = {
  uploaded: "secondary",
  processing: "warning",
  processed: "success",
  failed: "destructive",
};

const OCR_VARIANT: Record<string, BadgeVariant> = {
  pending: "secondary",
  processing: "warning",
  completed: "success",
  failed: "destructive",
  skipped: "outline",
  no_text: "outline",
  not_applicable: "outline",
};

const OCR_LABEL: Record<string, string> = {
  skipped: "OCR: off",
  no_text: "OCR: no text found",
  not_applicable: "Image (not text)",
};

const PAGE_SIZE = 20;

function categoryLabel(category: string | null): string {
  if (!category) return "Uncategorized";
  return DOCUMENT_CATEGORIES.find((c) => c.value === category)?.label ?? category;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function MedicalRecordsView({ embedded = false }: { embedded?: boolean } = {}) {
  const queryClient = useQueryClient();
  const [category, setCategory] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<MedicalDocument | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["documents", category, search, offset],
    queryFn: () =>
      documentService.list({
        category: category === "all" ? undefined : category,
        q: search.trim() || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
    // Uploads are read in the background; poll only while something is in flight.
    refetchInterval: (query) =>
      query.state.data?.items.some(
        (d) => d.processing_status === "uploaded" || d.processing_status === "processing"
      )
        ? 3000
        : false,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      toast.success("Document deleted.");
      setDeleting(null);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to delete this document.")),
  });

  const handleDownload = async (doc: MedicalDocument) => {
    setDownloadingId(doc.id);
    try {
      await documentService.download(doc.id, doc.original_filename);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Unable to download this document."));
    } finally {
      setDownloadingId(null);
    }
  };

  const items = data?.items ?? [];
  const hasMore = data ? offset + items.length < data.total : false;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        compact={embedded}
        title={embedded ? "Documents" : "Medical records"}
        description="Upload and review your lab reports, prescriptions, and other documents."
        action={
          <Button onClick={() => setUploadOpen(true)}>
            <Plus /> Upload document
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by title, doctor, or hospital..."
            className="pl-8"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
          />
        </div>
        <Select
          value={category}
          onValueChange={(v) => {
            setCategory(v);
            setOffset(0);
          }}
        >
          <SelectTrigger className="sm:w-56">
            <SelectValue placeholder="All categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {DOCUMENT_CATEGORIES.map((c) => (
              <SelectItem key={c.value} value={c.value}>
                {c.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading && <ListSkeleton />}
      {isError && <ErrorState description="Couldn't load your documents." onRetry={() => refetch()} />}

      {data && items.length === 0 && (
        <EmptyState
          icon={FileStack}
          title="No documents found"
          description="Upload a lab report, prescription, or other medical document to get started."
          action={
            <Button onClick={() => setUploadOpen(true)}>
              <Plus /> Upload document
            </Button>
          }
        />
      )}

      {items.length > 0 && (
        <div className="flex flex-col gap-3">
          {items.map((doc) => {
            const expanded = expandedId === doc.id;
            return (
              <Card key={doc.id}>
                <CardContent className="flex flex-col gap-3">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex flex-col gap-1">
                      <p className="font-medium">{doc.title}</p>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline">{categoryLabel(doc.category)}</Badge>
                        <Badge variant={PROCESSING_VARIANT[doc.processing_status] ?? "secondary"}>
                          {doc.processing_status}
                        </Badge>
                        <Badge variant={OCR_VARIANT[doc.ocr_status] ?? "secondary"}>
                          {OCR_LABEL[doc.ocr_status] ?? `OCR: ${doc.ocr_status}`}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {doc.original_filename} · {formatBytes(doc.file_size)}
                        {doc.visit_date ? ` · Visit ${doc.visit_date}` : ""}
                      </p>
                      {(doc.doctor_name || doc.hospital_name) && (
                        <p className="text-xs text-muted-foreground">
                          {[doc.doctor_name, doc.hospital_name].filter(Boolean).join(" · ")}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setExpandedId(expanded ? null : doc.id)}
                      >
                        {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
                        {expanded ? "Hide" : "Review"}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Download"
                        disabled={downloadingId === doc.id}
                        onClick={() => handleDownload(doc)}
                      >
                        {downloadingId === doc.id ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          <Download className="size-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Delete"
                        onClick={() => setDeleting(doc)}
                      >
                        <Trash2 className="size-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                  {expanded && (
                    <div className="border-t border-border pt-3">
                      <DocumentExtractionPanel document={doc} />
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
          {hasMore && (
            <Button variant="outline" onClick={() => setOffset((o) => o + PAGE_SIZE)} disabled={isLoading}>
              Load more
            </Button>
          )}
        </div>
      )}

      <UploadDocumentDialog open={uploadOpen} onOpenChange={setUploadOpen} />

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Delete this document?"
        description={`This will permanently delete "${deleting?.title}" and its file from storage. This cannot be undone.`}
        confirmLabel="Delete"
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
      />
    </div>
  );
}
