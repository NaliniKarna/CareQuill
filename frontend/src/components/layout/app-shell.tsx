"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileStack,
  CalendarClock,
  Sparkles,
  Settings,
  LogOut,
  NotebookPen,
  Menu,
} from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { BrandLogo } from "@/components/shared/brand";
import { NotificationBell } from "@/features/notifications/notification-bell";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, enabled: true },
  { href: "/medical-records", label: "Medical Records", icon: FileStack, enabled: true },
  { href: "/appointments", label: "Appointments", icon: CalendarClock, enabled: true },
  { href: "/record-summary", label: "Record Summary", icon: Sparkles, enabled: true },
  { href: "/journal", label: "Journal", icon: NotebookPen, enabled: true },
  { href: "/settings", label: "Settings", icon: Settings, enabled: true },
];

function NavLinks({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <>
      {NAV_ITEMS.map((item) => {
        const isActive = pathname === item.href;
        const content = (
          <span
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              item.enabled
                ? isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-foreground hover:bg-accent hover:text-accent-foreground"
                : "cursor-not-allowed text-muted-foreground/60"
            )}
          >
            <item.icon className="size-4" />
            {item.label}
            {!item.enabled && (
              <Badge variant="secondary" className="ml-auto text-[10px]">
                Soon
              </Badge>
            )}
          </span>
        );
        return item.enabled ? (
          <Link key={item.href} href={item.href} onClick={onNavigate}>
            {content}
          </Link>
        ) : (
          <span key={item.href} aria-disabled>
            {content}
          </span>
        );
      })}
    </>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const initials = user?.email?.slice(0, 2).toUpperCase() ?? "CQ";

  return (
    <div className="flex min-h-svh">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-card px-4 py-6 md:flex">
        <div className="mb-8 flex items-center justify-between px-2">
          <Link href="/dashboard" aria-label="CareQuill home">
            <BrandLogo markClassName="h-9" />
          </Link>
          <NotificationBell />
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          <NavLinks pathname={pathname} />
        </nav>
        <div className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
          <Avatar className="size-8">
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{user?.email}</p>
            <p className="text-xs text-muted-foreground">Patient account</p>
          </div>
          <Button variant="ghost" size="icon" onClick={() => logout()} aria-label="Log out">
            <LogOut className="size-4" />
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border px-4 py-3 md:hidden">
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              aria-label="Open menu"
              onClick={() => setMobileNavOpen(true)}
            >
              <Menu className="size-5" />
            </Button>
            <BrandLogo markClassName="h-7" textClassName="text-base" />
          </div>
          <div className="flex items-center gap-1">
            <NotificationBell />
            <Button variant="ghost" size="icon" onClick={() => logout()} aria-label="Log out">
              <LogOut className="size-4" />
            </Button>
          </div>
        </header>
        <main className="flex-1 px-4 py-6 md:px-8 md:py-8">{children}</main>
      </div>

      <Dialog open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <DialogContent
          showCloseButton
          className="top-0 left-0 h-full max-h-svh w-72 max-w-[85vw] translate-x-0 translate-y-0 rounded-none border-0 border-r border-border p-4"
        >
          <DialogHeader>
            <DialogTitle>Menu</DialogTitle>
          </DialogHeader>
          <nav className="flex flex-1 flex-col gap-1 overflow-y-auto">
            <NavLinks pathname={pathname} onNavigate={() => setMobileNavOpen(false)} />
          </nav>
        </DialogContent>
      </Dialog>
    </div>
  );
}
