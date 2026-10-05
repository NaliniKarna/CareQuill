"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { User } from "@/types/api";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  hasHydrated: boolean;
  setAuth: (params: { user: User; accessToken: string; refreshToken: string }) => void;
  setAccessToken: (accessToken: string) => void;
  setTokens: (params: { accessToken: string; refreshToken: string }) => void;
  clear: () => void;
  setHasHydrated: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      hasHydrated: false,
      setAuth: ({ user, accessToken, refreshToken }) =>
        set({ user, accessToken, refreshToken }),
      setAccessToken: (accessToken) => set({ accessToken }),
      setTokens: ({ accessToken, refreshToken }) => set({ accessToken, refreshToken }),
      clear: () => set({ user: null, accessToken: null, refreshToken: null }),
      setHasHydrated: (value) => set({ hasHydrated: value }),
    }),
    {
      name: "medqueue-auth",
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
