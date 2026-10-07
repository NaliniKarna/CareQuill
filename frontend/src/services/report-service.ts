import { apiClient } from "@/lib/api-client";
import { openBlob } from "@/lib/blob";
import type {
  EmailLogRead,
  HealthReportPreview,
  HealthReportRequest,
  ReportShareLink,
  ReportShareLinkCreated,
} from "@/types/api";

export const reportService = {
  async preview(payload: HealthReportRequest): Promise<HealthReportPreview> {
    const { data } = await apiClient.post<HealthReportPreview>("/reports/preview", payload);
    return data;
  },

  /** Fetches the report PDF and opens it in a new tab so the patient can
   * review it before sharing. Never triggers a send. */
  async generateAndOpen(payload: HealthReportRequest): Promise<void> {
    const response = await apiClient.post("/reports/generate", payload, {
      responseType: "blob",
    });
    openBlob(response.data as Blob);
  },

  async share(payload: HealthReportRequest): Promise<EmailLogRead> {
    const { data } = await apiClient.post<EmailLogRead>("/reports/share", payload);
    return data;
  },

  /** Creates a time-limited QR/link share. The URL is only returned here. */
  async createShareLink(
    report: HealthReportRequest,
    expiresInHours: number,
  ): Promise<ReportShareLinkCreated> {
    const { data } = await apiClient.post<ReportShareLinkCreated>("/reports/share-links", {
      report,
      expires_in_hours: expiresInHours,
    });
    return data;
  },

  async listShareLinks(): Promise<ReportShareLink[]> {
    const { data } = await apiClient.get<ReportShareLink[]>("/reports/share-links");
    return data;
  },

  async revokeShareLink(id: string): Promise<ReportShareLink> {
    const { data } = await apiClient.post<ReportShareLink>(`/reports/share-links/${id}/revoke`);
    return data;
  },
};
