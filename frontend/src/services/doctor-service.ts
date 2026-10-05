import { apiClient } from "@/lib/api-client";
import type { DoctorContact, DoctorContactInput } from "@/types/api";

export const doctorService = {
  async list(): Promise<DoctorContact[]> {
    const { data } = await apiClient.get<DoctorContact[]>("/doctors");
    return data;
  },
  async create(payload: DoctorContactInput): Promise<DoctorContact> {
    const { data } = await apiClient.post<DoctorContact>("/doctors", payload);
    return data;
  },
  async update(id: string, payload: DoctorContactInput): Promise<DoctorContact> {
    const { data } = await apiClient.put<DoctorContact>(`/doctors/${id}`, payload);
    return data;
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(`/doctors/${id}`);
  },
};
