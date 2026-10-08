"use client";

import Link from "next/link";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Checkbox } from "@/components/ui/checkbox";
import { PasswordStrength } from "@/components/shared/password-strength";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/api-client";
import { passwordProblem } from "@/lib/password";

const registerSchema = z
  .object({
    email: z.string().min(1, "Email is required").email("Enter a valid email address"),
    password: z.string().min(1, "Password is required"),
    confirmPassword: z.string().min(1, "Please confirm your password"),
    acceptedTerms: z.boolean().refine((value) => value, {
      message: "Please accept the Terms and Privacy Policy to continue",
    }),
  })
  .superRefine((data, ctx) => {
    const problem = passwordProblem(data.password, data.email);
    if (problem) ctx.addIssue({ code: "custom", message: problem, path: ["password"] });
    if (data.password !== data.confirmPassword) {
      ctx.addIssue({ code: "custom", message: "Passwords do not match", path: ["confirmPassword"] });
    }
  });

type RegisterFormValues = z.infer<typeof registerSchema>;

export function RegisterForm() {
  const { register: registerUser } = useAuth();
  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { acceptedTerms: false },
  });
  const password = useWatch({ control, name: "password" }) ?? "";
  const email = useWatch({ control, name: "email" });
  const acceptedTerms = useWatch({ control, name: "acceptedTerms" });

  const onSubmit = (values: RegisterFormValues) => {
    registerUser.mutate(
      { email: values.email, password: values.password, accepted_terms: values.acceptedTerms },
      {
        onSuccess: () => toast.success("Account created. Welcome to CareQuill."),
        onError: (error) => toast.error(getApiErrorMessage(error, "Unable to create account.")),
      }
    );
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5" noValidate>
      {registerUser.isError && (
        <Alert variant="destructive">
          <AlertDescription>
            {getApiErrorMessage(registerUser.error, "Unable to create account.")}
          </AlertDescription>
        </Alert>
      )}

      <div className="flex flex-col gap-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          aria-invalid={Boolean(errors.email)}
          {...register("email")}
        />
        {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          placeholder="Create a strong password"
          aria-invalid={Boolean(errors.password)}
          {...register("password")}
        />
        <PasswordStrength password={password} email={email} />
        {errors.password && (
          <p className="text-sm text-destructive">{errors.password.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="confirmPassword">Confirm password</Label>
        <Input
          id="confirmPassword"
          type="password"
          autoComplete="new-password"
          aria-invalid={Boolean(errors.confirmPassword)}
          {...register("confirmPassword")}
        />
        {errors.confirmPassword && (
          <p className="text-sm text-destructive">{errors.confirmPassword.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-2 rounded-lg border bg-accent/30 p-3">
        <div className="flex items-start gap-3">
          <Checkbox
            id="acceptedTerms"
            checked={acceptedTerms}
            onCheckedChange={(checked) =>
              setValue("acceptedTerms", checked === true, { shouldValidate: true })
            }
            aria-invalid={Boolean(errors.acceptedTerms)}
            aria-describedby="terms-help"
            className="mt-0.5"
          />
          <Label htmlFor="acceptedTerms" className="block text-sm leading-relaxed font-normal">
            I agree to the{" "}
            <Link href="/terms" target="_blank" className="font-medium text-primary hover:underline">
              Terms of Use
            </Link>{" "}
            and the{" "}
            <Link href="/privacy" target="_blank" className="font-medium text-primary hover:underline">
              Privacy Policy
            </Link>
            , and I consent to CareQuill storing and processing the health information I add, so it
            can organise it for me.
          </Label>
        </div>
        <p id="terms-help" className="pl-7 text-xs text-muted-foreground">
          You stay in control: you can download or delete all your data at any time.
        </p>
        {errors.acceptedTerms && (
          <p role="alert" className="pl-7 text-sm text-destructive">
            {errors.acceptedTerms.message}
          </p>
        )}
      </div>

      <Button type="submit" disabled={registerUser.isPending} className="mt-2">
        {registerUser.isPending && <Loader2 className="animate-spin" />}
        Create account
      </Button>

      <p className="text-center text-xs text-muted-foreground">
        CareQuill is an organisational tool. It does not provide medical advice, diagnosis, or
        treatment.
      </p>
    </form>
  );
}
