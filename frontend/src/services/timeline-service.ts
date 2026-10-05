import { apiClient } from "@/lib/api-client";
import type { TimelineEntry, TimelineNote, TimelineNoteInput } from "@/types/api";

export interface TimelineParams {
  type?: string;
  date_from?: string;
  date_to?: string;
}

export const timelineService = {
  async get(params: TimelineParams = {}): Promise<TimelineEntry[]> {
    const { data } = await apiClient.get<TimelineEntry[]>("/timeline", { params });
    return data;
  },
  async listNotes(): Promise<TimelineNote[]> {
    const { data } = await apiClient.get<TimelineNote[]>("/timeline/notes");
    return data;
  },
  async createNote(payload: TimelineNoteInput): Promise<TimelineNote> {
    const { data } = await apiClient.post<TimelineNote>("/timeline/notes", payload);
    return data;
  },
  async deleteNote(id: string): Promise<void> {
    await apiClient.delete(`/timeline/notes/${id}`);
  },
};
