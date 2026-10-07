"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HeartHandshake, Loader2, ShieldCheck, ShieldOff } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { familyService } from "@/services/family-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { FamilyLinkedToMe } from "@/types/api";

import { relationLabel } from "./family-constants";

function useDecision() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, allow }: { id: string; allow: boolean }) => familyService.decideAccess(id, allow),
    onSuccess: (_data, { allow }) => {
      queryClient.invalidateQueries({ queryKey: ["family", "linked"] });
      toast.success(allow ? "They can now help with your record." : "Their access to your record has ended.");
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to update access.")),
  });
}

/** The person's own side: decide who keeps helper access to my record. */
export function AccessPanel() {
  const decision = useDecision();
  const [ending, setEnding] = useState<FamilyLinkedToMe | null>(null);
  const { data } = useQuery({
    queryKey: ["family", "linked"],
    queryFn: () => familyService.listLinkedToMe(),
  });

  const pending = (data ?? []).filter((x) => x.link_status === "pending");
  const others = (data ?? []).filter((x) => x.link_status !== "pending");

  return (
    <>
      {pending.map((item) => (
        <Alert key={item.id} className="border-primary/40 bg-accent/40">
          <HeartHandshake />
          <AlertTitle>Choose who keeps access to your record</AlertTitle>
          <AlertDescription>
            <p>
              <strong>{item.manager_name}</strong> kept your documents (they added you as their{" "}
              {relationLabel(item.relation).toLowerCase()}). They are in your account now. Should{" "}
              {item.manager_name} stay on as a helper?
            </p>
            <ul className="mt-2 list-disc pl-5 text-sm">
              <li>If yes, they can view your documents, upload new ones and share them with a doctor.</li>
              <li>They can never edit or delete your records. You can remove them at any time.</li>
              <li>Until you choose, they cannot see anything.</li>
            </ul>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button
                size="sm"
                disabled={decision.isPending}
                onClick={() => decision.mutate({ id: item.id, allow: true })}
              >
                {decision.isPending ? <Loader2 className="animate-spin" /> : <ShieldCheck />}
                Yes, keep {item.manager_name} as helper
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={decision.isPending}
                onClick={() => decision.mutate({ id: item.id, allow: false })}
              >
                <ShieldOff /> No, only me
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      ))}

      {others.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Who helps with my record</CardTitle>
            <CardDescription>You decide. Helpers can view, upload and share, but never edit or delete.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {others.map((item) => (
              <div key={item.id} className="flex flex-wrap items-center gap-3 rounded-lg border p-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{item.manager_name}</p>
                  <p className="text-xs text-muted-foreground">Added you as {relationLabel(item.relation).toLowerCase()}</p>
                </div>
                {item.link_status === "active" ? (
                  <>
                    <Badge variant="success">Has access</Badge>
                    <Button size="sm" variant="outline" disabled={decision.isPending} onClick={() => setEnding(item)}>
                      End access
                    </Button>
                  </>
                ) : (
                  <>
                    <Badge variant="outline">No access</Badge>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={decision.isPending}
                      onClick={() => decision.mutate({ id: item.id, allow: true })}
                    >
                      Allow again
                    </Button>
                  </>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <ConfirmDialog
        open={Boolean(ending)}
        onOpenChange={(open) => !open && setEnding(null)}
        title="End access to your record?"
        description={`${ending?.manager_name ?? "This person"} will no longer be able to see or add your documents. Your records stay untouched.`}
        confirmLabel="End access"
        destructive
        isLoading={decision.isPending}
        onConfirm={() => {
          if (!ending) return;
          decision.mutate({ id: ending.id, allow: false }, { onSettled: () => setEnding(null) });
        }}
      />
    </>
  );
}
