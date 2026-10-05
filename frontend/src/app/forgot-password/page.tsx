"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import Link from "next/link";

import { AuthShell } from "@/features/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { authService } from "@/services/auth-service";
import { getApiErrorMessage } from "@/lib/api-client";

const schema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
});
type FormValues = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => authService.forgotPassword(values.email),
    onSuccess: () => setSent(true),
  });

  return (
    <AuthShell
      title="Reset your password"
      description="We'll send a reset link to your email if an account exists."
      footer={
        <Link href="/login" className="text-primary hover:underline">
          Back to log in
        </Link>
      }
    >
      {sent ? (
        <Alert>
          <AlertDescription>
            If an account exists for that email, a password reset link is on its way.
          </AlertDescription>
        </Alert>
      ) : (
        <form
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-5"
          noValidate
        >
          {mutation.isError && (
            <Alert variant="destructive">
              <AlertDescription>{getApiErrorMessage(mutation.error)}</AlertDescription>
            </Alert>
          )}
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              aria-invalid={Boolean(errors.email)}
              {...register("email")}
            />
            {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
          </div>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            Send reset link
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
