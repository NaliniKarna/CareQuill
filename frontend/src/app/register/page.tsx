import Link from "next/link";

import { AuthShell } from "@/features/auth/auth-shell";
import { RegisterForm } from "@/features/auth/register-form";

export default function RegisterPage() {
  return (
    <AuthShell
      title="Create your account"
      description="Start organizing your health records in one secure place."
      footer={
        <span>
          Already have an account?{" "}
          <Link href="/login" className="text-primary hover:underline">
            Log in
          </Link>
        </span>
      }
    >
      <RegisterForm />
    </AuthShell>
  );
}
