import { apiClient } from "@/lib/api-client";
import type { SharedReportInfo } from "@/types/api";

/**
 * Public access to a report a patient shared by QR code. The token always
 * travels in the request body (never the URL) so it stays out of logs.
 */
export const sharedReportService = {
  async info(token: string): Promise<SharedReportInfo> {
    const { data } = await apiClient.post<SharedReportInfo>("/public/shared-reports/info", {
      token,
    });
    return data;
  },

  async report(token: string): Promise<Blob> {
    const { data } = await apiClient.post("/public/shared-reports/report", { token }, {
      responseType: "blob",
    });
    return data as Blob;
  },

  async document(token: string, documentId: string): Promise<Blob> {
    const { data } = await apiClient.post(
      "/public/shared-reports/document",
      { token, document_id: documentId },
      { responseType: "blob" },
    );
    return data as Blob;
  },
};
