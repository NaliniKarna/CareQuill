"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { profileService } from "@/services/profile-service";
import { getApiErrorMessage } from "@/lib/api-client";
import type { HealthProfileInput } from "@/types/api";

const profileSchema = z.object({
  first_name: z.string().min(1, "First name is required").max(100),
  last_name: z.string().min(1, "Last name is required").max(100),
  date_of_birth: z.string().optional().or(z.literal("")),
  gender: z.string().optional().or(z.literal("")),
  blood_group: z.string().optional().or(z.literal("")),
  phone: z.string().max(30).optional().or(z.literal("")),
  address: z.string().max(500).optional().or(z.literal("")),
  emergency_contact_name: z.string().max(150).optional().or(z.literal("")),
  emergency_contact_phone: z.string().max(30).optional().or(z.literal("")),
  height: z
    .string()
    .optional()
    .or(z.literal(""))
    .refine(
      (v) => !v || (!Number.isNaN(Number(v)) && Number(v) >= 0 && Number(v) <= 999),
      "Enter a valid height"
    ),
  weight: z
    .string()
    .optional()
    .or(z.literal(""))
    .refine(
      (v) => !v || (!Number.isNaN(Number(v)) && Number(v) >= 0 && Number(v) <= 999),
      "Enter a valid weight"
    ),
});

type ProfileFormValues = z.infer<typeof profileSchema>;

const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
const GENDERS = ["female", "male", "non-binary", "prefer not to say"];

function toFormValues(profile: Awaited<ReturnType<typeof profileService.get>>): ProfileFormValues {
  return {
    first_name: profile?.first_name ?? "",
    last_name: profile?.last_name ?? "",
    date_of_birth: profile?.date_of_birth ?? "",
    gender: profile?.gender ?? "",
    blood_group: profile?.blood_group ?? "",
    phone: profile?.phone ?? "",
    address: profile?.address ?? "",
    emergency_contact_name: profile?.emergency_contact_name ?? "",
    emergency_contact_phone: profile?.emergency_contact_phone ?? "",
    height: profile?.height !== null && profile?.height !== undefined ? String(profile.height) : "",
    weight: profile?.weight !== null && profile?.weight !== undefined ? String(profile.weight) : "",
  };
}

export function ProfileForm() {
  const queryClient = useQueryClient();
  const { data: profile, isLoading } = useQuery({
    queryKey: ["health-profile"],
    queryFn: profileService.get,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: toFormValues(null),
  });

  useEffect(() => {
    if (profile !== undefined) {
      reset(toFormValues(profile));
    }
  }, [profile, reset]);

  const mutation = useMutation({
    mutationFn: (values: HealthProfileInput) => profileService.upsert(values),
    onSuccess: (updated) => {
      queryClient.setQueryData(["health-profile"], updated);
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Health profile saved.");
      reset(toFormValues(updated));
    },
    onError: (error) => toast.error(getApiErrorMessage(error, "Unable to save your profile.")),
  });

  const onSubmit = (values: ProfileFormValues) => {
    const payload: HealthProfileInput = {
      first_name: values.first_name,
      last_name: values.last_name,
      date_of_birth: values.date_of_birth || null,
      gender: values.gender || null,
      blood_group: values.blood_group || null,
      phone: values.phone || null,
      address: values.address || null,
      emergency_contact_name: values.emergency_contact_name || null,
      emergency_contact_phone: values.emergency_contact_phone || null,
      height: values.height ? Number(values.height) : null,
      weight: values.weight ? Number(values.weight) : null,
    };
    mutation.mutate(payload);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-6" noValidate>
      <Card>
        <CardHeader>
          <CardTitle>Personal information</CardTitle>
          <CardDescription>This information helps identify you across your records.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-2">
            <Label htmlFor="first_name">First name</Label>
            <Input id="first_name" aria-invalid={Boolean(errors.first_name)} {...register("first_name")} />
            {errors.first_name && <p className="text-sm text-destructive">{errors.first_name.message}</p>}
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="last_name">Last name</Label>
            <Input id="last_name" aria-invalid={Boolean(errors.last_name)} {...register("last_name")} />
            {errors.last_name && <p className="text-sm text-destructive">{errors.last_name.message}</p>}
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="date_of_birth">Date of birth</Label>
            <Input id="date_of_birth" type="date" {...register("date_of_birth")} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="gender">Gender</Label>
            <select
              id="gender"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-ring/30 focus-visible:ring-[3px]"
              {...register("gender")}
            >
              <option value="">Prefer not to answer</option>
              {GENDERS.map((g) => (
                <option key={g} value={g}>
                  {g[0].toUpperCase() + g.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="blood_group">Blood group</Label>
            <select
              id="blood_group"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-ring/30 focus-visible:ring-[3px]"
              {...register("blood_group")}
            >
              <option value="">Unknown</option>
              {BLOOD_GROUPS.map((bg) => (
                <option key={bg} value={bg}>
                  {bg}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="phone">Phone</Label>
            <Input id="phone" type="tel" {...register("phone")} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="height">Height (cm)</Label>
            <Input id="height" type="number" step="0.1" {...register("height")} />
            {errors.height && <p className="text-sm text-destructive">{errors.height.message}</p>}
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="weight">Weight (kg)</Label>
            <Input id="weight" type="number" step="0.1" {...register("weight")} />
            {errors.weight && <p className="text-sm text-destructive">{errors.weight.message}</p>}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Address &amp; emergency contact</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-2 sm:col-span-2">
            <Label htmlFor="address">Address</Label>
            <Textarea id="address" rows={2} {...register("address")} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="emergency_contact_name">Emergency contact name</Label>
            <Input id="emergency_contact_name" {...register("emergency_contact_name")} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="emergency_contact_phone">Emergency contact phone</Label>
            <Input id="emergency_contact_phone" type="tel" {...register("emergency_contact_phone")} />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button type="submit" disabled={mutation.isPending || !isDirty}>
          {mutation.isPending ? <Loader2 className="animate-spin" /> : <Save />}
          Save profile
        </Button>
      </div>
    </form>
  );
}
