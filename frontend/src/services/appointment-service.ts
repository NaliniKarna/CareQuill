import { apiClient } from "@/lib/api-client";
import type { Appointment, AppointmentCreateInput, AppointmentUpdateInput } from "@/types/api";

export type AppointmentFilter = "upcoming" | "past";

export const appointmentService = {
  async list(filter?: AppointmentFilter): Promise<Appointment[]> {
    const { data } = await apiClient.get<Appointment[]>("/appointments", {
      params: filter ? { filter } : undefined,
    });
    return data;
  },
  async create(payload: AppointmentCreateInput): Promise<Appointment> {
    const { data } = await apiClient.post<Appointment>("/appointments", payload);
    return data;
  },
  async update(id: string, payload: AppointmentUpdateInput): Promise<Appointment> {
    const { data } = await apiClient.put<Appointment>(`/appointments/${id}`, payload);
    return data;
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(`/appointments/${id}`);
  },
  async cancel(id: string): Promise<Appointment> {
    const { data } = await apiClient.patch<Appointment>(`/appointments/${id}/cancel`);
    return data;
  },
  async complete(id: string): Promise<Appointment> {
    const { data } = await apiClient.patch<Appointment>(`/appointments/${id}/complete`);
    return data;
  },
  async miss(id: string): Promise<Appointment> {
    const { data } = await apiClient.patch<Appointment>(`/appointments/${id}/miss`);
    return data;
  },
};
