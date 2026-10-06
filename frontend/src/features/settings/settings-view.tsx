"use client";

import { useMutation } from "@tanstack/react-query";
import { LogOut, Mail, ShieldCheck, ShieldQuestion } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/shared/page-states";
import { useAuth } from "@/hooks/use-auth";
import { authService } from "@/services/auth-service";
import { getApiErrorMessage } from "@/lib/api-client";

import { ChangePasswordForm } from "./change-password-form";
import { NotificationPreferencesForm } from "./notification-preferences-form";
import { PrivacySettingsForm } from "./privacy-settings-form";
import { YourDataCard } from "./your-data-card";

export function SettingsView() {
  const { user, logout } = useAuth();

  const resetMutation = useMutation({
    mutationFn: (email: string) => authService.forgotPassword(email),
    onSuccess: () => {
      toast.success("If that email is registered, a password reset link has been sent.");
    },
    onError: (error) =>
      toast.error(getApiErrorMessage(error, "Unable to send the password reset email right now.")),
  });

  if (!user) {
    return null;
  }

  const memberSince = new Date(user.created_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Settings" description="Manage your account." />

      <Tabs defaultValue="account">
        <TabsList className="h-auto flex-wrap">
          <TabsTrigger value="account">Account</TabsTrigger>
          <TabsTrigger value="password">Password</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="privacy">Privacy</TabsTrigger>
          <TabsTrigger value="data">Your data</TabsTrigger>
          <TabsTrigger value="logout">Logout</TabsTrigger>
        </TabsList>

        <TabsContent value="account" className="pt-4">
          <Card>
            <CardHeader>
              <CardTitle>Account</CardTitle>
              <CardDescription>Your MedQueue AI account details.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <Mail className="size-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">{user.email}</p>
                  <p className="text-xs text-muted-foreground">Member since {memberSince}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {user.is_verified ? (
                  <ShieldCheck className="size-4 text-success" />
                ) : (
                  <ShieldQuestion className="size-4 text-warning" />
                )}
                <div className="flex items-center gap-2">
                  <span className="text-sm">Email verification</span>
                  <Badge variant={user.is_verified ? "success" : "warning"}>
                    {user.is_verified ? "Verified" : "Not verified"}
                  </Badge>
                </div>
              </div>
              <Separator />
              <div className="flex flex-col gap-2">
                <p className="text-sm font-medium">Forgot your password?</p>
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
        </TabsContent>

        <TabsContent value="password" className="pt-4">
          <ChangePasswordForm />
        </TabsContent>

        <TabsContent value="notifications" className="pt-4">
          <NotificationPreferencesForm />
        </TabsContent>

        <TabsContent value="privacy" className="pt-4">
          <PrivacySettingsForm />
        </TabsContent>

        <TabsContent value="data" className="pt-4">
          <YourDataCard />
        </TabsContent>

        <TabsContent value="logout" className="pt-4">
          <Card>
            <CardHeader>
              <CardTitle>Session</CardTitle>
              <CardDescription>Sign out of MedQueue AI on this device.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="destructive" className="self-start" onClick={() => logout()}>
                <LogOut /> Log out
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
