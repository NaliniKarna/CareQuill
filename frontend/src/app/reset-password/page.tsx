"use client";

import { Suspense, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import Link from "next/link";

import { AuthShell } from "@/features/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { authService } from "@/services/auth-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { passwordProblem } from "@/lib/password";
import { PasswordStrength } from "@/components/shared/password-strength";

const schema = z.object({
  password: z
    .string()
    .min(1, "Enter a new password")
    .superRefine((value, ctx) => {
      const problem = passwordProblem(value);
      if (problem) ctx.addIssue({ code: "custom", message: problem });
    }),
});
type FormValues = z.infer<typeof schema>;

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [done, setDone] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });
  const password = useWatch({ control, name: "password" }) ?? "";

  const mutation = useMutation({
    mutationFn: (values: FormValues) => authService.resetPassword(token, values.password),
    onSuccess: () => setDone(true),
  });

  if (!token) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          This reset link is missing its token. Please request a new one.
        </AlertDescription>
      </Alert>
    );
  }

  if (done) {
    return (
      <Alert>
        <AlertDescription>
          Your password has been reset.{" "}
          <Link href="/login" className="text-primary hover:underline">
            Log in
          </Link>
        </AlertDescription>
      </Alert>
    );
  }

  return (
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
        <Label htmlFor="password">New password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          aria-invalid={Boolean(errors.password)}
          {...register("password")}
        />
        <PasswordStrength password={password} />
        {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
      </div>
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending && <Loader2 className="animate-spin" />}
        Reset password
      </Button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <AuthShell title="Set a new password" description="Choose a new password for your account.">
      <Suspense fallback={null}>
        <ResetPasswordForm />
      </Suspense>
    </AuthShell>
  );
}
