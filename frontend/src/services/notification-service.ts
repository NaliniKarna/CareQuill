import { apiClient } from "@/lib/api-client";
import type { Notification } from "@/types/api";

export const notificationService = {
  async list(params: { unreadOnly?: boolean } = {}): Promise<Notification[]> {
    const { data } = await apiClient.get<Notification[]>("/notifications", {
      params: params.unreadOnly ? { unread_only: true } : undefined,
    });
    return data;
  },

  async markRead(id: string): Promise<Notification> {
    const { data } = await apiClient.patch<Notification>(`/notifications/${id}/read`);
    return data;
  },
};
