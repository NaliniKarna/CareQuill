import { apiClient } from "@/lib/api-client";
import type { AuthResponse, ChangePasswordInput, User } from "@/types/api";

export interface RegisterPayload {
  email: string;
  password: string;
  /** Consent to the Terms and Privacy Policy (required by the server). */
  accepted_terms: boolean;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export const authService = {
  async register(payload: RegisterPayload): Promise<AuthResponse> {
    const { data } = await apiClient.post<AuthResponse>("/auth/register", payload);
    return data;
  },

  async login(payload: LoginPayload): Promise<AuthResponse> {
    const { data } = await apiClient.post<AuthResponse>("/auth/login", payload);
    return data;
  },

  async logout(refreshToken: string): Promise<void> {
    await apiClient.post("/auth/logout", { refresh_token: refreshToken });
  },

  async me(): Promise<User> {
    const { data } = await apiClient.get<User>("/auth/me");
    return data;
  },

  async forgotPassword(email: string): Promise<void> {
    await apiClient.post("/auth/forgot-password", { email });
  },

  async resetPassword(token: string, newPassword: string): Promise<void> {
    await apiClient.post("/auth/reset-password", { token, new_password: newPassword });
  },

  async verifyEmail(token: string): Promise<void> {
    await apiClient.post("/auth/verify-email", { token });
  },

  /** Changes the current user's password. On success, the backend revokes
   * every other session's refresh tokens, so other logged-in devices must
   * re-authenticate. */
  async changePassword(payload: ChangePasswordInput): Promise<void> {
    await apiClient.post("/auth/change-password", payload);
  },
};
