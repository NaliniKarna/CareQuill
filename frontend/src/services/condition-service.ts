import { apiClient } from "@/lib/api-client";
import type { MedicalCondition, MedicalConditionInput } from "@/types/api";

export const conditionService = {
  async list(): Promise<MedicalCondition[]> {
    const { data } = await apiClient.get<MedicalCondition[]>("/conditions");
    return data;
  },
  async create(payload: MedicalConditionInput): Promise<MedicalCondition> {
    const { data } = await apiClient.post<MedicalCondition>("/conditions", payload);
    return data;
  },
  async update(id: string, payload: MedicalConditionInput): Promise<MedicalCondition> {
    const { data } = await apiClient.put<MedicalCondition>(`/conditions/${id}`, payload);
    return data;
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(`/conditions/${id}`);
  },
};
