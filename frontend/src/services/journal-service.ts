import { apiClient } from "@/lib/api-client";
import type { JournalEntry, JournalEntryInput, JournalListResponse } from "@/types/api";

export interface JournalListParams {
  date_from?: string;
  date_to?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

export const journalService = {
  async list(params: JournalListParams = {}): Promise<JournalListResponse> {
    const { data } = await apiClient.get<JournalListResponse>("/journal", { params });
    return data;
  },
  async create(payload: JournalEntryInput): Promise<JournalEntry> {
    const { data } = await apiClient.post<JournalEntry>("/journal", payload);
    return data;
  },
  async update(id: string, payload: JournalEntryInput): Promise<JournalEntry> {
    const { data } = await apiClient.put<JournalEntry>(`/journal/${id}`, payload);
    return data;
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(`/journal/${id}`);
  },
};
