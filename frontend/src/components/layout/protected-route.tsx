"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { useAuthStore } from "@/store/auth-store";
import { AppShell } from "@/components/layout/app-shell";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, accessToken, hasHydrated } = useAuthStore();

  useEffect(() => {
    if (hasHydrated && !(user && accessToken)) {
      router.replace("/login");
    }
  }, [hasHydrated, user, accessToken, router]);

  if (!hasHydrated || !(user && accessToken)) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return <AppShell>{children}</AppShell>;
}
