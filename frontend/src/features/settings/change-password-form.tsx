"use client";

import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { KeyRound, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authService } from "@/services/auth-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { passwordProblem } from "@/lib/password";
import { PasswordStrength } from "@/components/shared/password-strength";
import { useAuth } from "@/hooks/use-auth";

const schema = z
  .object({
    current_password: z.string().min(1, "Enter your current password"),
    new_password: z.string().min(1, "Enter a new password"),
    confirm_password: z.string().min(1, "Confirm your new password"),
  })
  .superRefine((values, ctx) => {
    const problem = passwordProblem(values.new_password);
    if (problem) ctx.addIssue({ code: "custom", message: problem, path: ["new_password"] });
    if (values.new_password !== values.confirm_password) {
      ctx.addIssue({ code: "custom", message: "Passwords don't match", path: ["confirm_password"] });
    }
  });

type FormValues = z.infer<typeof schema>;

export function ChangePasswordForm() {
  const { user } = useAuth();
  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });
  const newPassword = useWatch({ control, name: "new_password" }) ?? "";

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      authService.changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      }),
    onSuccess: () => {
      toast.success("Password changed. Your other signed-in sessions have been logged out.");
      reset();
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to change your password.")),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Change password</CardTitle>
        <CardDescription>
          Changing your password signs you out of every other device and browser.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
          noValidate
        >
          <div className="flex flex-col gap-2">
            <Label htmlFor="current-password">Current password</Label>
            <Input
              id="current-password"
              type="password"
              autoComplete="current-password"
              aria-invalid={Boolean(errors.current_password)}
              {...register("current_password")}
            />
            {errors.current_password && (
              <p className="text-sm text-destructive">{errors.current_password.message}</p>
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="new-password">New password</Label>
              <Input
                id="new-password"
                type="password"
                autoComplete="new-password"
                aria-invalid={Boolean(errors.new_password)}
                {...register("new_password")}
              />
              {errors.new_password && (
                <p className="text-sm text-destructive">{errors.new_password.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="confirm-password">Confirm new password</Label>
              <Input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                aria-invalid={Boolean(errors.confirm_password)}
                {...register("confirm_password")}
              />
              {errors.confirm_password && (
                <p className="text-sm text-destructive">{errors.confirm_password.message}</p>
              )}
            </div>
          </div>
          <PasswordStrength password={newPassword} email={user?.email} />
          <Button type="submit" className="self-start" disabled={mutation.isPending}>
            {mutation.isPending ? <Loader2 className="animate-spin" /> : <KeyRound />}
            Change password
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
