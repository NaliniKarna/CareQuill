"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Separator } from "@/components/ui/separator";
import { accountService } from "@/services/account-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";

/** Patient control of their own data: take a copy, or erase everything. */
export function YourDataCard() {
  const queryClient = useQueryClient();
  const clearSession = useAuthStore((s) => s.clear);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [phrase, setPhrase] = useState("");

  const exportMutation = useMutation({
    mutationFn: () => accountService.exportData(),
    onSuccess: () => toast.success("Your data export has been downloaded."),
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to export your data.")),
  });

  const deleteMutation = useMutation({
    mutationFn: () => accountService.deleteAccount(password),
    onSuccess: () => {
      toast.success("Your account and all its data were deleted.");
      queryClient.clear();
      clearSession(); // ProtectedRoute then sends the user to /login
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to delete your account.")),
  });

  const canDelete = password.length > 0 && phrase === "DELETE" && !deleteMutation.isPending;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your data</CardTitle>
        <CardDescription>You own your health information. Take a copy or erase it.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium">Download a copy</p>
          <p className="text-sm text-muted-foreground">
            A ZIP file with all your records as readable JSON, plus the original documents you
            uploaded.
          </p>
          <Button
            variant="outline"
            className="self-start"
            disabled={exportMutation.isPending}
            onClick={() => exportMutation.mutate()}
          >
            {exportMutation.isPending ? <Loader2 className="animate-spin" /> : <Download />}
            Export my data
          </Button>
        </div>

        <Separator />

        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium text-destructive">Delete my account</p>
          <p className="text-sm text-muted-foreground">
            Permanently deletes your profile, records, documents, summaries and sent-email history.
            This cannot be undone. Emails already sent to doctors cannot be recalled.
          </p>
          <Button variant="destructive" className="self-start" onClick={() => setDialogOpen(true)}>
            <Trash2 /> Delete account
          </Button>
        </div>
      </CardContent>

      <Dialog
        open={dialogOpen}
        onOpenChange={(open) => {
          if (deleteMutation.isPending) return;
          setDialogOpen(open);
          if (!open) {
            setPassword("");
            setPhrase("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete your account?</DialogTitle>
            <DialogDescription>
              Everything is erased immediately. Consider exporting your data first.
            </DialogDescription>
          </DialogHeader>
          <Alert variant="destructive">
            <AlertTitle>This is permanent</AlertTitle>
            <AlertDescription>There is no way to recover a deleted account.</AlertDescription>
          </Alert>
          <div className="flex flex-col gap-2">
            <Label htmlFor="delete-password">Your password</Label>
            <Input
              id="delete-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="delete-phrase">Type DELETE to confirm</Label>
            <Input
              id="delete-phrase"
              autoComplete="off"
              value={phrase}
              onChange={(e) => setPhrase(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={deleteMutation.isPending}>
              Cancel
            </Button>
            <Button variant="destructive" disabled={!canDelete} onClick={() => deleteMutation.mutate()}>
              {deleteMutation.isPending && <Loader2 className="animate-spin" />}
              Delete everything
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
