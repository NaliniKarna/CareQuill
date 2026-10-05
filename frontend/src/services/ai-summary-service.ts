import { apiClient } from "@/lib/api-client";
import type { AISummary, AISummaryGenerateInput, EmailLog } from "@/types/api";

export const aiSummaryService = {
  async generate(payload: AISummaryGenerateInput): Promise<AISummary> {
    const { data } = await apiClient.post<AISummary>("/ai-summaries/generate", payload);
    return data;
  },
  async list(): Promise<AISummary[]> {
    const { data } = await apiClient.get<AISummary[]>("/ai-summaries");
    return data;
  },
  async get(id: string): Promise<AISummary> {
    const { data } = await apiClient.get<AISummary>(`/ai-summaries/${id}`);
    return data;
  },
  async saveEdit(id: string, editedSummaryText: string): Promise<AISummary> {
    const { data } = await apiClient.patch<AISummary>(`/ai-summaries/${id}`, {
      edited_summary_text: editedSummaryText,
    });
    return data;
  },
  async confirm(id: string): Promise<AISummary> {
    const { data } = await apiClient.post<AISummary>(`/ai-summaries/${id}/confirm`);
    return data;
  },
  async share(id: string, doctorContactId: string): Promise<EmailLog> {
    const { data } = await apiClient.post<EmailLog>(`/ai-summaries/${id}/share`, {
      doctor_contact_id: doctorContactId,
    });
    return data;
  },
};
