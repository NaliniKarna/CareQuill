import { apiClient } from "@/lib/api-client";
import type {
  DocumentExtraction,
  MedicalDocument,
  MedicalDocumentListResponse,
  MedicalDocumentUploadInput,
} from "@/types/api";

export interface DocumentListParams {
  category?: string;
  processing_status?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

export const documentService = {
  async list(params: DocumentListParams = {}): Promise<MedicalDocumentListResponse> {
    const { data } = await apiClient.get<MedicalDocumentListResponse>("/documents", { params });
    return data;
  },

  async get(id: string): Promise<MedicalDocument> {
    const { data } = await apiClient.get<MedicalDocument>(`/documents/${id}`);
    return data;
  },

  async upload(payload: MedicalDocumentUploadInput): Promise<MedicalDocument> {
    const form = new FormData();
    form.append("file", payload.file);
    form.append("title", payload.title);
    if (payload.category) form.append("category", payload.category);
    if (payload.visit_date) form.append("visit_date", payload.visit_date);
    if (payload.doctor_name) form.append("doctor_name", payload.doctor_name);
    if (payload.hospital_name) form.append("hospital_name", payload.hospital_name);

    const { data } = await apiClient.post<MedicalDocument>("/documents", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  async remove(id: string): Promise<void> {
    await apiClient.delete(`/documents/${id}`);
  },

  /** Streams the original file through the authorized API route (never a
   * direct storage URL) and triggers a browser save. */
  async download(id: string, filename: string): Promise<void> {
    const response = await apiClient.get(`/documents/${id}/download`, {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(response.data as Blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  async getExtraction(documentId: string): Promise<DocumentExtraction> {
    const { data } = await apiClient.get<DocumentExtraction>(
      `/documents/${documentId}/extraction`
    );
    return data;
  },

  async updateExtractionStatus(
    documentId: string,
    status: "reviewed" | "dismissed"
  ): Promise<DocumentExtraction> {
    const { data } = await apiClient.patch<DocumentExtraction>(
      `/documents/${documentId}/extraction`,
      { status }
    );
    return data;
  },
};
