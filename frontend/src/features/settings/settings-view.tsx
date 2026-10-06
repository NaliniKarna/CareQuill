"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import {
  Bell,
  Database,
  Inbox,
  KeyRound,
  LockKeyhole,
  LogOut,
  Mail,
  ShieldCheck,
  ShieldQuestion,
  SlidersHorizontal,
  UserCog,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { PageHeader } from "@/components/shared/page-states";
import { ProfileForm } from "@/features/health-profile/profile-form";
import { useAuth } from "@/hooks/use-auth";
import { authService } from "@/services/auth-service";
import { getApiErrorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";

import { NotificationsView } from "@/features/notifications/notifications-view";

import { ChangePasswordForm } from "./change-password-form";
import { NotificationPreferencesForm } from "./notification-preferences-form";
import { PrivacySettingsForm } from "./privacy-settings-form";
import { YourDataCard } from "./your-data-card";

const SECTIONS = [
  { id: "profile", label: "Health profile", hint: "Personal & emergency details", icon: UserRound },
  { id: "account", label: "Account", hint: "Email & verification", icon: UserCog },
  { id: "password", label: "Password", hint: "Change your password", icon: KeyRound },
  { id: "notifications", label: "Notifications", hint: "Your inbox & preferences", icon: Bell },
  { id: "privacy", label: "Privacy", hint: "AI & data processing", icon: LockKeyhole },
  { id: "data", label: "Your data", hint: "Export or delete", icon: Database },
  { id: "session", label: "Sign out", hint: "End this session", icon: LogOut },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

function isSectionId(value: string | null): value is SectionId {
  return SECTIONS.some((s) => s.id === value);
}

function SectionNav({ active }: { active: SectionId }) {
  return (
    <nav aria-label="Settings sections">
      {/* Phone/tablet: horizontally scrollable pills */}
      <ul className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 lg:hidden">
        {SECTIONS.map((s) => (
          <li key={s.id} className="shrink-0">
            <Link
              href={`/settings?tab=${s.id}`}
              scroll={false}
              aria-current={active === s.id ? "page" : undefined}
              className={cn(
                "flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors",
                active === s.id
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <s.icon className="size-4" />
              {s.label}
            </Link>
          </li>
        ))}
      </ul>

      {/* Desktop: vertical list with a hint under each label */}
      <ul className="hidden flex-col gap-1 lg:flex">
        {SECTIONS.map((s) => (
          <li key={s.id}>
            <Link
              href={`/settings?tab=${s.id}`}
              scroll={false}
              aria-current={active === s.id ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors",
                active === s.id
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <span
                className={cn(
                  "flex size-8 shrink-0 items-center justify-center rounded-md",
                  active === s.id ? "bg-primary text-primary-foreground" : "bg-secondary"
                )}
              >
                <s.icon className="size-4" />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium leading-tight">{s.label}</span>
                <span className="block truncate text-xs font-normal opacity-80">{s.hint}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function AccountSection() {
  const { user } = useAuth();
  const resetMutation = useMutation({
    mutationFn: (email: string) => authService.forgotPassword(email),
    onSuccess: () => {
      toast.success("If that email is registered, a password reset link has been sent.");
    },
    onError: (error) =>
      toast.error(getApiErrorMessage(error, "Unable to send the password reset email right now.")),
  });

  if (!user) return null;

  const memberSince = new Date(user.created_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  const initials = user.email.slice(0, 2).toUpperCase();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Account</CardTitle>
        <CardDescription>Your CareQuill sign-in details.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div className="flex items-center gap-4">
          <div className="flex size-14 shrink-0 items-center justify-center rounded-full bg-accent text-lg font-semibold text-accent-foreground">
            {initials}
          </div>
          <div className="min-w-0">
            <p className="flex items-center gap-2 truncate font-medium">
              <Mail className="size-4 shrink-0 text-muted-foreground" />
              <span className="truncate">{user.email}</span>
            </p>
            <p className="text-sm text-muted-foreground">Member since {memberSince}</p>
          </div>
        </div>

        <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-secondary/40 px-4 py-3">
          <div className="flex items-center gap-3">
            {user.is_verified ? (
              <ShieldCheck className="size-5 text-success" />
            ) : (
              <ShieldQuestion className="size-5 text-warning" />
            )}
            <div>
              <p className="text-sm font-medium">Email verification</p>
              <p className="text-xs text-muted-foreground">
                {user.is_verified
                  ? "Your email address is confirmed."
                  : "Open the verification link in your inbox to confirm your email."}
              </p>
            </div>
          </div>
          <Badge variant={user.is_verified ? "success" : "warning"}>
            {user.is_verified ? "Verified" : "Not verified"}
          </Badge>
        </div>

        <Separator />

        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium">Forgot your password?</p>
          <p className="text-sm text-muted-foreground">
            We will email a link that lets you choose a new one.
          </p>
          <Button
            variant="outline"
            className="self-start"
            disabled={resetMutation.isPending}
            onClick={() => resetMutation.mutate(user.email)}
          >
            Send password reset email
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function SessionSection() {
  const { logout } = useAuth();
  return (
    <Card>
      <CardHeader>
        <CardTitle>Sign out</CardTitle>
        <CardDescription>Sign out of CareQuill on this device.</CardDescription>
      </CardHeader>
      <CardContent>
        <Button variant="destructive" onClick={() => logout()}>
          <LogOut /> Log out
        </Button>
      </CardContent>
    </Card>
  );
}

function NotificationsSection() {
  return (
    <Tabs defaultValue="inbox">
      <TabsList>
        <TabsTrigger value="inbox">
          <Inbox className="size-4" /> Inbox
        </TabsTrigger>
        <TabsTrigger value="preferences">
          <SlidersHorizontal className="size-4" /> Preferences
        </TabsTrigger>
      </TabsList>
      <TabsContent value="inbox" className="flex flex-col gap-3 pt-4">
        <p className="text-sm text-muted-foreground">
          Updates about your AI summaries, documents and shared reports, plus upcoming appointments
          and medication reminders.
        </p>
        <NotificationsView />
      </TabsContent>
      <TabsContent value="preferences" className="pt-4">
        <NotificationPreferencesForm />
      </TabsContent>
    </Tabs>
  );
}

function SectionContent({ id }: { id: SectionId }) {
  switch (id) {
    case "profile":
      return <ProfileForm />;
    case "account":
      return <AccountSection />;
    case "password":
      return <ChangePasswordForm />;
    case "notifications":
      return <NotificationsSection />;
    case "privacy":
      return <PrivacySettingsForm />;
    case "data":
      return <YourDataCard />;
    case "session":
      return <SessionSection />;
  }
}

export function SettingsView() {
  const { user } = useAuth();
  const tab = useSearchParams().get("tab");
  const active: SectionId = isSectionId(tab) ? tab : "profile";
  const current = SECTIONS.find((s) => s.id === active) ?? SECTIONS[0];

  if (!user) return null;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Settings"
        description="Manage your health profile, account, privacy and data in one place."
      />

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[17rem_minmax(0,1fr)] lg:items-start">
        <aside className="min-w-0 lg:sticky lg:top-6">
          <SectionNav active={active} />
        </aside>
        <section aria-labelledby="settings-section-title" className="flex min-w-0 flex-col gap-4">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <current.icon className="size-5" />
            </div>
            <div>
              <h2 id="settings-section-title" className="text-lg font-semibold leading-tight">
                {current.label}
              </h2>
              <p className="text-sm text-muted-foreground">{current.hint}</p>
            </div>
          </div>
          <SectionContent id={active} />
        </section>
      </div>
    </div>
  );
}
