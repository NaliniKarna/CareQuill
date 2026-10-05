import { apiClient } from "@/lib/api-client";
import type { UserPreference, UserPreferenceUpdateInput } from "@/types/api";

export const preferenceService = {
  async get(): Promise<UserPreference> {
    const { data } = await apiClient.get<UserPreference>("/preferences");
    return data;
  },

  async update(payload: UserPreferenceUpdateInput): Promise<UserPreference> {
    const { data } = await apiClient.put<UserPreference>("/preferences", payload);
    return data;
  },
};
