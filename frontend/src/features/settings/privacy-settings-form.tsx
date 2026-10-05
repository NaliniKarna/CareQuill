"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { preferenceService } from "@/services/preference-service";
import { getApiErrorMessage } from "@/lib/api-client";

export function PrivacySettingsForm() {
  const queryClient = useQueryClient();
  const { data: preferences, isLoading } = useQuery({
    queryKey: ["preferences"],
    queryFn: () => preferenceService.get(),
  });

  const mutation = useMutation({
    mutationFn: (data_sharing_consent: boolean) => preferenceService.update({ data_sharing_consent }),
    onSuccess: (data) => {
      queryClient.setQueryData(["preferences"], data);
      toast.success(
        data.data_sharing_consent
          ? "AI/OCR processing is now enabled for future uploads."
          : "AI/OCR processing is now disabled for future uploads."
      );
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to update this setting.")),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Privacy</CardTitle>
        <CardDescription>Control how your documents are processed.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {isLoading && <Skeleton className="h-16" />}
        {preferences && (
          <div className="flex items-start justify-between gap-4">
            <div>
              <Label htmlFor="data-sharing-consent">Allow AI &amp; OCR processing of new documents</Label>
              <p className="text-xs text-muted-foreground">
                When enabled, medical documents you upload from now on are automatically scanned
                (OCR) and summarized by AI so you can review and confirm the extracted details.
                When disabled, new uploads are stored as-is and are never sent to OCR or AI
                processing — you can still add their details manually. This never changes how
                documents already processed were handled.
              </p>
            </div>
            <Switch
              id="data-sharing-consent"
              checked={preferences.data_sharing_consent}
              disabled={mutation.isPending}
              onCheckedChange={(checked) => mutation.mutate(checked)}
            />
          </div>
        )}

        <Alert>
          <AlertTitle>About AI in MedQueue AI</AlertTitle>
          <AlertDescription>
            AI-extracted or AI-generated information is always a suggestion you must review and
            confirm before it becomes part of your verified record. MedQueue AI does not diagnose
            conditions, prescribe treatment, or replace professional medical advice. See your{" "}
            <Link href="/ai-summary" className="text-primary hover:underline">
              AI summary page
            </Link>{" "}
            for the review step.
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );
}
