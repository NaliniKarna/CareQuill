"use client";

import { useRef, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Upload } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { documentService } from "@/services/document-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { DocumentCategory } from "@/types/api";

export const DOCUMENT_CATEGORIES: { value: DocumentCategory; label: string }[] = [
  { value: "prescription", label: "Prescription" },
  { value: "blood_test", label: "Blood test" },
  { value: "lab_report", label: "Lab report" },
  { value: "xray", label: "X-ray" },
  { value: "mri", label: "MRI" },
  { value: "ct_scan", label: "CT scan" },
  { value: "discharge_summary", label: "Discharge summary" },
  { value: "vaccination", label: "Vaccination" },
  { value: "referral", label: "Referral" },
  { value: "other", label: "Other" },
];

const MAX_FILE_BYTES = 20 * 1024 * 1024; // matches backend's own hard cap message conventions

const uploadSchema = z.object({
  title: z.string().min(1, "Title is required").max(200),
  category: z.string().optional(),
  visit_date: z.string().optional().or(z.literal("")),
  doctor_name: z.string().max(200).optional().or(z.literal("")),
  hospital_name: z.string().max(200).optional().or(z.literal("")),
});

type UploadFormValues = z.infer<typeof uploadSchema>;

export function UploadDocumentDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: { title: "", category: "", visit_date: "", doctor_name: "", hospital_name: "" },
  });

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      reset();
      setFile(null);
      setFileError(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
    onOpenChange(next);
  };

  const mutation = useMutation({
    mutationFn: (values: UploadFormValues) => {
      if (!file) throw new Error("A file is required.");
      return documentService.upload({
        file,
        title: values.title,
        category: (values.category as DocumentCategory) || undefined,
        visit_date: values.visit_date || undefined,
        doctor_name: values.doctor_name || undefined,
        hospital_name: values.hospital_name || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      toast.success("Document uploaded. It will process in the background.");
      handleOpenChange(false);
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to upload this document.")),
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    if (selected && selected.size > MAX_FILE_BYTES) {
      setFileError("File is too large (max 20 MB).");
      setFile(null);
      return;
    }
    setFileError(null);
    setFile(selected);
  };

  const onSubmit = (values: UploadFormValues) => {
    if (!file) {
      setFileError("Please choose a file to upload.");
      return;
    }
    mutation.mutate(values);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload medical document</DialogTitle>
          <DialogDescription>
            Accepted formats: PDF, JPG, PNG. Your original file is always preserved.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-2">
            <Label htmlFor="doc-file">File</Label>
            <Input
              id="doc-file"
              type="file"
              ref={fileInputRef}
              accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
              onChange={handleFileChange}
              aria-invalid={Boolean(fileError)}
            />
            {file && <p className="text-xs text-muted-foreground">{file.name} ({Math.round(file.size / 1024)} KB)</p>}
            {fileError && <p className="text-sm text-destructive">{fileError}</p>}
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="doc-title">Title</Label>
            <Input
              id="doc-title"
              placeholder="e.g. Blood test results, March 2026"
              aria-invalid={Boolean(errors.title)}
              {...register("title")}
            />
            {errors.title && <p className="text-sm text-destructive">{errors.title.message}</p>}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="doc-category">Category</Label>
              <Controller
                control={control}
                name="category"
                render={({ field }) => (
                  <Select value={field.value || "none"} onValueChange={(v) => field.onChange(v === "none" ? "" : v)}>
                    <SelectTrigger id="doc-category">
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Unspecified</SelectItem>
                      {DOCUMENT_CATEGORIES.map((c) => (
                        <SelectItem key={c.value} value={c.value}>
                          {c.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="doc-visit-date">Visit date</Label>
              <Input id="doc-visit-date" type="date" {...register("visit_date")} />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="doc-doctor">Doctor name</Label>
              <Input id="doc-doctor" {...register("doctor_name")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="doc-hospital">Hospital / clinic</Label>
              <Input id="doc-hospital" {...register("hospital_name")} />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? <Loader2 className="animate-spin" /> : <Upload />}
              Upload
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
