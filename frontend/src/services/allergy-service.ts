import { apiClient } from "@/lib/api-client";
import type { Allergy, AllergyInput } from "@/types/api";

export const allergyService = {
  async list(): Promise<Allergy[]> {
    const { data } = await apiClient.get<Allergy[]>("/allergies");
    return data;
  },
  async create(payload: AllergyInput): Promise<Allergy> {
    const { data } = await apiClient.post<Allergy>("/allergies", payload);
    return data;
  },
  async update(id: string, payload: AllergyInput): Promise<Allergy> {
    const { data } = await apiClient.put<Allergy>(`/allergies/${id}`, payload);
    return data;
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(`/allergies/${id}`);
  },
};
