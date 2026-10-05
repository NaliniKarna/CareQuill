"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  ShieldCheck,
  FileText,
  CalendarClock,
  Sparkles,
  FolderOpen,
  ClipboardCheck,
  Send,
  AlertTriangle,
  Lock,
  Eye,
  Ban,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth-store";

const FEATURES = [
  {
    icon: ShieldCheck,
    title: "One secure record",
    description:
      "Allergies, conditions, medications, and documents, all in one place you control.",
  },
  {
    icon: Sparkles,
    title: "AI-assisted summaries",
    description:
      "Organize your health information into a clear summary you review and approve yourself.",
  },
  {
    icon: FileText,
    title: "Share on your terms",
    description: "Generate a professional PDF and send exactly what you choose to your doctor.",
  },
  {
    icon: CalendarClock,
    title: "Never miss a visit",
    description: "Keep doctor contacts and appointments organized with reminders.",
  },
];

const HOW_IT_WORKS = [
  {
    icon: FolderOpen,
    title: "Organize your records",
    description:
      "Add your conditions, allergies, medications, doctor contacts, and upload medical documents as you go.",
  },
  {
    icon: Sparkles,
    title: "AI helps summarize",
    description:
      "AI reads your organized health data and drafts a clear, concise summary and extracts details from documents you upload.",
  },
  {
    icon: ClipboardCheck,
    title: "Review and approve",
    description:
      "Nothing AI extracts or drafts becomes part of your verified record until you review it and confirm it's accurate.",
  },
  {
    icon: Send,
    title: "Share with your doctor",
    description:
      "Choose exactly what to include, preview it, then email a professional report to your doctor when you're ready.",
  },
];

const PRIVACY_POINTS = [
  {
    icon: Lock,
    title: "You control your data",
    description:
      "Your health information belongs to you. You decide what's stored, what's included in a report, and who it's shared with.",
  },
  {
    icon: Eye,
    title: "AI and OCR results require review",
    description:
      "Anything AI or OCR extracts from your documents is a suggestion only. It never silently becomes part of your verified record.",
  },
  {
    icon: FileText,
    title: "Original documents are preserved",
    description: "Uploaded medical documents are stored securely and kept exactly as you provided them.",
  },
  {
    icon: Ban,
    title: "Your data is never sold",
    description: "MedQueue AI does not sell or share your health information with third parties for advertising or any other purpose.",
  },
];

export default function HomePage() {
  const router = useRouter();
  const { accessToken, user, hasHydrated } = useAuthStore();

  useEffect(() => {
    if (hasHydrated && accessToken && user) {
      router.replace("/dashboard");
    }
  }, [hasHydrated, accessToken, user, router]);

  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-lg font-semibold tracking-tight">MedQueue AI</span>
          <nav className="flex items-center gap-3">
            <Button asChild variant="ghost">
              <Link href="/login">Log in</Link>
            </Button>
            <Button asChild>
              <Link href="/register">Get started</Link>
            </Button>
          </nav>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-20 px-6 py-16">
        {/* Hero */}
        <section className="flex flex-col items-start gap-6">
          <span className="rounded-full bg-accent px-3 py-1 text-sm font-medium text-accent-foreground">
            Designed with privacy and security principles appropriate for handling
            sensitive health information
          </span>
          <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
            Your health history, intelligently organized for every consultation.
          </h1>
          <p className="max-w-xl text-lg text-muted-foreground">
            MedQueue AI helps you keep your health profile, medications, documents, and
            doctor contacts in one secure place, with AI assistance you always review
            before it&apos;s shared.
          </p>
          <div className="flex gap-3">
            <Button asChild size="lg">
              <Link href="/register">Create your account</Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/login">I already have an account</Link>
            </Button>
          </div>
        </section>

        {/* Problem */}
        <section className="flex flex-col gap-6">
          <div className="flex items-start gap-4 rounded-xl border border-border bg-card p-6 sm:items-center">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-warning/10 text-warning-foreground">
              <AlertTriangle className="size-5" />
            </div>
            <div>
              <h2 className="text-xl font-semibold tracking-tight">
                Your health history shouldn&apos;t live in scattered paper folders
              </h2>
              <p className="mt-2 text-muted-foreground">
                Prescriptions in a drawer, lab reports in an email, allergies you have to
                remember on the spot. When it matters most -- at a new doctor&apos;s office, in
                an emergency, or during a routine visit -- important details get left out
                simply because they weren&apos;t at hand.
              </p>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((feature) => (
            <div
              key={feature.title}
              className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5"
            >
              <feature.icon className="size-6 text-primary" />
              <h3 className="font-medium">{feature.title}</h3>
              <p className="text-sm text-muted-foreground">{feature.description}</p>
            </div>
          ))}
        </section>

        {/* How it works */}
        <section className="flex flex-col gap-8">
          <div className="flex flex-col gap-2 text-center">
            <h2 className="text-2xl font-semibold tracking-tight">How it works</h2>
            <p className="text-muted-foreground">From scattered records to a report your doctor can use.</p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {HOW_IT_WORKS.map((step, index) => (
              <div key={step.title} className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5">
                <div className="flex items-center gap-3">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                    {index + 1}
                  </span>
                  <step.icon className="size-5 text-primary" />
                </div>
                <h3 className="font-medium">{step.title}</h3>
                <p className="text-sm text-muted-foreground">{step.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* AI Assistance */}
        <section className="flex flex-col gap-4 rounded-xl border border-border bg-card p-6 sm:flex-row sm:items-start">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent text-accent-foreground">
            <Sparkles className="size-5" />
          </div>
          <div className="flex flex-col gap-2">
            <h2 className="text-xl font-semibold tracking-tight">AI that assists, never decides</h2>
            <p className="text-muted-foreground">
              MedQueue AI uses AI to help organize and summarize the health information you
              provide -- turning your records into a clear summary and pulling details out of
              documents you upload. It never diagnoses conditions, prescribes treatment, or
              acts on your behalf. Every AI-generated summary and every OCR-extracted detail
              is shown to you for review, and you can edit it before you confirm it or share
              it with anyone. Nothing AI produces becomes part of your verified health record
              without your explicit approval.
            </p>
          </div>
        </section>

        {/* Privacy & Security */}
        <section className="flex flex-col gap-8">
          <div className="flex flex-col gap-2 text-center">
            <h2 className="text-2xl font-semibold tracking-tight">Privacy &amp; security</h2>
            <p className="text-muted-foreground">Built around one rule: you stay in control of your data.</p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2">
            {PRIVACY_POINTS.map((point) => (
              <div key={point.title} className="flex gap-4 rounded-xl border border-border bg-card p-5">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent text-accent-foreground">
                  <point.icon className="size-5" />
                </div>
                <div>
                  <h3 className="font-medium">{point.title}</h3>
                  <p className="text-sm text-muted-foreground">{point.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-border bg-muted/40 p-6 text-sm text-muted-foreground">
          MedQueue AI is an organizational and communication assistant. It does not
          diagnose conditions, prescribe treatment, or replace professional medical
          advice. Always consult a qualified healthcare provider for medical decisions.
        </section>

        {/* Call to action */}
        <section className="flex flex-col items-center gap-4 rounded-xl border border-border bg-card px-6 py-12 text-center">
          <h2 className="text-2xl font-semibold tracking-tight">
            Bring every consultation up to speed
          </h2>
          <p className="max-w-md text-muted-foreground">
            Create your free account and start organizing your health records today.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Button asChild size="lg">
              <Link href="/register">Create your account</Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/login">I already have an account</Link>
            </Button>
          </div>
        </section>
      </main>

      <footer className="border-t border-border px-6 py-6 text-center text-sm text-muted-foreground">
        &copy; {new Date().getFullYear()} MedQueue AI. All rights reserved.
      </footer>
    </div>
  );
}
