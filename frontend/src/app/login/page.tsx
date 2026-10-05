import Link from "next/link";

import { AuthShell } from "@/features/auth/auth-shell";
import { LoginForm } from "@/features/auth/login-form";

export default function LoginPage() {
  return (
    <AuthShell
      title="Welcome back"
      description="Log in to access your health records."
      footer={
        <span>
          Don&apos;t have an account?{" "}
          <Link href="/register" className="text-primary hover:underline">
            Create one
          </Link>
        </span>
      }
    >
      <LoginForm />
    </AuthShell>
  );
}
