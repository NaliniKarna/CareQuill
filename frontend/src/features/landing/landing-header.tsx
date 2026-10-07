"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";

import { BrandLogo } from "@/components/shared/brand";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useLanguageStore, type Language } from "@/store/language-store";

import type { LandingCopy } from "./i18n";

const LANGUAGES: { code: Language; label: string; name: string }[] = [
  { code: "en", label: "EN", name: "English" },
  { code: "ne", label: "NP", name: "नेपाली" },
];

export function LanguageSwitch({ t, className }: { t: LandingCopy; className?: string }) {
  const { language, setLanguage } = useLanguageStore();
  return (
    <div
      role="group"
      aria-label={t.meta.langLabel}
      className={cn("inline-flex items-center rounded-full border border-border bg-card p-0.5", className)}
    >
      {LANGUAGES.map((l) => (
        <button
          key={l.code}
          type="button"
          lang={l.code}
          title={l.name}
          aria-pressed={language === l.code}
          onClick={() => setLanguage(l.code)}
          className={cn(
            "rounded-full px-3 py-1 text-xs font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
            language === l.code
              ? "bg-primary text-primary-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}

export function LandingHeader({ t }: { t: LandingCopy }) {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const links = [
    { href: "#home", label: t.nav.home },
    { href: "#features", label: t.nav.features },
    { href: "#how-it-works", label: t.nav.howItWorks },
    { href: "#faq", label: t.nav.faq },
    { href: "#contact", label: t.nav.contact },
  ];

  return (
    <header
      className={cn(
        "sticky top-0 z-40 border-b transition-colors",
        scrolled || open
          ? "border-border bg-background/90 backdrop-blur"
          : "border-transparent bg-background/60 backdrop-blur-sm"
      )}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="#home" aria-label="CareQuill" onClick={() => setOpen(false)}>
          <BrandLogo markClassName="h-9" />
        </Link>

        <nav className="hidden items-center gap-1 lg:flex" aria-label="Main">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-primary"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <LanguageSwitch t={t} />
          <div className="hidden items-center gap-2 sm:flex">
            <Button asChild variant="ghost">
              <Link href="/login">{t.nav.login}</Link>
            </Button>
            <Button asChild>
              <Link href="/register">{t.nav.signup}</Link>
            </Button>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-expanded={open}
            aria-controls="landing-mobile-nav"
            aria-label={open ? t.nav.closeMenu : t.nav.openMenu}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X /> : <Menu />}
          </Button>
        </div>
      </div>

      {open && (
        <nav
          id="landing-mobile-nav"
          aria-label="Main"
          className="border-t border-border bg-background px-4 pb-4 lg:hidden"
        >
          <ul className="flex flex-col py-2">
            {links.map((l) => (
              <li key={l.href}>
                <a
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="block rounded-md px-3 py-2.5 text-sm font-medium text-foreground hover:bg-accent"
                >
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
          <div className="grid grid-cols-2 gap-2 sm:hidden">
            <Button asChild variant="outline">
              <Link href="/login">{t.nav.login}</Link>
            </Button>
            <Button asChild>
              <Link href="/register">{t.nav.signup}</Link>
            </Button>
          </div>
        </nav>
      )}
    </header>
  );
}
