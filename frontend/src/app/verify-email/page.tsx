"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import Link from "next/link";

import { AuthShell } from "@/features/auth/auth-shell";
import { authService } from "@/services/auth-service";
import { getApiErrorMessage } from "@/lib/api-client";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    token ? "loading" : "error"
  );
  const [message, setMessage] = useState(
    token ? "" : "This verification link is missing its token."
  );

  useEffect(() => {
    if (!token) return;
    authService
      .verifyEmail(token)
      .then(() => setStatus("success"))
      .catch((error) => {
        setStatus("error");
        setMessage(getApiErrorMessage(error, "This link is invalid or has expired."));
      });
  }, [token]);

  if (status === "loading") {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Verifying your email...
      </div>
    );
  }

  if (status === "success") {
    return (
      <div className="flex flex-col items-center gap-3 text-center">
        <CheckCircle2 className="size-8 text-success" />
        <p>Your email has been verified.</p>
        <Link href="/login" className="text-primary hover:underline">
          Continue to log in
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3 text-center">
      <XCircle className="size-8 text-destructive" />
      <p>{message}</p>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <AuthShell title="Email verification" description="Confirming your email address.">
      <Suspense fallback={null}>
        <VerifyEmailContent />
      </Suspense>
    </AuthShell>
  );
}
