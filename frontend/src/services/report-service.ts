import { apiClient } from "@/lib/api-client";
import type { EmailLogRead, HealthReportPreview, HealthReportRequest } from "@/types/api";

export const reportService = {
  async preview(payload: HealthReportRequest): Promise<HealthReportPreview> {
    const { data } = await apiClient.post<HealthReportPreview>("/reports/preview", payload);
    return data;
  },

  /** Fetches the report PDF and opens it in a new tab so the patient can
   * review it before sharing. Never triggers a send.
   *
   * Uses a synthetic `<a target="_blank">` click (like
   * `document-service.download`) rather than `window.open()`: by the time
   * the blob is ready the browser is no longer inside the original click's
   * call stack, and `window.open()` there is routinely popup-blocked,
   * while a real anchor click is not. */
  async generateAndOpen(payload: HealthReportRequest): Promise<void> {
    const response = await apiClient.post("/reports/generate", payload, {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(response.data as Blob);
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
  },

  async share(payload: HealthReportRequest): Promise<EmailLogRead> {
    const { data } = await apiClient.post<EmailLogRead>("/reports/share", payload);
    return data;
  },
};
