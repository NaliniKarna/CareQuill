"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { familyService } from "@/services/family-service";
import { getApiErrorMessage } from "@/lib/api-client";

/** For the person being added: enter the code a relative gave you to take
 * over the profile they kept for you. */
export function ClaimCard() {
  const queryClient = useQueryClient();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (value: string) => familyService.claim(value),
    onSuccess: () => {
      setCode("");
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["family"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Record claimed. Their documents are now in your account.");
    },
    onError: (e) => setError(getApiErrorMessage(e, "That code didn't work.")),
  });

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (code.trim().length < 6) {
      setError("Enter the full code you were given.");
      return;
    }
    setError(null);
    mutation.mutate(code.trim());
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <KeyRound className="size-4 text-primary" /> Have an invite code?
        </CardTitle>
        <CardDescription>
          A relative can keep your documents safe until you join. Enter their code to move them into
          your own account.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="flex flex-col gap-3" noValidate>
          <div className="flex flex-col gap-2">
            <Label htmlFor="claim-code">Invite code</Label>
            <Input
              id="claim-code"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="CQ-XXXXX-XXXXX"
              autoComplete="off"
              spellCheck={false}
              className="font-mono tracking-wider"
              aria-invalid={Boolean(error)}
              aria-describedby={error ? "claim-code-error" : undefined}
            />
            {error && (
              <p id="claim-code-error" role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
          </div>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            Claim my record
          </Button>
          <p className="text-xs text-muted-foreground">
            After claiming, you choose whether the person who invited you keeps helper access.
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
