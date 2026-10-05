import { apiClient } from "@/lib/api-client";
import type {
  Medication,
  MedicationInput,
  MedicationReminder,
  MedicationReminderInput,
  MedicationReminderUpdateInput,
} from "@/types/api";

export interface MedicationListParams {
  active?: boolean;
  q?: string;
}

export const medicationService = {
  async list(params: MedicationListParams = {}): Promise<Medication[]> {
    const { data } = await apiClient.get<Medication[]>("/medications", { params });
    return data;
  },

  async get(id: string): Promise<Medication> {
    const { data } = await apiClient.get<Medication>(`/medications/${id}`);
    return data;
  },

  async create(payload: MedicationInput): Promise<Medication> {
    const { data } = await apiClient.post<Medication>("/medications", payload);
    return data;
  },

  async update(id: string, payload: MedicationInput): Promise<Medication> {
    const { data } = await apiClient.put<Medication>(`/medications/${id}`, payload);
    return data;
  },

  async remove(id: string): Promise<void> {
    await apiClient.delete(`/medications/${id}`);
  },

  async activate(id: string): Promise<Medication> {
    const { data } = await apiClient.patch<Medication>(`/medications/${id}/activate`);
    return data;
  },

  async deactivate(id: string): Promise<Medication> {
    const { data } = await apiClient.patch<Medication>(`/medications/${id}/deactivate`);
    return data;
  },

  async listReminders(medicationId: string): Promise<MedicationReminder[]> {
    const { data } = await apiClient.get<MedicationReminder[]>(
      `/medications/${medicationId}/reminders`
    );
    return data;
  },

  async createReminder(
    medicationId: string,
    payload: MedicationReminderInput
  ): Promise<MedicationReminder> {
    const { data } = await apiClient.post<MedicationReminder>(
      `/medications/${medicationId}/reminders`,
      payload
    );
    return data;
  },

  async updateReminder(
    medicationId: string,
    reminderId: string,
    payload: MedicationReminderUpdateInput
  ): Promise<MedicationReminder> {
    const { data } = await apiClient.patch<MedicationReminder>(
      `/medications/${medicationId}/reminders/${reminderId}`,
      payload
    );
    return data;
  },

  async deleteReminder(medicationId: string, reminderId: string): Promise<void> {
    await apiClient.delete(`/medications/${medicationId}/reminders/${reminderId}`);
  },
};
