"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { authService, type LoginPayload, type RegisterPayload } from "@/services/auth-service";
import { useAuthStore } from "@/store/auth-store";

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, accessToken, refreshToken, setAuth, clear } = useAuthStore();

  const loginMutation = useMutation({
    mutationFn: (payload: LoginPayload) => authService.login(payload),
    onSuccess: (data) => {
      setAuth({ user: data.user, accessToken: data.access_token, refreshToken: data.refresh_token });
      router.push("/dashboard");
    },
  });

  const registerMutation = useMutation({
    mutationFn: (payload: RegisterPayload) => authService.register(payload),
    onSuccess: (data) => {
      setAuth({ user: data.user, accessToken: data.access_token, refreshToken: data.refresh_token });
      router.push("/dashboard");
    },
  });

  const logout = async () => {
    if (refreshToken) {
      try {
        await authService.logout(refreshToken);
      } catch {
        // Best-effort: even if the server call fails, clear local state so
        // the user isn't stuck "logged in" in the UI.
      }
    }
    clear();
    queryClient.clear();
    router.push("/login");
  };

  return {
    user,
    isAuthenticated: Boolean(accessToken && user),
    login: loginMutation,
    register: registerMutation,
    logout,
  };
}
