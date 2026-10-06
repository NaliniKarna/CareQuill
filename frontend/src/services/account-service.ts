import { apiClient } from "@/lib/api-client";

export const accountService = {
  /** Downloads a ZIP with all of the patient's records (JSON) and original
   * documents, through the authorized API (never a public URL). */
  async exportData(): Promise<void> {
    const response = await apiClient.get("/account/export", { responseType: "blob" });
    const url = window.URL.createObjectURL(response.data as Blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `medai-export-${new Date().toISOString().slice(0, 10)}.zip`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  async deleteAccount(password: string): Promise<void> {
    await apiClient.post("/account/delete", { password, confirmation: "DELETE" });
  },
};
