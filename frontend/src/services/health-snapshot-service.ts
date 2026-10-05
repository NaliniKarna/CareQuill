import { apiClient } from "@/lib/api-client";
import type { HealthSnapshot, HealthSnapshotVersion } from "@/types/api";

export const healthSnapshotService = {
  async generate(): Promise<HealthSnapshot> {
    const { data } = await apiClient.post<HealthSnapshot>("/health-snapshots/generate");
    return data;
  },
  async list(): Promise<HealthSnapshotVersion[]> {
    const { data } = await apiClient.get<HealthSnapshotVersion[]>("/health-snapshots");
    return data;
  },
  async getLatest(): Promise<HealthSnapshot | null> {
    try {
      const { data } = await apiClient.get<HealthSnapshot>("/health-snapshots/latest");
      return data;
    } catch (error: unknown) {
      const axiosError = error as { response?: { status?: number } };
      if (axiosError.response?.status === 404) return null;
      throw error;
    }
  },
  async getById(id: string): Promise<HealthSnapshot> {
    const { data } = await apiClient.get<HealthSnapshot>(`/health-snapshots/${id}`);
    return data;
  },
};
