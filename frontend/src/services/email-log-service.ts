import { apiClient } from "@/lib/api-client";
import type { EmailLogListItem } from "@/types/api";

export const emailLogService = {
  async list(): Promise<EmailLogListItem[]> {
    const { data } = await apiClient.get<EmailLogListItem[]>("/email-logs");
    return data;
  },
};
