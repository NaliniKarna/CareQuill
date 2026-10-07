import { apiClient } from "@/lib/api-client";
import type {
  FamilyDocument,
  FamilyInviteCreated,
  FamilyLinkedToMe,
  FamilyMember,
  FamilyMemberInput,
  FamilyShareInput,
  FamilyShareLog,
  DocumentCategory,
} from "@/types/api";

export interface FamilyUploadInput {
  file: File;
  title: string;
  category?: DocumentCategory | "";
  visit_date?: string;
  doctor_name?: string;
  hospital_name?: string;
}

const base = (memberId: string) => `/family/members/${memberId}`;

export const familyService = {
  // -- profiles
  async listMembers(): Promise<FamilyMember[]> {
    const { data } = await apiClient.get<FamilyMember[]>("/family/members");
    return data;
  },

  async getMember(id: string): Promise<FamilyMember> {
    const { data } = await apiClient.get<FamilyMember>(base(id));
    return data;
  },

  async createMember(payload: FamilyMemberInput): Promise<FamilyMember> {
    const { data } = await apiClient.post<FamilyMember>("/family/members", payload);
    return data;
  },

  async updateMember(id: string, payload: Partial<FamilyMemberInput>): Promise<FamilyMember> {
    const { data } = await apiClient.patch<FamilyMember>(base(id), payload);
    return data;
  },

  async removeMember(id: string): Promise<void> {
    await apiClient.delete(base(id));
  },

  // -- hand-over
  async createInvite(id: string): Promise<FamilyInviteCreated> {
    const { data } = await apiClient.post<FamilyInviteCreated>(`${base(id)}/invite`);
    return data;
  },

  async revokeInvite(id: string): Promise<void> {
    await apiClient.delete(`${base(id)}/invite`);
  },

  async claim(code: string): Promise<FamilyLinkedToMe> {
    const { data } = await apiClient.post<FamilyLinkedToMe>("/family/claim", { code });
    return data;
  },

  async listLinkedToMe(): Promise<FamilyLinkedToMe[]> {
    const { data } = await apiClient.get<FamilyLinkedToMe[]>("/family/linked-to-me");
    return data;
  },

  async decideAccess(id: string, allow: boolean): Promise<FamilyLinkedToMe> {
    const { data } = await apiClient.post<FamilyLinkedToMe>(`/family/linked-to-me/${id}/access`, {
      allow,
    });
    return data;
  },

  // -- documents
  async listDocuments(memberId: string): Promise<FamilyDocument[]> {
    const { data } = await apiClient.get<FamilyDocument[]>(`${base(memberId)}/documents`);
    return data;
  },

  async uploadDocument(memberId: string, payload: FamilyUploadInput): Promise<FamilyDocument> {
    const form = new FormData();
    form.append("file", payload.file);
    form.append("title", payload.title);
    if (payload.category) form.append("category", payload.category);
    if (payload.visit_date) form.append("visit_date", payload.visit_date);
    if (payload.doctor_name) form.append("doctor_name", payload.doctor_name);
    if (payload.hospital_name) form.append("hospital_name", payload.hospital_name);
    const { data } = await apiClient.post<FamilyDocument>(`${base(memberId)}/documents`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  async removeDocument(memberId: string, documentId: string): Promise<void> {
    await apiClient.delete(`${base(memberId)}/documents/${documentId}`);
  },

  async downloadDocument(memberId: string, documentId: string, filename: string): Promise<void> {
    const response = await apiClient.get(`${base(memberId)}/documents/${documentId}/download`, {
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

  /** The caller owns the returned object URL and must revoke it. */
  async previewDocument(
    memberId: string,
    documentId: string,
  ): Promise<{ url: string; mimeType: string }> {
    const response = await apiClient.get(`${base(memberId)}/documents/${documentId}/preview`, {
      responseType: "blob",
    });
    const blob = response.data as Blob;
    return { url: window.URL.createObjectURL(blob), mimeType: blob.type };
  },

  // -- sharing
  async share(memberId: string, payload: FamilyShareInput): Promise<FamilyShareLog> {
    const { data } = await apiClient.post<FamilyShareLog>(`${base(memberId)}/share`, payload);
    return data;
  },

  async listShares(memberId: string): Promise<FamilyShareLog[]> {
    const { data } = await apiClient.get<FamilyShareLog[]>(`${base(memberId)}/shares`);
    return data;
  },
};
