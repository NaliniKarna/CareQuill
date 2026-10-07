"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Eye, FileText, Info, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState, ErrorState, ListSkeleton, PageHeader } from "@/components/shared/page-states";
import { DocumentViewer } from "@/features/medical-records/document-viewer";
import {
  DOCUMENT_CATEGORIES,
  UploadDocumentDialog,
} from "@/features/medical-records/upload-document-dialog";
import { familyService } from "@/services/family-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { formatBytes } from "@/lib/utils";
import type { FamilyDocument, FamilyMember } from "@/types/api";

function categoryLabel(category: string | null): string | null {
  if (!category) return null;
  return DOCUMENT_CATEGORIES.find((c) => c.value === category)?.label ?? category;
}

export function MemberDocumentsTab({ member }: { member: FamilyMember }) {
  const queryClient = useQueryClient();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [viewing, setViewing] = useState<FamilyDocument | null>(null);
  const [deleting, setDeleting] = useState<FamilyDocument | null>(null);
  const isHelper = member.link_status === "active";

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["family", "documents", member.id],
    queryFn: () => familyService.listDocuments(member.id),
  });

  const deleteMutation = useMutation({
    mutationFn: (doc: FamilyDocument) => familyService.removeDocument(member.id, doc.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["family"] });
      toast.success("Document deleted.");
      setDeleting(null);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to delete this document.")),
  });

  const download = (doc: FamilyDocument) =>
    familyService
      .downloadDocument(member.id, doc.id, doc.original_filename)
      .catch((error) => toast.error(getApiErrorMessage(error, "Unable to download this file.")));

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        compact
        title="Documents"
        description={`Reports, prescriptions and scans for ${member.full_name}.`}
        action={
          <Button onClick={() => setUploadOpen(true)}>
            <Plus /> Add document
          </Button>
        }
      />

      {isHelper && (
        <Alert>
          <Info />
          <AlertDescription>
            These are in {member.full_name}&apos;s own account. Files you add appear there for them to
            review. You can view, add and share, but only they can delete.
          </AlertDescription>
        </Alert>
      )}

      {isLoading && <ListSkeleton rows={3} />}
      {isError && <ErrorState description="Couldn't load documents." onRetry={() => refetch()} />}
      {data && data.length === 0 && (
        <EmptyState
          icon={FileText}
          title="No documents yet"
          description="Add a report or scan. The original file is stored unchanged."
          action={
            <Button onClick={() => setUploadOpen(true)}>
              <Plus /> Add document
            </Button>
          }
        />
      )}

      {data && data.length > 0 && (
        <ul className="flex flex-col gap-3">
          {data.map((doc) => (
            <li key={doc.id}>
              <Card>
                <CardContent className="flex flex-wrap items-center gap-3">
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                    <FileText className="size-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{doc.title}</p>
                    <p className="truncate text-sm text-muted-foreground">
                      {doc.original_filename} · {formatBytes(doc.file_size)}
                      {doc.visit_date ? ` · ${doc.visit_date}` : ""}
                    </p>
                    {(doc.doctor_name || doc.hospital_name) && (
                      <p className="truncate text-xs text-muted-foreground">
                        {[doc.doctor_name, doc.hospital_name].filter(Boolean).join(" · ")}
                      </p>
                    )}
                  </div>
                  {categoryLabel(doc.category) && <Badge variant="secondary">{categoryLabel(doc.category)}</Badge>}
                  <div className="flex gap-0.5">
                    <Button variant="ghost" size="icon" aria-label={`View ${doc.title}`} onClick={() => setViewing(doc)}>
                      <Eye className="size-4" />
                    </Button>
                    <Button variant="ghost" size="icon" aria-label={`Download ${doc.title}`} onClick={() => download(doc)}>
                      <Download className="size-4" />
                    </Button>
                    {doc.can_delete && (
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Delete ${doc.title}`}
                        onClick={() => setDeleting(doc)}
                      >
                        <Trash2 className="size-4 text-destructive" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <UploadDocumentDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        uploader={(input) => familyService.uploadDocument(member.id, input)}
        invalidate={[["family"]]}
        description={
          isHelper
            ? `Added to ${member.full_name}'s own account. PDF, JPG or PNG; the original is preserved.`
            : "Accepted formats: PDF, JPG, PNG. Your original file is always preserved."
        }
        successMessage={isHelper ? "Added to their record." : "Document added."}
      />

      <Dialog open={Boolean(viewing)} onOpenChange={(open) => !open && setViewing(null)}>
        <DialogContent className="sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle className="truncate">{viewing?.title}</DialogTitle>
          </DialogHeader>
          {viewing && (
            <DocumentViewer
              document={viewing}
              cacheKey={`family-${member.id}-${viewing.id}`}
              loadPreview={() => familyService.previewDocument(member.id, viewing.id)}
            />
          )}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Delete this document?"
        description={`"${deleting?.title ?? ""}" and its stored file will be permanently removed.`}
        confirmLabel="Delete"
        destructive
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleting && deleteMutation.mutate(deleting)}
      />
    </div>
  );
}
