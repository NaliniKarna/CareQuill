import { ProfileForm } from "@/features/health-profile/profile-form";

export default function ProfilePage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Health profile</h1>
        <p className="text-muted-foreground">
          Keep your personal and emergency information up to date.
        </p>
      </div>
      <ProfileForm />
    </div>
  );
}
