"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, KeyRound, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { familyService } from "@/services/family-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { FamilyInviteCreated, FamilyMember } from "@/types/api";

import { STATUS_INFO } from "./family-constants";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function InviteSection({ member }: { member: FamilyMember }) {
  const queryClient = useQueryClient();
  const [created, setCreated] = useState<FamilyInviteCreated | null>(null);
  const [copied, setCopied] = useState(false);

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["family"] });

  const create = useMutation({
    mutationFn: () => familyService.createInvite(member.id),
    onSuccess: (data) => {
      setCreated(data);
      setCopied(false);
      refresh();
    },
    onError: (e) => toast.error(getApiErrorMessage(e, "Unable to create a code.")),
  });

  const revoke = useMutation({
    mutationFn: () => familyService.revokeInvite(member.id),
    onSuccess: () => {
      setCreated(null);
      refresh();
      toast.success("Invite code cancelled.");
    },
    onError: (e) => toast.error(getApiErrorMessage(e, "Unable to cancel the code.")),
  });

  const copy = async () => {
    if (!created) return;
    try {
      await navigator.clipboard.writeText(created.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Couldn't copy. Select the code and copy it by hand.");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <KeyRound className="size-4 text-primary" /> Hand this profile over
        </CardTitle>
        <CardDescription>
          When {member.full_name} creates their own CareQuill account, give them a one-time code. Their
          documents move into their account and they decide if you stay on as a helper.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <ol className="list-decimal space-y-1 pl-5 text-sm text-muted-foreground">
          <li>Create a code below and share it with {member.full_name}.</li>
          <li>They sign up, open Family and enter the code.</li>
          <li>The documents move to their account. Until they choose, you cannot see them.</li>
          <li>They choose: keep you as a helper (view, add, share) or keep it only for themselves.</li>
        </ol>

        {created && (
          <div className="rounded-lg border border-primary/40 bg-accent/40 p-4">
            <p className="text-xs font-medium text-muted-foreground">Invite code (shown only once)</p>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <p className="font-mono text-2xl font-semibold tracking-wider" data-testid="invite-code">
                {created.code}
              </p>
              <Button type="button" variant="outline" size="sm" onClick={copy}>
                {copied ? <Check /> : <Copy />} {copied ? "Copied" : "Copy"}
              </Button>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Expires {formatDateTime(created.expires_at)}. Works once.
            </p>
          </div>
        )}

        {!created && member.invite_active && member.invite_expires_at && (
          <Alert>
            <KeyRound />
            <AlertDescription>
              A code is active until {formatDateTime(member.invite_expires_at)}. For safety it can&apos;t be
              shown again. Create a new code to replace it.
            </AlertDescription>
          </Alert>
        )}

        <div className="flex flex-wrap gap-2">
          <Button onClick={() => create.mutate()} disabled={create.isPending}>
            {create.isPending && <Loader2 className="animate-spin" />}
            {member.invite_active || created ? "Create a new code" : "Create invite code"}
          </Button>
          {(member.invite_active || created) && (
            <Button variant="outline" onClick={() => revoke.mutate()} disabled={revoke.isPending}>
              Cancel code
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function MemberAccessTab({ member }: { member: FamilyMember }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [removeOpen, setRemoveOpen] = useState(false);
  const status = STATUS_INFO[member.link_status];

  const remove = useMutation({
    mutationFn: () => familyService.removeMember(member.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["family"] });
      toast.success("Removed from your family.");
      router.replace("/family");
    },
    onError: (e) => toast.error(getApiErrorMessage(e, "Unable to remove this profile.")),
  });

  const removeText =
    member.link_status === "unlinked"
      ? `${member.full_name}'s profile and the documents you stored for them will be permanently deleted.`
      : `${member.full_name} will be removed from your family list. Their own account and documents are not affected.`;

  return (
    <div className="flex flex-col gap-5">
      {member.link_status === "unlinked" ? (
        <InviteSection member={member} />
      ) : (
        <Alert>
          <KeyRound />
          <AlertTitle>{status.label}</AlertTitle>
          <AlertDescription>
            {member.link_status === "pending" &&
              `${member.full_name} claimed this profile. They will choose whether you keep access. Until then you cannot see their documents.`}
            {member.link_status === "active" &&
              `${member.full_name} keeps you as a helper. You can view, add and share their documents, but you cannot edit or delete them. They can end this at any time.`}
            {member.link_status === "ended" &&
              `${member.full_name} ended your access. Only they can allow it again.`}
          </AlertDescription>
        </Alert>
      )}

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-base">Remove from my family</CardTitle>
          <CardDescription>{removeText}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={() => setRemoveOpen(true)}>
            <Trash2 className="text-destructive" /> Remove {member.full_name}
          </Button>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={removeOpen}
        onOpenChange={setRemoveOpen}
        title="Remove this family member?"
        description={removeText}
        confirmLabel="Remove"
        destructive
        isLoading={remove.isPending}
        onConfirm={() => remove.mutate()}
      />
    </div>
  );
}
