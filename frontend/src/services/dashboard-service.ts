import { apiClient } from "@/lib/api-client";
import type { DashboardResponse } from "@/types/api";

export const dashboardService = {
  async get(): Promise<DashboardResponse> {
    const { data } = await apiClient.get<DashboardResponse>("/dashboard");
    return data;
  },
};
