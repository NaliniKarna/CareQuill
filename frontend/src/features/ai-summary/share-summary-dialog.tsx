"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, Send, XCircle } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { aiSummaryService } from "@/services/ai-summary-service";
import { doctorService } from "@/services/doctor-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { AISummary, EmailLog } from "@/types/api";

export function ShareSummaryDialog({
  open,
  onOpenChange,
  summary,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  summary: AISummary | null;
}) {
  const queryClient = useQueryClient();
  const [doctorId, setDoctorId] = useState<string>("");
  const [result, setResult] = useState<EmailLog | null>(null);

  const { data: doctors } = useQuery({
    queryKey: ["doctors"],
    queryFn: () => doctorService.list(),
    enabled: open,
  });

  const shareMutation = useMutation({
    mutationFn: () => {
      if (!summary) throw new Error("No summary selected.");
      return aiSummaryService.share(summary.id, doctorId);
    },
    onSuccess: (log) => {
      queryClient.invalidateQueries({ queryKey: ["ai-summaries"] });
      setResult(log);
      if (log.status === "sent") {
        toast.success(`Summary shared with ${log.doctor_email}.`);
      } else {
        toast.error("The email could not be sent.");
      }
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to share this summary.")),
  });

  const doctorsWithEmail = doctors?.filter((d) => d.email);

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setResult(null);
      setDoctorId("");
    }
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Share health summary</DialogTitle>
          <DialogDescription>
            Send your confirmed health summary to a doctor by email.
          </DialogDescription>
        </DialogHeader>

        {!result && (
          <div className="flex flex-col gap-4">
            <Select value={doctorId} onValueChange={setDoctorId}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a doctor" />
              </SelectTrigger>
              <SelectContent>
                {doctorsWithEmail?.map((doctor) => (
                  <SelectItem key={doctor.id} value={doctor.id}>
                    {doctor.name} ({doctor.email})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {doctorsWithEmail?.length === 0 && (
              <p className="text-xs text-muted-foreground">
                None of your doctor contacts have an email address on file. Add one from the
                Doctor Contacts page first.
              </p>
            )}
          </div>
        )}

        {result && (
          <Alert variant={result.status === "sent" ? "success" : "destructive"}>
            {result.status === "sent" ? <CheckCircle2 /> : <XCircle />}
            <AlertTitle>{result.status === "sent" ? "Sent" : "Failed to send"}</AlertTitle>
            <AlertDescription>
              {result.status === "sent"
                ? `Your summary was emailed to ${result.doctor_email}.`
                : result.error_message ?? "The email could not be delivered. Please try again."}
            </AlertDescription>
          </Alert>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            {result ? "Close" : "Cancel"}
          </Button>
          {!result && (
            <Button
              onClick={() => shareMutation.mutate()}
              disabled={!doctorId || shareMutation.isPending}
            >
              {shareMutation.isPending ? <Loader2 className="animate-spin" /> : <Send />}
              Send
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
