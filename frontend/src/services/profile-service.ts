import { apiClient } from "@/lib/api-client";
import type { HealthProfile, HealthProfileInput } from "@/types/api";

export const profileService = {
  async get(): Promise<HealthProfile | null> {
    try {
      const { data } = await apiClient.get<HealthProfile>("/profile");
      return data;
    } catch (error: unknown) {
      const axiosError = error as { response?: { status?: number } };
      if (axiosError.response?.status === 404) return null;
      throw error;
    }
  },

  async upsert(payload: HealthProfileInput): Promise<HealthProfile> {
    const { data } = await apiClient.put<HealthProfile>("/profile", payload);
    return data;
  },
};
