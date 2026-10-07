"use client";

import { useState } from "react";
import QRCode from "qrcode";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, Download, Loader2, QrCode, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { reportService } from "@/services/report-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { HealthReportRequest, ReportShareLinkCreated } from "@/types/api";

const EXPIRY_OPTIONS = [
  { hours: 24, label: "24 hours" },
  { hours: 72, label: "3 days" },
  { hours: 168, label: "7 days" },
  { hours: 720, label: "30 days" },
];

/**
 * Creates a time-limited link to the report and shows it as a QR code.
 * Anyone who scans it can open the report and the attached documents until
 * it expires or the patient revokes it (History tab).
 */
export function QrShareDialog({
  open,
  onOpenChange,
  payload,
  documentCount,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  payload: HealthReportRequest;
  documentCount: number;
}) {
  const queryClient = useQueryClient();
  const [hours, setHours] = useState(72);
  const [created, setCreated] = useState<ReportShareLinkCreated | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setCreated(null);
      setQrDataUrl(null);
      setCopied(false);
    }
    onOpenChange(next);
  };

  const mutation = useMutation({
    mutationFn: () => reportService.createShareLink(payload, hours),
    onSuccess: async (link) => {
      setCreated(link);
      queryClient.invalidateQueries({ queryKey: ["share-links"] });
      try {
        setQrDataUrl(
          await QRCode.toDataURL(link.url, { width: 640, margin: 2, errorCorrectionLevel: "M" }),
        );
      } catch {
        toast.error("The link was created, but the QR image could not be drawn. Copy the link instead.");
      }
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to create a QR code.")),
  });

  const copyLink = async () => {
    if (!created) return;
    try {
      await navigator.clipboard.writeText(created.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Couldn't copy automatically. Select the link and copy it.");
    }
  };

  const expiresText = created
    ? new Date(created.expires_at).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : null;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <QrCode className="size-5 text-primary" />
            {created ? "Your QR code is ready" : "Share with a QR code"}
          </DialogTitle>
          <DialogDescription>
            {created
              ? "Show this code to your doctor, or send the link. It opens the report in any browser."
              : `Creates a private link to this report${
                  documentCount > 0
                    ? ` and ${documentCount} attached document${documentCount > 1 ? "s" : ""}`
                    : ""
                }. No login is needed to open it.`}
          </DialogDescription>
        </DialogHeader>

        {!created ? (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="qr-expiry">Link works for</Label>
              <Select value={String(hours)} onValueChange={(v) => setHours(Number(v))}>
                <SelectTrigger id="qr-expiry" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EXPIRY_OPTIONS.map((o) => (
                    <SelectItem key={o.hours} value={String(o.hours)}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Alert variant="warning">
              <ShieldAlert />
              <AlertTitle>Anyone with the code can view it</AlertTitle>
              <AlertDescription>
                Share it only with people you trust. You can stop the link at any time from the
                History tab, and you can see how many times it was opened.
              </AlertDescription>
            </Alert>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            {qrDataUrl && (
              // eslint-disable-next-line @next/next/no-img-element -- data URL, not a remote image
              <img
                src={qrDataUrl}
                alt="QR code for your shared health report"
                className="size-64 rounded-lg border border-border bg-white p-2"
              />
            )}
            <div className="flex w-full gap-2">
              <Input readOnly value={created.url} aria-label="Share link" onFocus={(e) => e.target.select()} />
              <Button variant="outline" size="icon" onClick={copyLink} aria-label="Copy link">
                {copied ? <Check className="text-success" /> : <Copy />}
              </Button>
            </div>
            <p className="text-center text-xs text-muted-foreground">
              Works until {expiresText}. This link is shown only now; create a new one if you lose it.
            </p>
          </div>
        )}

        <DialogFooter>
          {!created ? (
            <>
              <Button variant="outline" onClick={() => handleOpenChange(false)}>
                Cancel
              </Button>
              <Button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
                {mutation.isPending ? <Loader2 className="animate-spin" /> : <QrCode />}
                Create QR code
              </Button>
            </>
          ) : (
            <>
              {qrDataUrl && (
                <Button variant="outline" asChild>
                  <a href={qrDataUrl} download="carequill-report-qr.png">
                    <Download /> Download QR
                  </a>
                </Button>
              )}
              <Button onClick={() => handleOpenChange(false)}>Done</Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
