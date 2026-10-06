import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { useAuthStore } from "@/store/auth-store";
import type { ApiErrorBody, TokenPair } from "@/types/api";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const { accessToken } = useAuthStore.getState();
  if (accessToken && config.headers) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// Single-flight refresh: if multiple requests 401 at once, only issue one
// refresh call and let the others wait on it.
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, setTokens, clear } = useAuthStore.getState();
  if (!refreshToken) return null;

  try {
    const { data } = await axios.post<TokenPair>(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    });
    setTokens({ accessToken: data.access_token, refreshToken: data.refresh_token });
    return data.access_token;
  } catch {
    clear();
    return null;
  }
}

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorBody>) => {
    const originalRequest = error.config as RetriableConfig | undefined;
    // A 401 from these means "wrong password", not "expired token" -- do not
    // try to refresh the session (or redirect) because of it.
    const isAuthRoute =
      originalRequest?.url?.includes("/auth/") || originalRequest?.url?.includes("/account/delete");

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !isAuthRoute
    ) {
      originalRequest._retry = true;
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
      }
      const newAccessToken = await refreshPromise;
      if (newAccessToken) {
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);
      }
      if (typeof window !== "undefined") {
        // Hard redirect on purpose: this runs outside the React tree (an
        // axios interceptor), so `useRouter` isn't available here.
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

export function getApiErrorMessage(error: unknown, fallback = "Something went wrong."): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as ApiErrorBody | undefined;
    if (data?.error?.message) return data.error.message;
    if (error.message) return error.message;
  }
  return fallback;
}
